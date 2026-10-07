"""POST /api/webhook — comportamento original + F3 (assinatura opcional, JSON seguro, 503 sem fila)."""
import hashlib
import hmac

from broostore_api import extensions

SECRET = "test-webhook-secret"


def _assinar(data_id, request_id="req-1", ts="1700000000", secret=SECRET):
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return {"x-signature": f"ts={ts},v1={v1}", "x-request-id": request_id}


def test_webhook_enfileira_por_nome_com_retry(client, world):
    r = client.post("/api/webhook", json={"type": "payment", "data": {"id": "123"}})
    assert r.status_code == 200
    assert r.get_json() == {"status": "success", "message": "Webhook recebido e processamento enfileirado"}
    (job, args, kwargs), = world.queue.jobs
    assert job == "worker.process_mercado_pago_webhook" and args == ("123",)
    assert kwargs["retry"].max == 5 and kwargs["retry"].intervals == [60, 300, 900, 3600, 7200]


def test_webhook_sem_payment_id_responde_200_sem_enfileirar(client, world):
    for body in ({}, {"data": {}}, {"data": None}, {"data": "x"}):
        r = client.post("/api/webhook", json=body)
        assert r.status_code == 200 and r.get_json()["status"] == "success"
    assert world.queue.jobs == []


def test_webhook_corpo_invalido_nao_quebra(client, world):
    r = client.post("/api/webhook", data="isto nao e json", content_type="text/plain")
    assert r.status_code == 200 and world.queue.jobs == []
    r = client.post("/api/webhook", data="[1,2]", content_type="application/json")
    assert r.status_code == 200


def test_webhook_assinatura_desligada_por_padrao_aceita_qualquer_header(client, world):
    r = client.post("/api/webhook?data.id=9", json={"data": {"id": "9"}}, headers={"x-signature": "lixo"})
    assert r.status_code == 200 and len(world.queue.jobs) == 1


def test_webhook_fila_indisponivel_503(client, world, monkeypatch):
    extensions.set_queue(None)
    monkeypatch.setattr(extensions, "_connect", lambda: (_ for _ in ()).throw(ConnectionError("redis fora")))
    r = client.post("/api/webhook", json={"data": {"id": "1"}})
    assert r.status_code == 503
    assert r.get_json() == {"status": "error", "message": "Fila indisponível, tente novamente"}


def test_webhook_erro_ao_enfileirar_500_como_no_original(client, world):
    world.queue.fail_with = RuntimeError("boom")
    r = client.post("/api/webhook", json={"data": {"id": "1"}})
    assert r.status_code == 500
    assert r.get_json() == {"status": "error", "message": "Erro interno ao processar webhook: boom"}


def test_get_queue_reconecta_depois_do_intervalo(monkeypatch):
    chamadas = []

    def tentativa():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise ConnectionError("fora")
        return "FILA"
    extensions.set_queue(None)
    monkeypatch.setattr(extensions, "_connect", tentativa)
    assert extensions.get_queue() is None
    assert extensions.get_queue() is None and len(chamadas) == 1  # dentro da janela: não tenta de novo
    extensions._state["failed_at"] -= extensions.RETRY_AFTER + 1
    assert extensions.get_queue() == "FILA"
    extensions.set_queue(None)


# ---------------------------- F3: assinatura -------------------------------
def test_f3_assinatura_valida_aceita(client, world, monkeypatch):
    monkeypatch.setenv("WEBHOOK_VALIDATE_SIGNATURE", "true")
    headers = _assinar("555")
    r = client.post("/api/webhook?data.id=555", json={"data": {"id": "555"}}, headers=headers)
    assert r.status_code == 200 and len(world.queue.jobs) == 1


def test_f3_assinatura_invalida_401(client, world, monkeypatch):
    monkeypatch.setenv("WEBHOOK_VALIDATE_SIGNATURE", "1")
    headers = _assinar("555", secret="outro-segredo")
    r = client.post("/api/webhook?data.id=555", json={"data": {"id": "555"}}, headers=headers)
    assert r.status_code == 401
    assert r.get_json() == {"status": "error", "message": "Assinatura inválida"}
    assert world.queue.jobs == []


def test_f3_assinatura_ausente_ou_mal_formada_401(client, world, monkeypatch):
    monkeypatch.setenv("WEBHOOK_VALIDATE_SIGNATURE", "true")
    assert client.post("/api/webhook", json={"data": {"id": "1"}}).status_code == 401
    h = _assinar("1")
    h["x-signature"] = "semformato"
    assert client.post("/api/webhook?data.id=1", json={"data": {"id": "1"}}, headers=h).status_code == 401
    # data.id diferente do assinado
    assert client.post("/api/webhook?data.id=2", json={"data": {"id": "2"}}, headers=_assinar("1")).status_code == 401


def test_f3_sem_secret_configurado_401(client, world, monkeypatch):
    monkeypatch.setenv("WEBHOOK_VALIDATE_SIGNATURE", "true")
    monkeypatch.delenv("WEBHOOK_SECRET")
    assert client.post("/api/webhook?data.id=5", json={"data": {"id": "5"}}, headers=_assinar("5")).status_code == 401


def test_f3_valores_que_nao_ligam_a_validacao(client, world, monkeypatch):
    for v in ("false", "0", "", "no", "off"):
        monkeypatch.setenv("WEBHOOK_VALIDATE_SIGNATURE", v)
        assert client.post("/api/webhook", json={"data": {"id": "1"}}).status_code == 200
