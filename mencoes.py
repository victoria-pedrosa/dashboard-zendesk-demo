"""
mencoes.py
Conta @menções nos canais #conectado e #operação-atendimento,
agrupa por setor e publica no App Home do bot.
"""
import json
import logging
import os
import re
import time
import unicodedata
from datetime import date, datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import SLACK_BOT_TOKEN

log = logging.getLogger(__name__)
client = WebClient(token=SLACK_BOT_TOKEN, timeout=30)

# Caminhos
DATA_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
USUARIOS_FILE = os.path.join(DATA_DIR, "mencoes_users.json")

# ── Canais ───────────────────────────────────────────────────
CH_CONECTADO = "ID_SLACK_EXEMPLO"
CH_OP_ATEND  = "ID_SLACK_EXEMPLO"

IGNORAR_UIDS = {"ID_SLACK_EXEMPLO", "USLACKBOT"}

# ── Emojis por setor ─────────────────────────────────────────
EMOJIS_SETOR = {
    "Fiscal":        ":red_circle:",
    "Balanço":       ":large_blue_circle:",
    "Folha":         ":large_green_circle:",
    "IA":            ":large_purple_circle:",
    "Atendimento":   ":large_orange_circle:",
    "Comercial":     ":large_yellow_circle:",
    "Gestão":        ":white_circle:",
    "Procuradoria":  ":scales:",
    "Suporte":       ":wrench:",
    "Financeiro":    ":moneybag:",
    "Líderes":       ":star:",
    "Estagiários":   ":mortar_board:",
}

EMOJI_VERDE = ":large_green_square:"
EMOJI_VAZIO = ":white_large_square:"

# ── Prefixos de nome externo → setor ─────────────────────────
PREFIX_MAP = {
    # Abreviações passadas pela Victoria
    "Ate":          {"sectors": ["Atendimento"],            "role": "Atendimento"},
    "Pro":          {"sectors": ["Procuradoria"],           "role": "Procuradoria"},
    "Sup":          {"sectors": ["Suporte"],                "role": "Suporte"},
    "Fin":          {"sectors": ["Financeiro"],             "role": "Financeiro"},
    "Fol":          {"sectors": ["Folha"],                  "role": "Folha"},
    "Fis":          {"sectors": ["Fiscal"],                 "role": "Fiscal"},
    "Bal":          {"sectors": ["Balanço"],                "role": "Balanço"},
    "Fol/Fis":      {"sectors": ["Folha", "Fiscal"],        "role": "Folha/Fiscal"},
    "Ate e Bal":    {"sectors": ["Atendimento"],            "role": "Atendimento"},
    "Ate/Bal":      {"sectors": ["Atendimento"],            "role": "Atendimento"},
    "Prime":        {"sectors": ["Fiscal"],                 "role": "Prime Fiscal"},
    "Prime/Fis":    {"sectors": ["Fiscal"],                 "role": "Prime Fiscal"},
    "Prime/Bal":    {"sectors": ["Balanço"],                "role": "Prime Balanço"},
    "Prime/Fol":    {"sectors": ["Folha"],                  "role": "Prime Folha"},
    "Estag":        {"sectors": ["Estagiários"],            "role": "Estagiário"},
    # Palavras completas (Slack pode usar nome completo do setor)
    "Atendimento":  {"sectors": ["Atendimento"],            "role": "Atendimento"},
    "Fiscal":       {"sectors": ["Fiscal"],                 "role": "Fiscal"},
    "Folha":        {"sectors": ["Folha"],                  "role": "Folha"},
    "Balanco":      {"sectors": ["Balanço"],                "role": "Balanço"},
    "Balança":      {"sectors": ["Balanço"],                "role": "Balanço"},
    "Financeiro":   {"sectors": ["Financeiro"],             "role": "Financeiro"},
    "Suporte":      {"sectors": ["Suporte"],                "role": "Suporte"},
    "Procuradoria": {"sectors": ["Procuradoria"],           "role": "Procuradoria"},
    "Comercial":    {"sectors": ["Comercial"],              "role": "Comercial"},
    "Gestao":       {"sectors": ["Gestão"],                 "role": "Gestão"},
}

_PREFIX_RE = re.compile(r'^(.+?)\s*[-–]\s*(.+)$')


