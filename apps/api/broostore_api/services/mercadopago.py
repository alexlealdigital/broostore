"""Integração com o Mercado Pago (SDK oficial) e validação de assinatura do webhook.

O SDK é sempre acessado como ``mercadopago.SDK(...)`` (atributo do módulo no
momento da chamada), o que permite aos testes substituí-lo por um fake.
"""
import hashlib
import hmac
import logging
import uuid

import mercadopago

from ..config import get_settings

logger = logging.getLogger("broostore")


def get_sdk(access_token):
    return mercadopago.SDK(access_token)


def criar_pagamento_pix(sdk, payment_data):
    """Cria o pagamento PIX. Devolve a resposta crua do SDK ({'status', 'response'})."""
    return sdk.payment().create(payment_data)


def criar_pagamento_cartao(sdk, payment_data):
    """Cria o pagamento com cartão, com chave de idempotência nova (como no original)."""
    from mercadopago.config import RequestOptions
    request_options = RequestOptions(custom_headers={"X-Idempotency-Key": str(uuid.uuid4())})
    return sdk.payment().create(payment_data, request_options)


def consultar_pagamento(sdk, payment_id):
    return sdk.payment().get(payment_id)


def validar_assinatura_webhook(request):
    """Valida o header ``x-signature`` conforme o manifesto do Mercado Pago:
    ``id:<data.id>;request-id:<x-request-id>;ts:<ts>;`` com HMAC-SHA256 do WEBHOOK_SECRET."""
    try:
        x_signature = request.headers.get("x-signature")
        x_request_id = request.headers.get("x-request-id")

        if not x_signature or not x_request_id:
            return False

        parts = x_signature.split(",")
        ts = None
        hash_signature = None

        for part in parts:
            key_value = part.split("=", 1)
            if len(key_value) == 2:
                key = key_value[0].strip()
                value = key_value[1].strip()
                if key == "ts":
                    ts = value
                elif key == "v1":
                    hash_signature = value

        secret_key = get_settings().webhook_secret
        if not ts or not hash_signature or not secret_key:
            return False

        data_id = request.args.get("data.id", "")
        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        calculated_hash = hmac.new(
            secret_key.encode(),
            manifest.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(calculated_hash, hash_signature)

    except Exception as e:
        logger.error(f"Erro ao validar assinatura: {str(e)}")
        return False
