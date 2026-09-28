import logging
import os

os.makedirs("data", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/scheduler.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

from apscheduler.schedulers.blocking import BlockingScheduler
from config import HORA_RELATORIO
from database import criar_banco
from collector import coletar_mensagens
from notificador import checar_alertas_atraso, enviar_relatorio_diario
from app_home import publicar_home

try:
    from socket_handler import iniciar_socket
    _socket_ok = True
except Exception as _e:
    log.warning("Socket handler nao carregou: %s", _e)
    _socket_ok = False
    def iniciar_socket(**kw): pass

scheduler = BlockingScheduler(timezone="America/Bahia")


@scheduler.scheduled_job("interval", minutes=5, id="coletar_e_home")
def job_coletar():
    log.info("Coletando mensagens do Slack...")
    coletar_mensagens()
    log.info("Atualizando App Home...")
    publicar_home()


@scheduler.scheduled_job("interval", minutes=30, id="alertas")
def job_alertas():
    log.info("Verificando tickets atrasados...")
    checar_alertas_atraso()


hora, minuto = HORA_RELATORIO.split(":")


@scheduler.scheduled_job("cron", hour=int(hora), minute=int(minuto), id="relatorio")
def job_relatorio():
    log.info("Enviando relatorio diario...")
    enviar_relatorio_diario()


if __name__ == "__main__":
    log.info("Scheduler iniciado | App Home a cada 5 min | Relatorio as %s", HORA_RELATORIO)
    criar_banco()
    iniciar_socket(blocking=False)
    coletar_mensagens()
    publicar_home()
    scheduler.start()
