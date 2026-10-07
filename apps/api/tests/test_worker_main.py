"""``python worker.py``: REDIS_URL obrigatório, Worker com scheduler (necessário para o Retry com intervalo)."""
import pytest

from broostore_api import worker_main


class _Redis:
    def ping(self):
        return True


def test_sem_redis_url_levanta(monkeypatch):
    with pytest.raises(ValueError, match="REDIS_URL não configurada."):
        worker_main.main()


def test_redis_fora_encerra_com_1(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    with pytest.raises(SystemExit) as exc:
        worker_main.main()
    assert exc.value.code == 1


def test_inicia_worker_com_scheduler(monkeypatch, app):
    monkeypatch.setenv("REDIS_URL", "redis://fake")
    monkeypatch.setattr(worker_main.redis, "from_url", lambda url: _Redis())
    capturado = {}

    class FakeWorker:
        def __init__(self, queues, connection=None):
            capturado["queues"], capturado["conn"] = queues, connection

        def work(self, **kwargs):
            capturado["work"] = kwargs

    monkeypatch.setattr(worker_main, "Worker", FakeWorker)
    worker_main.main()   # o app do job é o app de teste (jobs.set_job_app na fixture)
    assert capturado["queues"] == ["default"] and capturado["work"] == {"with_scheduler": True}
