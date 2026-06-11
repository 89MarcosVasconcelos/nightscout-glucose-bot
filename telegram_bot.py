"""
Cliente para a API de Bots do Telegram.
Usa requests diretamente (sem biblioteca extra).

Documentação: https://core.telegram.org/bots/api
"""
import logging
import re

import requests

import config

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.telegram.org/bot{token}/{method}"


def _enabled() -> bool:
    """Retorna True se o Telegram está configurado."""
    return bool(config.TELEGRAM_BOT_TOKEN)


def _wa_to_html(text: str) -> str:
    """
    Converte formatação WhatsApp (*bold*, _italic_) para HTML do Telegram.
    Também escapa '<' e '>' literais antes da conversão.
    """
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*([^*\n]+)\*", r"<b>\1</b>", text)
    text = re.sub(r"_([^_\n]+)_", r"<i>\1</i>", text)
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)
    return text


def send_message(chat_id: str | int, text: str) -> bool:
    """
    Envia uma mensagem para um chat_id específico.

    Args:
        chat_id: ID do chat/usuário do Telegram
        text:    Texto com formatação WhatsApp (*bold*, _italic_)

    Returns:
        True se enviado com sucesso, False caso contrário.
    """
    if not _enabled():
        return False

    url = _BASE_URL.format(token=config.TELEGRAM_BOT_TOKEN, method="sendMessage")
    payload = {
        "chat_id": chat_id,
        "text": _wa_to_html(text),
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        logger.info("Telegram: mensagem enviada para chat_id %s", chat_id)
        return True
    except requests.RequestException as e:
        logger.error("Telegram: erro ao enviar para chat_id %s: %s", chat_id, e)
        return False


def send_to_all(text: str) -> None:
    """Envia a mensagem para todos os chat_ids configurados em TELEGRAM_CHAT_IDS."""
    if not _enabled():
        return

    chat_ids = [cid.strip() for cid in config.TELEGRAM_CHAT_IDS.split(",") if cid.strip()]
    if not chat_ids:
        logger.warning("Telegram: TELEGRAM_CHAT_IDS está vazio.")
        return

    for chat_id in chat_ids:
        send_message(chat_id, text)


def set_webhook(webhook_url: str) -> bool:
    """
    Registra o webhook no Telegram para receber mensagens em tempo real.
    Deve ser chamado uma vez na inicialização.
    """
    if not _enabled():
        return False

    if not webhook_url:
        logger.warning("Telegram: TELEGRAM_WEBHOOK_URL não definido — webhook não registrado.")
        return False

    url = _BASE_URL.format(token=config.TELEGRAM_BOT_TOKEN, method="setWebhook")
    try:
        resp = requests.post(url, json={"url": webhook_url}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            logger.info("Telegram webhook registrado: %s", webhook_url)
            return True
        logger.error("Telegram webhook falhou: %s", data)
        return False
    except requests.RequestException as e:
        logger.error("Telegram: erro ao registrar webhook: %s", e)
        return False


def parse_incoming(data: dict) -> tuple[int | None, str, str]:
    """
    Extrai (chat_id, text, username) de um update recebido pelo webhook.
    Suporta mensagens normais e comandos.
    Returns (None, '', '') se não for uma mensagem de texto.
    """
    message = data.get("message") or data.get("edited_message")
    if not message:
        return None, "", ""

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    username = (
        message.get("from", {}).get("username")
        or message.get("from", {}).get("first_name")
        or "desconhecido"
    )
    return chat_id, text, username
