"""GOLDEN do worker: o job ORIGINAL (worker.py) x o job novo (jobs.py) no caminho de sucesso —
mesmos e-mails (assunto + HTML), mesmas linhas no banco, mesmas chamadas ao Supabase.
(F1 muda só o caminho de FALHA do e-mail; ele é testado em tests/test_jobs.py.)"""
import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from broostore_api import jobs
from tests.golden.harness import Side, assert_same
from tests.golden.scenarios import seed

ENDERECO = json.dumps({"endereco": {"rua": "Rua A", "numero": "10", "complemento": "ap 2", "bairro": "Centro",
                                     "cidade": "SP", "estado": "SP", "cep": "01001-000"}, "frete": 25.5})


def _cobranca(s, ref, produto_id, email="comprador@example.test", nome="Maria Souza", valor=42.5, obs=None, status="pending"):
    s.execute("INSERT INTO cobrancas (external_reference,cliente_nome,cliente_email,valor,valor_original,status,data_criacao,product_id,observacoes)"
              " VALUES (:r,:n,:e,:v,:v,:s,:d,:p,:o)", r=ref, n=nome, e=email, v=valor, s=status, d=datetime.utcnow(), p=produto_id, o=obs)


def _chaves(s, produto_id, *seriais):
    for k in seriais:
        s.execute("INSERT INTO chaves_licenca (chave_serial,produto_id,vendida,ativa_no_app) VALUES (:k,:p,:v,:a)",
                  k=k, p=produto_id, v=False, a=False)


def _job(s, payment_id, original):
    try:
        if s.name == "original":
            original.run_job(payment_id)
        else:
            jobs.process_mercado_pago_webhook(payment_id)
        s.log.append(("job", "ok"))
    except Exception as e:  # noqa: BLE001 — o que importa é comparar a mensagem
        s.log.append(("job", "levantou", str(e)))


CASOS = {
    "ebook": lambda s: _cobranca(s, "ref-ebook", 1),
    "game": lambda s: (_chaves(s, 3, "KEY-AAA-1111-2222", "KEY-BBB"), _cobranca(s, "ref-game", 3)),
    "app": lambda s: (_chaves(s, 4, "APP-KEY-1"), _cobranca(s, "ref-app", 4)),
    "estoque_esgotado": lambda s: _cobranca(s, "ref-estoque", 3),
    "pdf99": lambda s: _cobranca(s, "codigo-liberacao-uuid", 99),
    "fisico": lambda s: _cobranca(s, "ref-fisico", 2, obs=ENDERECO, valor=85.5),
    "fisico_sem_endereco": lambda s: _cobranca(s, "ref-fisico", 2, obs="isto-nao-e-json"),
    "assinatura_nova": lambda s: _cobranca(s, "ref-ass", 10, email=" Novo@Cliente.test "),
    "assinatura_renovacao": lambda s: _cobranca(s, "ref-ass", 10, email="ativa@example.test"),
    "assinatura_expirada": lambda s: _cobranca(s, "ref-ass", 10, email="expirada@example.test"),
    "assinatura_sem_plano": lambda s: _cobranca(s, "ref-ass", 11),
    "cartao_ja_approved": lambda s: (_chaves(s, 3, "K1"), _cobranca(s, "ref-cartao", 3, status="approved")),
    "ja_entregue": lambda s: _cobranca(s, "ref-ent", 1, status="delivered"),
    "nao_aprovado": lambda s: _cobranca(s, "ref-pend", 1),
}


