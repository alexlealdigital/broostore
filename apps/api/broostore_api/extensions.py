"""Extensões compartilhadas (db, cors) e fila RQ/Redis preguiçosa.

O original conectava ao Redis no import do app.py (``redis_conn.ping()``) e, se
falhasse, deixava ``q = None`` para sempre. Aqui a conexão é criada sob demanda
(``get_queue()``); se falhar, o chamador recebe ``None`` (o webhook responde 503).
Uma nova tentativa só ocorre após ``RETRY_AFTER`` segundos, para não pagar o
timeout de conexão a cada requisição quando o Redis está fora.
"""
import logging
import time

from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from .config import get_settings

logger = logging.getLogger("broostore")

db = SQLAlchemy()
cors = CORS()

RETRY_AFTER = 30  # segundos entre tentativas de reconexão ao Redis

_state = {"queue": None, "failed_at": None}


def _connect():
    import redis
    from rq import Queue

    conn = redis.from_url(get_settings().redis_url, socket_connect_timeout=3)
    conn.ping()
    return Queue(connection=conn)


def get_queue():
    """Retorna a fila RQ ('default') ou ``None`` se o Redis estiver indisponível."""
    if _state["queue"] is not None:
        return _state["queue"]
    failed_at = _state["failed_at"]
    if failed_at is not None and (time.monotonic() - failed_at) < RETRY_AFTER:
        return None
    try:
        _state["queue"] = _connect()
        _state["failed_at"] = None
        return _state["queue"]
    except Exception as err:
        logger.error(f"[REDIS] Indisponível: {err}")
        _state["queue"] = None
        _state["failed_at"] = time.monotonic()
        return None


def set_queue(queue):
    """Injeta uma fila (testes). ``None`` limpa o cache e permite reconectar."""
    _state["queue"] = queue
    _state["failed_at"] = None


class FilaIndisponivel(Exception):
    """Redis/RQ fora do ar: não foi possível enfileirar o job."""


def enfileirar_webhook(payment_id):
    """Enfileira o job de entrega (POR STRING, como no original) com a política de retry (F1)."""
    from rq import Retry

    from .config import JOB_NAME, JOB_RETRY_INTERVALS, JOB_RETRY_MAX

    queue = get_queue()
    if queue is None:
        raise FilaIndisponivel("Fila indisponível")
    return queue.enqueue(
        JOB_NAME, payment_id,
        retry=Retry(max=JOB_RETRY_MAX, interval=JOB_RETRY_INTERVALS),
    )
