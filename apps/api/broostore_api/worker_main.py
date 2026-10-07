"""Inicialização do worker RQ (``python worker.py``)."""
import logging
import sys

import redis
from rq import Worker

from .config import configure_logging, get_settings
from .extensions import db
from .jobs import get_job_app

logger = logging.getLogger("broostore")


def main():
    configure_logging()
    redis_url = get_settings().redis_url_raw
    if not redis_url:
        raise ValueError("REDIS_URL não configurada.")

    # Conectar Redis
    try:
        redis_conn = redis.from_url(redis_url)
        redis_conn.ping()
        logger.info("[WORKER] ✅ Redis conectado.")
    except Exception as e:
        logger.error(f"[WORKER] ❌ Falha no Redis: {e}")
        sys.exit(1)

    # Criar tabelas se necessário (create_app já faz db.create_all())
    app = get_job_app()
    with app.app_context():
        db.create_all()
        logger.info("[WORKER] ✅ Tabelas verificadas.")
        # Descarta conexões abertas antes do fork do RQ (cada job roda num processo filho).
        db.engine.dispose()

    # Iniciar worker. with_scheduler=True é necessário para os retries com intervalo (F1).
    try:
        worker = Worker(["default"], connection=redis_conn)
        logger.info("[WORKER] 🚀 Worker iniciado...")
        worker.work(with_scheduler=True)
    except Exception as e:
        logger.error(f"[WORKER] ❌ Erro fatal: {e}")
