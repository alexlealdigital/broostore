"""Espelho da licença no Supabase do app (best-effort) + integração com trial e pagamento."""
from datetime import datetime, timedelta

import requests

from broostore_api import jobs
from broostore_api.extensions import db
from broostore_api.models import Licenca
from broostore_api.services.sync_licencas import config_do_app, montar_payload, sincronizar_licenca
from tests.helpers import add_cobranca, add_plano, add_produto

URL = "https://broostock-fake.supabase.test"


def configurar(monkeypatch, slug="BROOSTOCK", url=URL, chave="service-key-fake"):
    monkeypatch.setenv(f"{slug}_SUPABASE_URL", url)
    monkeypatch.setenv(f"{slug}_SUPABASE_SERVICE_KEY", chave)


def test_envia_upsert_por_email(world, monkeypatch):
    configurar(monkeypatch, url=URL + "/")
    expira = datetime.utcnow() + timedelta(days=30)
    assert sincronizar_licenca("broostock", " Cli@Example.test ", expira, "mensal") is True
    (url, corpo, headers), = world.http.licenses_posted
    assert url == f"{URL}/rest/v1/licenses?on_conflict=email"
    assert corpo["email"] == "cli@example.test" and corpo["ativa"] is True and corpo["plano"] == "mensal"
    assert corpo["is_trial"] is False and corpo["expira_em"].endswith("+00:00")
    assert headers["apikey"] == "service-key-fake" and headers["Authorization"] == "Bearer service-key-fake"
    assert headers["Prefer"] == "resolution=merge-duplicates,return=minimal"


def test_trial_e_licenca_inativa():
    p = montar_payload("a@x.test", None, "trial", is_trial=True, ativa=False)
    assert p["is_trial"] is True and p["ativa"] is False and p["expira_em"] is None


def test_sem_variaveis_nao_chama_a_rede(world):
    assert config_do_app("broostock") == (None, None)
    assert sincronizar_licenca("broostock", "a@x.test", datetime.utcnow(), "mensal") is False
    assert world.http.licenses_posted == []


def test_so_uma_das_variaveis_tambem_nao_chama(world, monkeypatch):
    monkeypatch.setenv("BROOSTOCK_SUPABASE_URL", URL)
    assert sincronizar_licenca("broostock", "a@x.test", datetime.utcnow(), "mensal") is False


def test_outro_app_usa_suas_proprias_variaveis(world, monkeypatch):
    configurar(monkeypatch, slug="MEUAPP", url="https://meuapp.supabase.test", chave="k2")
    assert sincronizar_licenca("meuapp", "a@x.test", datetime.utcnow(), "mensal") is True
    assert world.http.licenses_posted[0][0].startswith("https://meuapp.supabase.test/")
    assert sincronizar_licenca("broostock", "a@x.test", datetime.utcnow(), "mensal") is False


def test_falha_http_tenta_de_novo_e_nao_levanta(world, monkeypatch):
    configurar(monkeypatch)
    world.http.licenses_status = 500
    assert sincronizar_licenca("broostock", "a@x.test", datetime.utcnow(), "mensal") is False
    assert len(world.http.licenses_posted) == 2             # 2 tentativas


def test_falha_de_rede_nao_levanta(world, monkeypatch):
    configurar(monkeypatch)
    world.http.licenses_raises = requests.ConnectionError("rede fora (fake)")
    assert sincronizar_licenca("broostock", "a@x.test", datetime.utcnow(), "mensal") is False


def test_email_vazio_nao_envia(world, monkeypatch):
    configurar(monkeypatch)
    assert sincronizar_licenca("broostock", "  ", datetime.utcnow(), "mensal") is False
    assert world.http.licenses_posted == []


# ---------------------------------------------------------------------------
# Integração
# ---------------------------------------------------------------------------
def test_trial_espelha_no_app(client, world, monkeypatch):
    configurar(monkeypatch)
    r = client.post("/api/licenca/trial", json={"email": "novo@example.test"})
    assert r.status_code == 201
    (_, corpo, _), = world.http.licenses_posted
    assert corpo["email"] == "novo@example.test" and corpo["is_trial"] is True and corpo["plano"] == "trial"


def test_trial_continua_funcionando_se_o_espelho_falhar(client, world, monkeypatch):
    configurar(monkeypatch)
    world.http.licenses_raises = requests.ConnectionError("rede fora (fake)")
    r = client.post("/api/licenca/trial", json={"email": "novo@example.test"})
    assert r.status_code == 201 and r.get_json()["ok"] is True
    with client.application.app_context():
        assert Licenca.query.filter_by(cliente_email="novo@example.test").count() == 1


def test_pagamento_de_assinatura_espelha_no_app(world, db_session, monkeypatch):
    configurar(monkeypatch)
    add_produto(10, nome="BrooStock Mensal", tipo="assinatura")
    add_plano(10, dias=30, rotulo="mensal")
    add_cobranca("ref-1", produto_id=10, email="Cli@Example.test")
    world.mp.set_payment(555, "approved", "ref-1")
    jobs.process_mercado_pago_webhook(555)
    (_, corpo, _), = world.http.licenses_posted
    assert corpo["email"] == "cli@example.test" and corpo["ativa"] is True and corpo["plano"] == "mensal"
    assert corpo["is_trial"] is False


def test_pagamento_espelha_mesmo_se_o_email_falhar(world, db_session, monkeypatch):
    """O acesso ao app libera assim que o pedido é cumprido; a falha do e-mail só atrasa o aviso."""
    configurar(monkeypatch)
    add_produto(10, tipo="assinatura")
    add_plano(10, dias=30, rotulo="mensal")
    add_cobranca("ref-1", produto_id=10)
    world.mp.set_payment(555, "approved", "ref-1")
    world.smtp.fail_login = True
    try:
        jobs.process_mercado_pago_webhook(555)
    except jobs.EmailEntregaFalhou:
        pass
    assert len(world.http.licenses_posted) == 1


def test_pagamento_sem_variaveis_nao_quebra_a_entrega(world, db_session):
    add_produto(10, tipo="assinatura")
    add_plano(10, dias=30, rotulo="mensal")
    add_cobranca("ref-1", produto_id=10)
    world.mp.set_payment(555, "approved", "ref-1")
    jobs.process_mercado_pago_webhook(555)
    db.session.expire_all()
    assert world.http.licenses_posted == [] and len(world.smtp.messages()) == 1
