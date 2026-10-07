"""Job RQ ``process_mercado_pago_webhook``: entrega por tipo de produto + F1 (e-mail falha) + F2 (trava)."""
import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Query

from broostore_api import jobs
from broostore_api.extensions import db
from broostore_api.models import ChaveLicenca, Cobranca, Licenca, Sale
from broostore_api.services.entrega import EntregaErro
from tests.helpers import (add_chaves, add_cobranca, add_licenca, add_plano, add_produto)


def run(payment_id=555):
    jobs.process_mercado_pago_webhook(payment_id)


def approve(world, ref, payment_id=555):
    world.mp.set_payment(payment_id, "approved", ref)


def reload_cob(ref):
    db.session.expire_all()
    return Cobranca.query.filter_by(external_reference=ref).one()


# ===================== entrega por tipo =====================================
def test_digital_entrega_ebook(world, db_session):
    add_produto(1, nome="Meu Ebook", tipo="ebook", link="https://dl.example.test/ebook")
    add_cobranca("ref-1", produto_id=1, valor=29.9, nome="Maria")
    approve(world, "ref-1")
    run()
    assert reload_cob("ref-1").status == "delivered"
    (msg,) = world.smtp.messages()
    assert msg["subject"] == 'BrooStore: Seu e-book "Meu Ebook" está pronto! 🎉'
    assert msg["to"] == "cliente@example.test" and "https://dl.example.test/ebook" in msg["html"]
    assert "R$ 29.90" in msg["html"] and "Olá, Maria," in msg["html"]
    # venda local + Supabase (service role) registradas
    assert [(s.product_id, s.amount) for s in Sale.query.all()] == [(1, 29.9)]
    assert world.http.sales_posted == [{"product_id": 1, "customer_email": "cliente@example.test",
                                        "amount": 29.9, "payment_id": "555", "status": "paid"}]


def test_supabase_duplicado_nao_reinsere(world, db_session):
    add_produto(1)
    add_cobranca("ref-1")
    approve(world, "ref-1")
    world.http.sales_existing.add("555")
    run()
    assert world.http.sales_posted == [] and reload_cob("ref-1").status == "delivered"


def test_supabase_falha_nao_derruba_entrega(world, db_session):
    add_produto(1)
    add_cobranca("ref-1")
    approve(world, "ref-1")
    world.http.sales_status = 500
    run()
    assert reload_cob("ref-1").status == "delivered"


def test_sem_service_role_key_nao_derruba_entrega(world, db_session, monkeypatch):
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY")
    add_produto(1)
    add_cobranca("ref-1")
    approve(world, "ref-1")
    run()
    assert reload_cob("ref-1").status == "delivered" and world.http.sales_posted == []


def test_game_reserva_chave_mais_antiga_disponivel(world, db_session):
    add_produto(3, nome="Jogo X", tipo="game", link="https://dl.example.test/jogo")
    add_chaves(3, "KEY-AAA-1111", "KEY-BBB-2222")
    add_cobranca("ref-1", produto_id=3, email="comprador@example.test")
    approve(world, "ref-1")
    run()
    assert reload_cob("ref-1").status == "delivered"
    chaves = {c.chave_serial: c for c in ChaveLicenca.query.all()}
    assert chaves["KEY-AAA-1111"].vendida is True and chaves["KEY-AAA-1111"].cliente_email == "comprador@example.test"
    assert chaves["KEY-AAA-1111"].cobranca_id == Cobranca.query.one().id and chaves["KEY-BBB-2222"].vendida is False
    (msg,) = world.smtp.messages()
    assert msg["subject"] == 'BrooStore: Sua chave de acesso para "Jogo X" chegou! 🚀'
    assert "KEY-AAA-1111" in msg["html"] and "https://dl.example.test/jogo" in msg["html"]


def test_app_tambem_reserva_chave(world, db_session):
    add_produto(4, nome="App Y", tipo="app")
    add_chaves(4, "APP-KEY-1")
    add_cobranca("ref-1", produto_id=4)
    approve(world, "ref-1")
    run()
    assert "APP-KEY-1" in world.smtp.messages()[0]["html"]


def test_estoque_esgotado_levanta_e_nao_perde_o_pedido(world, db_session, caplog):
    add_produto(3, nome="Jogo X", tipo="game")
    add_cobranca("ref-1", produto_id=3, status="pending")
    approve(world, "ref-1")
    with caplog.at_level("ERROR", logger="broostore"):
        with pytest.raises(EntregaErro, match="Estoque esgotado: 3"):
            run()
    assert reload_cob("ref-1").status == "pending"   # status inalterado
    assert world.smtp.sent == []
    assert "PEDIDO PAGO SEM ENTREGA" in caplog.text and "cobrança 1" in caplog.text
    # repõe o estoque: o retry do RQ entrega
    add_chaves(3, "NOVA-CHAVE")
    run()
    assert reload_cob("ref-1").status == "delivered" and "NOVA-CHAVE" in world.smtp.messages()[0]["html"]


