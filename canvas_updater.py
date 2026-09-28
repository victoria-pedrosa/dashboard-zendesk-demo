"""
canvas_updater.py
Atualiza o Canvas do canal #zendesk com as metricas do dia.
Roda automaticamente pelo scheduler a cada 5 minutos.
"""
import logging
import os
from datetime import date, datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
from metrics import calcular_metricas
from database import buscar_todos

log = logging.getLogger(__name__)
client = WebClient(token=SLACK_BOT_TOKEN)


def obter_canvas_do_canal(channel_id):
    """Retorna o canvas_id associado ao canal, ou None."""
    try:
        resp = client.conversations_info(channel=channel_id, include_all_metadata=True)
        canal = resp.get("channel", {})
        canvas = canal.get("properties", {}).get("canvas", {})
        canvas_id = canvas.get("file_id") or canvas.get("id")
        return canvas_id
    except SlackApiError as e:
        log.error("Erro ao buscar canvas: %s", e.response.get("error"))
        return None


def gerar_conteudo_canvas(m):
    """Gera o markdown do canvas com as metricas."""
    hoje_str = date.today().strftime("%d/%m/%Y")
    hora_str = datetime.now().strftime("%H:%M")

    top_colab = m.get("top_colaboradores", {})
    ranking_lines = []
    for i, (nome, qtd) in enumerate(list(top_colab.items())[:5], 1):
        ranking_lines.append(f"{i}. {nome} — {qtd} ticket(s)")
    ranking = "\n".join(ranking_lines) if ranking_lines else "Sem dados"

    por_periodo = m.get("por_periodo", {})

    conteudo = f"""# Dashboard Zendesk — Exemplo
*Atualizado em {hoje_str} as {hora_str}*

---

## Resumo do dia

| Indicador | Valor |
|---|---|
| Tickets hoje | {m.get('total_hoje', 0)} |
| Resolvidos | {m.get('resolvidos_hoje', 0)} |
| Pendentes | {m.get('pendentes_hoje', 0)} |
| Taxa de resolucao | {m.get('taxa_resolucao', 0)}% |
| Total acumulado | {m.get('total', 0)} |

---

## Distribuicao por periodo

- Manha (6h-11h): {por_periodo.get('Manha', 0)} tickets
- Tarde (12h-17h): {por_periodo.get('Tarde', 0)} tickets
- Noite (18h-23h): {por_periodo.get('Noite', 0)} tickets

---

## Top colaboradores hoje

{ranking}

---

*Atualizacao automatica a cada 5 minutos | Sistema Dashboard Zendesk Exemplo*
"""
    return conteudo


def atualizar_canvas():
    """Le metricas e atualiza o Canvas do canal #zendesk."""
    canvas_id = obter_canvas_do_canal(SLACK_CHANNEL_ID)
    if not canvas_id:
        log.warning("Canvas nao encontrado no canal. Verifique se o canal tem canvas ativo.")
        return False

    m = calcular_metricas()
    if "erro" in m:
        log.warning("Sem dados para atualizar canvas: %s", m["erro"])
        return False

    conteudo = gerar_conteudo_canvas(m)

    try:
        client.canvases_edit(
            canvas_id=canvas_id,
            changes=[{
                "operation": "replace",
                "document_content": {
                    "type": "markdown",
                    "markdown": conteudo
                }
            }]
        )
        log.info("Canvas atualizado com sucesso — %s tickets hoje", m.get("total_hoje", 0))
        return True
    except SlackApiError as e:
        log.error("Erro ao atualizar canvas: %s", e.response.get("error"))
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ok = atualizar_canvas()
    if ok:
        print("Canvas atualizado!")
    else:
        print("Falha ao atualizar canvas. Verifique o log acima.")
