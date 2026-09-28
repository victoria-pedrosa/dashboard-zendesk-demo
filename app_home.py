"""
app_home.py
Publica o dashboard de metricas na aba Home do bot @Dashboard Zendesk no Slack.
"""
import logging
from datetime import date, datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import SLACK_BOT_TOKEN
from metrics import calcular_metricas

log = logging.getLogger(__name__)
client = WebClient(token=SLACK_BOT_TOKEN)

EMOJI_VERDE = ":large_green_square:"
EMOJI_VAZIO = ":white_large_square:"
BLOCO_MAX_CHARS = 2800  # margem de segurança abaixo do limite 3000 do Slack


def _bloco_divider():
    return {"type": "divider"}

def _bloco_header(texto):
    return {"type": "header", "text": {"type": "plain_text", "text": texto, "emoji": True}}

def _bloco_section(texto):
    # Garante que nunca excede o limite do Slack
    return {"type": "section", "text": {"type": "mrkdwn", "text": texto[:BLOCO_MAX_CHARS]}}

def _bloco_dois_campos(esq, dir_):
    return {
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": esq[:500]},
            {"type": "mrkdwn", "text": dir_[:500]}
        ]
    }

def _barra_grafico(valor, maximo, tamanho=6):
    if maximo == 0:
        preenchido = 0
    else:
        preenchido = round((valor / maximo) * tamanho)
    return EMOJI_VERDE * preenchido + EMOJI_VAZIO * (tamanho - preenchido)

def _grafico_setor(por_setor, max_itens=8):
    if not por_setor:
        return "Sem dados"
    maximo = max(por_setor.values())
    linhas = []
    for setor, qtd in list(por_setor.items())[:max_itens]:
        barra = _barra_grafico(qtd, maximo)
        linhas.append(f"{barra}  *{setor}* — {qtd}")
    return "\n".join(linhas)

