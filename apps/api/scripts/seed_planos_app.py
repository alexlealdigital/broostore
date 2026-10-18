# seed_planos_app.py
# ---------------------------------------------------------------------------
# Cadastra os PLANOS DE ASSINATURA de um app (mensal / anual / ...): um produto
# por plano na loja + a regra de duração (dias) + a qual app o plano libera.
# É o modelo para todo app novo no padrão "conta + e-mail" (como o BrooStock).
#
# Onde: painel do Render, aba "Shell", a partir de apps/api:
#     python scripts/seed_planos_app.py meuapp
#
# Pré-requisitos:
#   1. o app existe em apps_config.APPS (nome, url, dias de teste...)
#   2. as colunas/tabelas novas já existem no banco (migrations 002/003 do Supabase da BrooStore)
#   3. a lista PLANOS abaixo editada para o app
#
# Idempotente: se o produto já existir (pelo nome), só atualiza preço/plano.
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

# Permite executar de qualquer pasta (``python scripts/x.py``): põe apps/api no sys.path.
_RAIZ = str(Path(__file__).resolve().parent.parent)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from sqlalchemy import text

from broostore_api import apps_config, create_app
from broostore_api.extensions import db
from broostore_api.models import PlanoAssinatura, Produto

# EDITE: (nome do produto na loja, preço R$, dias de validade, rótulo)
# O nome deve começar pelo nome do app, ex.: "MeuApp — Plano Mensal".
PLANOS = [
    # ("MeuApp — Plano Mensal", 49.90,   30, "mensal"),
    # ("MeuApp — Plano Anual",  499.00, 365, "anual"),
]


def fix_sequence():
    """Evita colisão de id quando produtos foram inseridos à mão no Supabase (só PostgreSQL)."""
    if db.engine.dialect.name != "postgresql":
        return
    seq = db.session.execute(text("SELECT pg_get_serial_sequence('produtos','id')")).scalar()
    if seq:
        db.session.execute(
            text("SELECT setval(:seq, COALESCE((SELECT MAX(id) FROM produtos),0)+1, false)"),
            {"seq": seq},
        )
        db.session.commit()


def upsert_plano(slug, nome, preco, dias, rotulo):
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
        plano = PlanoAssinatura(produto_id=produto.id)
        db.session.add(plano)
    plano.dias = dias
    plano.rotulo = rotulo
    plano.app_slug = slug
    return produto


def main(slug=None, planos=None, app=None):
    """Devolve a lista [(produto_id, nome, preco, dias, rotulo)]."""
    slug = apps_config.normalizar_slug(slug)
    if not apps_config.obter_app(slug):
        raise SystemExit(f"App '{slug}' não está em apps_config.APPS. Cadastre-o antes.")
    planos = PLANOS if planos is None else planos
    if not planos:
        raise SystemExit("A lista PLANOS está vazia. Edite scripts/seed_planos_app.py antes de rodar.")

    app = app or create_app(role="worker")
    with app.app_context():
        fix_sequence()
        criados = [(upsert_plano(slug, *p), p) for p in planos]
        db.session.commit()
        resultado = [(prod.id, nome, preco, dias, rotulo) for prod, (nome, preco, dias, rotulo) in criados]

    print("====================================================")
    print(f"  PLANOS DE ASSINATURA — app '{slug}':")
    for pid, nome, preco, dias, rotulo in resultado:
        print(f"   id={pid:>4}  {rotulo:<8} R$ {preco:>8.2f}  ({dias} dias)  {nome}")
    print("----------------------------------------------------")
    print("  No frontend do app, use estes ids como IDs dos planos")
    print(f"  e APP_SLUG = '{slug}' nas chamadas /api/licenca/status e /trial.")
    print("====================================================")
    return resultado


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/seed_planos_app.py <slug-do-app>   (ex.: meuapp)")
    main(sys.argv[1])
