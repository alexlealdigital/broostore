import socket
import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from tests import fakes  # noqa: E402


@pytest.fixture(autouse=True)
def _ambiente_isolado(monkeypatch):
    """Variáveis de ambiente controladas + rede bloqueada (nenhum serviço real é chamado)."""
    for name in fakes.ALL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    for name, value in fakes.FAKE_ENV.items():
        monkeypatch.setenv(name, value)

    def _sem_rede(self, *args, **kwargs):
        raise AssertionError("Acesso à rede bloqueado nos testes")
    monkeypatch.setattr(socket.socket, "connect", _sem_rede)

    import redis

    def _sem_redis(*args, **kwargs):
        raise ConnectionError("Redis real bloqueado nos testes")
    monkeypatch.setattr(redis, "from_url", _sem_redis)


def install_fakes(monkeypatch):
    """Instala os dublês globais (requests, mercadopago.SDK, smtplib, resend, time.sleep)."""
    import mercadopago
    import requests
    import resend

    http = fakes.FakeHTTP()
    mp = fakes.MPState()
    smtp = fakes.SMTPState()
    queue = fakes.FakeQueue()
    resend_state = {"calls": [], "response": {"id": "email_fake_id"}, "raises": None}

    monkeypatch.setattr(requests, "get", http.get)
    monkeypatch.setattr(requests, "post", http.post)
    monkeypatch.setattr(mercadopago, "SDK", fakes.make_fake_sdk(mp))
    fake_smtp, fake_smtp_ssl = fakes.make_fake_smtp_classes(smtp)
    import smtplib
    monkeypatch.setattr(smtplib, "SMTP", fake_smtp)
    monkeypatch.setattr(smtplib, "SMTP_SSL", fake_smtp_ssl)

    def fake_send(params):
        resend_state["calls"].append(params)
        if resend_state["raises"]:
            raise resend_state["raises"]
        return resend_state["response"]
    monkeypatch.setattr(resend.Emails, "send", staticmethod(fake_send))

    import time
    monkeypatch.setattr(time, "sleep", lambda s: None)
    return fakes.World(http, mp, smtp, queue, resend_state)


@pytest.fixture
def world(monkeypatch):
    return install_fakes(monkeypatch)


@pytest.fixture
def app(world, tmp_path):
    from broostore_api import create_app, extensions, jobs
    from broostore_api.extensions import db

    application = create_app({
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "TESTING": True,
    })
    extensions.set_queue(world.queue)
    jobs.set_job_app(application)
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()
    extensions.set_queue(None)
    jobs.set_job_app(None)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    from broostore_api.extensions import db
    with app.app_context():
        yield db.session
        db.session.remove()