@pytest.mark.parametrize("caso", sorted(CASOS))
def test_golden_job(caso, original, nova, mundo, monkeypatch):
    from broostore_api.extensions import db
    so = Side("original", original.app, original.db, original.client, mundo)
    sn = Side("novo", nova, db, nova.test_client(), mundo)
    for lado in (so, sn):
        lado.reset_world()
        seed(lado)
        CASOS[caso](lado)
        with lado.app.app_context():
            ref = lado.db.session.execute(text("SELECT external_reference FROM cobrancas ORDER BY id DESC LIMIT 1")).scalar()
            lado.db.session.rollback()
        status_mp = "pending" if caso == "nao_aprovado" else "approved"
        mundo.mp.set_payment(777, status_mp, ref)
        _job(lado, 777, original)
        lado.snapshot("cobrancas", "chaves_licenca", "licencas", "sales")
    assert_same(so, sn)
    # sanidade: o cenário realmente exercitou algo (e-mail enviado ou erro/saída esperada)
    corpo = " ".join(str(i) for i in so.log)
    assert ("smtp" in corpo) and ("job" in corpo)


def test_golden_job_mp_saidas_antecipadas(original, nova, mundo, monkeypatch):
    from broostore_api.extensions import db
    so = Side("original", original.app, original.db, original.client, mundo)
    sn = Side("novo", nova, db, nova.test_client(), mundo)
    for lado in (so, sn):
        lado.reset_world()
        seed(lado)
        _job(lado, 1, original)                                   # pagamento desconhecido no MP (404)
        mundo.mp.set_payment(2, "approved", None)
        _job(lado, 2, original)                                   # sem external_reference
        mundo.mp.set_payment(3, "approved", "nao-existe-no-banco")
        _job(lado, 3, original)                                   # cobrança inexistente
        mundo.mp.get_raises = ConnectionError("fora")
        _job(lado, 4, original)                                   # MP indisponível
        mundo.mp.get_raises = None
        monkeypatch.delenv("MERCADOPAGO_ACCESS_TOKEN")
        _job(lado, 5, original)                                   # sem token
        monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "TEST-fake-mp-token")
        lado.snapshot("cobrancas")
    assert_same(so, sn)


def test_golden_cron_avisos(original, nova, mundo, monkeypatch):
    """notificar_expiracao.py original x scripts/notificar_expiracao.py: mesmos e-mails e mesma atualização de licenças."""
    import importlib.util
    import sys

    from broostore_api.extensions import db
    sys.modules["app"] = original.app_module           # o cron original faz `from app import app, db, Licenca`
    try:
        spec = importlib.util.spec_from_file_location("orig_cron", _cron_original_path())
        orig_cron = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(orig_cron)
        from scripts import notificar_expiracao as novo_cron
        so = Side("original", original.app, original.db, original.client, mundo)
        sn = Side("novo", nova, db, nova.test_client(), mundo)
        agora = datetime.utcnow()
        for lado, run in ((so, orig_cron.run), (sn, lambda: novo_cron.run(nova))):
            lado.reset_world()
            for email, status, delta, aviso in [
                ("trial2d@example.test", "trial", timedelta(days=1, hours=1), None),
                ("trialvenceu@example.test", "trial", -timedelta(hours=1), None),
                ("ativa7d@example.test", "ativa", timedelta(days=5), None),
                ("ativavenceu@example.test", "ativa", -timedelta(days=1), None),
                ("longe@example.test", "ativa", timedelta(days=60), None),
                ("jaavisado@example.test", "ativa", timedelta(days=3), "7d"),
                ("cancelada@example.test", "cancelada", -timedelta(days=3), None)]:
                lado.execute("INSERT INTO licencas (cliente_email,plano,status,inicia_em,expira_em,ultimo_pagamento_em,ultimo_aviso)"
                             " VALUES (:e,'p',:s,:i,:x,:i,:a)", e=email, s=status, i=agora, x=agora + delta, a=aviso)
            run()
            lado.snapshot("licencas")
        assert_same(so, sn)
        # sanidade: os 4 estágios de aviso foram realmente enviados nos dois lados
        assert [len(i[1]) for i in so.log if i[0] == "smtp"] == [4]
    finally:
        sys.modules.pop("app", None)


def _cron_original_path():
    from tests.golden.harness import ORIGINAL_DIR
    return ORIGINAL_DIR / "notificar_expiracao.py"
