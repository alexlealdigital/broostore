"""Vários apps na mesma loja: licença por e-mail E por app, rotas com ?app=, e-mails e CORS por app."""
from datetime import datetime, timedelta

import pytest

from broostore_api import apps_config, jobs
from broostore_api.extensions import db
from broostore_api.models import Licenca
from tests.helpers import add_cobranca, add_licenca, add_plano, add_produto

MEUAPP = {"nome": "MeuApp", "url": "https://meuapp.example.test", "login_path": "/entrar", "painel_path": "/home",
          "trial_dias": 14, "uso": "suas planilhas", "boas_vindas_passos": ["Crie seu primeiro projeto."]}


@pytest.fixture
def meuapp(monkeypatch):
    monkeypatch.setitem(apps_config.APPS, "meuapp", MEUAPP)


class TestRotas:
    def test_status_sem_param_app_e_broostock(self, client, db_session):
        add_licenca("a@example.test", datetime.utcnow() + timedelta(days=5), app="broostock")
        assert client.get("/api/licenca/status?email=a@example.test").get_json()["app"] == "broostock"

    def test_app_desconhecido_da_400(self, client):
        r = client.get("/api/licenca/status?email=a@example.test&app=nao-existe")
        assert r.status_code == 400 and r.get_json() == {"ativa": False, "motivo": "app_desconhecido"}
        r = client.post("/api/licenca/trial", json={"email": "a@example.test", "app": "nao-existe"})
        assert r.status_code == 400 and r.get_json()["motivo"] == "app_desconhecido"

    def test_status_e_isolado_por_app(self, client, db_session, meuapp):
        add_licenca("a@example.test", datetime.utcnow() + timedelta(days=5), app="broostock")
        so_stock = client.get("/api/licenca/status?email=a@example.test&app=broostock").get_json()
        so_meu = client.get("/api/licenca/status?email=a@example.test&app=meuapp").get_json()
        assert so_stock["ativa"] is True and so_stock["pode_testar"] is False
        assert so_meu["ativa"] is False and so_meu["pode_testar"] is True and so_meu["app"] == "meuapp"

    def test_trial_sem_app_continua_sendo_broostock_7_dias(self, client):
        j = client.post("/api/licenca/trial", json={"email": "a@example.test"}).get_json()
        assert j["app"] == "broostock" and j["dias_restantes"] == 7

    def test_trial_por_app_isolado(self, client, world, meuapp):
        assert client.post("/api/licenca/trial", json={"email": "a@example.test"}).status_code == 201
        r = client.post("/api/licenca/trial?app=meuapp", json={"email": "a@example.test"})   # outro app: pode testar
        j = r.get_json()
        assert r.status_code == 201 and j["dias_restantes"] == 14 and j["app"] == "meuapp"
        assert datetime.fromisoformat(j["expira_em"]) > datetime.utcnow() + timedelta(days=13)
        r2 = client.post("/api/licenca/trial", json={"email": "a@example.test", "app": "meuapp"})
        assert r2.status_code == 409 and r2.get_json()["motivo"] == "ja_utilizado"
        with client.application.app_context():
            assert {lic.app_slug for lic in Licenca.query.all()} == {"broostock", "meuapp"}

    def test_boas_vindas_usam_nome_e_link_do_app(self, client, world, meuapp):
        client.post("/api/licenca/trial", json={"email": "a@example.test", "app": "meuapp"})
        (msg,) = world.smtp.messages()
        assert msg["subject"] == "Bem-vindo ao MeuApp — seus 14 dias grátis começaram 🎉"
        assert "https://meuapp.example.test/home" in msg["html"] and "Crie seu primeiro projeto." in msg["html"]
        assert "BrooStock" not in msg["html"]

    def test_cors_inclui_origem_do_app_novo(self, monkeypatch, tmp_path, world):
        from broostore_api import create_app
        monkeypatch.setitem(apps_config.APPS, "meuapp", MEUAPP)
        app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'cors.db'}", "TESTING": True})
        r = app.test_client().options("/api/licenca/status", headers={
            "Origin": "https://meuapp.example.test", "Access-Control-Request-Method": "GET"})
        assert r.headers.get("Access-Control-Allow-Origin") == "https://meuapp.example.test"


