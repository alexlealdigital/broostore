"""GET /api/admin/dashboard — autenticação por ADMIN_TOKEN e agregações."""
import json
from datetime import datetime, timedelta

from tests.helpers import add_cobranca, add_cupom, add_produto

H = {"X-Admin-Token": "fake-admin-token"}


def test_sem_token_401(client):
    r = client.get("/api/admin/dashboard")
    assert r.status_code == 401 and r.get_json() == {"erro": "Não autorizado"}


def test_token_errado_401(client):
    assert client.get("/api/admin/dashboard", headers={"X-Admin-Token": "errado"}).status_code == 401


def test_admin_token_nao_configurado_sempre_401(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN")
    assert client.get("/api/admin/dashboard", headers={"X-Admin-Token": ""}).status_code == 401
    assert client.get("/api/admin/dashboard", headers=H).status_code == 401


def test_dashboard_vazio(client):
    r = client.get("/api/admin/dashboard", headers=H)
    j = r.get_json()
    assert r.status_code == 200 and j["periodo"] == "30d"
    assert j["metricas"] == {"bruto": 0.0, "frete": 0.0, "produtos": 0.0, "pedidos": 0, "ticket_medio": 0.0}
    assert j["comparacao"] is None and j["serie"] == [] and j["top_produtos"] == [] and j["envios_pendentes"] == []
    assert set(j["por_categoria"]) == {"digital", "fisico", "jogos_apps"}


def test_dashboard_agrega_pagos_approved_e_delivered(client, db_session):
    add_produto(1, nome="Ebook", tipo="ebook")
    add_produto(2, nome="Livro", tipo="fisico")
    add_produto(3, nome="Jogo", tipo="game")
    add_cupom("CUP")
    add_cobranca("a", produto_id=1, status="delivered", valor=40.0)
    add_cobranca("b", produto_id=3, status="approved", valor=60.0)
    add_cobranca("c", produto_id=1, status="pending", valor=999.0)   # não conta como venda
    obs = json.dumps({"endereco": {"cidade": "SP"}, "frete": 20.0, "subtotal_produto": 80.0, "transportadora": "Correios PAC"})
    add_cobranca("d", produto_id=2, status="delivered", valor=100.0, observacoes=obs)
    j = client.get("/api/admin/dashboard?periodo=7d", headers=H).get_json()
    assert j["periodo"] == "7d"
    assert j["metricas"] == {"bruto": 200.0, "frete": 20.0, "produtos": 180.0, "pedidos": 3, "ticket_medio": 66.67}
    assert j["por_categoria"]["fisico"] == {"subtotal": 80.0, "pedidos": 1}
    assert j["por_categoria"]["jogos_apps"] == {"subtotal": 60.0, "pedidos": 1}
    assert j["por_categoria"]["digital"] == {"subtotal": 40.0, "pedidos": 1}
    assert j["por_status"] == {"delivered": 2, "approved": 1, "pending": 1}
    assert [t["nome"] for t in j["top_produtos"]] == ["Livro", "Jogo", "Ebook"]
    assert len(j["ultimas_vendas"]) == 3
    assert j["envios_pendentes"][0]["transportadora"] == "Correios PAC" and j["envios_pendentes"][0]["endereco"] == {"cidade": "SP"}


def test_dashboard_periodo_todos_e_comparacao(client, db_session):
    add_produto(1, nome="Ebook")
    add_cobranca("recente", status="delivered", valor=50.0)
    from broostore_api.models import Cobranca
    antiga = add_cobranca("antiga", status="delivered", valor=25.0)
    antiga.data_criacao = datetime.utcnow() - timedelta(days=40)
    db_session.commit()
    j = client.get("/api/admin/dashboard?periodo=30d", headers=H).get_json()
    assert j["metricas"]["pedidos"] == 1 and j["comparacao"] == {"bruto": 100.0, "pedidos": 0.0}
    j = client.get("/api/admin/dashboard?periodo=todos", headers=H).get_json()
    assert j["metricas"]["pedidos"] == 2 and j["comparacao"] is None
    assert Cobranca.query.count() == 2


def test_cors_do_painel_so_com_dashboard_origin(client):
    # padrão: sem DASHBOARD_ORIGIN o CORS é idêntico ao original (X-Admin-Token não liberado)
    r = client.options("/api/admin/dashboard", headers={
        "Origin": "https://painel.example", "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-Admin-Token"})
    assert "Access-Control-Allow-Origin" not in r.headers


def test_cors_do_painel_com_dashboard_origin(world, tmp_path, monkeypatch):
    from broostore_api import create_app
    monkeypatch.setenv("DASHBOARD_ORIGIN", "https://painel.example")
    app2 = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'c.db'}"})
    r = app2.test_client().options("/api/admin/dashboard", headers={
        "Origin": "https://painel.example", "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-Admin-Token"})
    assert r.headers["Access-Control-Allow-Origin"] == "https://painel.example"
    assert "X-Admin-Token" in r.headers["Access-Control-Allow-Headers"]


def test_cors_extra_origins(world, tmp_path, monkeypatch):
    from broostore_api import create_app
    monkeypatch.setenv("CORS_EXTRA_ORIGINS", "https://www.loja.example/, https://outra.example")
    app2 = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'e.db'}"})
    for origem in ("https://www.loja.example", "https://outra.example"):
        r = app2.test_client().options("/api/cobrancas", headers={
            "Origin": origem, "Access-Control-Request-Method": "POST"})
        assert r.headers["Access-Control-Allow-Origin"] == origem
    r = app2.test_client().options("/api/cobrancas", headers={
        "Origin": "https://intruso.example", "Access-Control-Request-Method": "POST"})
    assert "Access-Control-Allow-Origin" not in r.headers
