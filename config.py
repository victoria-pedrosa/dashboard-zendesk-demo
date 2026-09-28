import os
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
DM_GESTOR_1 = os.getenv("DM_GESTOR_1", "ID_SLACK_EXEMPLO")
DM_GESTOR_2 = os.getenv("DM_GESTOR_2", "ID_SLACK_EXEMPLO")
HORA_RELATORIO = os.getenv("HORA_RELATORIO", "17:00")
ALERTA_HORAS = int(os.getenv("ALERTA_HORAS", "2"))

# Paleta Exemplo
CORES = {
    "verde_escuro": "#1a5c38",
    "verde_medio": "#2d8653",
    "verde_claro": "#4caf78",
    "verde_suave": "#e8f5ee",
    "branco": "#ffffff",
    "cinza": "#f5f5f5",
    "texto": "#1a1a1a",
}
