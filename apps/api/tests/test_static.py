"""Arquivos estáticos servidos pelo Flask (copiados sem alteração do original)."""
import filecmp
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_raiz_serve_index_html(client):
    r = client.get("/")
    assert r.status_code == 200 and r.mimetype == "text/html"
    assert r.data == (STATIC / "index.html").read_bytes()
    r.close()


def test_arquivo_estatico_pela_rota_coringa(client):
    r = client.get("/styles.css")
    assert r.status_code == 200 and r.mimetype == "text/css"
    assert r.data == (STATIC / "styles.css").read_bytes()
    r.close()


def test_arquivo_estatico_pela_rota_static_do_flask(client):
    r = client.get("/static/script.js")
    assert r.status_code == 200 and r.data == (STATIC / "script.js").read_bytes()
    r.close()


def test_pagina_de_compressao_e_checkout(client):
    for nome in ("comprar.html", "comprimir-pdf.html", "autor-login.html", "autor-produto.html"):
        r = client.get(f"/{nome}")
        assert r.status_code == 200, nome
        r.close()


def test_inexistente_404_e_traversal_bloqueado(client):
    assert client.get("/nao-existe.html").status_code == 404
    assert client.get("/../app.py").status_code == 404
    assert client.get("/api/produtos-que-nao-existe").status_code == 404


def test_post_em_rota_desconhecida_405(client):
    assert client.post("/qualquer-coisa").status_code == 405


def test_static_identico_ao_original():
    original = Path("/tmp/claude-0/-home-claude/f55b5e93-2d8b-53f6-a305-1ddf4465c5fd/scratchpad/back/broorread-main/static")
    if not original.exists():
        import pytest
        pytest.skip("diretório original não disponível nesta máquina")
    cmp = filecmp.dircmp(original, STATIC)
    assert not cmp.left_only and not cmp.right_only and not cmp.diff_files
