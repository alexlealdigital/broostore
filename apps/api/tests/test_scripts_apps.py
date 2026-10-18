"""Scripts de operação dos apps: cron por app/chaves/reconciliação, sincronização, seeds e reprocessamento."""
from datetime import datetime, timedelta

import pytest

from broostore_api import apps_config
from broostore_api.models import ChaveLicenca, Licenca, PlanoAssinatura, PlanoChave, Produto
from scripts import notificar_expiracao as cron
from scripts import reprocessar_pagamentos as repro
from scripts import seed_apps_chaves, seed_planos_app, sincronizar_licencas_app
from tests.helpers import add_chave_vendida, add_cobranca, add_licenca, add_plano, add_produto

MEUAPP = {"nome": "MeuApp", "url": "https://meuapp.example.test", "login_path": "/entrar", "painel_path": "/home",
          "trial_dias": 14, "uso": "suas planilhas", "boas_vindas_passos": []}


@pytest.fixture
def meuapp(monkeypatch):
    monkeypatch.setitem(apps_config.APPS, "meuapp", MEUAPP)


def configurar(monkeypatch, slug):
    monkeypatch.setenv(f"{slug}_SUPABASE_URL", f"https://{slug.lower()}.supabase.test")
    monkeypatch.setenv(f"{slug}_SUPABASE_SERVICE_KEY", "k")


# ---------------------------------------------------------------------------
# cron
# ---------------------------------------------------------------------------
def test_cron_aviso_usa_nome_e_link_do_app(app, world, db_session, meuapp):
    add_licenca("a@example.test", datetime.utcnow() + timedelta(days=3), app="meuapp")
    add_licenca("b@example.test", datetime.utcnow() + timedelta(days=3), app="broostock")
    db_session.remove()
    assert cron.run(app) == 2
    msgs = {m["to"]: m for m in world.smtp.messages()}
    assert msgs["a@example.test"]["subject"] == "Sua licença do MeuApp vai expirar"
    assert "https://meuapp.example.test/entrar" in msgs["a@example.test"]["html"]
    assert msgs["b@example.test"]["subject"] == "Sua licença do BrooStock vai expirar"


def test_cron_trial_expirado_menciona_o_uso_do_app(app, world, db_session, meuapp):
    add_licenca("a@example.test", datetime.utcnow() - timedelta(hours=1), status="trial", plano="trial", app="meuapp")
    db_session.remove()
    cron.run(app)
    (msg,) = world.smtp.messages()
    assert "suas planilhas" in msg["html"] and msg["subject"] == "Seu teste grátis do MeuApp terminou"


def test_cron_avisa_chaves_com_duracao(app, world, db_session):
    agora = datetime.utcnow()
    add_produto(5, nome="MeuApp Mensal", tipo="app")
    add_chave_vendida(5, "BROO-AAAA-0000-0000-0001", "perto@example.test", expira_em=agora + timedelta(days=5))
    add_chave_vendida(5, "BROO-AAAA-0000-0000-0002", "venceu@example.test", expira_em=agora - timedelta(hours=2))
    add_chave_vendida(5, "BROO-AAAA-0000-0000-0003", "longe@example.test", expira_em=agora + timedelta(days=60))
    add_chave_vendida(5, "BROO-AAAA-0000-0000-0004", "revogada@example.test", expira_em=agora + timedelta(days=1), revogada=True)
    add_chave_vendida(5, "BROO-AAAA-0000-0000-0005", "vitalicia@example.test", expira_em=None)
    db_session.remove()
    assert cron.run(app) == 2
    msgs = {m["to"]: m for m in world.smtp.messages()}
    assert set(msgs) == {"perto@example.test", "venceu@example.test"}
    assert msgs["perto@example.test"]["subject"] == "Sua licença de MeuApp Mensal vai expirar"
    assert msgs["venceu@example.test"]["subject"] == "Sua licença de MeuApp Mensal expirou"
    assert "https://broostore.netlify.app" in msgs["perto@example.test"]["html"]
    with app.app_context():
        avisos = {c.cliente_email: c.ultimo_aviso for c in ChaveLicenca.query.all()}
    assert avisos["perto@example.test"] == "7d" and avisos["venceu@example.test"] == "expirado"
    world.smtp.sent.clear()
    assert cron.run(app) == 0                                  # cada estágio uma vez só


