"""Compra de app com chave gerada (planos_chave): geração, renovação, e-mail e idempotência do retry (F1)."""
import json
from datetime import datetime, timedelta

import pytest

from broostore_api import jobs
from broostore_api.extensions import db
from broostore_api.models import ChaveLicenca, Cobranca
from broostore_api.services.licencas_chave import formato_valido
from tests.helpers import add_chave_vendida, add_chaves, add_cobranca, add_plano_chave, add_produto


def run(world, ref, payment_id=555):
    world.mp.set_payment(payment_id, "approved", ref)
    jobs.process_mercado_pago_webhook(payment_id)
    db.session.expire_all()


def test_compra_nova_gera_chave_com_validade_e_envia_no_email(world, db_session):
    add_produto(5, nome="MeuApp Mensal", tipo="app", link="https://dl.example.test/setup.exe")
    add_plano_chave(5, dias=30, rotulo="mensal", prefixo="MAPP")
    add_cobranca("ref-1", produto_id=5, email="Cli@Example.test ")
    antes = datetime.utcnow()
    run(world, "ref-1")
    chave = ChaveLicenca.query.one()
    assert chave.chave_serial.startswith("MAPP-") and formato_valido(chave.chave_serial)
    assert chave.vendida and chave.cliente_email == "cli@example.test" and chave.plano == "mensal"
    assert antes + timedelta(days=29, hours=23) < chave.expira_em < datetime.utcnow() + timedelta(days=30, hours=1)
    assert chave.cobranca_id == Cobranca.query.one().id and Cobranca.query.one().status == "delivered"
    (msg,) = world.smtp.messages()
    assert chave.chave_serial in msg["html"] and "válida até" in msg["html"]
    assert chave.expira_em.strftime("%d/%m/%Y") in msg["html"] and "(mensal)" in msg["html"]
    assert msg["subject"] == 'BrooStore: Sua chave de acesso para "MeuApp Mensal" chegou! 🚀'
    assert "https://dl.example.test/setup.exe" in msg["html"]


def test_segunda_compra_renova_a_mesma_chave_e_avisa(world, db_session):
    add_produto(5, nome="MeuApp Mensal", tipo="app")
    add_plano_chave(5, dias=30)
    add_cobranca("ref-1", produto_id=5, email="cli@example.test")
    run(world, "ref-1")
    primeira = ChaveLicenca.query.one()
    serial, expira1 = primeira.chave_serial, primeira.expira_em
    primeira.ultimo_aviso = "7d"
    db.session.commit()
    add_cobranca("ref-2", produto_id=5, email="CLI@example.test")
    world.smtp.sent.clear()
    run(world, "ref-2", payment_id=556)
    chave = ChaveLicenca.query.one()                                    # continua UMA chave
    assert chave.chave_serial == serial and chave.expira_em == expira1 + timedelta(days=30)
    assert chave.ultimo_aviso is None                                   # rearma os avisos de vencimento
    (msg,) = world.smtp.messages()
    assert msg["subject"] == 'BrooStore: Sua licença de "MeuApp Mensal" foi renovada! 🔄'
    assert "Licença renovada" in msg["html"] and serial in msg["html"]


def test_renovacao_depois_de_vencer_conta_de_agora(world, db_session):
    add_produto(5, tipo="app")
    add_plano_chave(5, dias=30)
    add_chave_vendida(5, "BROO-AAAA-BBBB-CCCC-DDDD", email="cli@example.test",
                      expira_em=datetime.utcnow() - timedelta(days=20))
    add_cobranca("ref-1", produto_id=5, email="cli@example.test")
    run(world, "ref-1")
    expira = ChaveLicenca.query.one().expira_em
    assert datetime.utcnow() + timedelta(days=29, hours=23) < expira < datetime.utcnow() + timedelta(days=30, hours=1)


def test_emails_diferentes_nao_compartilham_chave(world, db_session):
    add_produto(5, tipo="app")
    add_plano_chave(5, dias=30)
    add_cobranca("ref-1", produto_id=5, email="a@example.test")
    add_cobranca("ref-2", produto_id=5, email="b@example.test")
    run(world, "ref-1")
    run(world, "ref-2", payment_id=556)
    assert ChaveLicenca.query.count() == 2