def test_produto_99_envia_external_reference_como_codigo(world, db_session):
    add_produto(99, nome="Compressão de PDF", tipo="ebook")
    add_cobranca("codigo-liberacao-xyz", produto_id=99)
    approve(world, "codigo-liberacao-xyz")
    run()
    (msg,) = world.smtp.messages()
    assert msg["subject"] == "BrooStore: Seu código de compressão de PDF chegou! 🗜️"
    assert "codigo-liberacao-xyz" in msg["html"] and "comprimir-pdf.html" in msg["html"]
    assert reload_cob("codigo-liberacao-xyz").status == "delivered"


def test_fisico_envia_email_de_pedido_com_endereco(world, db_session):
    add_produto(2, nome="Livro Impresso", tipo="fisico")
    obs = json.dumps({"endereco": {"rua": "Rua A", "numero": "10", "complemento": "ap 2", "bairro": "Centro",
                                   "cidade": "SP", "estado": "SP", "cep": "01001-000"}})
    add_cobranca("ref-f", produto_id=2, observacoes=obs, valor=75.5)
    approve(world, "ref-f")
    run()
    (msg,) = world.smtp.messages()
    assert msg["subject"] == 'BrooStore: Pedido "Livro Impresso" confirmado! 📦'
    assert "Rua A 10, ap 2" in msg["html"] and "CEP: 01001-000" in msg["html"] and "R$ 75.50" in msg["html"]
    assert reload_cob("ref-f").status == "delivered" and Sale.query.count() == 1


def test_fisico_usa_ssl_na_porta_465(world, db_session, monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "465")
    add_produto(2, tipo="fisico")
    add_cobranca("ref-f", produto_id=2)
    approve(world, "ref-f")
    run()
    assert world.smtp.connections == [("SMTP_SSL", "smtp.example.test", 465, 10)] and world.smtp.starttls_calls == 0


# ===================== assinatura ===========================================
def test_assinatura_nova_licenca(world, db_session):
    add_produto(10, nome="BrooStock Mensal", tipo="assinatura")
    add_plano(10, dias=30, rotulo="mensal")
    add_cobranca("ref-a", produto_id=10, email="Cli@Example.test ", valor=129.9)
    approve(world, "ref-a")
    antes = datetime.utcnow()
    run()
    lic = Licenca.query.one()
    assert lic.cliente_email == "cli@example.test" and lic.status == "ativa" and lic.plano == "mensal"
    assert antes + timedelta(days=29, hours=23) < lic.expira_em < datetime.utcnow() + timedelta(days=30, hours=1)
    assert lic.cobranca_id == Cobranca.query.one().id and lic.produto_id == 10
    (msg,) = world.smtp.messages()
    assert msg["subject"] == "BrooStock: Sua licença está ativa! 🚀" and "Mensal" in msg["html"]
    assert lic.expira_em.strftime("%d/%m/%Y") in msg["html"]
    assert reload_cob("ref-a").status == "delivered"
    assert Sale.query.count() == 0 and world.http.sales_posted == []   # assinatura não registra venda


def test_assinatura_renovacao_soma_a_partir_da_expiracao_atual(world, db_session):
    add_produto(10, tipo="assinatura")
    add_plano(10, dias=30, rotulo="mensal")
    expira = datetime.utcnow() + timedelta(days=10)
    add_licenca("cliente@example.test", expira, status="ativa", ultimo_aviso="7d")
    add_cobranca("ref-a", produto_id=10)
    approve(world, "ref-a")
    run()
    db.session.expire_all()
    lic = Licenca.query.one()
    assert lic.expira_em == expira + timedelta(days=30) and lic.ultimo_aviso is None


def test_assinatura_expirada_renova_a_partir_de_agora(world, db_session):
    add_produto(10, tipo="assinatura")
    add_plano(10, dias=365, rotulo="anual")
    add_licenca("cliente@example.test", datetime.utcnow() - timedelta(days=20), status="expirado", plano="mensal")
    add_cobranca("ref-a", produto_id=10)
    approve(world, "ref-a")
    run()
    db.session.expire_all()
    lic = Licenca.query.one()
    assert lic.status == "ativa" and lic.plano == "anual"
    assert datetime.utcnow() + timedelta(days=364, hours=23) < lic.expira_em < datetime.utcnow() + timedelta(days=365, hours=1)


