"""Criação de cobranças (PIX e cartão) e consulta de status da cobrança."""
import json
import logging
import uuid

from flask import Blueprint, jsonify, request

from ..config import get_settings
from ..extensions import db, enfileirar_webhook
from ..models import Cobranca, Produto, Vendedor
from ..services import cupons as cupons_service
from ..services import mercadopago as mp_service
from ..services.frete import resolver_frete_fisico
from ..services.supabase_rest import sincronizar_produto_checkout

logger = logging.getLogger("broostore")

bp = Blueprint("cobrancas", __name__)

STATUS_PAGOS = ("approved", "delivered")


def _montar_observacoes(dados, frete_aplicado, frete_servico_desc, subtotal_produto):
    """JSON de observações (endereço + frete para produto físico)."""
    _endereco = dados.get("endereco") or {}
    _obs = {}
    if _endereco:
        _obs["endereco"] = _endereco
    if frete_aplicado > 0:
        _obs["frete"] = frete_aplicado
    if frete_servico_desc:
        _obs["transportadora"] = frete_servico_desc
    _obs["subtotal_produto"] = subtotal_produto
    return json.dumps(_obs) if _obs else None


def _resolver_frete(dados, is_fisico, p_dados, frete_autoritativo):
    """Frete autoritativo (recotado no servidor; fallback = frete fixo)."""
    frete_servico_desc = None
    if is_fisico:
        _cep_destino = (dados.get("endereco") or {}).get("cep") or dados.get("cep_destino")
        _servico_id = dados.get("frete_servico_id")
        frete_aplicado, frete_servico_desc = resolver_frete_fisico(
            p_dados, _cep_destino, _servico_id, frete_autoritativo)
    else:
        frete_aplicado = 0.0
    return frete_aplicado, frete_servico_desc


# ROTA DE CRIAÇÃO DE COBRANÇA (com Cupom e Telefone)
@bp.route("/api/cobrancas", methods=["POST"])
def create_cobranca():
    try:
        dados = request.get_json()

        if not dados:
            return jsonify({"status": "error", "message": "Nenhum dado foi enviado."}), 400

        email_cliente = dados.get("email")
        nome_cliente = dados.get("nome", "Cliente")
        telefone_cliente = dados.get("telefone")
        product_id_recebido = dados.get("product_id")
        vendedor_codigo_recebido = dados.get("vendedor_codigo")
        cupom_id_recebido = dados.get("cupom_id")
        usuario_id = dados.get("usuario_id")

        if not product_id_recebido:
            return jsonify({"status": "error", "message": "ID do produto é obrigatório."}), 400

        if not email_cliente or "@" not in email_cliente or "." not in email_cliente:
            return jsonify({"status": "error", "message": "Por favor, insira um email válido e obrigatório."}), 400

        if telefone_cliente:
            telefone_limpo = ''.join(filter(str.isdigit, telefone_cliente))
            if len(telefone_limpo) < 10:
                return jsonify({"status": "error", "message": "Telefone inválido."}), 400

        if vendedor_codigo_recebido:
            vendedor_existente = Vendedor.query.get(vendedor_codigo_recebido)
            if not vendedor_existente:
                logger.warning(f"ALERTA: Código de vendedor inválido: {vendedor_codigo_recebido}. Prosseguindo sem afiliação.")
                vendedor_codigo_recebido = None
        else:
            vendedor_codigo_recebido = None

        produto = db.session.get(Produto, int(product_id_recebido))

        # Valores autoritativos (fonte da verdade = Supabase). NUNCA confiar no cliente.
        # Sempre sincroniza preço e dados com o Supabase (evita cache desatualizado)
        produto, tipo_autoritativo, frete_autoritativo, p_dados = sincronizar_produto_checkout(
            product_id_recebido, produto, "Erro ao sincronizar produto com Supabase")

        if not produto:
            return jsonify({"status": "error", "message": "Produto não encontrado."}), 404

        valor_original = produto.preco
        cupom_obj, valor_final = cupons_service.aplicar_cupom_checkout(
            cupom_id_recebido, product_id_recebido, valor_original)

        # --- FRETE AUTORITATIVO (recotado no servidor; fallback = frete fixo) ---
        is_fisico = (tipo_autoritativo == "fisico")
        if is_fisico and frete_autoritativo is None:
            return jsonify({"status": "error", "message": "Não foi possível calcular o frete agora. Tente novamente em instantes."}), 503
        frete_aplicado, frete_servico_desc = _resolver_frete(dados, is_fisico, p_dados, frete_autoritativo)
        subtotal_produto = round(valor_final, 2)
        total_cobrado = round(subtotal_produto + frete_aplicado, 2)

        descricao_correta = produto.nome
        if cupom_obj:
            descricao_correta += f" (Cupom: {cupom_obj.codigo})"
        if frete_aplicado > 0:
            descricao_correta += " + Frete"

        # --- GERAÇÃO DO EXTERNAL_REFERENCE ---
        unique_id = str(uuid.uuid4())  # Identificador único para esta cobrança

        # Define o external_reference conforme o produto
        if usuario_id and int(product_id_recebido) == 7:  # produto de moedas
            external_reference = f"{usuario_id}:{unique_id}"
        else:
            external_reference = unique_id

        # --- CRIAÇÃO DO PAGAMENTO NO MERCADO PAGO ---
        access_token = get_settings().mercadopago_access_token
        if not access_token:
            return jsonify({"status": "error", "message": "Token do Mercado Pago não configurado."}), 500

        sdk = mp_service.get_sdk(access_token)

        payment_data = {
            "transaction_amount": total_cobrado,
            "description": descricao_correta,
            "payment_method_id": "pix",
            "external_reference": external_reference,
            "payer": {
                "email": email_cliente,
            }
        }

        payment_response = mp_service.criar_pagamento_pix(sdk, payment_data)

        if payment_response["status"] != 201:
            error_msg = payment_response.get("response", {}).get("message", "Erro desconhecido do Mercado Pago")
            return jsonify({"status": "error", "message": f"Erro do Mercado Pago: {error_msg}"}), 500

        payment = payment_response["response"]

        qr_code_base64 = payment["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        qr_code_text = payment["point_of_interaction"]["transaction_data"]["qr_code"]

        # --- CRIAÇÃO DA COBRANÇA NO BANCO (USA O MESMO external_reference) ---
        nova_cobranca = Cobranca(
            external_reference=external_reference,  # MESMO VALOR ENVIADO AO MP
            cliente_nome=nome_cliente,
            cliente_email=email_cliente,
            cliente_telefone=telefone_cliente,
            valor=total_cobrado,
            valor_original=round(valor_original, 2),
            status=payment["status"],
            product_id=produto.id,
            vendedor_codigo=vendedor_codigo_recebido,
            cupom_id=cupom_obj.id if cupom_obj else None,
            observacoes=_montar_observacoes(dados, frete_aplicado, frete_servico_desc, subtotal_produto),
        )

        cobranca_dict = nova_cobranca.to_dict()

        db.session.add(nova_cobranca)
        db.session.commit()

        # Prepara resposta
        resposta = {
            "status": "success",
            "message": "Cobrança PIX criada com sucesso!",
            "qr_code_base64": qr_code_base64,
            "qr_code_text": qr_code_text,
            "payment_id": payment["id"],
            "cobranca": cobranca_dict,
            "frete_aplicado": frete_aplicado,
            "subtotal_produto": subtotal_produto,
            "total_cobrado": total_cobrado
        }

        if cupom_obj:
            resposta["desconto_aplicado"] = cupons_service.desconto_aplicado(cupom_obj, valor_original, valor_final)

        return jsonify(resposta), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"ERRO CRÍTICO GERAL (CREATE): {str(e)}")
        return jsonify({"status": "error", "message": f"Falha ao criar cobrança: {str(e)}"}), 500


