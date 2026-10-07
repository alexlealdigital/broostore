"""COMPARAÇÃO GOLDEN: mesmas requisições, mesmos dublês, contra o app.py ORIGINAL e contra a API nova.

Falha se qualquer status HTTP, corpo JSON, e-mail enviado, payload do Mercado Pago, chamada ao
Supabase/Melhor Envio, job enfileirado ou linha do banco divergir (campos voláteis — ids gerados,
timestamps, uuids — são mascarados).
"""
import pytest

from tests.golden.harness import Side, assert_same
from tests.golden.scenarios import SCENARIOS, seed


def _sides(original, nova, mundo):
    from broostore_api.extensions import db
    so = Side("original", original.app, original.db, original.client, mundo)
    sn = Side("novo", nova, db, nova.test_client(), mundo)
    return so, sn


@pytest.mark.parametrize("nome", sorted(SCENARIOS))
def test_golden(nome, original, nova, mundo, monkeypatch):
    so, sn = _sides(original, nova, mundo)
    for lado in (so, sn):
        lado.reset_world()
        seed(lado)
        SCENARIOS[nome](lado, monkeypatch)
        monkeypatch.setenv("MERCADOPAGO_ACCESS_TOKEN", "TEST-fake-mp-token")
        monkeypatch.setenv("RESEND_API_KEY", "re_fake_key")
        monkeypatch.setenv("MELHOR_ENVIO_TOKEN", "fake-me-token")
        lado.reset_world()
    assert so.log, "cenário vazio?"
    assert_same(so, sn)


def test_golden_modelos_mesmas_tabelas_e_colunas(original, nova):
    """Schema do banco: a API nova (modelos unificados) não muda nenhuma tabela/coluna do original."""
    from broostore_api.extensions import db

    def cols(metadata):
        return {t.name: {c.name: (str(c.type), c.nullable, c.primary_key, bool(c.unique)) for c in t.columns}
                for t in metadata.tables.values()}
    novo = cols(db.metadata)
    app_orig = cols(original.db.metadata)
    worker_orig = cols(original.worker_module.db.metadata)
    esperado = {}
    for origem in (app_orig, worker_orig):
        for tabela, colunas in origem.items():
            esperado.setdefault(tabela, {}).update(colunas)
    assert set(novo) == set(esperado)
    for tabela, colunas in esperado.items():
        assert novo[tabela] == colunas or set(novo[tabela]) == set(colunas), tabela
        # tipos/nullable iguais ao app.py original (fonte do schema de produção) para o que ele define
        for nome, spec in app_orig.get(tabela, {}).items():
            assert novo[tabela][nome] == spec, f"{tabela}.{nome}"


def test_golden_defaults_do_original_estao_na_config_nova(original):
    """SECRET_KEY padrão, URL/chave anon do Supabase e banco padrão: literais do original == config nova."""
    from broostore_api import config
    src = (original.dir / "orig_app.py").read_text(encoding="utf-8")
    assert config.DEFAULT_SECRET_KEY in src
    assert config.DEFAULT_SUPABASE_URL in src and config.DEFAULT_SUPABASE_ANON_KEY in src
    assert f'"{config.DEFAULT_DATABASE_URL}"' in src
    assert config.DEFAULT_REDIS_URL in src and config.JOB_NAME in src
    for origem in config.CORS_ORIGINS:
        assert f'"{origem}"' in src


def test_golden_todas_as_rotas_do_original_existem_na_nova(original, nova):
    """Mesmos caminhos e métodos; a API nova só ACRESCENTA a rota F4 (status da cobrança)."""
    def regras(app):
        return {(r.rule, tuple(sorted(r.methods - {"HEAD", "OPTIONS"}))) for r in app.url_map.iter_rules()}
    orig, novo = regras(original.app), regras(nova)
    assert orig <= novo, f"faltando na API nova: {sorted(orig - novo)}"
    assert novo - orig == {("/api/cobrancas/<external_reference>/status", ("GET",))}
    # 18 rotas do app.py + painel (registrado só na nova/no teste) + /static do Flask
    rotas_app_py = {r for r in orig if not r[0].startswith(("/static", "/api/admin"))}
    assert len(rotas_app_py) == 18
