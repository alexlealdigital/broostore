"""POST /api/cotar-frete e o serviço de frete."""
from broostore_api.services.frete import curar_opcoes

FISICO = dict(title="Livro", price=60.0, tipo="fisico", peso_kg=0.5, altura_cm=3, largura_cm=15, comprimento_cm=21)


def _cotar(client, **body):
    return client.post("/api/cotar-frete", json=body)


def test_cep_obrigatorio(client):
    r = _cotar(client, product_id=1)
    assert r.status_code == 400 and r.get_json() == {"status": "error", "message": "CEP de destino obrigatório."}


def test_product_id_obrigatorio(client):
    r = _cotar(client, cep="01001000")
    assert r.status_code == 400 and r.get_json()["message"] == "product_id obrigatório."


def test_corpo_vazio_nao_json_cai_em_400(client):
    assert client.post("/api/cotar-frete", json={}).status_code == 400


def test_produto_nao_encontrado_404(client, world):
    r = _cotar(client, cep_destino="01001000", product_id=1)
    assert r.status_code == 404 and r.get_json()["message"] == "Produto não encontrado."


def test_produto_nao_fisico_400(client, world):
    world.http.add_product(1, tipo="ebook")
    r = _cotar(client, cep_destino="01001000", product_id=1)
    assert r.status_code == 400 and r.get_json()["message"] == "Produto não é físico (não tem frete)."


def test_produto_sem_medidas_422(client, world):
    world.http.add_product(1, tipo="fisico", peso_kg=0.5)
    r = _cotar(client, cep_destino="01001000", product_id=1)
    assert r.status_code == 422
    assert r.get_json()["message"] == "Produto sem medidas cadastradas: altura_cm, largura_cm, comprimento_cm."


def test_supabase_fora_500(client, world):
    world.http.supabase_down = True
    r = _cotar(client, cep_destino="01001000", product_id=1)
    assert r.status_code == 500 and r.get_json()["message"].startswith("Erro ao buscar produto: ")


def test_sucesso_ordenado_e_curado(client, world):
    world.http.add_product(1, **FISICO)
    r = _cotar(client, cep="01001-000", product_id=1)
    j = r.get_json()
    assert r.status_code == 200 and j["status"] == "success" and j["total_disponivel"] == 3
    assert j["opcoes"] == [
        {"id": 1, "nome": "PAC", "empresa": "Correios", "preco": 25.5, "prazo": 8, "destaque": "Mais barato"},
        {"id": 3, "nome": ".Package", "empresa": "Jadlog", "preco": 31.0, "prazo": 5, "destaque": "Custo-beneficio"},
        {"id": 2, "nome": "SEDEX", "empresa": "Correios", "preco": 45.9, "prazo": 3, "destaque": "Mais rapido"},
    ]
    # chamada ao Supabase com timeout=10 e ao Melhor Envio com timeout=15
    get = [c for c in world.http.calls if c[0] == "GET"][0]
    assert get[1].endswith("select=id,price,tipo,peso_kg,altura_cm,largura_cm,comprimento_cm") and get[2]["timeout"] == 10
    post = [c for c in world.http.calls if c[0] == "POST"][0]
    assert post[1] == "https://www.melhorenvio.com.br/api/v2/me/shipment/calculate" and post[2]["timeout"] == 15
    assert post[2]["json"]["from"] == {"postal_code": "01001000"}
    assert post[2]["headers"]["Authorization"] == "Bearer fake-me-token"
    assert post[2]["headers"]["User-Agent"] == "BrooStore (entrega.broo@zohomail.com)"


def test_erros_do_melhor_envio_502(client, world, monkeypatch):
    world.http.add_product(1, **FISICO)
    casos = [
        (401, "Token do Melhor Envio inválido ou expirado (401)."),
        (403, "Token sem a permissão de cotação 'shipping-calculate' (403)."),
        (500, "Melhor Envio respondeu 500: "),
    ]
    for status, msg in casos:
        world.http.me_status = status
        r = _cotar(client, cep_destino="01001000", product_id=1)
        assert r.status_code == 502 and r.get_json()["message"].startswith(msg)
    world.http.me_status = 200
    world.http.me_raises = ConnectionError("timeout")
    r = _cotar(client, cep_destino="01001000", product_id=1)
    assert r.status_code == 502 and r.get_json()["message"] == "Falha ao consultar Melhor Envio: timeout"
    world.http.me_raises = None
    r = _cotar(client, cep_destino="123", product_id=1)
    assert r.status_code == 502 and r.get_json()["message"] == "CEP de destino inválido."


def test_sem_token_ou_cep_origem_502(client, world, monkeypatch):
    world.http.add_product(1, **FISICO)
    monkeypatch.delenv("MELHOR_ENVIO_TOKEN")
    assert _cotar(client, cep_destino="01001000", product_id=1).get_json()["message"] == "MELHOR_ENVIO_TOKEN não configurado no servidor."
    monkeypatch.setenv("MELHOR_ENVIO_TOKEN", "t")
    monkeypatch.delenv("CEP_ORIGEM")
    assert _cotar(client, cep_destino="01001000", product_id=1).get_json()["message"] == "CEP_ORIGEM não configurado no servidor."


def test_nenhuma_transportadora_404(client, world):
    world.http.add_product(1, **FISICO)
    world.http.me_body = [{"id": 9, "name": "X", "error": "indisponível"}]
    r = _cotar(client, cep_destino="01001000", product_id=1)
    assert r.status_code == 404 and r.get_json()["message"] == "Nenhuma transportadora disponível para este CEP."


def test_curar_opcoes_maximo_3_e_vazio():
    assert curar_opcoes([]) == []
    ops = [{"id": i, "nome": str(i), "empresa": "E", "preco": 10.0 + i, "prazo": 10 - i} for i in range(6)]
    cur = curar_opcoes(ops)
    assert len(cur) == 3 and [o["preco"] for o in cur] == sorted(o["preco"] for o in cur)
    assert {o["destaque"] for o in cur} <= {"Mais barato", "Custo-beneficio", "Mais rapido", ""}