# ─────────────────────────────────────────────
# PAGAMENTO COM CARTÃO DE CRÉDITO
# ─────────────────────────────────────────────
@bp.route("/api/cobrancas-cartao", methods=["POST"])
def create_cobranca_cartao():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({"status": "error", "message": "Nenhum dado enviado."}), 400

        token = dados.get("token")
        payment_method = dados.get("payment_method_id")
        installments = dados.get("installments", 1)
        email_cliente = dados.get("email")
        nome_cliente = dados.get("nome", "Cliente")
        cpf_cliente = dados.get("cpf", "")
        product_id_rec = dados.get("product_id")
        cupom_id_rec = dados.get("cupom_id")
        issuer_id = dados.get("issuer_id")
        telefone_cliente = dados.get("telefone")

        if not token:
            return jsonify({"status": "error", "message": "Token do cartão é obrigatório."}), 400
        if not email_cliente or "@" not in email_cliente:
            return jsonify({"status": "error", "message": "E-mail inválido."}), 400
        if not product_id_rec:
            return jsonify({"status": "error", "message": "ID do produto é obrigatório."}), 400

        # Busca/sincroniza produto
        produto = db.session.get(Produto, int(product_id_rec))
        produto, tipo_autoritativo, frete_autoritativo, p_dados = sincronizar_produto_checkout(
            product_id_rec, produto, "[CARTAO] Erro ao sincronizar produto")

        if not produto:
            return jsonify({"status": "error", "message": "Produto não encontrado."}), 404

        valor_original = produto.preco
        cupom_obj, valor_final = cupons_service.aplicar_cupom_checkout(
            cupom_id_rec, product_id_rec, valor_original)

        # --- FRETE AUTORITATIVO (recotado no servidor; fallback = frete fixo) ---
        is_fisico = (tipo_autoritativo == "fisico")
        if is_fisico and frete_autoritativo is None:
            return jsonify({"status": "error", "message": "Não foi possível calcular o frete agora. Tente novamente em instantes."}), 503
        frete_aplicado, frete_servico_desc = _resolver_frete(dados, is_fisico, p_dados, frete_autoritativo)
        subtotal_produto = round(valor_final, 2)
        total_cobrado = round(subtotal_produto + frete_aplicado, 2)

        external_reference = str(uuid.uuid4())

        access_token = get_settings().mercadopago_access_token
        if not access_token:
            return jsonify({"status": "error", "message": "Token do Mercado Pago não configurado."}), 500

        sdk = mp_service.get_sdk(access_token)

        payment_data = {
            "transaction_amount": total_cobrado,
            "token":              token,
            "description":        (produto.nome + " + Frete") if frete_aplicado > 0 else produto.nome,
            "installments":       int(installments),
            "payment_method_id":  payment_method,
            "external_reference": external_reference,
            "payer": {
                "email": email_cliente,
                "first_name": nome_cliente.split()[0] if nome_cliente else "Cliente",
                "last_name":  " ".join(nome_cliente.split()[1:]) if len(nome_cliente.split()) > 1 else ".",
                "identification": {
                    "type":   "CPF",
                    "number": cpf_cliente.replace(".", "").replace("-", "")
                }
            }
        }
        if issuer_id:
            payment_data["issuer_id"] = int(issuer_id)

        payment_response = mp_service.criar_pagamento_cartao(sdk, payment_data)

        logger.info(f"[CARTAO] Resposta MP status={payment_response.get('status')} response={payment_response.get('response')}")

        if payment_response["status"] not in [200, 201]:
            resp_body = payment_response.get("response") or {}
            error_msg = (
                resp_body.get("message")
                or resp_body.get("error")
                or str(resp_body)
                or "Erro desconhecido do Mercado Pago"
            )
            logger.error(f"[CARTAO] ERRO MP completo: {payment_response}")
            return jsonify({"status": "error", "message": f"Erro MP: {error_msg}"}), 500

        payment = payment_response["response"]
        status_mp = payment.get("status")
        status_detail = payment.get("status_detail", "")

        # Observações (endereço + frete para produto físico)
        nova_cobranca = Cobranca(
            external_reference=external_reference,
            cliente_nome=nome_cliente,
            cliente_email=email_cliente,
            cliente_telefone=telefone_cliente,
            valor=total_cobrado,
            valor_original=round(valor_original, 2),
            status=status_mp,
            product_id=produto.id,
            cupom_id=cupom_obj.id if cupom_obj else None,
            observacoes=_montar_observacoes(dados, frete_aplicado, frete_servico_desc, subtotal_produto),
        )
        db.session.add(nova_cobranca)
        db.session.commit()

        if status_mp == "approved":
            try:
                enfileirar_webhook(payment["id"])
            except Exception as _rq_err:
                logger.error(f"[CARTAO] Redis indisponível, webhook não enfileirado: {_rq_err}")
            mensagem = "Pagamento aprovado! Você receberá o produto por e-mail em instantes."
        elif status_mp == "in_process":
            mensagem = "Pagamento em análise. Você receberá o produto assim que aprovado."
        else:
            mensagem = f"Pagamento não aprovado ({status_detail}). Verifique os dados do cartão."

        resposta = {
            "status":        status_mp,
            "status_detail": status_detail,
            "payment_id":    payment["id"],
            "mensagem":      mensagem,
            "frete_aplicado": frete_aplicado,
            "subtotal_produto": subtotal_produto,
            "total_cobrado": total_cobrado,
        }
        if cupom_obj:
            resposta["desconto_aplicado"] = cupons_service.desconto_aplicado(cupom_obj, valor_original, valor_final)

        return jsonify(resposta), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"ERRO CRÍTICO GERAL (CARTÃO): {str(e)}")
        return jsonify({"status": "error", "message": f"Falha ao criar cobrança com cartão: {str(e)}"}), 500


# NOVO (F4, aditivo): status da cobrança — consultado pela loja nova após gerar o PIX.
# Não expõe dados pessoais: apenas status e se já está pago.
@bp.route("/api/cobrancas/<external_reference>/status", methods=["GET"])
def status_cobranca(external_reference):
    try:
        cobranca = Cobranca.query.filter_by(external_reference=external_reference).first()
        if not cobranca:
            resp = jsonify({"status": "error", "message": "Cobrança não encontrada."})
            resp.status_code = 404
        else:
            resp = jsonify({"status": cobranca.status, "pago": cobranca.status in STATUS_PAGOS})
            resp.status_code = 200
        resp.headers["Cache-Control"] = "no-store"
        return resp
    except Exception as e:
        logger.error(f"ERRO (STATUS COBRANCA): {str(e)}")
        return jsonify({"status": "error", "message": "Falha ao consultar a cobrança."}), 500