def test_cron_reconcilia_cada_app_com_o_seu_supabase(app, world, db_session, monkeypatch, meuapp):
    configurar(monkeypatch, "BROOSTOCK")
    add_licenca("a@example.test", datetime.utcnow() + timedelta(days=60), app="broostock")
    add_licenca("b@example.test", datetime.utcnow() + timedelta(days=60), app="meuapp")   # sem variáveis
    db_session.remove()
    cron.run(app)
    (url, corpo, _), = world.http.licenses_posted
    assert url.startswith("https://broostock.supabase.test/") and corpo["email"] == "a@example.test"


def test_cron_app_sem_variaveis_nao_derruba(app, world, db_session):
    add_licenca("a@example.test", datetime.utcnow() + timedelta(days=60))
    db_session.remove()
    assert cron.run(app) == 0 and world.http.licenses_posted == []


# ---------------------------------------------------------------------------
# sincronizar_licencas_app
# ---------------------------------------------------------------------------
def test_sincronizar_envia_todas_as_licencas_do_app(app, world, db_session, monkeypatch, meuapp):
    configurar(monkeypatch, "BROOSTOCK")
    agora = datetime.utcnow()
    add_licenca("ativa@example.test", agora + timedelta(days=9))
    add_licenca("trial@example.test", agora + timedelta(days=2), status="trial", plano="trial")
    add_licenca("vencida@example.test", agora - timedelta(days=2))
    add_licenca("outro@example.test", agora + timedelta(days=9), app="meuapp")
    db_session.remove()
    assert sincronizar_licencas_app.main("broostock", app) == (3, 3, 1, 0)
    enviados = {c["email"]: c for _, c, _ in world.http.licenses_posted}
    assert set(enviados) == {"ativa@example.test", "trial@example.test", "vencida@example.test"}
    assert enviados["vencida@example.test"]["ativa"] is False and enviados["trial@example.test"]["is_trial"] is True


def test_sincronizar_exige_app_cadastrado_e_variaveis(app):
    with pytest.raises(SystemExit, match="não está em apps_config"):
        sincronizar_licencas_app.main("nao-existe", app)
    with pytest.raises(SystemExit, match="BROOSTOCK_SUPABASE_URL"):
        sincronizar_licencas_app.main("broostock", app)


def test_sincronizar_com_falha_termina_com_erro(app, world, db_session, monkeypatch):
    configurar(monkeypatch, "BROOSTOCK")
    add_licenca("a@example.test", datetime.utcnow() + timedelta(days=9))
    db_session.remove()
    world.http.licenses_status = 500
    with pytest.raises(SystemExit, match="Houve falhas"):
        sincronizar_licencas_app.main("broostock", app)


# ---------------------------------------------------------------------------
# seeds
# ---------------------------------------------------------------------------
def test_seed_planos_app_e_idempotente(app, meuapp):
    planos = [("MeuApp — Plano Mensal", 49.9, 30, "mensal"), ("MeuApp — Plano Anual", 499.0, 365, "anual")]
    criados = seed_planos_app.main("meuapp", planos, app)
    assert [(n, d, r) for _, n, _, d, r in criados] == [("MeuApp — Plano Mensal", 30, "mensal"), ("MeuApp — Plano Anual", 365, "anual")]
    seed_planos_app.main("meuapp", [("MeuApp — Plano Mensal", 59.9, 31, "mensal")], app)   # reexecução atualiza
    with app.app_context():
        assert Produto.query.count() == 2 and PlanoAssinatura.query.count() == 2
        mensal = Produto.query.filter_by(nome="MeuApp — Plano Mensal").one()
        plano = PlanoAssinatura.query.get(mensal.id)
        assert mensal.preco == 59.9 and mensal.tipo == "assinatura" and plano.dias == 31 and plano.app_slug == "meuapp"


def test_seed_planos_app_valida_entrada(app):
    with pytest.raises(SystemExit, match="não está em apps_config"):
        seed_planos_app.main("nao-existe", [("x", 1, 1, "m")], app)
    with pytest.raises(SystemExit, match="vazia"):
        seed_planos_app.main("broostock", None, app)


