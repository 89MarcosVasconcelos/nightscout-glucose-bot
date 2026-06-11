"""
Configurações do bot carregadas via variáveis de ambiente.
"""
import os

# ── Nightscout ──────────────────────────────────────────────────────────────
NIGHTSCOUT_URL = os.getenv("NIGHTSCOUT_URL", "").rstrip("/")
NIGHTSCOUT_API_SECRET = os.getenv("NIGHTSCOUT_API_SECRET", "")
NIGHTSCOUT_TOKEN = os.getenv("NIGHTSCOUT_TOKEN", "")

# ── Evolution API (WhatsApp) ────────────────────────────────────────────────
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "").rstrip("/")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "caquinho-bot")

# ── Telegram ────────────────────────────────────────────────────────────────
# TELEGRAM_BOT_TOKEN: token gerado pelo @BotFather
# TELEGRAM_CHAT_IDS: IDs separados por vírgula (ex: "8396408129,123456789")
# TELEGRAM_WEBHOOK_URL: URL pública do bot + /telegram/webhook
#   ex: "https://caquinho.marcosvasconcelos.dev.br/telegram/webhook"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "")
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")

# ── Limites de glicose (mg/dL) ──────────────────────────────────────────────
GLUCOSE_LOW = int(os.getenv("GLUCOSE_LOW", "70"))
GLUCOSE_HIGH = int(os.getenv("GLUCOSE_HIGH", "180"))

# ── Comportamento ───────────────────────────────────────────────────────────
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))    # 5 minutos
ALERT_COOLDOWN = int(os.getenv("ALERT_COOLDOWN", "1800")) # 30 minutos
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))
CONTACTS_FILE = os.getenv("CONTACTS_FILE", "/data/contacts.json")


def validate():
    missing = []
    if not NIGHTSCOUT_URL:
        missing.append("NIGHTSCOUT_URL")
    if not EVOLUTION_API_URL:
        missing.append("EVOLUTION_API_URL")
    if not EVOLUTION_API_KEY:
        missing.append("EVOLUTION_API_KEY")
    if missing:
        raise EnvironmentError(
            f"Variáveis de ambiente obrigatórias não definidas: {', '.join(missing)}"
        )

    # Telegram é opcional — avisa se token sem IDs ou vice-versa
    import logging
    _log = logging.getLogger(__name__)
    if TELEGRAM_BOT_TOKEN and not TELEGRAM_CHAT_IDS:
        _log.warning(
            "TELEGRAM_BOT_TOKEN definido mas TELEGRAM_CHAT_IDS está vazio. "
            "Nenhuma mensagem Telegram será enviada."
        )
    if TELEGRAM_CHAT_IDS and not TELEGRAM_BOT_TOKEN:
        _log.warning(
            "TELEGRAM_CHAT_IDS definido mas TELEGRAM_BOT_TOKEN está vazio. "
            "Nenhuma mensagem Telegram será enviada."
        )
