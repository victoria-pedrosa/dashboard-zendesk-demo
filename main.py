"""
Dashboard Zendesk — Escritório Contábil Exemplo
Executa a coleta inicial e inicia o scheduler em background.
Para o dashboard visual, rode: streamlit run dashboard.py
"""
import threading
import logging
from database import criar_banco
from collector import coletar_mensagens
from scheduler import scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/main.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

def main():
    print("🚀 Dashboard Zendesk — Exemplo")
    print("=" * 40)

    # Cria banco se não existir
    criar_banco()

    # Coleta inicial
    print("📥 Fazendo coleta inicial de tickets...")
    novos = coletar_mensagens()
    print(f"✅ {novos} tickets coletados")

    # Inicia scheduler em thread separada
    print("⏰ Iniciando agendador (coleta a cada 5 min, relatório às 17h)...")
    t = threading.Thread(target=scheduler.start, daemon=True)
    t.start()

    print("\n✅ Sistema rodando!")
    print("📊 Para ver o dashboard: streamlit run dashboard.py")
    print("⏹  Para parar: Ctrl+C\n")

    try:
        t.join()
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Encerrando...")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
