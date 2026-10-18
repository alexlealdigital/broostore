"""Funções de apoio para montar dados no banco de teste."""
from datetime import date, datetime, timedelta

from broostore_api.extensions import db
from broostore_api.models import (ChaveLicenca, Cobranca, Cupom, Licenca, PlanoAssinatura, PlanoChave, Produto,
                                  Vendedor)


def add_produto(id, nome="Produto Teste", preco=10.0, tipo="ebook", link="https://dl.example.test/p"):
    p = Produto(id=id, nome=nome, preco=preco, link_download=link, tipo=tipo)
    db.session.add(p)
    db.session.commit()
    return p


def add_cobranca(external_reference="ref-1", produto_id=1, status="pending", email="cliente@example.test",
                 nome="Cliente Teste", valor=10.0, observacoes=None, vendedor_codigo=None):
    c = Cobranca(external_reference=external_reference, cliente_nome=nome, cliente_email=email, valor=valor,
                 valor_original=valor, status=status, product_id=produto_id, observacoes=observacoes,
                 vendedor_codigo=vendedor_codigo)
    db.session.add(c)
    db.session.commit()
    return c


def add_chaves(produto_id, *seriais):
    for s in seriais:
        db.session.add(ChaveLicenca(chave_serial=s, produto_id=produto_id))
    db.session.commit()


def add_plano(produto_id, dias=30, rotulo="mensal", app="broostock"):
    db.session.add(PlanoAssinatura(produto_id=produto_id, dias=dias, rotulo=rotulo, app_slug=app))
    db.session.commit()


def add_plano_chave(produto_id, dias=30, rotulo="mensal", max_dispositivos=1, prefixo="BROO"):
    """Plano de um app vendido por chave (a chave é GERADA na compra)."""
    db.session.add(PlanoChave(produto_id=produto_id, dias=dias, rotulo=rotulo,
                              max_dispositivos=max_dispositivos, prefixo=prefixo))
    db.session.commit()


def add_chave_vendida(produto_id, serial, email="cli@example.test", expira_em=None, plano="mensal",
                      revogada=False, vendida=True):
    c = ChaveLicenca(chave_serial=serial, produto_id=produto_id, vendida=vendida,
                     vendida_em=datetime.utcnow() if vendida else None, cliente_email=email,
                     plano=plano, expira_em=expira_em, revogada=revogada)
    db.session.add(c)
    db.session.commit()
    return c


def add_licenca(email, expira_em, status="ativa", plano="mensal", ultimo_aviso=None, cobranca_id=None,
                app="broostock"):
    lic = Licenca(cliente_email=email, app_slug=app, plano=plano, status=status, inicia_em=datetime.utcnow(),
                  expira_em=expira_em, ultimo_pagamento_em=datetime.utcnow(), ultimo_aviso=ultimo_aviso,
                  cobranca_id=cobranca_id)
    db.session.add(lic)
    db.session.commit()
    return lic


def add_cupom(codigo="PROMO10", tipo="percentual", valor=10.0, produto_id=None, valido_de=None, valido_ate=None,
              usos_maximos=None, usos_atuais=0, ativo=True):
    c = Cupom(codigo=codigo, tipo=tipo, valor=valor, produto_id=produto_id,
              valido_de=valido_de or date.today() - timedelta(days=1), valido_ate=valido_ate,
              usos_maximos=usos_maximos, usos_atuais=usos_atuais, ativo=ativo)
    db.session.add(c)
    db.session.commit()
    return c


def add_vendedor(codigo, nome):
    db.session.add(Vendedor(codigo_ranking=codigo, nome_vendedor=nome))
    db.session.commit()
