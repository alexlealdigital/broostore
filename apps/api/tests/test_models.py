"""Modelos unificados: mesmas tabelas/colunas do original (sem mudança de schema)."""
from importlib import import_module

from broostore_api.extensions import db


def _colunas():
    import_module("broostore_api.models")
    return {t.name: {c.name for c in t.columns} for t in db.metadata.sorted_tables}


def test_tabelas_e_colunas_esperadas():
    cols = _colunas()
    assert set(cols) == {"vendedores", "cupons", "cobrancas", "produtos", "chaves_licenca", "sales",
                         "planos_assinatura", "licencas"}
    assert cols["cobrancas"] == {"id", "external_reference", "cliente_nome", "cliente_email", "cliente_telefone", "valor",
                                 "valor_original", "status", "data_criacao", "product_id", "vendedor_codigo", "cupom_id",
                                 "observacoes"}
    assert cols["chaves_licenca"] == {"id", "chave_serial", "produto_id", "vendida", "vendida_em", "cobranca_id",
                                      "cliente_email", "ativa_no_app"}
    assert cols["licencas"] == {"id", "cliente_email", "plano", "status", "inicia_em", "expira_em",
                                "ultimo_pagamento_em", "cobranca_id", "produto_id", "ultimo_aviso"}
    assert cols["sales"] == {"id", "product_id", "amount", "created_at"}


def test_cupom_calculo():
    from broostore_api.models import Cupom
    c = Cupom(codigo="X", tipo="percentual", valor=25)
    assert c.calcular_desconto(80) == {"valor_original": 80, "desconto": 20.0, "valor_final": 60.0, "percentual_aplicado": 25}
    f = Cupom(codigo="Y", tipo="valor_fixo", valor=10)
    assert f.calcular_desconto(40)["valor_final"] == 30 and f.calcular_desconto(40)["percentual_aplicado"] == 25.0
