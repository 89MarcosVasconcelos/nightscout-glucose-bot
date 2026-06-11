"""
Cliente para a Evolution API (wrapper WhatsApp Web).
Documentação: https://doc.evolution-api.com
"""
import logging

import requests

import config

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "apikey": config.EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }


def send_text(number: str, text: str) -> bool:
    """
    Envia uma mensagem de texto para um número.

    Args:
        number: número no formato internacional sem '+', ex: '5511999998888'
        text:   texto da mensagem (suporta markdown do WhatsApp: *negrito*, _itálico_)

    Returns:
        True se enviado com sucesso, False caso contrário.
    """
    url = f"{config.EVOLUTION_API_URL}/message/sendText/{config.EVOLUTION_INSTANCE}"
    payload = {
        "number": number,
        "text": text,
        "delay": 0,
    }
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
        resp.raise_for_status()
        logger.info("Mensagem enviada para %s", number)
        return True
    except requests.RequestException as e:
        logger.error("Erro ao enviar mensagem para %s: %s", number, e)
        return False


def send_to_all(contacts: list[dict], text: str) -> None:
    """Envia a mesma mensagem para todos os contatos da lista."""
    for contact in contacts:
        number = contact.get("number", "")
        name = contact.get("name", number)
        if not number:
            continue
        ok = send_text(number, text)
        if ok:
            logger.info("Alerta enviado para %s (%s)", name, number)
        else:
            logger.warning("Falha ao enviar para %s (%s)", name, number)


def set_webhook(webhook_url: str) -> bool:
    """
    Configura o webhook da instância para receber mensagens recebidas.
    Deve ser chamado uma vez na inicialização.
    """
    url = f"{config.EVOLUTION_API_URL}/webhook/set/{config.EVOLUTION_INSTANCE}"
    payload = {
        "url": webhook_url,
        "webhook_by_events": False,
        "webhook_base64": False,
        "events": ["MESSAGES_UPSERT"],
    }
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=10)
        resp.raise_for_status()
        logger.info("Webhook configurado: %s", webhook_url)
        return True
    except requests.RequestException as e:
        logger.error("Erro ao configurar webhook: %s", e)
        return False


def get_instance_status() -> str | None:
    """Retorna o status de conexão da instância ('open', 'close', etc.)."""
    url = f"{config.EVOLUTION_API_URL}/instance/connectionState/{config.EVOLUTION_INSTANCE}"
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("instance", {}).get("state")
    except requests.RequestException as e:
        logger.error("Erro ao verificar status da instância: %s", e)
        return None