def test_seed_apps_chaves_cria_produto_e_plano(app):
    apps = [("MeuApp — Mensal", 29.9, "https://x.test/setup.exe", 30, "mensal", 1, "MAPP"),
            ("MeuApp — Vitalícia", 599.0, "https://x.test/setup.exe", None, "vitalicia", 2, "MAPP")]
    criados = seed_apps_chaves.main(apps, app)
    assert len(criados) == 2
    seed_apps_chaves.main(apps, app)                           # idempotente
    with app.app_context():
        assert Produto.query.filter_by(tipo="app").count() == 2 and PlanoChave.query.count() == 2
        vit = PlanoChave.query.filter_by(rotulo="vitalicia").one()
        assert vit.dias is None and vit.max_dispositivos == 2 and vit.prefixo == "MAPP"
    with pytest.raises(SystemExit, match="vazia"):
        seed_apps_chaves.main(None, app)


# ---------------------------------------------------------------------------
# reprocessar_pagamentos
# ---------------------------------------------------------------------------
class FakeSDK:
    def __init__(self, pagos, quebra=()):
        self.pagos, self.quebra = pagos, set(quebra)

    def payment(self):
        return self

    def search(self, filtros):
        ref = filtros["external_reference"]
        if ref in self.quebra:
            return {"status": 500, "response": {}}
        if ref in self.pagos:
            return {"status": 200, "response": {"results": [{"id": self.pagos[ref], "status": "approved"}]}}
        return {"status": 200, "response": {"results": [{"id": 1, "status": "pending"}]}}


@pytest.fixture
def banco(app, db_session):
    add_produto(1)
    add_cobranca("paga-nao-entregue", produto_id=1, status="approved")
    add_cobranca("nunca-paga", produto_id=1, status="pending")
    add_cobranca("ja-entregue", produto_id=1, status="delivered")
    antiga = add_cobranca("paga-antiga", produto_id=1, status="pending")
    antiga.data_criacao = datetime.utcnow() - timedelta(days=30)
    db_session.commit()


def test_reprocessar_modo_lista_nao_entrega_nada(banco):
    chamados = []
    sdk = FakeSDK({"paga-nao-entregue": 901, "paga-antiga": 902})
    pagas, entregues = repro.reprocessar(7, False, sdk, chamados.append)
    assert len(pagas) == 1 and entregues == 0 and chamados == []


def test_reprocessar_executar_entrega_so_as_pagas_recentes(banco):
    chamados = []
    sdk = FakeSDK({"paga-nao-entregue": 901, "paga-antiga": 902})
    pagas, entregues = repro.reprocessar(7, True, sdk, chamados.append)
    assert chamados == [901] and entregues == 1
    repro.reprocessar(60, True, sdk, chamados.append)           # janela maior pega a antiga também
    assert 902 in chamados


def test_reprocessar_falha_numa_entrega_nao_para_as_outras(banco, db_session):
    add_cobranca("paga-2", produto_id=1, status="pending")
    chamados = []

    def processar(pid):
        chamados.append(pid)
        if pid == 901:
            raise RuntimeError("boom")
    sdk = FakeSDK({"paga-nao-entregue": 901, "paga-2": 903}, quebra={"nunca-paga"})
    pagas, entregues = repro.reprocessar(7, True, sdk, processar)
    assert chamados == [901, 903] and entregues == 1 and len(pagas) == 2


def test_reprocessar_entrega_de_verdade_pelo_job(world, banco, db_session):
    """Sem dublê de processamento: usa o job real (e-mail incluso)."""
    world.mp.set_payment(901, "approved", "paga-nao-entregue")
    sdk = FakeSDK({"paga-nao-entregue": 901})
    pagas, entregues = repro.reprocessar(7, True, sdk)
    assert entregues == 1 and len(world.smtp.messages()) == 1


def test_reprocessar_sem_token_aborta(app, monkeypatch):
    monkeypatch.delenv("MERCADOPAGO_ACCESS_TOKEN")
    with pytest.raises(SystemExit, match="MERCADOPAGO_ACCESS_TOKEN"):
        repro.reprocessar(7, False)


def test_atalhos_da_raiz_reexportam():
    import reprocessar_pagamentos
    import sincronizar_licencas_app as atalho
    assert reprocessar_pagamentos.reprocessar is repro.reprocessar and atalho.main is sincronizar_licencas_app.main


def test_add_plano_helper_define_o_app(app, db_session):
    add_produto(9, tipo="assinatura")
    add_plano(9, app="meuapp")
    assert PlanoAssinatura.query.get(9).app_slug == "meuapp" and Licenca.query.count() == 0
