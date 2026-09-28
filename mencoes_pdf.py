"""
mencoes_pdf.py
Gera um PDF do relatório de menções e envia por DM no Slack.
"""
import io
import logging
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

log = logging.getLogger(__name__)

CORES_SETOR = {
    "Fiscal":        colors.HexColor("#E53E3E"),
    "Balanço":       colors.HexColor("#3182CE"),
    "Folha":         colors.HexColor("#38A169"),
    "IA":            colors.HexColor("#805AD5"),
    "Atendimento":   colors.HexColor("#DD6B20"),
    "Comercial":     colors.HexColor("#D69E2E"),
    "Gestão":        colors.HexColor("#718096"),
    "Procuradoria":  colors.HexColor("#2C7A7B"),
    "Suporte":       colors.HexColor("#744210"),
    "Financeiro":    colors.HexColor("#276749"),
    "Líderes":       colors.HexColor("#6B46C1"),
    "Estagiários":   colors.HexColor("#B7791F"),
    "Outros":        colors.HexColor("#A0AEC0"),
}


def gerar_pdf_bytes(counts: dict, data_inicio: date, data_fim: date) -> bytes:
    """Gera o PDF em memória e retorna os bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        "titulo", parent=styles["Title"],
        fontSize=18, textColor=colors.HexColor("#1A202C"),
        spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#718096"),
        spaceAfter=12
    )
    setor_style = ParagraphStyle(
        "setor", parent=styles["Heading2"],
        fontSize=13, textColor=colors.white,
        spaceAfter=0, spaceBefore=12,
        leftIndent=6
    )
    normal = styles["Normal"]
    normal.fontSize = 9

    story = []

    # Cabeçalho
    story.append(Paragraph("📊 Menções Slack — Exemplo", titulo_style))
    inicio_fmt = data_inicio.strftime("%d/%m/%Y")
    fim_fmt = data_fim.strftime("%d/%m/%Y")
    gerado = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(
        f"Período: {inicio_fmt} → {fim_fmt}   |   Gerado em: {gerado}",
        sub_style
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0")))
    story.append(Spacer(1, 0.3*cm))

    # Agrupar por setor (respeita multi-setor como Fol/Fis)
    por_setor: dict[str, list] = {}
    for d in counts.values():
        for s in d.get("sectors", [d.get("sector", "Outros")]):
            por_setor.setdefault(s, []).append(d)

    setor_totais = {s: sum(p["total"] for p in ps) for s, ps in por_setor.items()}
    setor_order = sorted(setor_totais, key=lambda s: -setor_totais[s])
    total_geral = sum(setor_totais.values())

    # Resumo por setor (tabela)
    story.append(Paragraph("Resumo por Setor", styles["Heading2"]))
    story.append(Spacer(1, 0.2*cm))

    resumo_data = [["Setor", "Menções", "%"]]
    for s in setor_order:
        pct = f"{setor_totais[s]/total_geral*100:.1f}%" if total_geral else "0%"
        resumo_data.append([s, str(setor_totais[s]), pct])
    resumo_data.append(["TOTAL", str(total_geral), "100%"])

    t = Table(resumo_data, colWidths=[9*cm, 4*cm, 4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D3748")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ALIGN",      (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#F7FAFC"), colors.white]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EDF2F7")),
        ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # Ranking detalhado por setor
    story.append(Paragraph("Ranking por Setor", styles["Heading2"]))

    for s in setor_order:
        cor = CORES_SETOR.get(s, colors.HexColor("#718096"))
        pessoas = sorted(por_setor[s], key=lambda p: -p["total"])

        # Header do setor colorido
        header_data = [[f"{s}  —  {setor_totais[s]} menções"]]
        ht = Table(header_data, colWidths=[17*cm])
        ht.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), cor),
            ("TEXTCOLOR",  (0, 0), (-1, -1), colors.white),
            ("FONTNAME",   (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(Spacer(1, 0.3*cm))
        story.append(ht)

        # Tabela de pessoas
        rows = [["#", "Squad", "Nome", "Total", "#conectado", "#op-atend"]]
        for i, p in enumerate(pessoas, 1):
            role = p.get("role", "—")
            if role in ("—", "Externo", ""):
                role = "—"
            rows.append([
                str(i),
                role,
                p["name"],
                str(p["total"]),
                str(p["con"]),
                str(p.get("at", 0)),
            ])

        dt = Table(rows, colWidths=[1*cm, 4*cm, 5*cm, 2*cm, 2.5*cm, 2.5*cm])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8),
            ("ALIGN",      (0, 0), (0, -1), "CENTER"),
            ("ALIGN",      (3, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
            ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(dt)

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0")))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Total geral: {total_geral} menções  |  {len(counts)} pessoas  |  #conectado + #operação-atendimento",
        ParagraphStyle("rodape", parent=normal, textColor=colors.HexColor("#718096"),
                       alignment=TA_CENTER)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def enviar_pdf_dm(user_id: str, counts: dict, data_inicio: date, data_fim: date, client):
    """Gera o PDF e envia como arquivo por DM ao user_id."""
    try:
        pdf_bytes = gerar_pdf_bytes(counts, data_inicio, data_fim)
        nome_arquivo = f"mencoes_{data_inicio.isoformat()}_{data_fim.isoformat()}.pdf"

        # Abre o canal DM para obter o channel_id correto (começa com D...)
        resp_dm = client.conversations_open(users=[user_id])
        channel_id = resp_dm["channel"]["id"]

        client.files_upload_v2(
            channel=channel_id,
            content=pdf_bytes,
            filename=nome_arquivo,
            title=f"Menções Slack — {data_inicio.strftime('%d/%m')} → {data_fim.strftime('%d/%m/%Y')}",
            initial_comment=":page_facing_up: Relatório de menções gerado!"
        )
        log.info("PDF enviado para %s (%d bytes)", user_id, len(pdf_bytes))
    except Exception as e:
        log.error("Erro ao gerar/enviar PDF: %s", e)
        try:
            client.chat_postMessage(
                channel=user_id,
                text=f":x: Erro ao gerar PDF: {e}"
            )
        except Exception:
            pass
