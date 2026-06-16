"""
Bot de alertas de glicose via WhatsApp e Telegram.

Funcionalidades:
- Polling do Nightscout a cada POLL_INTERVAL segundos
- Alertas automáticos de hipoglicemia (< GLUCOSE_LOW mg/dL) e hiperglicemia (> GLUCOSE_HIGH mg/dL)
- Cooldown por tipo de alerta para não spam
- Alertas enviados via WhatsApp (Evolution API) E Telegram (opcional)
- Webhook para receber mensagens: responde a "glicose caquinho" com a leitura atual
- Comandos admin para adicionar/remover contatos via WhatsApp
- Endpoint REST para a Alexa Skill ("Glicose agora") consultar a leitura atual
"""
import logging
import os
import threading
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, request

import config
import contacts
import evolution
import nightscout
import telegram_bot

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Flask app ────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ─── Chave de acesso para a Alexa Skill (separada do segredo do Nightscout) ──
ALEXA_API_KEY = os.environ.get("ALEXA_API_KEY", "")

# ─── Estado de alertas (cooldown) ─────────────────────────────────────────────
_last_alert: dict[str, float] = {}
_alert_lock = threading.Lock()

def _can_alert(alert_type: str) -> bool:
    """Retorna True se o cooldown para esse tipo de alerta já passou."""
    with _alert_lock:
        last = _last_alert.get(alert_type, 0)
        if time.time() - last >= config.ALERT_COOLDOWN:
            _last_alert[alert_type] = time.time()
            return True
        return False

# ─── Loop de monitoramento ────────────────────────────────────────────────────
def _monitor_loop():
    logger.info(
        "Monitor iniciado | Baixa < %d | Alta > %d | Intervalo %ds",
        config.GLUCOSE_LOW,
        config.GLUCOSE_HIGH,
        config.POLL_INTERVAL,
    )
    while True:
        try:
            entry = nightscout.get_latest_entry()
            if entry:
                sgv = entry["sgv"]
                logger.info("Glicose atual: %d mg/dL (%s)", sgv, entry["direction"])

                if sgv < config.GLUCOSE_LOW and _can_alert("low"):
                    _send_alert("low", entry)
                elif sgv > config.GLUCOSE_HIGH and _can_alert("high"):
                    _send_alert("high", entry)
        except Exception as e:
            logger.exception("Erro inesperado no monitor: %s", e)

        time.sleep(config.POLL_INTERVAL)

def _send_alert(alert_type: str, entry: dict):
    """Monta e envia a mensagem de alerta via WhatsApp e Telegram."""
    sgv = entry["sgv"]
    reading = nightscout.format_reading(entry)

    if alert_type == "low":
        header = (
            f"🚨 *ALERTA: GLICOSE BAIXA!*\n"
            f"Glicose em *{sgv} mg/dL* — abaixo de {config.GLUCOSE_LOW} mg/dL!\n\n"
        )
    else:
        header = (
            f"⚠️ *ALERTA: GLICOSE ALTA!*\n"
            f"Glicose em *{sgv} mg/dL* — acima de {config.GLUCOSE_HIGH} mg/dL!\n\n"
        )

    message = header + reading

    # ── WhatsApp ──────────────────────────────────────────────────────────────
    all_contacts = contacts.load()
    if all_contacts:
        logger.info("Enviando alerta '%s' via WhatsApp para %d contato(s)", alert_type, len(all_contacts))
        evolution.send_to_all(all_contacts, message)
    else:
        logger.warning("Nenhum contato WhatsApp cadastrado para receber alertas.")

    # ── Telegram ──────────────────────────────────────────────────────────────
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_IDS:
        logger.info("Enviando alerta '%s' via Telegram", alert_type)
        telegram_bot.send_to_all(message)
    else:
        logger.debug("Telegram não configurado — alerta não enviado por Telegram.")

