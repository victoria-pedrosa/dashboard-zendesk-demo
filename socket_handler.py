"""
socket_handler.py
Escuta cliques de botões via Socket Mode.
"""
import logging
import os
import threading
import time
from datetime import date, timedelta
from slack_sdk import WebClient
from slack_sdk.socket_mode.builtin import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.socket_mode.request import SocketModeRequest
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN

log = logging.getLogger(__name__)
client = WebClient(token=SLACK_BOT_TOKEN)

_socket_client = None

# Usuários com acesso ao dashboard de menções
_ALLOWLIST = {
    "ID_SLACK_EXEMPLO",  # Victoria (você)
    "ID_SLACK_EXEMPLO",  # Colaborador 43
    "ID_SLACK_EXEMPLO",  # Colaborador 19
}

# Estado por usuário
_user_dates: dict = {}   # {user_id: {"inicio": date, "fim": date}}
_user_prefs: dict = {}   # {user_id: {"setor_filtro": str}}


def _get_setor(user_id: str) -> str:
    return _user_prefs.get(user_id, {}).get("setor_filtro", "todos")


def _set_setor(user_id: str, setor: str):
    _user_prefs.setdefault(user_id, {})["setor_filtro"] = setor


def _get_datas(user_id: str) -> tuple:
    d = _user_dates.get(user_id, {})
    return d.get("inicio"), d.get("fim")


def _set_datas(user_id: str, inicio: date, fim: date):
    _user_dates[user_id] = {"inicio": inicio, "fim": fim}


def _publicar_loading(uid: str, di: date, df: date):
    """Publica tela de carregamento imediata no App Home."""
    try:
        ini = di.strftime("%d/%m/%Y") if di else "—"
        fim = df.strftime("%d/%m/%Y") if df else "—"
        client.views_publish(user_id=uid, view={"type": "home", "blocks": [
            {"type": "header",
             "text": {"type": "plain_text", "text": "📊 Menções Slack — Exemplo", "emoji": True}},
            {"type": "section",
             "text": {"type": "mrkdwn",
                      "text": f":hourglass_flowing_sand: *Buscando menções de {ini} → {fim}...*\n_Aguarde, isso pode levar até 1 minuto._"}},
            {"type": "divider"},
            {"type": "section",
             "text": {"type": "mrkdwn",
                      "text": ":mag: Consultando #conectado e #operação-atendimento..."}},
        ]})
    except Exception as e:
        log.warning("Erro ao publicar loading: %s", e)


def _publicar(uid: str, di: date, df: date, setor: str):
    """Publica menções em background thread, sempre recarregando o código mais recente."""
    def _run():
        try:
            import sys, importlib, importlib.util
            # Deleta o .pyc para forçar recompilação a partir do .py atualizado
            try:
                _src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mencoes.py")
                _pyc = importlib.util.cache_from_source(_src)
                if os.path.exists(_pyc):
                    os.remove(_pyc)
            except Exception:
                pass
            importlib.invalidate_caches()
            if "mencoes" in sys.modules:
                importlib.reload(sys.modules["mencoes"])
            from mencoes import publicar_mencoes
            publicar_mencoes(uid, di, df, setor)
        except Exception as e:
            log.error("Erro ao publicar menções para %s: %s", uid, e)
            try:
                client.chat_postMessage(channel=uid, text=f":x: Erro ao buscar menções: {e}")
            except Exception:
                pass
    threading.Thread(target=_run, daemon=True).start()


