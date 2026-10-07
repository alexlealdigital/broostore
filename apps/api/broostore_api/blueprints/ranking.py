"""Gamificação: lista de vendedores e ranking."""
import logging

from flask import Blueprint, current_app, jsonify
from sqlalchemy import func

from ..extensions import db
from ..models import Cobranca, Vendedor

logger = logging.getLogger("broostore")

bp = Blueprint("ranking", __name__)


@bp.route("/api/vendedores", methods=["GET"])
def get_vendedores():
    try:
        with current_app.app_context():
            vendedores = Vendedor.query.order_by(Vendedor.nome_vendedor).all()
            return jsonify([v.to_dict() for v in vendedores]), 200
    except Exception as e:
        logger.error(f"ERRO (VENDEDORES): {str(e)}")
        return jsonify({"status": "error", "message": "Não foi possível carregar a lista de vendedores."}), 500


# ROTA DE RANKING / DASHBOARD
@bp.route("/api/ranking", methods=["GET"])
def get_ranking():
    try:
        # Configurações de metas e comissões
        META_VENDAS_DIA = 100
        PRECO_BASE_EBOOK = 15.90
        COMISSOES = {0: 0.15, 1: 0.10, 2: 0.05}

        with current_app.app_context():
            vendas_entregues_query = db.session.query(
                Cobranca.vendedor_codigo,
                func.count(Cobranca.id).label('pontos')
            ).filter(
                Cobranca.status == 'delivered',
                Cobranca.vendedor_codigo != None  # noqa: E711
            ).group_by(
                Cobranca.vendedor_codigo
            ).subquery()

            ranking_query = db.session.query(
                Vendedor.nome_vendedor,
                Vendedor.codigo_ranking,
                func.coalesce(vendas_entregues_query.c.pontos, 0).label('pontos')
            ).outerjoin(
                vendas_entregues_query,
                Vendedor.codigo_ranking == vendas_entregues_query.c.vendedor_codigo
            ).order_by(
                func.coalesce(vendas_entregues_query.c.pontos, 0).desc()
            )

            ranking_db = ranking_query.all()

            ranking_final = []
            total_vendas_geral = 0

            for i, (nome, codigo, pontos) in enumerate(ranking_db):

                total_vendas_geral += pontos
                valor_vendido_bruto = pontos * PRECO_BASE_EBOOK

                percentual_comissao = COMISSOES.get(i, 0)
                valor_comissao_calculado = valor_vendido_bruto * percentual_comissao

                ranking_final.append({
                    "rank": i + 1,
                    "nome": nome,
                    "codigo": codigo,
                    "pontos": pontos,
                    "valor_comissao_brl": f"R$ {valor_comissao_calculado:,.2f}",
                    "percentual_comissao": f"{percentual_comissao * 100:.0f}%"
                })

            meta = {
                "objetivo": META_VENDAS_DIA,
                "atual": total_vendas_geral,
                "percentual_meta": min((total_vendas_geral / META_VENDAS_DIA) * 100, 100)
            }

            return jsonify({
                "status": "success",
                "ranking": ranking_final,
                "meta_diaria": meta
            }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"ERRO CRÍTICO (RANKING): {str(e)}")
        return jsonify({"status": "error", "message": f"Erro interno ao calcular ranking: {str(e)}"}), 500
