"""Produtos: detalhes (checkout) e sincronização com o Supabase."""
import logging

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Produto
from ..services import supabase_rest

logger = logging.getLogger("broostore")

bp = Blueprint("produtos", __name__)


# Detalhes de um produto (usado pela página de checkout comprar.html)
@bp.route("/api/produto/<int:produto_id>", methods=["GET"])
def get_produto(produto_id):
    try:
        produto = db.session.get(Produto, produto_id)
        if not produto:
            return jsonify({"status": "error", "message": "Produto não encontrado."}), 404
        return jsonify({
            "status": "success",
            "id": produto.id,
            "nome": produto.nome,
            "preco": produto.preco,
            "tipo": produto.tipo,
        }), 200
    except Exception as e:
        logger.error(f"ERRO (GET PRODUTO): {str(e)}")
        return jsonify({"status": "error", "message": "Falha ao carregar o produto."}), 500


@bp.route("/api/sync-produto", methods=["POST"])
def sync_produto():
    """Sincroniza preço e dados de um produto da tabela products (Supabase) para produtos (local).
    Chamado pelo painel do autor após salvar edições."""
    dados = request.get_json(silent=True) or {}
    product_id = dados.get("product_id")

    if not product_id:
        return jsonify({"status": "error", "message": "product_id obrigatório"}), 400

    try:
        rows = supabase_rest.buscar_produto_rows(product_id, supabase_rest.SELECT_SYNC)
        if not rows:
            return jsonify({"status": "error", "message": "Produto não encontrado no Supabase"}), 404

        p = rows[0]
        produto = db.session.get(Produto, int(p["id"]))
        if produto:
            produto.preco = float(p["price"])
            produto.nome = p["title"]
            produto.link_download = p.get("link_pdf") or produto.link_download
        else:
            produto = Produto(
                id=p["id"],
                nome=p["title"],
                preco=float(p["price"]),
                link_download=p.get("link_pdf") or "",
                tipo="ebook"
            )
            db.session.add(produto)

        db.session.commit()
        logger.info(f"[sync-produto] id={p['id']} nome={p['title']} preco={p['price']}")
        return jsonify({"status": "ok", "preco": float(p["price"]), "nome": p["title"]})

    except Exception as e:
        logger.error(f"[sync-produto] Erro: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
