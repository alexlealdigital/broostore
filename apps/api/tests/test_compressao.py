"""Compressão de PDF (produto 99) e imagem (produto 98): validação de código e compressão."""
import io

import pikepdf
from PIL import Image

from tests.helpers import add_cobranca, add_produto


def _pdf_bytes():
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGBA", (3000, 2000), (200, 30, 30, 255)).save(buf, format="PNG")
    return buf.getvalue()


# ------------------------------ PDF -----------------------------------------
def test_validar_codigo_pdf(client, db_session):
    add_produto(99, nome="Compressão de PDF")
    add_cobranca("cod-ok", produto_id=99, status="approved")
    add_cobranca("cod-entregue", produto_id=99, status="delivered")
    add_cobranca("cod-pendente", produto_id=99, status="pending")
    for ref in ("cod-ok", "cod-entregue"):
        r = client.post("/api/validar-codigo-compressao", json={"codigo": ref})
        assert r.status_code == 200 and r.get_json() == {"status": "ok", "message": "Código válido."}
    r = client.post("/api/validar-codigo-compressao", json={"codigo": "cod-pendente"})
    assert r.status_code == 404
    assert r.get_json() == {"status": "erro", "message": "Código inválido ou pagamento ainda não confirmado."}


def test_validar_codigo_pdf_vazio_e_produto_errado(client, db_session):
    add_produto(5)
    add_cobranca("outro", produto_id=5, status="approved")
    r = client.post("/api/validar-codigo-compressao", json={"codigo": "  "})
    assert r.status_code == 400 and r.get_json() == {"status": "erro", "message": "Código não informado."}
    r = client.post("/api/validar-codigo-compressao", json={"codigo": "outro"})
    assert r.status_code == 400 and r.get_json() == {"status": "erro", "message": "Código inválido para este serviço."}


def test_comprimir_pdf_ok(client, db_session):
    add_produto(99)
    add_cobranca("cod-pdf", produto_id=99, status="delivered")
    r = client.post("/api/comprimir-pdf", data={"codigo": "cod-pdf", "pdf": (io.BytesIO(_pdf_bytes()), "a.pdf")},
                    content_type="multipart/form-data")
    assert r.status_code == 200 and r.mimetype == "application/pdf"
    assert r.data.startswith(b"%PDF") and "comprimido.pdf" in r.headers["Content-Disposition"]


def test_comprimir_pdf_erros(client, db_session):
    add_produto(99)
    add_cobranca("cod-pdf", produto_id=99, status="pending")
    r = client.post("/api/comprimir-pdf", data={"pdf": (io.BytesIO(b"x"), "a.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 400 and r.get_json()["message"] == "Código não informado."
    r = client.post("/api/comprimir-pdf", data={"codigo": "cod-pdf"}, content_type="multipart/form-data")
    assert r.status_code == 400 and r.get_json()["message"] == "Nenhum arquivo enviado."
    r = client.post("/api/comprimir-pdf", data={"codigo": "cod-pdf", "pdf": (io.BytesIO(b"x"), "a.pdf")},
                    content_type="multipart/form-data")
    assert r.status_code == 403 and r.get_json()["message"] == "Código inválido ou pagamento não confirmado."


def test_comprimir_pdf_arquivo_corrompido_500(client, db_session):
    add_produto(99)
    add_cobranca("cod-pdf", produto_id=99, status="approved")
    r = client.post("/api/comprimir-pdf", data={"codigo": "cod-pdf", "pdf": (io.BytesIO(b"nao e pdf"), "a.pdf")},
                    content_type="multipart/form-data")
    assert r.status_code == 500 and r.get_json()["status"] == "erro"


def test_comprimir_pdf_codigo_pode_ser_reutilizado_comportamento_original(client, db_session):
    """O 'código já utilizado' nunca dispara: compressao_usada não é coluna do banco (observação no CHANGELOG)."""
    add_produto(99)
    add_cobranca("cod-pdf", produto_id=99, status="approved")
    for _ in range(2):
        r = client.post("/api/comprimir-pdf", data={"codigo": "cod-pdf", "pdf": (io.BytesIO(_pdf_bytes()), "a.pdf")},
                        content_type="multipart/form-data")
        assert r.status_code == 200


# ----------------------------- Imagem ---------------------------------------
def test_validar_codigo_imagem(client, db_session):
    add_produto(98)
    add_produto(99)
    add_cobranca("img-ok", produto_id=98, status="approved")
    add_cobranca("pdf-cod", produto_id=99, status="approved")
    r = client.post("/api/validar-codigo-compressao-imagem", json={"codigo": "img-ok"})
    assert r.status_code == 200 and r.get_json() == {"status": "ok", "message": "Código válido."}
    r = client.post("/api/validar-codigo-compressao-imagem", json={"codigo": "pdf-cod"})
    assert r.status_code == 400 and r.get_json()["message"] == "Código inválido para este serviço."
    r = client.post("/api/validar-codigo-compressao-imagem", json={"codigo": "nada"})
    assert r.status_code == 404
    r = client.post("/api/validar-codigo-compressao-imagem", json={"codigo": ""})
    assert r.status_code == 400 and r.get_json()["message"] == "Código não informado."


def test_comprimir_imagem_ok(client, db_session):
    add_produto(98)
    add_cobranca("img-ok", produto_id=98, status="delivered")
    r = client.post("/api/comprimir-imagem", data={"codigo": "img-ok", "imagem": (io.BytesIO(_png_bytes()), "foto.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 200 and r.mimetype == "image/jpeg"
    img = Image.open(io.BytesIO(r.data))
    assert img.format == "JPEG" and max(img.size) <= 1920


def test_comprimir_imagem_erros(client, db_session):
    add_produto(98)
    add_cobranca("img-pend", produto_id=98, status="pending")
    r = client.post("/api/comprimir-imagem", data={"imagem": (io.BytesIO(b"x"), "a.png")}, content_type="multipart/form-data")
    assert r.status_code == 400 and r.get_json()["message"] == "Código não informado."
    r = client.post("/api/comprimir-imagem", data={"codigo": "c"}, content_type="multipart/form-data")
    assert r.status_code == 400 and r.get_json()["message"] == "Nenhuma imagem enviada."
    r = client.post("/api/comprimir-imagem", data={"codigo": "c", "imagem": (io.BytesIO(b"x"), "a.gif")},
                    content_type="multipart/form-data")
    assert r.status_code == 400 and r.get_json()["message"] == "Formato não suportado. Use JPEG, PNG ou WebP."
    r = client.post("/api/comprimir-imagem", data={"codigo": "img-pend", "imagem": (io.BytesIO(b"x"), "a.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 403 and r.get_json()["message"] == "Código inválido ou pagamento não confirmado."
