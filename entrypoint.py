"""
Entrypoint para execução via gunicorn com --preload.

O gunicorn com --preload carrega o app ANTES de fazer fork dos workers.
Isso garante que start_monitor() seja chamado uma única vez, no processo mestre,
e o thread de monitoramento sobrevive no worker (já que usamos --workers 1).
"""
from main import app, start_monitor  # noqa: F401

start_monitor()