# ─── Webhook Flask ────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    """Recebe eventos da Evolution API (mensagens recebidas)."""
    data = request.get_json(silent=True) or {}

    event = data.get("event", "")
    if event != "messages.upsert":
        return jsonify({"ok": True})

    message_data = data.get("data", {})
    key = message_data.get("key", {})
    from_me = key.get("fromMe", False)

    if from_me:
        return jsonify({"ok": True})

    remote_jid = key.get("remoteJid", "")
    sender_number = remote_jid.split("@")[0]

    msg = message_data.get("message", {})
    text = (
        msg.get("conversation")
        or msg.get("extendedTextMessage", {}).get("text")
        or ""
    ).strip()

    logger.info("Mensagem recebida de %s: %s", sender_number, text)
    _handle_message(sender_number, text)

    return jsonify({"ok": True})

@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    """Recebe updates do Telegram (mensagens enviadas ao bot)."""
    data = request.get_json(silent=True) or {}
    chat_id, text, username = telegram_bot.parse_incoming(data)

    if not chat_id or not text:
        return jsonify({"ok": True})

    logger.info("Telegram: mensagem de %s (chat_id=%s): %s", username, chat_id, text)
    _handle_telegram_message(chat_id, text)
    return jsonify({"ok": True})

def _handle_telegram_message(chat_id: int, text: str):
    """Processa comandos recebidos via Telegram."""
    lower = text.lower().strip()

    # ── Consulta pública ──────────────────────────────────────────────────────
    if lower in ("glicose caquinho", "/glicose", "/start"):
        entry = nightscout.get_latest_entry()
        if entry:
            reply = "🩸 *Última medição de Caquinho:*\n\n" + nightscout.format_reading(entry)
        else:
            reply = "❌ Não foi possível obter a leitura do Nightscout. Tente mais tarde."
        telegram_bot.send_message(chat_id, reply)
        return

    # ── Ajuda ─────────────────────────────────────────────────────────────────
    if lower in ("ajuda", "/ajuda", "/help", "?"):
        msg = (
            "🤖 *Bot Glicose Caquinho*\n\n"
            "*Comandos disponíveis:*\n"
            "• `Glicose Caquinho` ou `/glicose` — última medição\n"
            "• `/ajuda` — esta mensagem\n\n"
            "_Alertas automáticos são enviados quando a glicose sai dos limites._"
        )
        telegram_bot.send_message(chat_id, msg)
        return

@app.route("/health", methods=["GET"])
def health():
    """Health check para o Coolify."""
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})

