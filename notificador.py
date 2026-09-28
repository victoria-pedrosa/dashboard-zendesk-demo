import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import SLACK_BOT_TOKEN, DM_GESTOR_1, DM_GESTOR_2, ALERTA_HORAS
from database import buscar_tickets_sem_alerta, marcar_alerta_enviado
from metrics import calcular_metricas

log = logging.getLogger(__name__)
client = WebClient(token=SLACK_BOT_TOKEN)

def enviar_mensagem(canal_id: str, texto: str):
    try:
        client.chat_postMessage(channel=canal_id, text=texto, mrkdwn=True)
        log.info(f"📤 Mensagem enviada para {canal_id}")
    except SlackApiError as e:
        log.error(f"❌ Erro ao enviar mensagem: {e.response['error']}")

def checar_alertas_atraso():
    """Verifica tickets sem resposta há mais de X horas e avisa Colaborador 41."""
    tickets_atrasados = buscar_tickets_sem_alerta(ALERTA_HORAS)
    if not tickets_atrasados:
        return

    for t in tickets_atrasados:
        ticket_id, numero, colaborador, cliente, timestamp = t
        msg = (
            f"⚠️ *Ticket sem resposta há mais de {ALERTA_HORAS}h*\n"
            f"🎫 Ticket #*{numero}*\n"
            f"👤 Colaborador: *{colaborador}*\n"
            f"🏢 Cliente: *{cliente}*\n"
            f"🕐 Aberto em: {timestamp}\n"
            f"Por favor, verificar."
        )
        enviar_mensagem(DM_GESTOR_1, msg)
        marcar_alerta_enviado(ticket_id)
        log.info(f"🚨 Alerta enviado para Colaborador 41 — Ticket #{numero}")

def enviar_relatorio_diario():
    """Envia relatório diário às 17h para Colaborador 41 e Colaborador 42."""
    m = calcular_metricas()
    if "erro" in m:
        log.warning("Sem dados para relatório")
        return

    top3 = list(m["top_colaboradores"].items())[:3]
    ranking = "\n".join([f"  {i+1}. {nome} — {qtd} ticket(s)" for i, (nome, qtd) in enumerate(top3)])

    msg = (
        f"📊 *DASHBOARD ZENDESK — {__import__('datetime').date.today().strftime('%d/%m/%Y')}*\n\n"
        f"🎫 *Tickets recebidos hoje:* {m['total_hoje']}\n"
        f"✅ *Resolvidos:* {m['resolvidos_hoje']}\n"
        f"⏳ *Pendentes:* {m['pendentes_hoje']}\n"
        f"📈 *Taxa de resolução:* {m['taxa_resolucao']}%\n\n"
        f"🏆 *Top colaboradores do dia:*\n{ranking}\n\n"
        f"⏰ *Distribuição por período:*\n"
        f"  🌅 Manhã: {m['por_periodo']['Manhã']}\n"
        f"  ☀️ Tarde: {m['por_periodo']['Tarde']}\n"
        f"  🌙 Noite: {m['por_periodo']['Noite']}\n\n"
        f"📌 *Total acumulado:* {m['total']} tickets\n"
        f"_Relatório automático — Dashboard Zendesk Exemplo_"
    )

    enviar_mensagem(DM_GESTOR_1, msg)
    enviar_mensagem(DM_GESTOR_2, msg)
    log.info("📊 Relatório diário enviado para Colaborador 41 e Colaborador 42")

if __name__ == "__main__":
    checar_alertas_atraso()
