"""Validação de cupom de desconto."""
import logging

from flask import Blueprint, jsonify, request

from ..models import Cupom

logger = logging.getLogger("broostore")

bp = Blueprint("cupons", __name__)


@bp.route("/api/validar-cupom", methods=["POST"])
def validar_cupom():
    """Valida um cupom de desconto e retorna o valor calculado"""
    try:
        dados = request.get_json()
        codigo = dados.get("codigo", "").strip().upper()
        produto_id = dados.get("produto_id")
        valor_original = dados.get("valor_original")

        if not codigo:
            return jsonify({"status": "error", "message": "Código do cupom é obrigatório"}), 400

        if not produto_id or not valor_original:
            return jsonify({"status": "error", "message": "ID do produto e valor original são obrigatórios"}), 400

        cupom = Cupom.query.filter_by(codigo=codigo).first()

        if not cupom:
            return jsonify({"status": "error", "message": "Cupom não encontrado"}), 404

        valido, motivo = cupom.esta_valido()
        if not valido:
            return jsonify({"status": "error", "message": motivo}), 400

        # Verifica se o cupom é específico para um produto
        if cupom.produto_id is not None and cupom.produto_id != int(produto_id):
            return jsonify({"status": "error", "message": "Este cupom não é válido para este produto"}), 400

        # Calcula o desconto
        calculo = cupom.calcular_desconto(float(valor_original))

        return jsonify({
            "status": "success",
            "cupom": cupom.to_dict(),
            "calculo": calculo
        }), 200

    except Exception as e:
        logger.error(f"Erro ao validar cupom: {str(e)}")
        return jsonify({"status": "error", "message": f"Erro interno: {str(e)}"}), 500
