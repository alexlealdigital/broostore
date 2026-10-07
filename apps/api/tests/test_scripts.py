"""Scripts: seeds (idempotentes) e cron de avisos de expiração."""
from datetime import datetime, timedelta

from broostore_api.models import Cupom, Licenca, PlanoAssinatura, Produto
from scripts import notificar_expiracao as cron
from scripts import seed_planos_broostock as seed
from tests.helpers import add_licenca


def test_seed_cria_planos_e_cupom_e_e_idempotente(app, capsys):
    criados = seed.main(app)
    assert [(n, p, d, r) for _, n, p, d, r in criados] == [
        ("BrooStock — Plano Mensal", 129.9, 30, "mensal"),
        ("BrooStock — Plano Anual", 1078.8, 365, "anual"),
        ("BrooStock — TESTE (R$ 1)", 1.0, 30, "mensal")]
    saida = capsys.readouterr().out
    assert "PRODUTOS DE ASSINATURA" in saida and "Cupom de teste: 'TESTE' (99% off)" in saida
    seed.main(app)  # 2ª execução: nada duplicado
    with app.app_context():
        assert Produto.query.count() == 3 and PlanoAssinatura.query.count() == 3 and Cupom.query.count() == 1
        assert Produto.query.filter_by(tipo="assinatura").count() == 3
        assert Cupom.query.one().valor == 99


def test_seed_chave_e_copia_do_seed_planos(app):
    from scripts import seed_chave_broostock
    assert seed_chave_broostock.main is seed.main


def test_cron_avisos(app, world, db_session):
    agora = datetime.utcnow()
    add_licenca("trial2d@example.test", agora + timedelta(days=1, hours=1), status="trial", plano="trial")
    add_licenca("trialvenceu@example.test", agora - timedelta(hours=1), status="trial", plano="trial")
    add_licenca("ativa7d@example.test", agora + timedelta(days=5), status="ativa")
    add_licenca("ativavenceu@example.test", agora - timedelta(days=1), status="ativa")
    add_licenca("longe@example.test", agora + timedelta(days=60), status="ativa")
    add_licenca("jaavisado@example.test", agora + timedelta(days=3), status="ativa", ultimo_aviso="7d")
    add_licenca("cancelada@example.test", agora - timedelta(days=3), status="cancelada")
    db_session.remove()
    assert cron.run(app) == 4
    msgs = {m["to"]: m for m in world.smtp.messages()}
    assert set(msgs) == {"trial2d@example.test", "trialvenceu@example.test", "ativa7d@example.test", "ativavenceu@example.test"}
    assert msgs["trial2d@example.test"]["subject"] == "Seu teste grátis do BrooStock está acabando ⏳"
    assert msgs["trialvenceu@example.test"]["subject"] == "Seu teste grátis do BrooStock terminou"
    assert msgs["ativa7d@example.test"]["subject"] == "Sua licença do BrooStock vai expirar"
    assert msgs["ativavenceu@example.test"]["subject"] == "Sua licença do BrooStock expirou"
    assert "https://brootechstock.netlify.app/login" in msgs["ativa7d@example.test"]["html"]
    with app.app_context():
        por_email = {lic.cliente_email: lic for lic in Licenca.query.all()}
        assert por_email["trial2d@example.test"].ultimo_aviso == "2d"
        assert por_email["ativa7d@example.test"].ultimo_aviso == "7d"
        assert por_email["ativavenceu@example.test"].status == "expirado" and por_email["ativavenceu@example.test"].ultimo_aviso == "expirado"
        assert por_email["trialvenceu@example.test"].status == "expirado"
    # segunda execução: cada estágio é enviado UMA vez
    world.smtp.sent.clear()
    assert cron.run(app) == 0 and world.smtp.sent == []


def test_cron_falha_de_smtp_nao_marca_aviso(app, world, db_session):
    add_licenca("a@example.test", datetime.utcnow() + timedelta(days=2), status="ativa")
    db_session.remove()
    world.smtp.fail_connect = True
    assert cron.run(app) == 0
    with app.app_context():
        assert Licenca.query.one().ultimo_aviso is None


def test_entrypoint_raiz_do_cron_reexporta_run():
    import notificar_expiracao
    assert notificar_expiracao.run is cron.run
