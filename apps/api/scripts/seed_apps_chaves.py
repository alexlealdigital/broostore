# seed_apps_chaves.py
# ---------------------------------------------------------------------------
# Cadastra os APPS vendidos por chave de licença: o produto (tipo "app") e o
# plano (duração + nº de dispositivos). Depois disso, cada compra aprovada gera
# a chave sozinha — não precisa mais carregar lista de chaves.
#
# Onde: painel do Render, aba "Shell", a partir de apps/api:
#     python scripts/seed_apps_chaves.py
#
# Pré-requisito: colunas/tabelas das chaves já existem no banco (migration 002 do
# Supabase da BrooStore) e o código desta versão já está no ar.
#
# É idempotente: se o produto já existir (pelo nome), só atualiza preço/plano.
#
# EDITE a lista APPS abaixo antes de rodar. Cada app pode ter vários planos
# (um produto por plano, como no BrooStock: Mensal, Anual, Vitalícia...).
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
from broostore_api.models import PlanoChave, Produto

APPS = [
    # (nome do produto, preço R$, link de download, dias, rótulo, máx. dispositivos, prefixo)
    #   dias = None  ->  licença vitalícia
    #
    # Exemplos (descomente e ajuste):
    # ("MeuApp — Plano Mensal",    29.90, "https://exemplo.com/MeuApp-setup.exe",   30, "mensal",    1, "MAPP"),
    # ("MeuApp — Plano Anual",    299.00, "https://exemplo.com/MeuApp-setup.exe",  365, "anual",     2, "MAPP"),
    # ("MeuApp — Vitalícia",      599.00, "https://exemplo.com/MeuApp-setup.exe", None, "vitalicia", 2, "MAPP"),
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


def upsert(nome, preco, link, dias, rotulo, max_disp, prefixo):
    produto = Produto.query.filter_by(nome=nome).first()
    if not produto:
        produto = Produto(nome=nome, preco=preco, link_download=link, tipo="app")
        db.session.add(produto)
        db.session.flush()
    else:
        produto.preco = preco
        produto.link_download = link
        produto.tipo = "app"

    plano = db.session.get(PlanoChave, produto.id)
    if not plano:
        plano = PlanoChave(produto_id=produto.id)
        db.session.add(plano)
    plano.dias = dias
    plano.rotulo = rotulo
    plano.max_dispositivos = max_disp
    plano.prefixo = prefixo
    return produto


def main(apps=None, app=None):
    """Devolve a lista [(produto_id, nome, preco, dias, rotulo, max_dispositivos, prefixo)]."""
    apps = APPS if apps is None else apps
    if not apps:
        raise SystemExit("A lista APPS está vazia. Edite scripts/seed_apps_chaves.py antes de rodar.")

    app = app or create_app(role="worker")
    with app.app_context():
        fix_sequence()
        criados = [(upsert(*a), a) for a in apps]
        db.session.commit()
        resultado = [(p.id, nome, preco, dias, rotulo, max_disp, prefixo)
                     for p, (nome, preco, _link, dias, rotulo, max_disp, prefixo) in criados]

    print("====================================================")
    print("  APPS COM CHAVE AUTOMÁTICA:")
    for pid, nome, preco, dias, _rotulo, max_disp, prefixo in resultado:
        validade = "vitalícia" if dias is None else f"{dias} dias"
        print(f"   id={pid:>4}  R$ {preco:>8.2f}  {validade:<10} {max_disp} disp.  [{prefixo}]  {nome}")
    print("----------------------------------------------------")
    print("  Use o 'id' acima como product_id no app (rota /api/validar_chave)")
    print("  e na página de compra da loja.")
    print("====================================================")
    return resultado


if __name__ == "__main__":
    main()
