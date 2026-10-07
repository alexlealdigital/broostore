"""Formulário de contato (e-mail via Resend)."""
import logging

from flask import Blueprint, jsonify, request

from ..services import email as email_service

logger = logging.getLogger("broostore")

bp = Blueprint("contato", __name__)


@bp.route("/api/contato", methods=["POST"])
def handle_contact_form():
    dados = request.get_json()
    nome = dados.get("nome")
    email_remetente = dados.get("email")
    assunto = dados.get("assunto")
    mensagem = dados.get("mensagem")

    if not all([nome, email_remetente, assunto, mensagem]):
        return jsonify({"status": "error", "message": "Todos os campos são obrigatórios."}), 400

    try:
        resultado = email_service.enviar_contato(nome, email_remetente, assunto, mensagem)
        if resultado == "sem_api_key":
            return jsonify({"status": "error", "message": "API de email não configurada."}), 500
        if resultado == "ok":
            return jsonify({"status": "success", "message": "Mensagem enviada com sucesso!"}), 200
        else:
            return jsonify({"status": "error", "message": "Falha ao enviar e-mail."}), 500

    except Exception as e:
        logger.error(f"[CONTACT FORM] ERRO RESEND: {e}")
        return jsonify({"status": "error", "message": "Não foi possível enviar a mensagem no momento."}), 500
