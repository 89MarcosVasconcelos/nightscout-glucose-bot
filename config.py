"""
Configurações do bot carregadas via variáveis de ambiente.
"""
import os

# ── Nightscout ──────────────────────────────────────────────────────────────
NIGHTSCOUT_URL = os.getenv("NIGHTSCOUT_URL", "").rstrip("/")
NIGHTSCOUT_API_SECRET = os.getenv("NIGHTSCOUT_API_SECRET", "")
NIGHTSCOUT_TOKEN = os.getenv("NIGHTSCOUT_TOKEN", "")

# ── Evolution API ───────────────────────────────────────────────────────────
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "").rstrip("/")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "caquinho-bot")

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
