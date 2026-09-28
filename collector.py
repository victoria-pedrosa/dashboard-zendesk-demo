import logging
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
from parser import parse_attachment
from database import salvar_ticket

os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/collector.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

client = WebClient(token=SLACK_BOT_TOKEN)


def buscar_id_canal(nome_canal):
    try:
        resp = client.conversations_list(types="public_channel,private_channel", limit=200)
        for canal in resp["channels"]:
            if canal["name"] == nome_canal.lstrip("#"):
                return canal["id"]
    except SlackApiError as e:
        log.error(f"Erro ao listar canais: {e.response['error']}")
    return None


def coletar_mensagens(channel_id=None, limite=200):
    if not channel_id:
        channel_id = SLACK_CHANNEL_ID

    novos = 0
    try:
        resp = client.conversations_history(channel=channel_id, limit=limite)
        mensagens = resp.get("messages", [])
        log.info(f"Mensagens encontradas: {len(mensagens)}")

        for msg in mensagens:
            ts = msg.get("ts", "")
            ts_unix = float(ts) if ts else None

            attachments = msg.get("attachments", [])
            if not attachments and "root" in msg:
                attachments = msg["root"].get("attachments", [])

            for att in attachments:
                ticket = parse_attachment(att, ts_slack=ts, ts_unix=ts_unix)
                if ticket:
                    inserido = salvar_ticket(ticket)
                    if inserido:
                        novos += 1
                        log.info(
                            "Ticket #%s salvo - %s | %s",
                            ticket["numero"], ticket["colaborador"], ticket["cliente"]
                        )
                    break

        log.info(f"Total tickets novos: {novos}")
        return novos

    except SlackApiError as e:
        log.error(f"Erro Slack API: {e.response['error']}")
        return 0


if __name__ == "__main__":
    from database import criar_banco
    criar_banco()
    total = coletar_mensagens()
    print(f"\nColeta concluida: {total} tickets novos")