def _normalizar(s: str) -> str:
    """Lowercase sem acentos para comparação tolerante."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.lower())
        if unicodedata.category(c) != 'Mn'
    )

_PREFIX_NORM = {_normalizar(k): v for k, v in PREFIX_MAP.items()}


def _parse_prefix(display_name: str) -> dict | None:
    """
    Tenta mapear um display_name com prefixo de setor.
    Suporta:
      - "Ate - Maria"   (traço com espaço)
      - "Fin-Colaborador 34"    (traço sem espaço)
      - "Fol/Fis - Ana" (barra no prefixo, traço como separador)
      - "Estag/João"    (barra como separador, sem traço)
    """
    def _lookup(prefix_raw: str, name: str) -> dict | None:
        if prefix_raw in PREFIX_MAP:
            info = PREFIX_MAP[prefix_raw]
            return {"name": name, "sectors": info["sectors"],
                    "role": info["role"], "sector": info["sectors"][0]}
        info = _PREFIX_NORM.get(_normalizar(prefix_raw))
        if info:
            return {"name": name, "sectors": info["sectors"],
                    "role": info["role"], "sector": info["sectors"][0]}
        return None

    # 1. Tentar separador traço primeiro (cobre "Fol/Fis - Ana", "Ate - Maria", "Fin-Colaborador 34")
    m = _PREFIX_RE.match(display_name)
    if m:
        result = _lookup(m.group(1).strip(), m.group(2).strip())
        if result:
            return result

    # 2. Fallback: barra como separador (cobre "Estag/João", "Fol/Nome")
    #    só tenta se não houver traço já tratado acima
    if '/' in display_name and '-' not in display_name:
        parts = display_name.split('/', 1)
        result = _lookup(parts[0].strip(), parts[1].strip())
        if result:
            return result

    log.debug("Prefixo nao mapeado: %r", display_name)
    return None


# ── Mapeamento interno ────────────────────────────────────────
USER_MAP = {
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 35",          "role": "Fiscal 1",       "sector": "Fiscal",      "sectors": ["Fiscal"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 36",            "role": "Fiscal 2",       "sector": "Fiscal",      "sectors": ["Fiscal"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 13",   "role": "Fiscal 3",       "sector": "Fiscal",      "sectors": ["Fiscal"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 14", "role": "Fiscal 4 & 5",   "sector": "Fiscal",      "sectors": ["Fiscal"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 37",            "role": "Prime Fiscal",   "sector": "Fiscal",      "sectors": ["Fiscal", "Líderes"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 15",     "role": "Líder Fiscal",   "sector": "Fiscal",      "sectors": ["Fiscal", "Líderes"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 38",         "role": "Líder Balanço",  "sector": "Balanço",     "sectors": ["Balanço", "Líderes"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 16",    "role": "Balanço 2",      "sector": "Balanço",     "sectors": ["Balanço"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 64",        "role": "Balanço 3",      "sector": "Balanço",     "sectors": ["Balanço"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 65",         "role": "Time Informe",   "sector": "Balanço",     "sectors": ["Balanço"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 67",            "role": "Prime Balanço",  "sector": "Balanço",     "sectors": ["Balanço"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 17",  "role": "Prime Balanço",  "sector": "Balanço",     "sectors": ["Balanço"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 68",            "role": "Folha 1",        "sector": "Folha",       "sectors": ["Folha"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 63",      "role": "Folha 2",        "sector": "Folha",       "sectors": ["Folha"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 66",           "role": "Folha 3",        "sector": "Folha",       "sectors": ["Folha"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 69",            "role": "Folha 4",        "sector": "Folha",       "sectors": ["Folha"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 39",            "role": "Folha 6",        "sector": "Folha",       "sectors": ["Folha"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 62",      "role": "Líder Folha",    "sector": "Folha",       "sectors": ["Folha", "Líderes"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 18",       "role": "Líder Folha",    "sector": "Folha",       "sectors": ["Folha", "Líderes"]},
    "ID_SLACK_EXEMPLO": {"name": "Victoria Pedrosa", "role": "Líder IA",       "sector": "IA",          "sectors": ["IA"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 4",     "role": "Atendimento",    "sector": "Atendimento", "sectors": ["Atendimento"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 61",     "role": "Atend & Onb",    "sector": "Atendimento", "sectors": ["Atendimento"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 60","role": "Onb & Atend",    "sector": "Atendimento", "sectors": ["Atendimento"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 19", "role": "Líder Atend",    "sector": "Atendimento", "sectors": ["Atendimento", "Líderes"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 20",   "role": "Comercial",      "sector": "Comercial",   "sectors": ["Comercial"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 21",     "role": "Líder Comercial","sector": "Comercial",   "sectors": ["Comercial"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 22",    "role": "Líder Gestão",   "sector": "Gestão",      "sectors": ["Gestão", "Líderes"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 3",  "role": "Líder Gestão",   "sector": "Gestão",      "sectors": ["Gestão", "Líderes"]},
    # Estagiários
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 71", "role": "Estagiário",  "sector": "Estagiários", "sectors": ["Estagiários"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 70",  "role": "Estagiário",  "sector": "Estagiários", "sectors": ["Estagiários"]},
    # Líderes (novos)
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 23",       "role": "Líder Suporte",  "sector": "Suporte",     "sectors": ["Suporte", "Líderes"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 73",  "role": "Líder",          "sector": "Líderes",     "sectors": ["Líderes"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 24",    "role": "Líder Proc.",    "sector": "Procuradoria","sectors": ["Procuradoria", "Líderes"]},
    # Comercial / Gestão / Atendimento / Suporte
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 77",     "role": "Comercial",      "sector": "Comercial",   "sectors": ["Comercial"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 78",      "role": "Gestão",         "sector": "Gestão",      "sectors": ["Gestão"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 25",       "role": "Suporte",        "sector": "Suporte",     "sectors": ["Suporte"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 26",   "role": "Atendimento",    "sector": "Atendimento", "sectors": ["Atendimento"]},
    # Adicionados após identificação automática de não classificados
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 72",   "role": "Fol/Fis",        "sector": "Folha",       "sectors": ["Folha", "Fiscal"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 27",         "role": "Atendimento",    "sector": "Atendimento", "sectors": ["Atendimento"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 80",               "role": "Procuradoria",   "sector": "Procuradoria","sectors": ["Procuradoria"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 74",      "role": "Prime Fiscal",   "sector": "Fiscal",      "sectors": ["Fiscal"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 79",             "role": "Procuradoria",   "sector": "Procuradoria","sectors": ["Procuradoria"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 28",        "role": "Financeiro",     "sector": "Financeiro",  "sectors": ["Financeiro"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 76",       "role": "Atendimento",    "sector": "Atendimento", "sectors": ["Atendimento"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 29",   "role": "Atendimento",    "sector": "Atendimento", "sectors": ["Atendimento"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 30",         "role": "Folha",          "sector": "Folha",       "sectors": ["Folha"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 31",     "role": "Suporte",        "sector": "Suporte",     "sectors": ["Suporte"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 32",     "role": "Suporte",        "sector": "Suporte",     "sectors": ["Suporte"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 75",      "role": "Folha",          "sector": "Folha",       "sectors": ["Folha"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 40",              "role": "Estagiária",     "sector": "Estagiários", "sectors": ["Estagiários"]},
    "ID_SLACK_EXEMPLO": {"name": "Colaborador 33",     "role": "Estagiária",     "sector": "Estagiários", "sectors": ["Estagiários"]},
}

MENTION_RE = re.compile(r"<@([A-Z0-9]+)(?:\|[^>]+)?>")
_USER_NAME_CACHE: dict = {}


def _resolver_externo(uid: str) -> dict:
    """Resolve UID desconhecido SEM chamada de API — usa apenas o cache e prefixo do display_name."""
    if uid in _USER_NAME_CACHE:
        return _USER_NAME_CACHE[uid]
    # Não faz users_info — evita travamento por rate limit em lotes grandes
    result = {"name": uid, "role": "Externo", "sector": "Outros", "sectors": ["Outros"]}
    log.warning("SEM CLASSIFICACAO uid=%s", uid)
    _USER_NAME_CACHE[uid] = result
    return result


def _extrair_mencoes(text: str) -> list:
    return MENTION_RE.findall(text or "")


MAX_THREADS_POR_CANAL = 50  # limite para evitar travamento


def _buscar_canal(ch_id: str, oldest: float, latest: float) -> tuple:
    counts = {}
    threads = []
    cursor = None
    while True:
        try:
            kwargs = dict(channel=ch_id, oldest=str(oldest), latest=str(latest), limit=200)
            if cursor:
                kwargs["cursor"] = cursor
            resp = client.conversations_history(**kwargs)
        except Exception as e:
            log.error("conversations_history erro [%s]: %s", ch_id, e)
            break
        for msg in resp.get("messages", []):
            for uid in _extrair_mencoes(msg.get("text", "")):
                if uid in IGNORAR_UIDS:
                    continue
                counts.setdefault(uid, 0)
                counts[uid] += 1
            if (msg.get("reply_count") or 0) > 0:
                threads.append(msg["ts"])
        if not resp.get("has_more"):
            break
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.5)

    # Limita threads para evitar travamento em canais muito ativos
    threads_a_buscar = threads[:MAX_THREADS_POR_CANAL]
    if len(threads) > MAX_THREADS_POR_CANAL:
        log.warning("Canal %s: %d threads, buscando só as %d primeiras",
                    ch_id, len(threads), MAX_THREADS_POR_CANAL)

    for ts in threads_a_buscar:
        try:
            tresp = client.conversations_replies(channel=ch_id, ts=ts, limit=100)
            for msg in tresp.get("messages", [])[1:]:
                for uid in _extrair_mencoes(msg.get("text", "")):
                    if uid in IGNORAR_UIDS:
                        continue
                    counts.setdefault(uid, 0)
                    counts[uid] += 1
        except Exception as e:
            log.warning("conversations_replies erro [%s]: %s", ch_id, e)
        time.sleep(0.3)
    return counts, threads


def _carregar_overrides() -> dict:
    """Lê mencoes_overrides.json ao vivo — sem cache, sem restart."""
    path = os.path.join(DATA_DIR, "mencoes_overrides.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def buscar_mencoes(data_inicio: date, data_fim: date) -> dict:
    oldest = datetime(data_inicio.year, data_inicio.month, data_inicio.day).timestamp()
    latest = datetime(data_fim.year, data_fim.month, data_fim.day, 23, 59, 59).timestamp()
    log.info("Buscando menções %s → %s", data_inicio, data_fim)
    overrides = _carregar_overrides()
    counts_con, thr_con = _buscar_canal(CH_CONECTADO, oldest, latest)
    counts_at,  thr_at  = _buscar_canal(CH_OP_ATEND,  oldest, latest)
    log.info("#conectado: %d   #op-atend: %d", len(counts_con), len(counts_at))
    combined = {}
    for uid in (set(counts_con) | set(counts_at)) - IGNORAR_UIDS:
        u = overrides.get(uid) or USER_MAP.get(uid) or _resolver_externo(uid)
        c = counts_con.get(uid, 0)
        a = counts_at.get(uid, 0)
        combined[uid] = {**u, "con": c, "at": a, "total": c + a}
    return combined


def _agrupar_por_setor(counts: dict) -> dict:
    por_setor = {}
    for d in counts.values():
        for s in d.get("sectors", [d.get("sector", "Outros")]):
            por_setor.setdefault(s, []).append(d)
    return por_setor


def _barra(valor, maximo, tamanho=6) -> str:
    p = round((valor / maximo) * tamanho) if maximo else 0
    return EMOJI_VERDE * p + EMOJI_VAZIO * (tamanho - p)


def _tabela_setor(pessoas: list) -> str:
    """Tabela monospace com alinhamento de colunas."""
    header = f"{'#':>2}  {'Nome':<20}  {'Total':>5}  {'Con':>4}  {'At':>3}"
    sep    = "-" * 42
    linhas = [header, sep]
    for i, p in enumerate(pessoas, 1):
        nome = p["name"][:20]
        linhas.append(
            f"{i:>2}  {nome:<20}  {p['total']:>5}  {p['con']:>4}  {p.get('at', 0):>3}"
        )
    return "```\n" + "\n".join(linhas) + "\n```"


def _opcoes_setores() -> list:
    opts = [{"text": {"type": "plain_text", "text": "Todos os setores"}, "value": "todos"}]
    for setor in EMOJIS_SETOR:
        opts.append({"text": {"type": "plain_text", "text": setor}, "value": setor})
    return opts


# ── Block Kit ────────────────────────────────────────────────

def gerar_blocos_mencoes(counts: dict, data_inicio: date, data_fim: date,
                          setor_filtro: str = "todos") -> list:
    if not counts:
        return [{"type": "section",
                 "text": {"type": "mrkdwn",
                          "text": ":warning: Nenhuma menção encontrada no período."}}]

    por_setor    = _agrupar_por_setor(counts)
    setor_totais = {s: sum(p["total"] for p in ps) for s, ps in por_setor.items()}
    setor_order  = sorted(setor_totais, key=lambda s: -setor_totais[s])
    max_setor    = max(setor_totais.values(), default=1)

    setores_a_mostrar = (
        [setor_filtro] if (setor_filtro != "todos" and setor_filtro in por_setor)
        else setor_order
    )

    hoje_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    ini_str  = data_inicio.strftime("%d/%m/%Y")
    fim_str  = data_fim.strftime("%d/%m/%Y")
    ini_iso  = data_inicio.isoformat()
    fim_iso  = data_fim.isoformat()

    blocos = [
        {"type": "header",
         "text": {"type": "plain_text", "text": "📊 Menções Slack — Exemplo", "emoji": True}},
        {"type": "section",
         "text": {"type": "mrkdwn",
                  "text": f":clock1: *Período:* {ini_str} → {fim_str}   |   _atualizado {hoje_str}_"}},
        {"type": "divider"},
    ]

    # ── Atalhos de período ────────────────────────────────────
    blocos.append({
        "type": "actions",
        "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Hoje", "emoji": True},
             "action_id": "mencoes_periodo_hoje"},
            {"type": "button", "text": {"type": "plain_text", "text": "Esta semana", "emoji": True},
             "action_id": "mencoes_periodo_semana"},
            {"type": "button", "text": {"type": "plain_text", "text": "Este mês", "emoji": True},
             "action_id": "mencoes_periodo_mes"},
        ]
    })

    # ── Datepickers + Atualizar + PDF ─────────────────────────
    blocos.append({
        "type": "actions",
        "elements": [
            {"type": "datepicker", "action_id": "mencoes_data_inicio",
             "initial_date": ini_iso, "placeholder": {"type": "plain_text", "text": "Data início"}},
            {"type": "datepicker", "action_id": "mencoes_data_fim",
             "initial_date": fim_iso, "placeholder": {"type": "plain_text", "text": "Data fim"}},
            {"type": "button", "text": {"type": "plain_text", "text": "🔄 Atualizar", "emoji": True},
             "style": "primary", "action_id": "atualizar_mencoes"},
            {"type": "button", "text": {"type": "plain_text", "text": "📄 Gerar PDF", "emoji": True},
             "action_id": "mencoes_gerar_pdf", "value": f"{ini_iso}|{fim_iso}"},
        ]
    })

    # ── Filtro por setor ──────────────────────────────────────
    filtro_label = setor_filtro if setor_filtro != "todos" else "Todos os setores"
    blocos.append({
        "type": "actions",
        "elements": [{
            "type": "static_select",
            "action_id": "mencoes_filtro_setor",
            "placeholder": {"type": "plain_text", "text": "Filtrar por setor"},
            "initial_option": {"text": {"type": "plain_text", "text": filtro_label},
                               "value": setor_filtro},
            "options": _opcoes_setores(),
        }]
    })

    blocos.append({"type": "divider"})

    # ── Visão geral em barras (sempre mostra todos) ───────────
    blocos.append({"type": "header",
                   "text": {"type": "plain_text", "text": "🏆 Visão Geral por Setor", "emoji": True}})
    linhas_setor = []
    for s in setor_order:
        if s == "Outros":
            continue
        emoji = EMOJIS_SETOR.get(s, ":white_circle:")
        barra = _barra(setor_totais[s], max_setor)
        linhas_setor.append(f"{emoji} {barra}  *{s}* — {setor_totais[s]}")
    blocos.append({"type": "section",
                   "text": {"type": "mrkdwn", "text": "\n".join(linhas_setor)}})

    blocos.append({"type": "divider"})

    # ── Ranking em tabela (filtrado ou todos) ─────────────────
    titulo = f"👤 {setor_filtro}" if setor_filtro != "todos" else "👤 Ranking por Setor"
    blocos.append({"type": "header",
                   "text": {"type": "plain_text", "text": titulo, "emoji": True}})

    for s in setores_a_mostrar:
        if s == "Outros":
            continue
        pessoas = sorted(por_setor.get(s, []), key=lambda p: -p["total"])
        emoji   = EMOJIS_SETOR.get(s, ":white_circle:")
        tabela  = _tabela_setor(pessoas[:10])
        blocos.append({"type": "section",
                       "text": {"type": "mrkdwn",
                                "text": f"{emoji} *{s}*  —  {setor_totais.get(s, 0)} menções"}})
        blocos.append({"type": "section",
                       "text": {"type": "mrkdwn", "text": tabela}})

    # Aviso de não classificados (mostra nome + uid para depuração)
    nao_class_uids = [(uid, d) for uid, d in counts.items() if "Outros" in d.get("sectors", [d.get("sector", "")])]
    if nao_class_uids:
        linhas_nc = [f"• {d['name']} `{uid}`" for uid, d in nao_class_uids]
        aviso = ":warning: *Sem classificacao (me envie os IDs para corrigir):*\n" + "\n".join(linhas_nc)
        blocos.append({"type": "section",
                       "text": {"type": "mrkdwn", "text": aviso}})

    # ── Rodapé ────────────────────────────────────────────────
    blocos.append({"type": "divider"})
    total_geral = sum(d["total"] for d in counts.values())
    blocos.append({"type": "section",
                   "text": {"type": "mrkdwn",
                            "text": (f":bar_chart: *Total:* {total_geral} menções  |  "
                                     f"{len(counts)} pessoas  |  "
                                     f":slack: #conectado + #operação-atendimento")}})

    return blocos


# ── Persistência de usuários ─────────────────────────────────

def registrar_usuario(user_id: str):
    """Salva user_id para auto-refresh."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        users = json.loads(open(USUARIOS_FILE).read()) if os.path.exists(USUARIOS_FILE) else []
        if user_id not in users:
            users.append(user_id)
            with open(USUARIOS_FILE, "w") as f:
                json.dump(users, f)
    except Exception as e:
        log.warning("registrar_usuario: %s", e)


