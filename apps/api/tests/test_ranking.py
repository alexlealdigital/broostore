"""GET /api/vendedores e /api/ranking."""
from tests.helpers import add_cobranca, add_produto, add_vendedor


def test_vendedores_ordenados_por_nome(client, db_session):
    add_vendedor("B", "Bruno")
    add_vendedor("A", "Ana")
    r = client.get("/api/vendedores")
    assert r.status_code == 200
    assert r.get_json() == [{"codigo_ranking": "A", "nome_vendedor": "Ana"},
                            {"codigo_ranking": "B", "nome_vendedor": "Bruno"}]


def test_ranking_vazio(client):
    r = client.get("/api/ranking")
    assert r.status_code == 200
    assert r.get_json() == {"status": "success", "ranking": [],
                            "meta_diaria": {"objetivo": 100, "atual": 0, "percentual_meta": 0.0}}


def test_ranking_conta_somente_delivered_e_aplica_comissao(client, db_session):
    add_produto(1)
    for cod, nome in (("A", "Ana"), ("B", "Bruno"), ("C", "Caio"), ("D", "Dani")):
        add_vendedor(cod, nome)
    n = 0
    for cod, entregues in (("A", 3), ("B", 2), ("C", 1)):
        for _ in range(entregues):
            n += 1
            add_cobranca(f"r{n}", status="delivered", vendedor_codigo=cod)
    add_cobranca("pend", status="pending", vendedor_codigo="D")
    add_cobranca("apr", status="approved", vendedor_codigo="D")   # approved NÃO conta (só delivered)
    j = client.get("/api/ranking").get_json()
    assert j["ranking"] == [
        {"rank": 1, "nome": "Ana", "codigo": "A", "pontos": 3, "valor_comissao_brl": "R$ 7.16", "percentual_comissao": "15%"},
        {"rank": 2, "nome": "Bruno", "codigo": "B", "pontos": 2, "valor_comissao_brl": "R$ 3.18", "percentual_comissao": "10%"},
        {"rank": 3, "nome": "Caio", "codigo": "C", "pontos": 1, "valor_comissao_brl": "R$ 0.80", "percentual_comissao": "5%"},
        {"rank": 4, "nome": "Dani", "codigo": "D", "pontos": 0, "valor_comissao_brl": "R$ 0.00", "percentual_comissao": "0%"},
    ]
    assert j["meta_diaria"] == {"objetivo": 100, "atual": 6, "percentual_meta": 6.0}