def test_assinatura_sem_plano_levanta_e_nao_perde_pedido(world, db_session, caplog):
    add_produto(10, tipo="assinatura")
    add_cobranca("ref-a", produto_id=10, status="pending")
    approve(world, "ref-a")
    with caplog.at_level("ERROR", logger="broostore"):
        with pytest.raises(EntregaErro, match="Plano de assinatura não configurado para produto 10"):
            run()
    assert reload_cob("ref-a").status == "pending" and Licenca.query.count() == 0 and world.smtp.sent == []
    assert "PEDIDO PAGO SEM ENTREGA" in caplog.text


# ===================== casos de saída do job ================================
def test_sem_token_mp_retorna_sem_fazer_nada(world, db_session, monkeypatch):
    monkeypatch.delenv("MERCADOPAGO_ACCESS_TOKEN")
    assert run() is None and world.mp.tokens == []


def test_falha_ao_consultar_mp_retorna(world, db_session):
    world.mp.get_raises = ConnectionError("mp fora")
    assert run() is None


def test_mp_status_nao_200_levanta_para_o_rq_tentar_de_novo(world, db_session):
    world.mp.get_override = {"status": 500, "response": {}}
    with pytest.raises(RuntimeError, match="Erro na API do MP: 500"):
        run()


@pytest.mark.parametrize("status", ["pending", "rejected", "in_process"])
def test_pagamento_nao_aprovado_nao_entrega(world, db_session, status):
    add_produto(1)
    add_cobranca("ref-1", status="pending")
    world.mp.set_payment(555, status, "ref-1")
    run()
    assert reload_cob("ref-1").status == "pending" and world.smtp.sent == []


def test_pagamento_sem_external_reference(world, db_session):
    world.mp.payments["555"] = {"id": 555, "status": "approved"}
    run()
    assert world.smtp.sent == []


def test_cobranca_nao_encontrada_tenta_5_vezes(world, db_session, monkeypatch):
    esperas = []
    monkeypatch.setattr("time.sleep", lambda s: esperas.append(s))
    approve(world, "nao-existe")
    run()
    assert esperas == [2, 2, 2, 2] and world.smtp.sent == []


def test_produto_da_cobranca_sem_produto(world, db_session):
    add_cobranca("ref-1", produto_id=None)
    approve(world, "ref-1")
    run()
    assert reload_cob("ref-1").status == "pending" and world.smtp.sent == []


# ===================== F2: trava e reconferência ============================
def test_f2_segunda_execucao_encerra_quando_ja_entregue(world, db_session):
    add_produto(3, nome="Jogo", tipo="game")
    add_chaves(3, "K1", "K2")
    add_cobranca("ref-1", produto_id=3)
    approve(world, "ref-1")
    run()
    run()   # webhook duplicado
    assert len(world.smtp.sent) == 1 and len(world.http.sales_posted) == 1
    assert ChaveLicenca.query.filter_by(vendida=True).count() == 1 and Sale.query.count() == 1


def test_f2_trava_a_cobranca_com_for_update(world, db_session, monkeypatch):
    chamadas = []
    original = Query.with_for_update

    def espia(self, *a, **k):
        chamadas.append(str(self.column_descriptions[0]["name"]))
        return original(self, *a, **k)
    monkeypatch.setattr(Query, "with_for_update", espia)
    add_produto(1)
    add_cobranca("ref-1")
    approve(world, "ref-1")
    run()
    assert chamadas.count("Cobranca") == 2   # antes de cumprir e antes de enviar o e-mail


def test_f2_recheca_status_com_a_trava_mesmo_com_leitura_antiga(world, db_session, monkeypatch):
    """Simula o outro webhook entregando entre a leitura da cobrança e a obtenção da trava."""
    add_produto(1)
    add_cobranca("ref-1")
    approve(world, "ref-1")
    original = jobs._buscar_cobranca

    def buscar_e_outro_processo_entrega(ref):
        cob = original(ref)                       # esta sessão enxerga 'pending'
        with db.engine.begin() as conn:           # outro processo comita 'delivered'
            conn.execute(db.text("UPDATE cobrancas SET status='delivered' WHERE id=:i"), {"i": cob.id})
        return cob
    monkeypatch.setattr(jobs, "_buscar_cobranca", buscar_e_outro_processo_entrega)
    run()
    assert world.smtp.sent == [] and Sale.query.count() == 0


