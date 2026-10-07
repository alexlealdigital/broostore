"""Caracterização de /api/produto/<id> e /api/sync-produto."""
from broostore_api.models import Produto
from tests.helpers import add_produto


def test_get_produto_200(client, db_session):
    add_produto(5, nome="E-book 5", preco=19.9, tipo="ebook")
    r = client.get("/api/produto/5")
    assert r.status_code == 200
    assert r.get_json() == {"status": "success", "id": 5, "nome": "E-book 5", "preco": 19.9, "tipo": "ebook"}


def test_get_produto_404(client):
    r = client.get("/api/produto/404")
    assert r.status_code == 404
    assert r.get_json() == {"status": "error", "message": "Produto não encontrado."}


def test_get_produto_id_nao_inteiro_cai_no_static_404(client):
    # `/api/produto/abc` não casa a rota com <int:>, cai na rota coringa de estáticos (404 HTML)
    assert client.get("/api/produto/abc").status_code == 404


def test_sync_sem_product_id_400(client):
    r = client.post("/api/sync-produto", json={})
    assert r.status_code == 400
    assert r.get_json() == {"status": "error", "message": "product_id obrigatório"}


def test_sync_corpo_invalido_400(client):
    assert client.post("/api/sync-produto", data="nao-json").status_code == 400


def test_sync_produto_nao_existe_no_supabase_404(client, world):
    r = client.post("/api/sync-produto", json={"product_id": 9})
    assert r.status_code == 404
    assert r.get_json() == {"status": "error", "message": "Produto não encontrado no Supabase"}


def test_sync_cria_produto_local(client, world, db_session):
    world.http.add_product(9, title="Novo Livro", price=33.5, link_pdf="https://x/y", tipo="fisico")
    r = client.post("/api/sync-produto", json={"product_id": 9})
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok", "preco": 33.5, "nome": "Novo Livro"}
    p = db_session.get(Produto, 9)
    # o sync NÃO traz o tipo do Supabase: cria sempre como "ebook" (comportamento original)
    assert (p.nome, p.preco, p.link_download, p.tipo) == ("Novo Livro", 33.5, "https://x/y", "ebook")
    # select e cabeçalhos usados na chamada ao Supabase
    method, url, kw = world.http.calls[0]
    assert url.endswith("/rest/v1/products?id=eq.9&select=id,title,price,link_pdf")
    assert kw["headers"]["apikey"] == kw["headers"]["Authorization"].replace("Bearer ", "")
    assert "timeout" not in kw


def test_sync_atualiza_produto_existente_sem_mudar_tipo(client, world, db_session):
    add_produto(9, nome="Velho", preco=1.0, tipo="game", link="https://old")
    world.http.add_product(9, title="Novo", price=2.5, link_pdf="")
    r = client.post("/api/sync-produto", json={"product_id": 9})
    assert r.status_code == 200
    db_session.expire_all()
    p = db_session.get(Produto, 9)
    assert (p.nome, p.preco, p.link_download, p.tipo) == ("Novo", 2.5, "https://old", "game")


def test_sync_supabase_fora_do_ar_500(client, world):
    world.http.supabase_down = True
    r = client.post("/api/sync-produto", json={"product_id": 9})
    assert r.status_code == 500
    assert r.get_json()["status"] == "error" and "supabase fora do ar" in r.get_json()["message"]
