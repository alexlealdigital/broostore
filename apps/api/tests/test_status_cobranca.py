"""F4 — GET /api/cobrancas/<external_reference>/status (aditivo)."""
import pytest

from tests.helpers import add_cobranca, add_produto


@pytest.mark.parametrize("status,pago", [("pending", False), ("in_process", False), ("rejected", False),
                                         ("approved", True), ("delivered", True)])
def test_status_por_estado(client, db_session, status, pago):
    add_produto(1)
    add_cobranca("abc-123", status=status)
    r = client.get("/api/cobrancas/abc-123/status")
    assert r.status_code == 200
    assert r.get_json() == {"status": status, "pago": pago}


def test_status_nao_expoe_dados_pessoais(client, db_session):
    add_produto(1)
    add_cobranca("abc-123", status="approved", email="segredo@example.test", nome="Fulano Secreto")
    r = client.get("/api/cobrancas/abc-123/status")
    assert set(r.get_json()) == {"status", "pago"}
    assert b"segredo" not in r.data and b"Fulano" not in r.data


def test_status_desconhecido_404(client):
    r = client.get("/api/cobrancas/nao-existe/status")
    assert r.status_code == 404
    assert r.get_json() == {"status": "error", "message": "Cobrança não encontrada."}


def test_status_com_external_reference_de_moedas(client, db_session):
    add_produto(7)
    add_cobranca("user-1:uuid-xyz", produto_id=7, status="delivered")
    assert client.get("/api/cobrancas/user-1:uuid-xyz/status").get_json() == {"status": "delivered", "pago": True}


def test_status_cors_e_sem_cache(client, db_session):
    add_produto(1)
    add_cobranca("abc", status="pending")
    r = client.get("/api/cobrancas/abc/status", headers={"Origin": "https://broostore.netlify.app"})
    assert r.headers["Access-Control-Allow-Origin"] == "https://broostore.netlify.app"
    assert r.headers["Cache-Control"] == "no-store"
    r = client.get("/api/cobrancas/nao/status", headers={"Origin": "https://broostore.netlify.app"})
    assert r.status_code == 404 and r.headers["Access-Control-Allow-Origin"] == "https://broostore.netlify.app"


def test_status_origem_nao_permitida_sem_cors(client, db_session):
    r = client.get("/api/cobrancas/abc/status", headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in r.headers


def test_status_preflight_options(client):
    r = client.options("/api/cobrancas/abc/status", headers={
        "Origin": "https://broostore.netlify.app", "Access-Control-Request-Method": "GET"})
    assert r.status_code == 200 and r.headers["Access-Control-Allow-Origin"] == "https://broostore.netlify.app"


def test_rota_pix_post_continua_existindo(client):
    # a nova rota não pode ter engolido /api/cobrancas
    assert client.post("/api/cobrancas", json={}).status_code == 400
