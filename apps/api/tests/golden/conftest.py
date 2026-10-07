"""Fixtures da comparação golden: dublês, app ORIGINAL (SQLite) e app NOVO."""
import pytest

from broostore_api import extensions, jobs
from tests.conftest import install_fakes
from tests.golden.harness import Original


@pytest.fixture
def mundo(monkeypatch):
    return install_fakes(monkeypatch)


@pytest.fixture
def original(tmp_path, monkeypatch, mundo):
    orig = Original(tmp_path, monkeypatch)
    with orig.worker_module.app.app_context():
        orig.worker_module.db.create_all()    # em produção a tabela 'sales' é criada pelo worker
    orig.attach_queue(mundo.queue, monkeypatch)
    yield orig
    orig.close()


@pytest.fixture
def nova(tmp_path, mundo):
    from broostore_api import create_app
    from broostore_api.extensions import db
    application = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'novo.db'}"})
    extensions.set_queue(mundo.queue)
    jobs.set_job_app(application)
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()
    extensions.set_queue(None)
    jobs.set_job_app(None)
