"""Caracterização de POST /api/cobrancas (PIX)."""
import json

from broostore_api.models import Cobranca, Cupom
from tests.fakes import UUID_RE
from tests.helpers import add_cupom, add_produto, add_vendedor

BASE = {"email": "cli@example.test", "nome": "Maria Silva", "product_id": 1}


def _setup_digital(world, preco=50.0):
    world.http.add_product(1, title="E-book Um", price=preco, link_pdf="https://dl/ebook1", tipo="ebook")


def test_pix_digital_201(client, world, db_session):
    _setup_digital(world)
    r = client.post("/api/cobrancas", json=BASE)
    j = r.get_json()
    assert r.status_code == 201
    assert j["status"] == "success" and j["message"] == "Cobrança PIX criada com sucesso!"
    assert j["qr_code_base64"] == "QkFTRTY0RkFLRQ==" and j["qr_code_text"] == "00020126FAKEPIX"
    assert j["payment_id"] == 1001
    assert (j["frete_aplicado"], j["subtotal_produto"], j["total_cobrado"]) == (0.0, 50.0, 50.0)
    assert "desconto_aplicado" not in j
    c = j["cobranca"]
    # to_dict() é chamado ANTES do commit: id e data_criacao ainda não existem (comportamento original)
    assert c["id"] is None and c["data_criacao"] is None
    assert c["status"] == "pending" and c["valor"] == 50.0 and c["valor_original"] == 50.0
    assert c["cliente_email"] == "cli@example.test" and c["cupom_id"] is None and c["vendedor_codigo"] is None
    assert UUID_RE.fullmatch(c["external_reference"])
    # o produto local foi criado a partir do Supabase
    db_session.expire_all()
    cob = Cobranca.query.one()
    assert cob.external_reference == c["external_reference"] and cob.product_id == 1
    assert json.loads(cob.observacoes) == {"subtotal_produto": 50.0}
    # payload enviado ao Mercado Pago
    data, opts = world.mp.created[0]
    assert data == {"transaction_amount": 50.0, "description": "E-book Um", "payment_method_id": "pix",
                    "external_reference": c["external_reference"], "payer": {"email": "cli@example.test"}}
    assert opts is None and world.mp.tokens == ["TEST-fake-mp-token"]


def test_pix_cupom_percentual_aplica_e_conta_uso(client, world, db_session):
    _setup_digital(world)
    cupom = add_cupom("OFF20", tipo="percentual", valor=20, usos_maximos=5)
    r = client.post("/api/cobrancas", json={**BASE, "cupom_id": cupom.id})
    j = r.get_json()
    assert r.status_code == 201 and j["total_cobrado"] == 40.0 and j["cobranca"]["cupom_id"] == cupom.id
    assert j["desconto_aplicado"] == {"cupom_codigo": "OFF20", "tipo": "percentual", "valor_desconto": 10.0,
                                      "valor_original": 50.0, "valor_final": 40.0}
    assert world.mp.created[0][0]["description"] == "E-book Um (Cupom: OFF20)"
    db_session.expire_all()
    assert db_session.get(Cupom, cupom.id).usos_atuais == 1


def test_pix_cupom_invalido_nao_desconta_mas_aparece_na_resposta(client, world, db_session):
    """Comportamento original (estranho, preservado): cupom inativo não desconta, mas continua
    citado na descrição, no cupom_id e em desconto_aplicado (com desconto 0)."""
    _setup_digital(world)
    cupom = add_cupom("INATIVO", ativo=False)
    j = client.post("/api/cobrancas", json={**BASE, "cupom_id": cupom.id}).get_json()
    assert j["total_cobrado"] == 50.0 and j["cobranca"]["cupom_id"] == cupom.id
    assert j["desconto_aplicado"]["valor_desconto"] == 0.0
    assert world.mp.created[0][0]["description"] == "E-book Um (Cupom: INATIVO)"


def test_pix_vendedor_valido_e_invalido(client, world, db_session):
    _setup_digital(world)
    add_vendedor("V1", "Vendedor Um")
    j = client.post("/api/cobrancas", json={**BASE, "vendedor_codigo": "V1"}).get_json()
    assert j["cobranca"]["vendedor_codigo"] == "V1"
    j = client.post("/api/cobrancas", json={**BASE, "vendedor_codigo": "NAOEXISTE"}).get_json()
    assert j["cobranca"]["vendedor_codigo"] is None


def test_pix_produto_7_com_usuario_id_prefixa_external_reference(client, world, db_session):
    world.http.add_product(7, title="Moedas", price=5.0)
    j = client.post("/api/cobrancas", json={**BASE, "product_id": 7, "usuario_id": "user-123"}).get_json()
    ref = j["cobranca"]["external_reference"]
    assert ref.startswith("user-123:") and UUID_RE.fullmatch(ref.split(":", 1)[1])
    # outro produto com usuario_id NÃO prefixa
    world.http.add_product(8, title="Outro", price=5.0)
    ref2 = client.post("/api/cobrancas", json={**BASE, "product_id": 8, "usuario_id": "user-123"}).get_json()["cobranca"]["external_reference"]
    assert UUID_RE.fullmatch(ref2)