def publicar_para_todos(data_inicio: date = None, data_fim: date = None):
    """Republica o dashboard para todos os usuários registrados."""
    if not os.path.exists(USUARIOS_FILE):
        log.warning("Nenhum usuário registrado para auto-refresh.")
        return
    try:
        users = json.loads(open(USUARIOS_FILE).read())
    except Exception as e:
        log.error("Erro ao ler usuarios: %s", e)
        return
    hoje = date.today()
    di = data_inicio or hoje.replace(day=1)
    df = data_fim or hoje
    log.info("Auto-refresh para %d usuários (%s → %s)", len(users), di, df)
    for uid in users:
        try:
            publicar_mencoes(uid, di, df)
        except Exception as e:
            log.error("Erro ao publicar para %s: %s", uid, e)


# ── Publicar ─────────────────────────────────────────────────

def publicar_mencoes(user_id: str, data_inicio: date = None, data_fim: date = None,
                     setor_filtro: str = "todos"):
    hoje = date.today()
    if data_inicio is None:
        data_inicio = hoje.replace(day=1)
    if data_fim is None:
        data_fim = hoje

    registrar_usuario(user_id)

    try:
        client.chat_postMessage(
            channel=user_id,
            text=":hourglass_flowing_sand: Buscando menções... pode levar até 1 minuto."
        )
    except Exception:
        pass

    try:
        counts = buscar_mencoes(data_inicio, data_fim)
        blocos = gerar_blocos_mencoes(counts, data_inicio, data_fim, setor_filtro)
        client.views_publish(user_id=user_id, view={"type": "home", "blocks": blocos})
        client.chat_postMessage(
            channel=user_id,
            text=":white_check_mark: Dashboard atualizado! Abra a aba *Home* do bot."
        )
        log.info("Menções publicadas para %s (%d pessoas)", user_id, len(counts))
    except SlackApiError as e:
        log.error("Erro ao publicar menções: %s", e)
        try:
            client.chat_postMessage(channel=user_id,
                                    text=f":x: Erro: {e.response.get('error')}")
        except Exception:
            pass


# ── CLI ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    hoje = date.today()
    inicio = hoje.replace(day=1)
    if len(sys.argv) >= 3:
        try:
            inicio = date.fromisoformat(sys.argv[1])
            hoje   = date.fromisoformat(sys.argv[2])
        except ValueError:
            print("Uso: python mencoes.py AAAA-MM-DD AAAA-MM-DD")
            sys.exit(1)

    print(f"Buscando menções de {inicio} até {hoje}...")
    resultado = buscar_mencoes(inicio, hoje)

    if not resultado:
        print("Nenhuma menção encontrada.")
        sys.exit(0)

    por_setor = _agrupar_por_setor(resultado)
    print(f"\n{'='*50}")
    print(f"  MENÇÕES SLACK  |  {inicio} → {hoje}")
    print(f"{'='*50}")
    for setor in sorted(por_setor, key=lambda s: -sum(p["total"] for p in por_setor[s])):
        pessoas = sorted(por_setor[setor], key=lambda p: -p["total"])
        print(f"\n{setor} ({sum(p['total'] for p in pessoas)} menções)")
        for p in pessoas:
            print(f"  {p['name']:<25} {p['total']:>4}  (con={p['con']}, at={p.get('at',0)})")
