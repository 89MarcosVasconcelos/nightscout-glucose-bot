"""
Gerenciamento de contatos cadastrados para alertas.

O arquivo JSON tem o formato:
[
  {"name": "Marcos", "number": "5511999998888"},
  {"name": "Fulano", "number": "5521988887777"}
]

Números no formato E.164 sem '+': código do país + DDD + número.
Brasil: 55 + DDD (2 dígitos) + número (8 ou 9 dígitos)
Ex: 55 11 99999-8888 → "5511999998888"
"""
import json
import logging
import os

import config

logger = logging.getLogger(__name__)


def _ensure_file() -> None:
    """Cria o arquivo de contatos se não existir."""
    os.makedirs(os.path.dirname(config.CONTACTS_FILE), exist_ok=True)
    if not os.path.exists(config.CONTACTS_FILE):
        with open(config.CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        logger.info("Arquivo de contatos criado: %s", config.CONTACTS_FILE)


def load() -> list[dict]:
    """Carrega e retorna a lista de contatos."""
    _ensure_file()
    try:
        with open(config.CONTACTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Erro ao carregar contatos: %s", e)
        return []


def save(contacts: list[dict]) -> None:
    """Salva a lista de contatos no arquivo."""
    _ensure_file()
    with open(config.CONTACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(contacts, f, ensure_ascii=False, indent=2)


def add(name: str, number: str) -> bool:
    """
    Adiciona um contato. Retorna True se adicionado, False se já existe.
    """
    contacts = load()
    # Remove caracteres não-numéricos
    clean_number = "".join(c for c in number if c.isdigit())
    for c in contacts:
        if c.get("number") == clean_number:
            logger.info("Contato já existe: %s (%s)", name, clean_number)
            return False
    contacts.append({"name": name, "number": clean_number})
    save(contacts)
    logger.info("Contato adicionado: %s (%s)", name, clean_number)
    return True


def remove(number: str) -> bool:
    """Remove um contato pelo número. Retorna True se removido."""
    clean_number = "".join(c for c in number if c.isdigit())
    contacts = load()
    new_contacts = [c for c in contacts if c.get("number") != clean_number]
    if len(new_contacts) == len(contacts):
        return False
    save(new_contacts)
    logger.info("Contato removido: %s", clean_number)
    return True


def is_registered(number: str) -> bool:
    """Verifica se um número está cadastrado."""
    clean_number = "".join(c for c in number if c.isdigit())
    return any(c.get("number") == clean_number for c in load())
