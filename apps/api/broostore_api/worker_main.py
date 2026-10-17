"""Inicialização do worker RQ (``python worker.py``)."""
import logging
import sys

import redis
from rq import Worker
from rq.defaults import DEFAULT_LOGGING_DATE_FORMAT, DEFAULT_LOGGING_FORMAT
from rq.scheduler import RQScheduler

from .config import configure_logging, get_settings
from .extensions import db
from .jobs import get_job_app

logger = logging.getLogger("broostore")

class ThrottledWorker(Worker):
    """Worker do RQ cujo agendador consulta o Redis a cada ``rq_scheduler_interval_s`` s.

    O agendador (necessário para os retries com intervalo) consulta o Redis a cada 1 s por
    padrão: ~780 mil comandos/dia mesmo sem nenhuma venda, o que estoura qualquer plano que
    limita ou cobra por comando (ex.: Upstash grátis = 500 mil/mês). Com 120 s o consumo cai
    ~100x e os retries só esperam até 2 min a mais (config.DEFAULT_RQ_SCHEDULER_INTERVAL_S).
    """

    def _start_scheduler(self, burst=False, logging_level="INFO",
                         date_format=DEFAULT_LOGGING_DATE_FORMAT, log_format=DEFAULT_LOGGING_FORMAT):
        self.scheduler = RQScheduler(
            self.queues,
            connection=self.connection,
            interval=get_settings().rq_scheduler_interval_s,
            logging_level=logging_level if logging_level is not None else self.log.level,
            date_format=date_format,
            log_format=log_format,
            serializer=self.serializer,
        )
        self.scheduler.acquire_locks()
        if self.scheduler.acquired_locks:
            if burst:
                try:
                    self.scheduler.register_birth()
                    self.scheduler.enqueue_scheduled_jobs()
                finally:
                    self.scheduler.release_locks()
                    self.scheduler.register_death()
            else:
                self.scheduler.start()


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
        worker = ThrottledWorker(["default"], connection=redis_conn)
        logger.info("[WORKER] 🚀 Worker iniciado...")
        worker.work(with_scheduler=True)
    except Exception as e:
        logger.error(f"[WORKER] ❌ Erro fatal: {e}")
