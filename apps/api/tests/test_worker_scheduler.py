"""O agendador do RQ não pode consultar o Redis a cada 1 s (estoura planos por comando)."""
from broostore_api import worker_main


class _FakeScheduler:
    criados = []

    def __init__(self, queues, connection, interval=1, **kw):
        self.interval = interval
        self.acquired_locks = True
        self.iniciado = False
        _FakeScheduler.criados.append(self)

    def acquire_locks(self):
        pass

    def start(self):
        self.iniciado = True


def _worker_sem_redis():
    w = worker_main.ThrottledWorker.__new__(worker_main.ThrottledWorker)
    w.queues, w.connection, w.serializer = [], object(), None
    return w


def test_agendador_usa_intervalo_configurado(monkeypatch):
    monkeypatch.setattr(worker_main, "RQScheduler", _FakeScheduler)
    monkeypatch.delenv("RQ_SCHEDULER_INTERVAL", raising=False)
    _FakeScheduler.criados.clear()
    w = _worker_sem_redis()
    w._start_scheduler()
    assert _FakeScheduler.criados[0].interval == 120
    assert _FakeScheduler.criados[0].iniciado is True


def test_intervalo_padrao_e_bem_maior_que_o_do_rq(monkeypatch):
    from broostore_api.config import get_settings
    monkeypatch.delenv("RQ_SCHEDULER_INTERVAL", raising=False)
    assert get_settings().rq_scheduler_interval_s >= 60   # padrão do RQ = 1 s (~780 mil comandos/dia)


def test_intervalo_pode_ser_ajustado_e_valor_invalido_volta_ao_padrao(monkeypatch):
    from broostore_api.config import DEFAULT_RQ_SCHEDULER_INTERVAL_S, get_settings
    monkeypatch.setenv("RQ_SCHEDULER_INTERVAL", "30")
    assert get_settings().rq_scheduler_interval_s == 30
    for ruim in ("0", "-5", "abc", ""):
        monkeypatch.setenv("RQ_SCHEDULER_INTERVAL", ruim)
        assert get_settings().rq_scheduler_interval_s == DEFAULT_RQ_SCHEDULER_INTERVAL_S
