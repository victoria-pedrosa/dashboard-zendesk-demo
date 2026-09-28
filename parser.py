import re
from datetime import datetime


def periodo_do_dia(hora):
    if 6 <= hora < 12:
        return "Manha"
    elif 12 <= hora < 18:
        return "Tarde"
    elif 18 <= hora < 24:
        return "Noite"
    else:
        return "Madrugada"


def _limpar_mention(texto):
    return re.sub(r'<@\w+>', '', texto or "").strip()


def _limpar_links(texto):
    return re.sub(r'<https?://[^|>]+\|([^>]+)>', r'\1', texto or "")


def extrair_numero_ticket(footer, texto=""):
    match = re.search(r'Ticket #(\d{4,6})', footer or "")
    if match:
        return match.group(1)
    match = re.search(r'#(\d{4,6})', texto or "")
    if match:
        return match.group(1)
    return "0"


def extrair_status(footer):
    match = re.search(r'Status:\s*(\w+)', footer or "", re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return "aberto"


def extrair_prioridade(footer, fields_text=""):
    match = re.search(r'Prioridade[:\s*]+(\w+)', footer or "", re.IGNORECASE)
    if match:
        return match.group(1).capitalize()
    match = re.search(r'Prioridade[*\s:]+(\w+)', fields_text or "", re.IGNORECASE)
    if match:
        return match.group(1).capitalize()
    return "Normal"


def extrair_colaborador(fields_text, texto_fallback=""):
    match = re.search(r'Atribu[ií]do\*?[:\s]+([^\n]+)', fields_text or "", re.IGNORECASE)
    if match:
        atribuido = match.group(1).strip().replace("*", "")
        if "/" in atribuido:
            atribuido = atribuido.split("/")[-1].strip()
        if atribuido and atribuido.lower() not in ("nao atribuido", "-", ""):
            return atribuido
    return "Nao atribuido"


def extrair_setor(fields_text, texto_fallback=""):
    mapa_nome = {
        "fiscal": "Fiscal", "folha": "Folha", "atendimento": "Atendimento",
        "infra": "Infra", "migracao": "Migracao", "administrativo": "Administrativo",
        "contabil": "Contabil",
    }
    mapa_sigla = {
        "fis": "Fiscal", "fol": "Folha", "atd": "Atendimento",
        "inf": "Infra", "mig": "Migracao", "adm": "Administrativo",
    }
    match = re.search(r'Atribu[ií]do\*?[:\s]+([^/\n]+)/', fields_text or "", re.IGNORECASE)
    if match:
        setor_raw = match.group(1).strip().replace("*", "").lower()
        for k, v in mapa_nome.items():
            if k in setor_raw:
                return v
        return setor_raw.capitalize()
    match2 = re.search(r'@([A-Za-z]{2,4})\s*[-]', texto_fallback or "")
    if match2:
        sigla = match2.group(1).lower()
        return mapa_sigla.get(sigla, sigla.capitalize())
    return "Geral"


def extrair_cliente(texto_fallback):
    texto = _limpar_mention(texto_fallback or "")
    texto = texto.strip("[]").strip()
    match = re.search(r'Novo ticket chegou\s*-\s*(.+)', texto, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    partes = [p.strip() for p in re.split(r'\s*-\s*', texto)]
    partes = [p for p in partes if not re.match(r'Ticket #\d+', p, re.IGNORECASE) and p]
    for p in reversed(partes):
        if len(p) > 3 and p == p.upper():
            return p
    if partes:
        return partes[-1]
    return "Nao identificado"


def extrair_solicitante(fields_text):
    match = re.search(r'Solicitante\*?[:\s]+([^\n*]+)', fields_text or "", re.IGNORECASE)
    if match:
        return match.group(1).strip().replace("*", "")
    return "Nao informado"


def extrair_descricao(fields_text):
    match = re.search(
        r'Descri[cç][aã]o\*?[:\s]*\n?([^\n]+(?:\n(?!\*)[^\n]+)*)',
        fields_text or "", re.IGNORECASE
    )
    if match:
        return match.group(1).strip()[:300]
    primeira = _limpar_links((fields_text or "").split("\n")[0].strip())
    return primeira[:300]


def parse_attachment(attachment, ts_slack, ts_unix=None):
    footer = attachment.get("footer", "")
    texto = attachment.get("text", "") or attachment.get("fallback", "")
    fields = attachment.get("fields", [])
    fields_text = "\n".join(f.get("value", "") for f in fields) if fields else ""

    numero = extrair_numero_ticket(footer, texto)
    if numero == "0":
        return None

    colaborador = extrair_colaborador(fields_text, texto)
    setor = extrair_setor(fields_text, texto)
    cliente = extrair_cliente(texto)
    solicitante = extrair_solicitante(fields_text)
    status = extrair_status(footer)
    prioridade = extrair_prioridade(footer, fields_text)
    descricao = extrair_descricao(fields_text)

    if ts_unix:
        dt = datetime.fromtimestamp(ts_unix)
    else:
        dt = datetime.now()

    hora = dt.hour
    periodo = periodo_do_dia(hora)
    data = dt.strftime("%Y-%m-%d")
    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")

    return {
        "ticket_id": f"ticket_{numero}_{data}",
        "numero": numero,
        "colaborador": colaborador,
        "setor": setor,
        "cliente": cliente,
        "solicitante": solicitante,
        "status": status,
        "prioridade": prioridade,
        "descricao": descricao,
        "timestamp": timestamp,
        "hora": hora,
        "periodo": periodo,
        "data": data,
        "ts_slack": ts_slack,
    }


def parse_mensagem(texto, ts_slack, ts_unix=None):
    fake_attachment = {"text": texto, "fallback": texto, "footer": texto}
    return parse_attachment(fake_attachment, ts_slack, ts_unix)
