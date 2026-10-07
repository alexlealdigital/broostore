"""Config centralizada: padrões idênticos ao original, SECRET_KEY, engine, CORS e 'env só em config.py'."""
import re
from pathlib import Path

import pytest

from broostore_api import config, create_app
from broostore_api.extensions import db

API = Path(__file__).resolve().parent.parent


def test_padroes_sem_variaveis(monkeypatch):
    for name in ("SECRET_KEY", "MERCADOPAGO_ACCESS_TOKEN", "EMAIL_USER", "EMAIL_PASSWORD", "SMTP_PORT", "ADMIN_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    s = config.get_settings()
    assert s.database_url == "sqlite:///cobrancas.db"
    assert s.secret_key == "asdf#FGSgvasgf$5$WGT" and s.secret_key_is_default
    assert s.supabase_url == "https://gyepvrzkwesohbagpgfa.supabase.co"
    assert s.supabase_anon_key.startswith("eyJhbGciOiJIUzI1NiIs") and s.supabase_anon_key.endswith("ePwzEE8FjikLiTyjbtJXUtIIwFRlaSf5RYe7iKMDnTA")
    assert s.redis_url == "redis://localhost:6379" and s.redis_url_raw is None
    assert s.smtp_port() == 587
    assert s.melhor_envio_url == "https://www.melhorenvio.com.br/api/v2"
    assert s.melhor_envio_email == "entrega.broo@zohomail.com"
    assert s.broostock_url == "https://brootechstock.netlify.app/login"
    assert s.webhook_validate_signature is False and s.admin_token == ""
    assert s.email_user is None and s.port == 5000


def test_smtp_padrao_zoho(monkeypatch):
    monkeypatch.delenv("SMTP_SERVER")
    assert config.get_settings().smtp_server == "smtp.zoho.com"


@pytest.mark.parametrize("entrada,saida", [
    ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("sqlite:///x.db", "sqlite:///x.db"),
])
def test_normalize_db_url(entrada, saida):
    assert config.normalize_db_url(entrada) == saida


def test_connect_args_so_no_postgres():
    pg = config.build_engine_options("postgresql+psycopg://u:p@h/db", 3600)
    assert pg == {"pool_pre_ping": True, "pool_recycle": 3600, "connect_args": {"prepare_threshold": None}}
    lite = config.build_engine_options("sqlite:///x.db", 3600)
    assert lite == {"pool_pre_ping": True, "pool_recycle": 3600}


def test_pool_recycle_web_3600_worker_300(tmp_path):
    uri = f"sqlite:///{tmp_path / 'a.db'}"
    web = create_app({"SQLALCHEMY_DATABASE_URI": uri})
    worker = create_app({"SQLALCHEMY_DATABASE_URI": uri}, role="worker")
    assert web.config["SQLALCHEMY_ENGINE_OPTIONS"]["pool_recycle"] == 3600
    assert worker.config["SQLALCHEMY_ENGINE_OPTIONS"]["pool_recycle"] == 300
    for a in (web, worker):
        with a.app_context():
            db.engine.dispose()


def test_worker_nao_registra_rotas(tmp_path):
    a = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'w.db'}"}, role="worker")
    assert not [r for r in a.url_map.iter_rules() if r.rule.startswith("/api")]


def test_aviso_quando_secret_key_cai_no_padrao(monkeypatch, caplog, tmp_path):
    monkeypatch.delenv("SECRET_KEY")
    with caplog.at_level("WARNING", logger="broostore"):
        a = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 's.db'}"})
    assert "SECRET_KEY não definida" in caplog.text and a.config["SECRET_KEY"] == "asdf#FGSgvasgf$5$WGT"


def test_sem_aviso_quando_secret_key_definida(caplog, tmp_path):
    with caplog.at_level("WARNING", logger="broostore"):
        create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 's.db'}"})
    assert "SECRET_KEY" not in caplog.text


def test_cors_origens_identicas_ao_original():
    assert config.CORS_ORIGINS == [
        "https://rread.netlify.app", "https://mercadopago-final.onrender.com", "https://rankedsale.netlify.app",
        "https://broostore.netlify.app", "https://brootechstock.netlify.app"]
    assert config.CORS_METHODS == ["GET", "POST", "OPTIONS"]
    assert config.CORS_ALLOW_HEADERS == ["Content-Type", "Authorization", "X-Requested-With"]


def test_cors_preflight_origem_permitida_e_negada(client):
    ok = client.options("/api/cobrancas", headers={"Origin": "https://rread.netlify.app",
                                                    "Access-Control-Request-Method": "POST"})
    assert ok.headers["Access-Control-Allow-Origin"] == "https://rread.netlify.app"
    assert set(ok.headers["Access-Control-Allow-Methods"].split(", ")) == {"GET", "POST", "OPTIONS"}
    no = client.options("/api/cobrancas", headers={"Origin": "https://nao-permitida.example",
                                                    "Access-Control-Request-Method": "POST"})
    assert "Access-Control-Allow-Origin" not in no.headers


def test_variaveis_de_ambiente_so_sao_lidas_em_config_py():
    ofensores = []
    for arquivo in list((API / "broostore_api").rglob("*.py")) + list((API / "scripts").rglob("*.py")):
        if arquivo.name == "config.py":
            continue
        if re.search(r"os\.environ|os\.getenv|getenv\(", arquivo.read_text(encoding="utf-8")):
            ofensores.append(str(arquivo.relative_to(API)))
    assert ofensores == []


def test_env_example_documenta_todas_as_variaveis():
    fonte = (API / "broostore_api" / "config.py").read_text(encoding="utf-8")
    usadas = set(re.findall(r'env(?:\.get\(|\[)\s*"([A-Z_]+)"', fonte))
    exemplo = (API / ".env.example").read_text(encoding="utf-8")
    faltando = [v for v in sorted(usadas) if not re.search(rf"^#?\s*{v}=", exemplo, re.M)]
    assert faltando == []
    assert len(usadas) >= 20