class TestJobPorApp:
    def test_compra_cria_licenca_do_app_certo_sem_tocar_na_do_outro(self, world, db_session, meuapp):
        add_licenca("a@example.test", datetime.utcnow() + timedelta(days=3), app="broostock")
        add_produto(20, nome="MeuApp Mensal", tipo="assinatura")
        add_plano(20, dias=30, rotulo="mensal", app="meuapp")
        add_cobranca("ref-1", produto_id=20, email="A@example.test")
        world.mp.set_payment(555, "approved", "ref-1")
        jobs.process_mercado_pago_webhook(555)
        db.session.expire_all()
        por_app = {lic.app_slug: lic for lic in Licenca.query.all()}
        assert set(por_app) == {"broostock", "meuapp"}
        assert por_app["meuapp"].plano == "mensal" and por_app["meuapp"].status == "ativa"
        assert por_app["broostock"].expira_em < datetime.utcnow() + timedelta(days=4)     # intacta

    def test_renovar_soma_dias_so_no_mesmo_app(self, world, db_session, meuapp):
        expira = datetime.utcnow() + timedelta(days=10)
        add_licenca("a@example.test", expira, app="meuapp")
        add_licenca("a@example.test", expira, app="broostock")
        add_produto(20, tipo="assinatura")
        add_plano(20, dias=30, rotulo="mensal", app="meuapp")
        add_cobranca("ref-1", produto_id=20, email="a@example.test")
        world.mp.set_payment(555, "approved", "ref-1")
        jobs.process_mercado_pago_webhook(555)
        db.session.expire_all()
        por_app = {lic.app_slug: lic for lic in Licenca.query.all()}
        assert abs((por_app["meuapp"].expira_em - expira).days - 30) <= 1
        assert por_app["broostock"].expira_em == expira

    def test_email_de_licenca_usa_nome_e_link_do_app(self, world, db_session, meuapp):
        add_produto(20, tipo="assinatura")
        add_plano(20, dias=30, rotulo="mensal", app="meuapp")
        add_cobranca("ref-1", produto_id=20, email="a@example.test")
        world.mp.set_payment(555, "approved", "ref-1")
        jobs.process_mercado_pago_webhook(555)
        (msg,) = world.smtp.messages()
        assert msg["subject"] == "MeuApp: Sua licença está ativa! 🚀" and "Licença MeuApp ativada" in msg["html"]
        assert "https://meuapp.example.test/entrar" in msg["html"]

    def test_retry_de_assinatura_mantem_o_app_no_email(self, world, db_session, meuapp):
        add_produto(20, tipo="assinatura")
        add_plano(20, dias=30, rotulo="mensal", app="meuapp")
        add_cobranca("ref-1", produto_id=20, email="a@example.test")
        world.mp.set_payment(555, "approved", "ref-1")
        world.smtp.fail_login = True
        with pytest.raises(jobs.EmailEntregaFalhou):
            jobs.process_mercado_pago_webhook(555)
        world.smtp.fail_login = False
        jobs.process_mercado_pago_webhook(555)
        (msg,) = world.smtp.messages()
        assert msg["subject"].startswith("MeuApp:")
        db.session.expire_all()
        assert Licenca.query.count() == 1

    def test_plano_sem_app_vira_broostock(self, world, db_session):
        add_produto(10, tipo="assinatura")
        add_plano(10, dias=30, rotulo="mensal")                 # default da coluna
        add_cobranca("ref-1", produto_id=10, email="a@example.test")
        world.mp.set_payment(555, "approved", "ref-1")
        jobs.process_mercado_pago_webhook(555)
        db.session.expire_all()
        assert Licenca.query.one().app_slug == "broostock"