def test_vitalicia_gera_chave_nova_a_cada_compra(world, db_session):
    add_produto(5, tipo="app")
    add_plano_chave(5, dias=None, rotulo="vitalicia")
    add_cobranca("ref-1", produto_id=5, email="a@example.test")
    add_cobranca("ref-2", produto_id=5, email="a@example.test")
    run(world, "ref-1")
    run(world, "ref-2", payment_id=556)
    chaves = ChaveLicenca.query.all()
    assert len(chaves) == 2 and all(c.expira_em is None for c in chaves)
    assert "vitalícia" in world.smtp.messages()[0]["html"]


def test_chave_revogada_nao_e_renovada(world, db_session):
    add_produto(5, tipo="app")
    add_plano_chave(5, dias=30)
    add_chave_vendida(5, "BROO-AAAA-BBBB-CCCC-DDDD", email="a@example.test", revogada=True,
                      expira_em=datetime.utcnow() + timedelta(days=5))
    add_cobranca("ref-1", produto_id=5, email="a@example.test")
    run(world, "ref-1")
    assert ChaveLicenca.query.count() == 2                              # a revogada fica como está; nasce outra


def test_produto_sem_plano_continua_no_estoque_pre_carregado(world, db_session):
    add_produto(3, nome="Jogo", tipo="game")
    add_chaves(3, "KEY-AAA-1111-2222")
    add_cobranca("ref-1", produto_id=3)
    run(world, "ref-1")
    c = ChaveLicenca.query.one()
    assert c.vendida and c.expira_em is None and c.plano is None
    (msg,) = world.smtp.messages()
    assert "KEY-AAA-1111-2222" in msg["html"] and "válida até" not in msg["html"] and "vitalícia" not in msg["html"]
    assert "use-a no instalador" in msg["html"]                         # texto de sempre


def test_retry_nao_gera_outra_chave(world, db_session):
    add_produto(5, tipo="app")
    add_plano_chave(5, dias=30)
    add_cobranca("ref-1", produto_id=5)
    world.mp.set_payment(555, "approved", "ref-1")
    world.smtp.fail_login = True
    for _ in range(2):
        with pytest.raises(jobs.EmailEntregaFalhou):
            jobs.process_mercado_pago_webhook(555)
    assert ChaveLicenca.query.count() == 1
    world.smtp.fail_login = False
    jobs.process_mercado_pago_webhook(555)
    db.session.expire_all()
    (chave,) = ChaveLicenca.query.all()
    (msg,) = world.smtp.messages()
    assert chave.chave_serial in msg["html"] and "válida até" in msg["html"]


def test_retry_nao_soma_os_dias_da_renovacao_duas_vezes(world, db_session):
    add_produto(5, tipo="app")
    add_plano_chave(5, dias=30)
    add_chave_vendida(5, "BROO-AAAA-BBBB-CCCC-DDDD", email="a@example.test",
                      expira_em=datetime.utcnow() + timedelta(days=10))
    original = ChaveLicenca.query.one().expira_em
    add_cobranca("ref-1", produto_id=5, email="a@example.test")
    world.mp.set_payment(555, "approved", "ref-1")
    world.smtp.fail_login = True
    for _ in range(3):
        with pytest.raises(jobs.EmailEntregaFalhou):
            jobs.process_mercado_pago_webhook(555)
    db.session.expire_all()
    assert ChaveLicenca.query.one().expira_em == original + timedelta(days=30)   # +30 uma vez só
    obs = json.loads(Cobranca.query.one().observacoes)
    assert obs["chave_aplicada"] == "BROO-AAAA-BBBB-CCCC-DDDD" and obs["chave_renovada"] is True
    world.smtp.fail_login = False
    jobs.process_mercado_pago_webhook(555)
    db.session.expire_all()
    assert ChaveLicenca.query.one().expira_em == original + timedelta(days=30)
    (msg,) = world.smtp.messages()
    assert "Licença renovada" in msg["html"]                            # o e-mail do retry continua dizendo "renovada"
