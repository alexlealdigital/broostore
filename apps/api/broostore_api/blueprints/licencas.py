"""Licença/assinatura do BrooStock: status por e-mail e teste grátis."""
import logging
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Licenca
from ..services import email as email_service
from ..services.licencas import TRIAL_DIAS, licenca_esta_ativa

logger = logging.getLogger("broostore")

bp = Blueprint("licencas", __name__)


# Status da licença por e-mail (consultado pelo BrooStock no login)
@bp.route("/api/licenca/status", methods=["GET"])
def licenca_status():
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ativa": False, "motivo": "email_ausente"}), 400
    try:
        licenca = (Licenca.query
                   .filter_by(cliente_email=email)
                   .order_by(Licenca.expira_em.desc())
                   .first())
        if not licenca:
            # Nunca teve licença -> elegível ao teste grátis
            return jsonify({"ativa": False, "plano": None, "status": None,
                            "expira_em": None, "is_trial": False,
                            "pode_testar": True, "dias_restantes": 0}), 200
        agora = datetime.utcnow()
        ativa = licenca_esta_ativa(licenca, agora)
        is_trial = (licenca.status == "trial")
        dias = 0
        if licenca.expira_em and licenca.expira_em > agora:
            dias = (licenca.expira_em - agora).days
        return jsonify({
            "ativa": ativa,
            "plano": licenca.plano,
            "status": licenca.status,
            "expira_em": licenca.expira_em.isoformat() if licenca.expira_em else None,
            "is_trial": is_trial,
            "pode_testar": False,
            "dias_restantes": dias,
        }), 200
    except Exception as e:
        logger.error(f"ERRO (LICENCA STATUS): {str(e)}")
        return jsonify({"ativa": False, "motivo": "erro_interno"}), 500


# Ativa um teste grátis de 7 dias (somente se o e-mail nunca teve licença)
@bp.route("/api/licenca/trial", methods=["POST"])
def licenca_trial():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ok": False, "motivo": "email_ausente"}), 400
    try:
        existente = Licenca.query.filter_by(cliente_email=email).first()
        if existente:
            ativa = licenca_esta_ativa(existente)
            return jsonify({"ok": False, "motivo": "ja_utilizado", "ativa": ativa}), 409

        agora = datetime.utcnow()
        expira = agora + timedelta(days=TRIAL_DIAS)
        nova = Licenca(
            cliente_email=email,
            plano="trial",
            status="trial",
            inicia_em=agora,
            expira_em=expira,
            ultimo_pagamento_em=agora,  # coluna NOT NULL; sem significado no trial
            ultimo_aviso=None,
        )
        db.session.add(nova)
        db.session.commit()
        logger.info(f"[TRIAL] Teste de {TRIAL_DIAS} dias criado para {email} (expira {expira.date()})")
        # E-mail de boas-vindas (best-effort: não derruba a ativação se falhar)
        try:
            email_service.enviar_boas_vindas(email, expira)
        except Exception as e:
            logger.error(f"[TRIAL] Boas-vindas (best-effort) falhou: {e}")
        return jsonify({"ok": True, "status": "trial", "expira_em": expira.isoformat(), "dias_restantes": TRIAL_DIAS}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"ERRO (TRIAL): {str(e)}")
        return jsonify({"ok": False, "motivo": "erro_interno"}), 500
