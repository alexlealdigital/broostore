"""Caracterização de /api/licenca/status e /api/licenca/trial."""
from datetime import datetime, timedelta

from tests.helpers import add_licenca


def test_status_sem_email_400(client):
    r = client.get("/api/licenca/status")
    assert r.status_code == 400
    assert r.get_json() == {"ativa": False, "motivo": "email_ausente"}


def test_status_email_so_espacos_400(client):
    r = client.get("/api/licenca/status?email=%20%20")
    assert r.status_code == 400


def test_status_nunca_teve_licenca_pode_testar(client):
    r = client.get("/api/licenca/status?email=novo@example.test")
    assert r.status_code == 200
    assert r.get_json() == {"ativa": False, "plano": None, "status": None, "expira_em": None,
                            "is_trial": False, "pode_testar": True, "dias_restantes": 0}


def test_status_licenca_ativa(client, db_session):
    expira = datetime.utcnow() + timedelta(days=10, hours=1)
    add_licenca("cli@example.test", expira, status="ativa", plano="mensal")
    r = client.get("/api/licenca/status?email=CLI@Example.test")  # e-mail normalizado (lower)
    j = r.get_json()
    assert r.status_code == 200
    assert j["ativa"] is True and j["plano"] == "mensal" and j["status"] == "ativa"
    assert j["is_trial"] is False and j["pode_testar"] is False and j["dias_restantes"] == 10
    assert j["expira_em"] == expira.isoformat()


def test_status_licenca_expirada(client, db_session):
    add_licenca("old@example.test", datetime.utcnow() - timedelta(days=1), status="ativa")
    j = client.get("/api/licenca/status?email=old@example.test").get_json()
    assert j["ativa"] is False and j["dias_restantes"] == 0 and j["pode_testar"] is False


def test_status_licenca_status_expirado_mesmo_com_data_futura(client, db_session):
    add_licenca("x@example.test", datetime.utcnow() + timedelta(days=5), status="expirado")
    assert client.get("/api/licenca/status?email=x@example.test").get_json()["ativa"] is False


def test_status_pega_a_licenca_que_expira_mais_tarde(client, db_session):
    add_licenca("m@example.test", datetime.utcnow() + timedelta(days=2), plano="a")
    add_licenca("m@example.test", datetime.utcnow() + timedelta(days=40), plano="b")
    assert client.get("/api/licenca/status?email=m@example.test").get_json()["plano"] == "b"


def test_trial_cria_201_e_envia_boas_vindas(client, world):
    r = client.post("/api/licenca/trial", json={"email": "  Novo@Example.test "})
    j = r.get_json()
    assert r.status_code == 201
    assert j["ok"] is True and j["status"] == "trial" and j["dias_restantes"] == 7
    assert datetime.fromisoformat(j["expira_em"]) > datetime.utcnow() + timedelta(days=6)
    msgs = world.smtp.messages()
    assert len(msgs) == 1 and msgs[0]["to"] == "novo@example.test"
    assert msgs[0]["subject"] == "Bem-vindo ao BrooStock — seus 7 dias grátis começaram 🎉"
    assert "https://brootechstock.netlify.app/painel" in msgs[0]["html"]
    # SMTP padrão: porta 587 + STARTTLS, timeout 15
    assert world.smtp.connections == [("SMTP", "smtp.example.test", 587, 15)] and world.smtp.starttls_calls == 1
    st = client.get("/api/licenca/status?email=novo@example.test").get_json()
    assert st["ativa"] is True and st["is_trial"] is True and st["plano"] == "trial"


def test_trial_segundo_pedido_409(client):
    assert client.post("/api/licenca/trial", json={"email": "a@example.test"}).status_code == 201
    r = client.post("/api/licenca/trial", json={"email": "a@example.test"})
    assert r.status_code == 409
    assert r.get_json() == {"ok": False, "motivo": "ja_utilizado", "ativa": True}


def test_trial_email_ausente_400(client):
    r = client.post("/api/licenca/trial", json={})
    assert r.status_code == 400 and r.get_json() == {"ok": False, "motivo": "email_ausente"}


def test_trial_email_via_query_string(client):
    assert client.post("/api/licenca/trial?email=q@example.test").status_code == 201


def test_trial_nao_quebra_se_smtp_falhar(client, world):
    world.smtp.fail_connect = True
    r = client.post("/api/licenca/trial", json={"email": "falha@example.test"})
    assert r.status_code == 201 and world.smtp.sent == []


def test_trial_sem_credenciais_smtp_nao_envia(client, world, monkeypatch):
    monkeypatch.delenv("EMAIL_USER")
    assert client.post("/api/licenca/trial", json={"email": "s@example.test"}).status_code == 201
    assert world.smtp.sent == []