# ===================== F1: e-mail falhou ====================================
def test_f1_falha_de_email_mantem_approved_e_levanta(world, db_session):
    add_produto(3, nome="Jogo", tipo="game")
    add_chaves(3, "K1", "K2")
    add_cobranca("ref-1", produto_id=3, status="pending")
    approve(world, "ref-1")
    world.smtp.fail_login = True
    with pytest.raises(jobs.EmailEntregaFalhou):
        run()
    assert reload_cob("ref-1").status == "approved"
    k1 = ChaveLicenca.query.filter_by(chave_serial="K1").one()
    assert k1.vendida is True and k1.cobranca_id is not None     # fulfilment ficou comitado
    assert Sale.query.count() == 0 and world.http.sales_posted == []


def test_f1_retry_nao_reserva_outra_chave(world, db_session):
    add_produto(3, nome="Jogo", tipo="game")
    add_chaves(3, "K1", "K2")
    add_cobranca("ref-1", produto_id=3, status="pending")
    approve(world, "ref-1")
    world.smtp.fail_login = True
    with pytest.raises(jobs.EmailEntregaFalhou):
        run()
    with pytest.raises(jobs.EmailEntregaFalhou):    # segunda tentativa também falha: ainda 1 chave só
        run()
    assert ChaveLicenca.query.filter_by(vendida=True).count() == 1
    world.smtp.fail_login = False
    run()                                           # terceira funciona
    assert reload_cob("ref-1").status == "delivered"
    vendidas = ChaveLicenca.query.filter_by(vendida=True).all()
    assert [c.chave_serial for c in vendidas] == ["K1"]
    (msg,) = world.smtp.messages()
    assert "K1" in msg["html"]                      # o e-mail do retry leva a MESMA chave
    assert Sale.query.count() == 1 and len(world.http.sales_posted) == 1


def test_f1_retry_nao_estende_a_licenca_duas_vezes(world, db_session):
    add_produto(10, tipo="assinatura")
    add_plano(10, dias=30, rotulo="mensal")
    add_cobranca("ref-a", produto_id=10, status="pending")
    approve(world, "ref-a")
    world.smtp.fail_connect = True
    with pytest.raises(jobs.EmailEntregaFalhou):
        run()
    expira_1 = Licenca.query.one().expira_em
    assert reload_cob("ref-a").status == "approved"
    with pytest.raises(jobs.EmailEntregaFalhou):
        run()
    world.smtp.fail_connect = False
    run()
    db.session.expire_all()
    lic = Licenca.query.one()
    assert lic.expira_em == expira_1 and Licenca.query.count() == 1
    assert reload_cob("ref-a").status == "delivered"
    (msg,) = world.smtp.messages()
    assert expira_1.strftime("%d/%m/%Y") in msg["html"]


def test_f1_retry_assinatura_nao_estende_mesmo_se_outra_compra_sobrescreveu_a_licenca(world, db_session):
    """A licença guarda só a última cobrança; a marca em observacoes garante a idempotência mesmo assim."""
    add_produto(10, tipo="assinatura")
    add_plano(10, dias=30, rotulo="mensal")
    add_cobranca("ref-x", produto_id=10, status="pending")
    approve(world, "ref-x", 555)
    world.smtp.fail_connect = True
    with pytest.raises(jobs.EmailEntregaFalhou):
        run(555)
    world.smtp.fail_connect = False
    # compra Y do mesmo cliente é entregue e sobrescreve licenca.cobranca_id
    add_cobranca("ref-y", produto_id=10, status="pending")
    approve(world, "ref-y", 556)
    run(556)
    db.session.expire_all()
    expira_apos_y = Licenca.query.one().expira_em
    run(555)   # retry de X
    db.session.expire_all()
    assert Licenca.query.one().expira_em == expira_apos_y
    assert reload_cob("ref-x").status == "delivered"


def test_f1_cartao_ja_nasce_approved_e_ainda_cumpre_o_pedido(world, db_session):
    """Cobrança de cartão é gravada como 'approved' na criação (antes de qualquer entrega)."""
    add_produto(3, nome="Jogo", tipo="game")
    add_chaves(3, "K1", "K2")
    add_cobranca("ref-c", produto_id=3, status="approved")
    approve(world, "ref-c")
    run()
    assert reload_cob("ref-c").status == "delivered"
    assert ChaveLicenca.query.filter_by(vendida=True).count() == 1 and "K1" in world.smtp.messages()[0]["html"]


def test_f1_sem_credenciais_de_email_levanta_e_mantem_approved(world, db_session, monkeypatch):
    monkeypatch.delenv("EMAIL_PASSWORD")
    add_produto(1)
    add_cobranca("ref-1")
    approve(world, "ref-1")
    with pytest.raises(jobs.EmailEntregaFalhou):
        run()
    assert reload_cob("ref-1").status == "approved"
    monkeypatch.setenv("EMAIL_PASSWORD", "x")
    run()
    assert reload_cob("ref-1").status == "delivered"


