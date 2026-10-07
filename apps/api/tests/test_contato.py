"""POST /api/contato."""
BODY = {"nome": "Ana", "email": "ana@example.test", "assunto": "Dúvida", "mensagem": "Olá!"}


def test_contato_ok(client, world):
    r = client.post("/api/contato", json=BODY)
    assert r.status_code == 200
    assert r.get_json() == {"status": "success", "message": "Mensagem enviada com sucesso!"}
    assert world.resend["calls"] == [{
        "from": "BrooStore <onboarding@resend.dev>", "to": "profalexleal@gmail.com",
        "reply_to": "ana@example.test", "subject": "Contato BrooStore: Dúvida",
        "html": "<p>De: Ana (ana@example.test)</p><hr><p>Olá!</p>"}]


def test_contato_campos_obrigatorios(client):
    for campo in BODY:
        r = client.post("/api/contato", json={**BODY, campo: ""})
        assert r.status_code == 400
        assert r.get_json() == {"status": "error", "message": "Todos os campos são obrigatórios."}


def test_contato_sem_api_key(client, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY")
    r = client.post("/api/contato", json=BODY)
    assert r.status_code == 500 and r.get_json() == {"status": "error", "message": "API de email não configurada."}


def test_contato_resend_sem_id(client, world):
    world.resend["response"] = {}
    r = client.post("/api/contato", json=BODY)
    assert r.status_code == 500 and r.get_json() == {"status": "error", "message": "Falha ao enviar e-mail."}


def test_contato_resend_excecao(client, world):
    world.resend["raises"] = RuntimeError("resend caiu")
    r = client.post("/api/contato", json=BODY)
    assert r.status_code == 500
    assert r.get_json() == {"status": "error", "message": "Não foi possível enviar a mensagem no momento."}
