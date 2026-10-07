"""Cotação de frete (Melhor Envio) para o checkout de produtos físicos."""
import logging

from flask import Blueprint, jsonify, request

from ..services import supabase_rest
from ..services.frete import cotar_frete_melhor_envio, curar_opcoes

logger = logging.getLogger("broostore")

bp = Blueprint("frete", __name__)


@bp.route("/api/cotar-frete", methods=["POST"])
def cotar_frete():
    try:
        dados = request.get_json() or {}
        cep_destino = dados.get("cep_destino") or dados.get("cep")
        product_id = dados.get("product_id")

        if not cep_destino:
            return jsonify({"status": "error", "message": "CEP de destino obrigatório."}), 400
        if not product_id:
            return jsonify({"status": "error", "message": "product_id obrigatório."}), 400

        # Busca dados físicos do produto no Supabase (fonte da verdade)
        try:
            rows = supabase_rest.buscar_produto_rows(
                product_id, supabase_rest.SELECT_FRETE, timeout=10)
        except Exception as e:
            return jsonify({"status": "error", "message": f"Erro ao buscar produto: {e}"}), 500

        if not rows:
            return jsonify({"status": "error", "message": "Produto não encontrado."}), 404

        p = rows[0]
        if (p.get("tipo") or "").strip().lower() != "fisico":
            return jsonify({"status": "error", "message": "Produto não é físico (não tem frete)."}), 400

        faltando = [c for c in ("peso_kg", "altura_cm", "largura_cm", "comprimento_cm") if not p.get(c)]
        if faltando:
            return jsonify({"status": "error",
                            "message": f"Produto sem medidas cadastradas: {', '.join(faltando)}."}), 422

        opcoes, erro = cotar_frete_melhor_envio(
            cep_destino=cep_destino,
            peso_kg=p["peso_kg"],
            altura_cm=p["altura_cm"],
            largura_cm=p["largura_cm"],
            comprimento_cm=p["comprimento_cm"],
            valor_segurado=float(p.get("price") or 0),
        )
        if erro:
            return jsonify({"status": "error", "message": erro}), 502
        if not opcoes:
            return jsonify({"status": "error",
                            "message": "Nenhuma transportadora disponível para este CEP."}), 404

        opcoes.sort(key=lambda o: o["preco"])
        opcoes_curadas = curar_opcoes(opcoes)
        return jsonify({"status": "success",
                        "opcoes": opcoes_curadas,
                        "total_disponivel": len(opcoes)}), 200

    except Exception as e:
        logger.error(f"ERRO (COTAR FRETE): {str(e)}")
        return jsonify({"status": "error", "message": f"Erro ao cotar frete: {str(e)}"}), 500
