"""Webhook do Mercado Pago: enfileira o job de entrega."""
import logging

from flask import Blueprint, jsonify, request

from ..config import get_settings
from ..extensions import FilaIndisponivel, enfileirar_webhook
from ..services.mercadopago import validar_assinatura_webhook

logger = logging.getLogger("broostore")

bp = Blueprint("webhook", __name__)


@bp.route("/api/webhook", methods=["POST"])
def webhook():
    try:
        # F3: validação de assinatura atrás de WEBHOOK_VALIDATE_SIGNATURE (padrão: DESLIGADA,
        # exatamente como o original, que tinha a checagem comentada).
        if get_settings().webhook_validate_signature and not validar_assinatura_webhook(request):
            return jsonify({"status": "error", "message": "Assinatura inválida"}), 401

        dados = request.get_json(silent=True) or {}
        data = dados.get("data") if isinstance(dados, dict) else None
        payment_id = data.get("id") if isinstance(data, dict) else None

        if payment_id:
            try:
                enfileirar_webhook(payment_id)
            except FilaIndisponivel:
                # 503 => o Mercado Pago tenta de novo (antes: 500 com stack trace)
                return jsonify({"status": "error", "message": "Fila indisponível, tente novamente"}), 503

        return jsonify({"status": "success", "message": "Webhook recebido e processamento enfileirado"}), 200

    except Exception as e:
        logger.error(f"Erro ao processar webhook: {str(e)}")
        return jsonify({"status": "error", "message": f"Erro interno ao processar webhook: {str(e)}"}), 500