def _handle_action(socket_client, req: SocketModeRequest):
    # ── App Home aberto: publica dashboard automaticamente ────
    if req.type == "events_api":
        event = req.payload.get("event", {})
        if event.get("type") == "app_home_opened":
            uid = event.get("user")
            if uid and uid not in ("USLACKBOT", "ID_SLACK_EXEMPLO"):
                socket_client.send_socket_mode_response(
                    SocketModeResponse(envelope_id=req.envelope_id)
                )
                if uid not in _ALLOWLIST:
                    log.info("app_home_opened: acesso negado para %s", uid)
                    client.views_publish(user_id=uid, view={"type": "home", "blocks": [
                        {"type": "header", "text": {"type": "plain_text", "text": "📊 Dashboard Menções — Exemplo", "emoji": True}},
                        {"type": "section", "text": {"type": "mrkdwn", "text": ":lock: *Acesso restrito.* Você não tem permissão para acessar este dashboard.\nSe acredita que isso é um erro, fale com a Victória."}},
                    ]})
                    return
                hoje = date.today()
                di, df = _get_datas(uid)
                di = di or hoje.replace(day=1)
                df = df or hoje
                log.info("app_home_opened: publicando para %s", uid)
                _publicar(uid, di, df, _get_setor(uid))
        return

    if req.type != "interactive":
        return

    payload   = req.payload
    action_id = ""
    if "actions" in payload and payload["actions"]:
        action_id = payload["actions"][0].get("action_id", "")

    # Confirma recebimento imediatamente (Slack exige em até 3s)
    socket_client.send_socket_mode_response(
        SocketModeResponse(envelope_id=req.envelope_id)
    )

    user_id = payload.get("user", {}).get("id")
    if not user_id:
        return
    if user_id not in _ALLOWLIST:
        log.info("ação bloqueada para %s (sem permissão)", user_id)
        return

    hoje = date.today()

    # ── Datepickers salvam silenciosamente ───────────────────
    if action_id == "mencoes_data_inicio":
        val = payload["actions"][0].get("selected_date")
        if val:
            _user_dates.setdefault(user_id, {})["inicio"] = date.fromisoformat(val)
            log.info("Data início: %s por %s", val, user_id)
        return

    if action_id == "mencoes_data_fim":
        val = payload["actions"][0].get("selected_date")
        if val:
            _user_dates.setdefault(user_id, {})["fim"] = date.fromisoformat(val)
            log.info("Data fim: %s por %s", val, user_id)
        return

    # ── Atalhos de período ───────────────────────────────────
    if action_id == "mencoes_periodo_hoje":
        _set_datas(user_id, hoje, hoje)
        log.info("Período: hoje (%s) por %s", hoje, user_id)
        _publicar_loading(user_id, hoje, hoje)
        _publicar(user_id, hoje, hoje, _get_setor(user_id))
        return

    if action_id == "mencoes_periodo_semana":
        segunda = hoje - timedelta(days=hoje.weekday())
        _set_datas(user_id, segunda, hoje)
        log.info("Período: semana (%s → %s) por %s", segunda, hoje, user_id)
        _publicar_loading(user_id, segunda, hoje)
        _publicar(user_id, segunda, hoje, _get_setor(user_id))
        return

    if action_id == "mencoes_periodo_mes":
        primeiro = hoje.replace(day=1)
        _set_datas(user_id, primeiro, hoje)
        log.info("Período: mês (%s → %s) por %s", primeiro, hoje, user_id)
        _publicar_loading(user_id, primeiro, hoje)
        _publicar(user_id, primeiro, hoje, _get_setor(user_id))
        return

    # ── Filtro por setor ─────────────────────────────────────
    if action_id == "mencoes_filtro_setor":
        val = payload["actions"][0].get("selected_option", {}).get("value", "todos")
        _set_setor(user_id, val)
        di, df = _get_datas(user_id)
        if di is None:
            di = hoje.replace(day=1)
        if df is None:
            df = hoje
        log.info("Filtro setor: '%s' por %s", val, user_id)
        _publicar(user_id, di, df, val)
        return

    # ── Atualizar menções (botão Atualizar + ver_mencoes) ────
    if action_id in ("ver_mencoes", "atualizar_mencoes"):
        # Captura datepickers do mesmo payload se presentes
        for a in payload.get("actions", []):
            aid = a.get("action_id", "")
            val = a.get("selected_date") or a.get("value")
            if aid == "mencoes_data_inicio" and val:
                _user_dates.setdefault(user_id, {})["inicio"] = date.fromisoformat(val)
            elif aid == "mencoes_data_fim" and val:
                _user_dates.setdefault(user_id, {})["fim"] = date.fromisoformat(val)
        di, df = _get_datas(user_id)
        # Default: hoje (não o mês inteiro) quando estado foi perdido após restart
        if di is None:
            di = hoje
        if df is None:
            df = hoje
        _set_datas(user_id, di, df)
        log.info("Atualizar menções: %s → %s por %s", di, df, user_id)
        # Publica tela de carregamento imediatamente
        _publicar_loading(user_id, di, df)
        _publicar(user_id, di, df, _get_setor(user_id))
        return

    # ── Gerar PDF ────────────────────────────────────────────
    if action_id == "mencoes_gerar_pdf":
        # Lê datas do value do botão (formato "YYYY-MM-DD|YYYY-MM-DD")
        btn_value = payload["actions"][0].get("value", "")
        try:
            parts = btn_value.split("|")
            di = date.fromisoformat(parts[0])
            df = date.fromisoformat(parts[1])
        except Exception:
            # Fallback: datas salvas em memória ou hoje
            di, df = _get_datas(user_id)
            if di is None:
                di = hoje
            if df is None:
                df = hoje
        log.info("PDF menções: %s → %s por %s", di, df, user_id)
        def _pdf(uid=user_id, _di=di, _df=df):
            try:
                client.chat_postMessage(
                    channel=uid,
                    text=":hourglass_flowing_sand: Gerando PDF... aguarde."
                )
                from mencoes import buscar_mencoes
                from mencoes_pdf import enviar_pdf_dm
                counts = buscar_mencoes(_di, _df)
                enviar_pdf_dm(uid, counts, _di, _df, client)
            except Exception as e:
                log.error("Erro ao gerar PDF: %s", e)
                try:
                    client.chat_postMessage(channel=uid, text=f":x: Erro ao gerar PDF: {e}")
                except Exception:
                    pass
        threading.Thread(target=_pdf, daemon=True).start()
        return

    # ── Dashboard Zendesk (botões legados) ───────────────────
    if action_id == "atualizar_dashboard":
        log.info("Atualização manual do dashboard por %s", user_id)
        def _atualizar():
            try:
                client.chat_postMessage(channel=user_id,
                                        text=":arrows_counterclockwise: Atualizando dashboard...")
                from collector import coletar_mensagens
                from app_home import publicar_home
                novos = coletar_mensagens()
                publicar_home()
                client.chat_postMessage(
                    channel=user_id,
                    text=f":white_check_mark: Dashboard atualizado! {novos} ticket(s) novo(s)."
                )
            except Exception as e:
                log.error("Erro ao atualizar dashboard: %s", e)
                try:
                    client.chat_postMessage(channel=user_id, text=f":x: Erro ao atualizar: {e}")
                except Exception:
                    pass
        threading.Thread(target=_atualizar, daemon=True).start()
        return

    if action_id == "gerar_pdf":
        log.info("Gerar PDF Zendesk por %s", user_id)
        def _gerar_e_enviar():
            try:
                client.chat_postMessage(channel=user_id,
                                        text=":hourglass_flowing_sand: Gerando PDF...")
                from gerar_pdf import gerar_relatorio
                caminho = gerar_relatorio()
                dm = client.conversations_open(users=user_id)
                channel_id = dm["channel"]["id"]
                with open(caminho, "rb") as f:
                    client.files_upload_v2(
                        channel=channel_id, file=f,
                        filename=os.path.basename(caminho),
                        title="Relatório Zendesk - Exemplo",
                        initial_comment=":page_facing_up: Relatório PDF gerado!"
                    )
            except Exception as e:
                log.error("Erro ao gerar PDF Zendesk: %s", e)
                try:
                    client.chat_postMessage(channel=user_id, text=f":x: Erro: {e}")
                except Exception:
                    pass
        threading.Thread(target=_gerar_e_enviar, daemon=True).start()
        return