def _calcular_tempo_aberto(timestamp_str):
    try:
        ts = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        delta = datetime.now() - ts
        horas = int(delta.total_seconds() // 3600)
        minutos = int((delta.total_seconds() % 3600) // 60)
        if horas > 0:
            return f"{horas}h{minutos:02d}min"
        return f"{minutos}min"
    except Exception:
        return "?"

def _blocos_tickets_atrasados(tickets_atrasados):
    """
    Gera lista de blocos para os tickets atrasados.
    Divide em multiplos blocos de ~20 tickets para nao estourar o limite de 3000 chars.
    """
    total = len(tickets_atrasados)
    if total == 0:
        return [_bloco_section(":white_check_mark: Nenhum ticket em atraso no momento.")]

    blocos = []
    lote = []
    for row in tickets_atrasados:
        numero, colab, setor, cliente, ts = row
        tempo = _calcular_tempo_aberto(ts)
        lote.append(f":red_circle: *#{numero}* — {colab} | {cliente} | _{tempo}_")

        # A cada 20 linhas, fecha o bloco
        if len(lote) == 20:
            blocos.append(_bloco_section("\n".join(lote)))
            lote = []

    if lote:
        blocos.append(_bloco_section("\n".join(lote)))

    if total > 0:
        blocos.append(_bloco_section(
            f"_Lista completa: execute *gerar_pdf.bat* para exportar todos os {total} tickets em PDF._"
        ))

    return blocos


def gerar_blocos(m):
    hoje = date.today().strftime("%d/%m/%Y")
    hora = datetime.now().strftime("%H:%M")

    por_periodo      = m.get("por_periodo", {})
    top_colab        = m.get("top_colaboradores", {})
    top_clientes     = m.get("top_clientes", {})
    por_setor        = m.get("por_setor", {})
    top_por_setor    = m.get("top_por_setor", {})
    tickets_atrasados = m.get("tickets_atrasados", [])
    total_atrasados   = len(tickets_atrasados)

    ranking_colab = "\n".join(
        f"{i}. *{nome}* — {qtd}"
        for i, (nome, qtd) in enumerate(list(top_colab.items())[:5], 1)
    ) or "Sem dados"

    ranking_cli = "\n".join(
        f"{i}. {nome} — {qtd}"
        for i, (nome, qtd) in enumerate(list(top_clientes.items())[:5], 1)
    ) or "Sem dados"

    grafico_setor_txt = _grafico_setor(por_setor)

    blocos_por_setor = []
    for setor in sorted(top_por_setor.keys()):
        ranking = top_por_setor[setor]
        if not ranking:
            continue
        linhas = "\n".join(
            f"  {i}. *{nome}* — {qtd}"
            for i, (nome, qtd) in enumerate(ranking.items(), 1)
        )
        blocos_por_setor.append(_bloco_section(f":small_blue_diamond: *{setor}*\n{linhas}"))

    titulo_atrasados = (
        f":rotating_light: {total_atrasados} ticket(s) com mais de 2h em aberto"
        if total_atrasados > 0
        else ":rotating_light: Tickets com mais de 2h em aberto"
    )

    blocos_atrasados = _blocos_tickets_atrasados(tickets_atrasados)

    blocos = [
        _bloco_header(":bar_chart: Dashboard Zendesk | Exemplo"),
        _bloco_section(f":clock1: *Atualizado em {hoje} as {hora}*"),
        _bloco_divider(),

        _bloco_header(":pushpin: Resumo do dia"),
        _bloco_dois_campos(
            f":ticket: *Tickets hoje*\n{m.get('total_hoje', 0)}",
            f":package: *Total acumulado*\n{m.get('total', 0)}"
        ),
        _bloco_divider(),

        _bloco_header(":building_construction: Tickets por setor (hoje)"),
        _bloco_section(grafico_setor_txt or "Sem movimentacao hoje"),
        _bloco_divider(),

        _bloco_header(":medal: Top 5 por setor (hoje)"),
    ] + (blocos_por_setor if blocos_por_setor else [_bloco_section("Sem dados por setor hoje")]) + [
        _bloco_divider(),

        _bloco_header(":clock3: Distribuicao por periodo"),
        _bloco_section(
            f":sunrise: *Manha (6h-11h):* {por_periodo.get('Manha', 0)} tickets\n"
            f":sun_with_face: *Tarde (12h-17h):* {por_periodo.get('Tarde', 0)} tickets\n"
            f":night_with_stars: *Noite (18h-23h):* {por_periodo.get('Noite', 0)} tickets"
        ),
        _bloco_divider(),

        _bloco_header(":trophy: Top colaboradores hoje"),
        _bloco_section(ranking_colab),
        _bloco_divider(),

        _bloco_header(":office: Top clientes hoje"),
        _bloco_section(ranking_cli),
        _bloco_divider(),

        # Tickets atrasados — no final
        _bloco_header(titulo_atrasados),
    ] + blocos_atrasados + [
        _bloco_divider(),
        _bloco_section(
            "_Dashboard atualizado automaticamente a cada 5 minutos._"
        ),
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":arrows_counterclockwise: Atualizar agora", "emoji": True},
                    "action_id": "atualizar_dashboard"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":page_facing_up: Gerar PDF completo", "emoji": True},
                    "style": "primary",
                    "action_id": "gerar_pdf"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": ":bar_chart: Ver Menções Slack", "emoji": True},
                    "action_id": "ver_mencoes"
                }
            ]
        },
    ]

    return blocos


def publicar_home(user_id=None):
    m = calcular_metricas()
    if "erro" in m:
        blocos = [_bloco_section(":warning: Sem dados ainda. Execute a coleta primeiro.")]
    else:
        blocos = gerar_blocos(m)

    view = {"type": "home", "blocks": blocos}
    ids = [user_id] if user_id else _listar_usuarios_do_bot()

    sucesso = 0
    for uid in ids:
        try:
            client.views_publish(user_id=uid, view=view)
            sucesso += 1
        except SlackApiError as e:
            log.error("Erro ao publicar home para %s: %s", uid, e.response.get("error"))

    log.info("App Home publicado para %d usuario(s)", sucesso)
    return sucesso


def _listar_usuarios_do_bot():
    ids = []
    try:
        resp = client.conversations_list(types="im", limit=200)
        for conv in resp.get("channels", []):
            uid = conv.get("user")
            if uid and uid != "USLACKBOT":
                ids.append(uid)
    except SlackApiError as e:
        log.error("Erro ao listar DMs: %s", e.response.get("error"))
    return ids


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    n = publicar_home()
    print(f"Dashboard publicado na Home para {n} usuario(s).")
    print("No Slack: clique em @Dashboard Zendesk -> aba 'Home' para ver.")
