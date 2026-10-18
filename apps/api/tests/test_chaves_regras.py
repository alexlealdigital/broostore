"""Regras puras das chaves de licença (formato, dígito verificador, duração) e do registro de apps."""
from datetime import datetime, timedelta

import pytest

from broostore_api import apps_config
from broostore_api.services.licencas_chave import (ALFABETO, calcular_expiracao, formato_valido, gerar_chave,
                                                   normalizar_chave, situacao_licenca, tem_formato_novo)

AGORA = datetime(2026, 10, 15, 12, 0, 0)


def test_formato_e_digito_verificador():
    chave = gerar_chave()
    assert chave.startswith("BROO-") and len(chave) == len("BROO-XXXX-XXXX-XXXX-XXXX")
    assert formato_valido(chave) and tem_formato_novo(chave)
    assert formato_valido(gerar_chave("mapp")) and gerar_chave("mapp").startswith("MAPP-")


def test_nao_usa_caracteres_ambiguos_e_sao_unicas():
    chaves = {gerar_chave() for _ in range(200)}
    assert len(chaves) == 200
    for c in chaves:
        assert not set("01IO") & set(c.replace("BROO", "").replace("-", ""))
    assert len(ALFABETO) == 32


def test_erro_de_digitacao_e_rejeitado():
    chave = gerar_chave()
    trocado = chave[:-1] + ("A" if chave[-1] != "A" else "B")
    assert tem_formato_novo(trocado) and not formato_valido(trocado)


def test_normalizacao_aceita_minuscula_espacos_e_tracos_tipograficos():
    chave = gerar_chave()
    assert normalizar_chave("  " + chave.lower().replace("-", "–") + " ") == chave
    assert normalizar_chave(None) == ""


def test_chave_do_estoque_antigo_nao_tem_formato_novo():
    assert not tem_formato_novo("KEY-AAA-1111-2222") and not formato_valido("KEY-AAA-1111-2222")


def test_duracao_primeira_compra_renovacao_e_vitalicia():
    assert calcular_expiracao(30, None, AGORA) == AGORA + timedelta(days=30)
    futura = AGORA + timedelta(days=10)
    assert calcular_expiracao(30, futura, AGORA) == futura + timedelta(days=30)      # soma o que sobrou
    vencida = AGORA - timedelta(days=3)
    assert calcular_expiracao(30, vencida, AGORA) == AGORA + timedelta(days=30)      # conta de agora
    assert calcular_expiracao(None, futura, AGORA) is None and calcular_expiracao(0, None, AGORA) is None


def test_situacao_da_licenca():
    assert situacao_licenca(None, AGORA) == (True, None)
    assert situacao_licenca(AGORA + timedelta(hours=2), AGORA) == (True, 1)           # arredonda para cima
    assert situacao_licenca(AGORA + timedelta(days=5), AGORA) == (True, 5)
    assert situacao_licenca(AGORA - timedelta(seconds=1), AGORA) == (False, 0)


# ---------------------------------------------------------------------------
# apps_config
# ---------------------------------------------------------------------------
def test_slug_padrao_e_desconhecido():
    assert apps_config.normalizar_slug(None) == "broostock" and apps_config.normalizar_slug("  ") == "broostock"
    assert apps_config.normalizar_slug(" BrooStock ") == "broostock"
    assert apps_config.obter_app("broostock")["nome"] == "BrooStock"
    assert apps_config.obter_app("nao-existe") is None
    assert apps_config.slug_valido("meu-app") and not apps_config.slug_valido("Meu App")


def test_config_generica_nunca_quebra():
    cfg = apps_config.config_ou_generica("appremovido")
    assert cfg["nome"] == "Appremovido" and cfg["url"] == "https://broostore.netlify.app" and cfg["trial_dias"] == 7


def test_urls_do_app(monkeypatch):
    assert apps_config.url_login("broostock") == "https://brootechstock.netlify.app/login"
    assert apps_config.url_painel("broostock") == "https://brootechstock.netlify.app/painel"
    monkeypatch.setenv("BROOSTOCK_URL", "https://outro.example.test/entrar")        # variável antiga continua valendo
    assert apps_config.url_login("broostock") == "https://outro.example.test/entrar"
    monkeypatch.setenv("LOJA_URL", "https://loja.example.test")
    assert apps_config.config_ou_generica("zzz")["url"] == "https://loja.example.test"


def test_origens_cors_dos_apps():
    assert apps_config.origens_cors() == ["https://brootechstock.netlify.app"]


@pytest.mark.parametrize("slug", ["meuapp"])
def test_app_novo_so_precisa_de_uma_entrada(monkeypatch, slug):
    monkeypatch.setitem(apps_config.APPS, slug, {
        "nome": "MeuApp", "url": "https://meuapp.example.test/", "login_path": "/entrar", "painel_path": "/home",
        "trial_dias": 14, "uso": "suas planilhas", "boas_vindas_passos": ["Crie um projeto."]})
    assert apps_config.url_login(slug) == "https://meuapp.example.test/entrar"
    assert "https://meuapp.example.test" in apps_config.origens_cors()