def iniciar_socket(blocking=False):
    global _socket_client

    if not SLACK_APP_TOKEN:
        log.warning("SLACK_APP_TOKEN não configurado — botões desativados.")
        return

    try:
        _socket_client = SocketModeClient(
            app_token=SLACK_APP_TOKEN,
            web_client=client
        )
        _socket_client.socket_mode_request_listeners.append(_handle_action)
        _socket_client.connect()
        log.info("Socket Mode ativo.")

        # Publica dashboard para todos os usuários da allowlist ao iniciar
        def _publicar_todos():
            hoje = date.today()
            for uid in _ALLOWLIST:
                try:
                    di, df = _get_datas(uid)
                    di = di or hoje
                    df = df or hoje
                    log.info("Publicando home inicial para %s", uid)
                    _publicar(uid, di, df, _get_setor(uid))
                    time.sleep(2)  # evita flood na API
                except Exception as e:
                    log.warning("Erro ao publicar home para %s: %s", uid, e)
        threading.Thread(target=_publicar_todos, daemon=True).start()

    except Exception as e:
        log.error("Erro ao iniciar Socket Mode: %s", e)
        return

    if blocking:
        print("\nConectado! Aguardando interações...\n")
        while True:
            time.sleep(1)


if __name__ == "__main__":
    import logging as _log
    _log.basicConfig(
        level=_log.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            _log.FileHandler("data/socket.log", encoding="utf-8"),
            _log.StreamHandler()
        ]
    )
    os.makedirs("data", exist_ok=True)
    iniciar_socket(blocking=True)
