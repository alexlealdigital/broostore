# seed_planos_broostock.py
# ---------------------------------------------------------------------------
# Cria os produtos de ASSINATURA do BrooStock (Mensal / Anual), um produto de
# TESTE de R$ 1,00, os planos (dias de validade) e um cupom de teste de 99%.
#
# Onde rodar: painel do Render do serviço (aba "Shell"), a partir de apps/api:
#     python scripts/seed_planos_broostock.py
#
# Pré-requisito: o backend novo (modelos Licenca e PlanoAssinatura) já deve estar
# no deploy, pois o db.create_all() cria as tabelas novas. Rode DEPOIS do deploy.
#
# É idempotente: se um produto já existir (pelo nome), ele reaproveita.
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

# Permite executar de qualquer pasta (``python scripts/x.py``): põe apps/api no sys.path.
_RAIZ = str(Path(__file__).resolve().parent.parent)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from sqlalchemy import text

from broostore_api import create_app
from broostore_api.extensions import db
from broostore_api.models import Cupom, PlanoAssinatura, Produto

PLANOS = [
    # (nome, preco, dias, rotulo)
    ("BrooStock — Plano Mensal", 129.90, 30,  "mensal"),
    ("BrooStock — Plano Anual",  1078.80, 365, "anual"),
    ("BrooStock — TESTE (R$ 1)", 1.00,    30,  "mensal"),
]

CUPOM_TESTE = "TESTE"   # 99% de desconto, para testar o fluxo real


def fix_sequence():
    # A sequência SERIAL só existe no PostgreSQL (no original o seed só rodava lá).
    if db.engine.dialect.name != "postgresql":
        return
    seq = db.session.execute(text("SELECT pg_get_serial_sequence('produtos','id')")).scalar()
    if seq:
        db.session.execute(
            text("SELECT setval(:seq, COALESCE((SELECT MAX(id) FROM produtos),0)+1, false)"),
            {"seq": seq},
        )
        db.session.commit()


def upsert_produto(nome, preco, dias, rotulo):
    produto = Produto.query.filter_by(nome=nome).first()
    if not produto:
        produto = Produto(nome=nome, preco=preco, link_download="", tipo="assinatura")
        db.session.add(produto)
        db.session.flush()
    else:
        produto.preco = preco
        produto.tipo = "assinatura"

    plano = db.session.get(PlanoAssinatura, produto.id)
    if not plano:
        db.session.add(PlanoAssinatura(produto_id=produto.id, dias=dias, rotulo=rotulo))
    else:
        plano.dias = dias
        plano.rotulo = rotulo
    return produto


def main(app=None):
    app = app or create_app(role="worker")
    with app.app_context():
        fix_sequence()

        criados = []
        for nome, preco, dias, rotulo in PLANOS:
            p = upsert_produto(nome, preco, dias, rotulo)
            criados.append((p.id, nome, preco, dias, rotulo))

        # Cupom de teste 99% (global). produto_id NULL = vale para qualquer produto.
        cupom = Cupom.query.filter_by(codigo=CUPOM_TESTE).first()
        if not cupom:
            db.session.add(Cupom(
                codigo=CUPOM_TESTE, tipo="percentual", valor=99,
                produto_id=None, ativo=True,
            ))

        db.session.commit()

        print("====================================================")
        print("  PRODUTOS DE ASSINATURA:")
        for pid, nome, preco, dias, rotulo in criados:
            print(f"   id={pid:>4}  {rotulo:<7}  R$ {preco:>8.2f}  ({dias} dias)  {nome}")
        print("----------------------------------------------------")
        print("  No broostore.ts use:")
        print(f"   BROOSTOCK_PLANO_MENSAL_ID = {criados[0][0]}")
        print(f"   BROOSTOCK_PLANO_ANUAL_ID  = {criados[1][0]}")
        print(f"   (produto de teste R$1: id = {criados[2][0]})")
        print(f"  Cupom de teste: '{CUPOM_TESTE}' (99% off)")
        print("====================================================")
        return criados


if __name__ == "__main__":
    main()
