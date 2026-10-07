"""Caracterização de POST /api/cobrancas-cartao."""
import json

from broostore_api.models import Cobranca
from tests.fakes import UUID_RE
from tests.helpers import add_cupom

BASE = {"token": "tok_card", "payment_method_id": "visa", "installments": 3, "email": "cli@example.test",
        "nome": "Maria da Silva Souza", "cpf": "123.456.789-00", "product_id": 1}


def _setup(world, price=80.0):
    world.http.add_product(1, title="Curso", price=price, link_pdf="https://dl/c", tipo="ebook")


def test_cartao_aprovado_enfileira_job(client, world, db_session):
    _setup(world)
    r = client.post("/api/cobrancas-cartao", json={**BASE, "issuer_id": "24"})
    j = r.get_json()
    assert r.status_code == 201
    assert j == {"status": "approved", "status_detail": "accredited", "payment_id": 1001,
                 "mensagem": "Pagamento aprovado! Você receberá o produto por e-mail em instantes.",
                 "frete_aplicado": 0.0, "subtotal_produto": 80.0, "total_cobrado": 80.0}
    data, opts = world.mp.created[0]
    assert UUID_RE.fullmatch(data.pop("external_reference"))
    assert data == {"transaction_amount": 80.0, "token": "tok_card", "description": "Curso", "installments": 3,
                    "payment_method_id": "visa", "issuer_id": 24,
                    "payer": {"email": "cli@example.test", "first_name": "Maria", "last_name": "da Silva Souza",
                              "identification": {"type": "CPF", "number": "12345678900"}}}
    assert opts is not None and "X-Idempotency-Key" in opts.custom_headers
    cob = Cobranca.query.one()
    assert cob.status == "approved" and cob.vendedor_codigo is None
    # F1: enfileirado por nome, com política de retry
    (job, args, kwargs), = world.queue.jobs
    assert job == "worker.process_mercado_pago_webhook" and args == (1001,)
    retry = kwargs["retry"]
    assert retry.max == 5 and retry.intervals == [60, 300, 900, 3600, 7200]


def test_cartao_rejeitado(client, world, db_session):
    _setup(world)
    world.mp.card_status, world.mp.card_status_detail = "rejected", "cc_rejected_insufficient_amount"
    j = client.post("/api/cobrancas-cartao", json=BASE).get_json()
    assert j["status"] == "rejected" and j["status_detail"] == "cc_rejected_insufficient_amount"
    assert j["mensagem"] == "Pagamento não aprovado (cc_rejected_insufficient_amount). Verifique os dados do cartão."
    assert world.queue.jobs == [] and Cobranca.query.one().status == "rejected"


def test_cartao_em_analise(client, world, db_session):
    _setup(world)
    world.mp.card_status, world.mp.card_status_detail = "in_process", "pending_contingency"
    j = client.post("/api/cobrancas-cartao", json=BASE).get_json()
    assert j["status"] == "in_process"
    assert j["mensagem"] == "Pagamento em análise. Você receberá o produto assim que aprovado."
    assert world.queue.jobs == []


def test_cartao_aprovado_com_redis_fora_nao_derruba_a_resposta(client, world, db_session):
    _setup(world)
    world.queue.fail_with = ConnectionError("redis fora")
    r = client.post("/api/cobrancas-cartao", json=BASE)
    assert r.status_code == 201 and r.get_json()["status"] == "approved"


def test_cartao_com_cupom_e_frete_fisico(client, world, db_session):
    world.http.add_product(2, title="Camiseta", price=100.0, tipo="fisico", frete=15.0,
                           peso_kg=0.3, altura_cm=2, largura_cm=20, comprimento_cm=30)
    cupom = add_cupom("C10", valor=10)
    body = {**BASE, "product_id": 2, "cupom_id": cupom.id, "frete_servico_id": 1,
            "endereco": {"cep": "01001000", "cidade": "SP"}}
    j = client.post("/api/cobrancas-cartao", json=body).get_json()
    assert (j["frete_aplicado"], j["subtotal_produto"], j["total_cobrado"]) == (25.5, 90.0, 115.5)
    assert j["desconto_aplicado"]["valor_desconto"] == 10.0
    assert world.mp.created[0][0]["description"] == "Camiseta + Frete"
    obs = json.loads(Cobranca.query.one().observacoes)
    assert obs["transportadora"] == "Correios PAC" and obs["frete"] == 25.5


def test_cartao_validacoes(client, world):
    assert client.post("/api/cobrancas-cartao", json={}).get_json()["message"] == "Nenhum dado enviado."
    r = client.post("/api/cobrancas-cartao", json={**BASE, "token": ""})
    assert (r.status_code, r.get_json()["message"]) == (400, "Token do cartão é obrigatório.")
    r = client.post("/api/cobrancas-cartao", json={**BASE, "email": "semarroba"})
    assert (r.status_code, r.get_json()["message"]) == (400, "E-mail inválido.")
    r = client.post("/api/cobrancas-cartao", json={**BASE, "product_id": None})
    assert (r.status_code, r.get_json()["message"]) == (400, "ID do produto é obrigatório.")


def test_cartao_produto_inexistente_404(client, world):
    r = client.post("/api/cobrancas-cartao", json={**BASE, "product_id": 55})
    assert r.status_code == 404 and r.get_json()["message"] == "Produto não encontrado."


def test_cartao_sem_token_mp_500(client, world, monkeypatch):
    _setup(world)
    monkeypatch.delenv("MERCADOPAGO_ACCESS_TOKEN")
    r = client.post("/api/cobrancas-cartao", json=BASE)
    assert r.status_code == 500 and r.get_json()["message"] == "Token do Mercado Pago não configurado."


def test_cartao_erro_mp_usa_message_error_ou_corpo(client, world):
    _setup(world)
    world.mp.create_override = {"status": 400, "response": {"message": "cc_rejected_bad_filled_card_number"}}
    r = client.post("/api/cobrancas-cartao", json=BASE)
    assert r.status_code == 500 and r.get_json() == {"status": "error", "message": "Erro MP: cc_rejected_bad_filled_card_number"}
    world.mp.create_override = {"status": 500, "response": {"error": "internal_error"}}
    assert client.post("/api/cobrancas-cartao", json=BASE).get_json()["message"] == "Erro MP: internal_error"
    world.mp.create_override = {"status": 500, "response": {"x": 1}}
    assert client.post("/api/cobrancas-cartao", json=BASE).get_json()["message"] == "Erro MP: {'x': 1}"


def test_cartao_nome_de_uma_palavra_e_vazio(client, world):
    _setup(world)
    client.post("/api/cobrancas-cartao", json={**BASE, "nome": "Maria"})
    assert world.mp.created[0][0]["payer"]["last_name"] == "."
    client.post("/api/cobrancas-cartao", json={**BASE, "nome": ""})
    assert world.mp.created[1][0]["payer"]["first_name"] == "Cliente"