def test_f1_falha_temporaria_smtp_depois_recupera(world, db_session):
    add_produto(1)
    add_cobranca("ref-1")
    approve(world, "ref-1")
    world.smtp.fail_times = 1
    with pytest.raises(jobs.EmailEntregaFalhou):
        run()
    run()
    assert reload_cob("ref-1").status == "delivered" and len(world.smtp.sent) == 1


def test_f1_status_approved_continua_valido_para_compressao_e_f4(client, world, db_session):
    add_produto(99)
    add_cobranca("cod-1", produto_id=99, status="pending")
    approve(world, "cod-1")
    world.smtp.fail_login = True
    with pytest.raises(jobs.EmailEntregaFalhou):
        run()
    # com o e-mail pendente o cliente já pode usar o código e a loja já vê "pago"
    assert client.post("/api/validar-codigo-compressao", json={"codigo": "cod-1"}).status_code == 200
    assert client.get("/api/cobrancas/cod-1/status").get_json() == {"status": "approved", "pago": True}


# ===================== fila + nome do job ===================================
def test_job_resolve_pelo_nome_da_fila_e_roda_inline(world, client, db_session):
    add_produto(1)
    add_cobranca("ref-1", status="pending")
    approve(world, "ref-1", 777)
    client.post("/api/webhook", json={"data": {"id": 777}})
    world.queue.run_all()   # importa "worker" e chama process_mercado_pago_webhook(777)
    assert reload_cob("ref-1").status == "delivered"


def test_shim_worker_reexporta_o_mesmo_job():
    import worker
    assert worker.process_mercado_pago_webhook is jobs.process_mercado_pago_webhook


def test_retry_aceito_pelo_rq_de_verdade():
    """O Retry(max=5, interval=[...]) que enfileiramos é aceito por rq.Queue.enqueue (Redis falso em memória)."""
    import fakeredis
    from rq import Queue
    from rq.job import Job

    from broostore_api.config import JOB_NAME, JOB_RETRY_INTERVALS, JOB_RETRY_MAX
    from rq import Retry
    q = Queue(connection=fakeredis.FakeStrictRedis(), is_async=False)
    q.connection.flushall()
    q2 = Queue("teste", connection=q.connection)
    job = q2.enqueue(JOB_NAME, 1, retry=Retry(max=JOB_RETRY_MAX, interval=JOB_RETRY_INTERVALS))
    assert isinstance(job, Job) and job.func_name == "worker.process_mercado_pago_webhook"
    assert job.retries_left == 5 and job.retry_intervals == [60, 300, 900, 3600, 7200]


def test_rq_real_worker_agenda_retry_quando_o_email_falha(world, db_session):
    """Worker RQ de verdade (Redis falso em memória): job que levanta com Retry vira SCHEDULED
    (e o pedido continua 'approved' com a chave reservada); com o e-mail OK, o job termina."""
    import fakeredis
    from rq import Queue, SimpleWorker
    from rq.registry import FailedJobRegistry, ScheduledJobRegistry

    from broostore_api.extensions import enfileirar_webhook
    from broostore_api import extensions

    conn = fakeredis.FakeStrictRedis()
    fila = Queue(connection=conn)
    extensions.set_queue(fila)
    add_produto(3, nome="Jogo", tipo="game")
    add_chaves(3, "K1", "K2")
    add_cobranca("ref-1", produto_id=3)
    approve(world, "ref-1", 888)
    world.smtp.fail_login = True

    job = enfileirar_webhook(888)
    SimpleWorker([fila], connection=conn).work(burst=True)
    job.refresh()
    assert job.get_status() == "scheduled" and job.retries_left == 4
    assert len(ScheduledJobRegistry(queue=fila)) == 1 and len(FailedJobRegistry(queue=fila)) == 0
    assert reload_cob("ref-1").status == "approved"
    assert ChaveLicenca.query.filter_by(vendida=True).count() == 1

    # próxima tentativa (o scheduler do worker a enfileiraria depois do intervalo): e-mail OK
    world.smtp.fail_login = False
    fila.enqueue(jobs_name(), 888)
    SimpleWorker([fila], connection=conn).work(burst=True)
    assert reload_cob("ref-1").status == "delivered"
    assert ChaveLicenca.query.filter_by(vendida=True).count() == 1


def jobs_name():
    from broostore_api.config import JOB_NAME
    return JOB_NAME
