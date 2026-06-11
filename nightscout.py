"""
Cliente para a API do Nightscout.
Documentação: https://nightscout.github.io/nightscout/api/
"""
import hashlib
import logging
from datetime import datetime, timezone

import requests

import config

logger = logging.getLogger(__name__)

# Setas de tendência do Nightscout → emoji legível
DIRECTION_MAP = {
    "DoubleUp": "⬆⬆ Subindo muito rápido",
    "SingleUp": "⬆ Subindo",
    "FortyFiveUp": "↗ Subindo levemente",
    "Flat": "→ Estável",
    "FortyFiveDown": "↘ Descendo levemente",
    "SingleDown": "⬇ Descendo",
    "DoubleDown": "⬇⬇ Descendo muito rápido",
    "NOT COMPUTABLE": "? Não calculável",
    "RATE OUT OF RANGE": "! Fora do intervalo",
}


def _headers() -> dict:
    """Monta os headers de autenticação para o Nightscout."""
    headers = {"Content-Type": "application/json"}
    if config.NIGHTSCOUT_API_SECRET:
        hashed = hashlib.sha1(config.NIGHTSCOUT_API_SECRET.encode()).hexdigest()
        headers["api-secret"] = hashed
    return headers


def _params() -> dict:
    """Parâmetros de query opcionais (token)."""
    params = {}
    if config.NIGHTSCOUT_TOKEN:
        params["token"] = config.NIGHTSCOUT_TOKEN
    return params


def get_latest_entry() -> dict | None:
    """
    Retorna a leitura mais recente do Nightscout.

    Retorna um dict com:
        sgv       - valor da glicose em mg/dL
        date      - datetime (UTC)
        direction - string de tendência
        direction_emoji - texto legível com emoji
    Retorna None se houver erro.
    """
    url = f"{config.NIGHTSCOUT_URL}/api/v1/entries/current.json"
    try:
        resp = requests.get(
            url,
            headers=_headers(),
            params=_params(),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        # A API pode retornar lista ou objeto único
        if isinstance(data, list):
            if not data:
                logger.warning("Nightscout retornou lista vazia")
                return None
            entry = data[0]
        else:
            entry = data

        sgv = entry.get("sgv")
        date_ms = entry.get("date")  # timestamp em milissegundos
        direction = entry.get("direction", "Flat")

        if sgv is None or date_ms is None:
            logger.warning("Entrada do Nightscout sem sgv ou date: %s", entry)
            return None

        dt = datetime.fromtimestamp(date_ms / 1000, tz=timezone.utc)

        return {
            "sgv": sgv,
            "date": dt,
            "direction": direction,
            "direction_emoji": DIRECTION_MAP.get(direction, direction),
        }

    except requests.RequestException as e:
        logger.error("Erro ao consultar Nightscout: %s", e)
        return None


def format_reading(entry: dict) -> str:
    """Formata uma leitura para envio via WhatsApp."""
    sgv = entry["sgv"]
    dt_local = entry["date"].astimezone()  # converte para fuso local do container
    date_str = dt_local.strftime("%d/%m/%Y %H:%M")
    direction = entry["direction_emoji"]

    return (
        f"🩸 *Glicose:* {sgv} mg/dL\n"
        f"📈 *Tendência:* {direction}\n"
        f"🕐 *Medição:* {date_str}"
    )