@app.route("/api/alexa/glucose", methods=["GET"])
def alexa_glucose():
    """
    Endpoint consumido pela Alexa Skill "Glicose agora".
    Protegido por uma chave própria (header X-Api-Key), independente
    do API_SECRET do Nightscout, que nunca é exposto aqui.
    """
    if ALEXA_API_KEY:
        provided = request.headers.get("X-Api-Key", "")
        if provided != ALEXA_API_KEY:
            return jsonify({"error": "unauthorized"}), 401

    entry = nightscout.get_latest_entry()
    if not entry:
        return jsonify({"error": "unavailable"}), 503

    now = datetime.now(timezone.utc)
    minutes_ago = max(0, int((now - entry["date"]).total_seconds() // 60))

    return jsonify(
        {
            "sgv": entry["sgv"],
            "direction": entry["direction"],
            "direction_text": entry["direction_emoji"],
            "minutes_ago": minutes_ago,
            "datetime_utc": entry["date"].isoformat(),
        }
    )

def _handle_message(sender: str, text: str):
    """Processa comandos recebidos via WhatsApp."""
    lower = text.lower().strip()

    # ── Consulta pública (qualquer pessoa pode usar) ──────────────────────────
    if lower == "glicose caquinho":
        entry = nightscout.get_latest_entry()
        if entry:
            reply = "🩸 *Última medição de Caquinho:*\n\n" + nightscout.format_reading(entry)
        else:
            reply = "❌ Não foi possível obter a leitura do Nightscout. Tente mais tarde."
        evolution.send_text(sender, reply)
        return

    # ── Comandos admin (apenas contatos cadastrados) ──────────────────────────
    if not contacts.is_registered(sender):
        return

    # add <nome> <número>
    if lower.startswith("add "):
        parts = text.split(None, 2)
        if len(parts) == 3:
            _, name, number = parts
            added = contacts.add(name, number)
            msg = (
                f"✅ Contato *{name}* ({number}) adicionado!"
                if added
                else f"ℹ️ O número {number} já está cadastrado."
            )
        else:
            msg = "❌ Formato: *add Nome 5511999998888*"
        evolution.send_text(sender, msg)
        return

    # remove <número>
    if lower.startswith("remove "):
        parts = text.split(None, 1)
        if len(parts) == 2:
            number = parts[1].strip()
            removed = contacts.remove(number)
            msg = (
                f"✅ Número {number} removido."
                if removed
                else f"ℹ️ Número {number} não encontrado."
            )
        else:
            msg = "❌ Formato: *remove 5511999998888*"
        evolution.send_text(sender, msg)
        return

    # lista
    if lower == "lista":
        all_contacts = contacts.load()
        if not all_contacts:
            msg = "📋 Nenhum contato cadastrado."
        else:
            lines = [f" • {c['name']} — {c['number']}" for c in all_contacts]
            msg = "📋 *Contatos cadastrados:*\n" + "\n".join(lines)
        evolution.send_text(sender, msg)
        return

    # ajuda
    if lower in ("ajuda", "help", "?"):
        msg = (
            "🤖 *Bot Glicose Caquinho*\n\n"
            "*Comandos públicos:*\n"
            "• `Glicose Caquinho` — consulta a última medição\n\n"
            "*Comandos admin (só contatos cadastrados):*\n"
            "• `add Nome 5511999998888` — adiciona contato para alertas\n"
            "• `remove 5511999998888` — remove contato\n"
            "• `lista` — lista todos os contatos\n"
        )
        evolution.send_text(sender, msg)

# ─── Inicialização (chamada pelo entrypoint) ──────────────────────────────────
def start_monitor():
    """Inicia o thread de monitoramento. Chamado pelo entrypoint antes do servidor."""
    config.validate()

    logger.info("Testando conexão com Nightscout (%s)...", config.NIGHTSCOUT_URL)
    entry = nightscout.get_latest_entry()
    if entry:
        logger.info("Nightscout OK — glicose atual: %d mg/dL", entry["sgv"])
    else:
        logger.warning("Não foi possível obter dados do Nightscout na inicialização.")

    logger.info("Verificando instância Evolution API...")
    status = evolution.get_instance_status()
    if status == "open":
        logger.info("Evolution API: instância conectada (open)")
    else:
        logger.warning(
            "Evolution API: status = '%s'. Certifique-se de que o QR code foi escaneado.", status
        )

    # Configura o webhook para apontar para este container
    webhook_url = f"http://caquinho-bot:{config.WEBHOOK_PORT}/webhook"
    evolution.set_webhook(webhook_url)

    # Telegram
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_IDS:
        logger.info("Telegram habilitado — chat_ids: %s", config.TELEGRAM_CHAT_IDS)
        if config.TELEGRAM_WEBHOOK_URL:
            telegram_bot.set_webhook(config.TELEGRAM_WEBHOOK_URL)
        else:
            logger.warning(
                "TELEGRAM_WEBHOOK_URL não definido — comandos Telegram não funcionarão. "
                "Defina como: https://<seu-dominio>/telegram/webhook"
            )
    else:
        logger.info("Telegram não configurado (opcional) — alertas somente via WhatsApp.")

    if ALEXA_API_KEY:
        logger.info("Endpoint da Alexa habilitado em /api/alexa/glucose")
    else:
        logger.info("ALEXA_API_KEY não definida — endpoint /api/alexa/glucose ficará sem autenticação.")

    monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    monitor_thread.start()
    logger.info("Thread de monitoramento iniciada.")

if __name__ == "__main__":
    start_monitor()
    app.run(host="0.0.0.0", port=config.WEBHOOK_PORT, debug=False)
