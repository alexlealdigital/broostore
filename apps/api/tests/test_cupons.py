"""Caracterização de /api/validar-cupom."""
from datetime import date, timedelta

from tests.helpers import add_cupom, add_produto


def _post(client, **body):
    return client.post("/api/validar-cupom", json=body)


def test_cupom_percentual_valido(client, db_session):
    add_produto(1)
    add_cupom("PROMO10", tipo="percentual", valor=10)
    r = _post(client, codigo=" promo10 ", produto_id=1, valor_original=50)
    j = r.get_json()
    assert r.status_code == 200 and j["status"] == "success"
    assert j["cupom"]["codigo"] == "PROMO10" and j["cupom"]["tipo"] == "percentual"
    assert j["calculo"] == {"valor_original": 50.0, "desconto": 5.0, "valor_final": 45.0, "percentual_aplicado": 10.0}


def test_cupom_valor_fixo_nao_passa_do_valor(client, db_session):
    add_produto(1)
    add_cupom("FIXO", tipo="valor_fixo", valor=100)
    j = _post(client, codigo="fixo", produto_id=1, valor_original=30).get_json()
    assert j["calculo"] == {"valor_original": 30.0, "desconto": 30.0, "valor_final": 0, "percentual_aplicado": 100.0}


def test_cupom_codigo_obrigatorio(client):
    r = _post(client, codigo="  ", produto_id=1, valor_original=10)
    assert r.status_code == 400
    assert r.get_json() == {"status": "error", "message": "Código do cupom é obrigatório"}


def test_cupom_produto_e_valor_obrigatorios(client):
    r = _post(client, codigo="X")
    assert r.status_code == 400
    assert r.get_json()["message"] == "ID do produto e valor original são obrigatórios"


def test_cupom_inexistente_404(client):
    r = _post(client, codigo="NAO", produto_id=1, valor_original=10)
    assert r.status_code == 404 and r.get_json() == {"status": "error", "message": "Cupom não encontrado"}


def test_cupom_expirado(client, db_session):
    add_cupom("VELHO", valido_ate=date.today() - timedelta(days=1))
    r = _post(client, codigo="velho", produto_id=1, valor_original=10)
    assert r.status_code == 400 and r.get_json()["message"] == "Cupom expirado"


def test_cupom_inativo_e_futuro_e_limite(client, db_session):
    add_cupom("OFF", ativo=False)
    add_cupom("FUT", valido_de=date.today() + timedelta(days=3))
    add_cupom("LIM", usos_maximos=2, usos_atuais=2)
    assert _post(client, codigo="off", produto_id=1, valor_original=10).get_json()["message"] == "Cupom inativo"
    assert _post(client, codigo="fut", produto_id=1, valor_original=10).get_json()["message"] == "Cupom ainda não está válido"
    assert _post(client, codigo="lim", produto_id=1, valor_original=10).get_json()["message"] == "Limite de usos atingido"


def test_cupom_de_outro_produto(client, db_session):
    add_produto(1)
    add_produto(2)
    add_cupom("SOP2", produto_id=2)
    r = _post(client, codigo="sop2", produto_id=1, valor_original=10)
    assert r.status_code == 400
    assert r.get_json() == {"status": "error", "message": "Este cupom não é válido para este produto"}


def test_cupom_validar_nao_consome_uso(client, db_session):
    add_cupom("U", usos_maximos=1)
    _post(client, codigo="u", produto_id=1, valor_original=10)
    assert _post(client, codigo="u", produto_id=1, valor_original=10).status_code == 200


def test_cupom_valor_invalido_500(client, db_session):
    add_cupom("Z")
    r = _post(client, codigo="z", produto_id=1, valor_original="abc")
    assert r.status_code == 500 and r.get_json()["message"].startswith("Erro interno: ")