def test_pix_fisico_com_frete_cotado(client, world, db_session):
    world.http.add_product(2, title="Livro Físico", price=60.0, tipo="fisico", frete=20.0,
                           peso_kg=0.5, altura_cm=3, largura_cm=15, comprimento_cm=21)
    body = {**BASE, "product_id": 2, "frete_servico_id": 2, "telefone": "(11) 98888-7777",
            "endereco": {"cep": "01310-100", "rua": "Av Paulista", "numero": "1"}}
    r = client.post("/api/cobrancas", json=body)
    j = r.get_json()
    assert r.status_code == 201
    assert (j["frete_aplicado"], j["subtotal_produto"], j["total_cobrado"]) == (45.9, 60.0, 105.9)
    assert world.mp.created[0][0]["description"] == "Livro Físico + Frete"
    assert world.mp.created[0][0]["transaction_amount"] == 105.9
    assert j["cobranca"]["cliente_telefone"] == "(11) 98888-7777"
    obs = json.loads(Cobranca.query.one().observacoes)
    assert obs == {"endereco": body["endereco"], "frete": 45.9, "transportadora": "Correios SEDEX",
                   "subtotal_produto": 60.0}
    # a recotação usou CEP do endereço e o pacote do Supabase
    post = [c for c in world.http.calls if c[0] == "POST"][0]
    assert post[2]["json"]["to"] == {"postal_code": "01310100"} and post[2]["json"]["package"]["weight"] == 0.5
    assert post[2]["json"]["options"]["insurance_value"] == 60.0


def test_pix_fisico_sem_servico_usa_frete_fixo(client, world, db_session):
    world.http.add_product(2, title="Livro Físico", price=60.0, tipo="fisico", frete=20.0,
                           peso_kg=0.5, altura_cm=3, largura_cm=15, comprimento_cm=21)
    j = client.post("/api/cobrancas", json={**BASE, "product_id": 2}).get_json()
    assert (j["frete_aplicado"], j["total_cobrado"]) == (20.0, 80.0)
    assert [c for c in world.http.calls if c[0] == "POST"] == []


def test_pix_fisico_servico_inexistente_ou_erro_cai_no_frete_fixo(client, world, db_session):
    world.http.add_product(2, title="Livro", price=60.0, tipo="fisico", frete=20.0,
                           peso_kg=0.5, altura_cm=3, largura_cm=15, comprimento_cm=21)
    body = {**BASE, "product_id": 2, "cep_destino": "01310-100", "frete_servico_id": 999}
    assert client.post("/api/cobrancas", json=body).get_json()["frete_aplicado"] == 20.0
    world.http.me_status = 500
    body["frete_servico_id"] = 1
    assert client.post("/api/cobrancas", json=body).get_json()["frete_aplicado"] == 20.0


def test_pix_fisico_com_supabase_fora_e_produto_local_fisico_503(client, world, db_session):
    add_produto(2, nome="Livro Local", preco=60.0, tipo="fisico")
    world.http.supabase_down = True
    r = client.post("/api/cobrancas", json={**BASE, "product_id": 2})
    assert r.status_code == 503
    assert r.get_json() == {"status": "error", "message": "Não foi possível calcular o frete agora. Tente novamente em instantes."}


def test_pix_supabase_fora_usa_produto_local(client, world, db_session):
    add_produto(1, nome="Local", preco=12.0)
    world.http.supabase_down = True
    r = client.post("/api/cobrancas", json=BASE)
    assert r.status_code == 201 and r.get_json()["total_cobrado"] == 12.0


def test_pix_sync_atualiza_preco_do_produto_local(client, world, db_session):
    add_produto(1, nome="Velho", preco=99.0)
    _setup_digital(world, preco=50.0)
    assert client.post("/api/cobrancas", json=BASE).get_json()["total_cobrado"] == 50.0


def test_pix_validacoes(client, world):
    assert client.post("/api/cobrancas", json={}).get_json() == {"status": "error", "message": "Nenhum dado foi enviado."}
    r = client.post("/api/cobrancas", json={"email": "a@b.c"})
    assert (r.status_code, r.get_json()["message"]) == (400, "ID do produto é obrigatório.")
    for bad in ("", "semarroba", "a@b"):
        r = client.post("/api/cobrancas", json={**BASE, "email": bad})
        assert r.status_code == 400
        assert r.get_json()["message"] == "Por favor, insira um email válido e obrigatório."
    r = client.post("/api/cobrancas", json={**BASE, "telefone": "123"})
    assert (r.status_code, r.get_json()["message"]) == (400, "Telefone inválido.")


def test_pix_produto_desconhecido_404(client, world):
    r = client.post("/api/cobrancas", json={**BASE, "product_id": 777})
    assert r.status_code == 404 and r.get_json() == {"status": "error", "message": "Produto não encontrado."}


def test_pix_sem_token_mp_500(client, world, monkeypatch):
    _setup_digital(world)
    monkeypatch.delenv("MERCADOPAGO_ACCESS_TOKEN")
    r = client.post("/api/cobrancas", json=BASE)
    assert r.status_code == 500 and r.get_json() == {"status": "error", "message": "Token do Mercado Pago não configurado."}


def test_pix_erro_do_mercado_pago_500(client, world, db_session):
    _setup_digital(world)
    world.mp.create_override = {"status": 400, "response": {"message": "invalid amount"}}
    r = client.post("/api/cobrancas", json=BASE)
    assert r.status_code == 500 and r.get_json() == {"status": "error", "message": "Erro do Mercado Pago: invalid amount"}
    assert Cobranca.query.count() == 0


def test_pix_nome_padrao_cliente(client, world, db_session):
    _setup_digital(world)
    body = {k: v for k, v in BASE.items() if k != "nome"}
    assert client.post("/api/cobrancas", json=body).get_json()["cobranca"]["cliente_nome"] == "Cliente"


def test_pix_product_id_invalido_500(client, world):
    r = client.post("/api/cobrancas", json={**BASE, "product_id": "abc"})
    assert r.status_code == 500 and r.get_json()["message"].startswith("Falha ao criar cobrança: ")
