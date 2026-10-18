"""Licença/assinatura dos apps: status por e-mail + app e teste grátis (um por e-mail POR APP)."""
import logging
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from .. import apps_config
from ..extensions import db
from ..models import Licenca
from ..services import email as email_service
from ..services.licencas import TRIAL_DIAS, licenca_esta_ativa
from ..services.sync_licencas import sincronizar_licenca

logger = logging.getLogger("broostore")

bp = Blueprint("licencas", __name__)


def _app_da_requisicao(valor):
    """Resolve o slug do app vindo do cliente. Ausente -> app padrão (o BrooStock antigo não
    mandava o parâmetro). Desconhecido -> None (a rota responde 400)."""
    slug = apps_config.normalizar_slug(valor)
    return slug if apps_config.obter_app(slug) else None


# Status da licença por e-mail e por app (consultado pelo app no login)
@bp.route("/api/licenca/status", methods=["GET"])
def licenca_status():
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ativa": False, "motivo": "email_ausente"}), 400
    slug = _app_da_requisicao(request.args.get("app"))
    if not slug:
        return jsonify({"ativa": False, "motivo": "app_desconhecido"}), 400
    try:
        licenca = (Licenca.query
                   .filter_by(cliente_email=email, app_slug=slug)
                   .order_by(Licenca.expira_em.desc())
                   .first())
        if not licenca:
            # Nunca teve licença deste app -> elegível ao teste grátis
            return jsonify({"ativa": False, "plano": None, "status": None,
                            "expira_em": None, "is_trial": False,
                            "pode_testar": True, "dias_restantes": 0, "app": slug}), 200
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
            "app": slug,
        }), 200
    except Exception as e:
        logger.error(f"ERRO (LICENCA STATUS): {str(e)}")
        return jsonify({"ativa": False, "motivo": "erro_interno"}), 500


# Ativa o teste grátis (dias definidos em apps_config) — somente se o e-mail nunca teve licença DAQUELE app
@bp.route("/api/licenca/trial", methods=["POST"])
def licenca_trial():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ok": False, "motivo": "email_ausente"}), 400
    slug = _app_da_requisicao(data.get("app") or request.args.get("app"))
    if not slug:
        return jsonify({"ok": False, "motivo": "app_desconhecido"}), 400
    trial_dias = apps_config.obter_app(slug).get("trial_dias", TRIAL_DIAS)
    try:
        # O teste é UM por e-mail POR APP: quem já testou o BrooStock ainda pode testar outro app.
        existente = Licenca.query.filter_by(cliente_email=email, app_slug=slug).first()
        if existente:
            ativa = licenca_esta_ativa(existente)
            return jsonify({"ok": False, "motivo": "ja_utilizado", "ativa": ativa}), 409

        agora = datetime.utcnow()
        expira = agora + timedelta(days=trial_dias)
        nova = Licenca(
            cliente_email=email,
            app_slug=slug,
            plano="trial",
            status="trial",
            inicia_em=agora,
            expira_em=expira,
            ultimo_pagamento_em=agora,  # coluna NOT NULL; sem significado no trial
            ultimo_aviso=None,
        )
        db.session.add(nova)
        db.session.commit()
        logger.info(f"[TRIAL] Teste de {trial_dias} dias ({slug}) criado para {email} (expira {expira.date()})")
        # Espelha no Supabase do app (melhor esforço; não derruba o cadastro)
        sincronizar_licenca(slug, email, expira, "trial", is_trial=True)
        # E-mail de boas-vindas (best-effort: não derruba a ativação se falhar)
        try:
            email_service.enviar_boas_vindas(email, expira, slug)
        except Exception as e:
            logger.error(f"[TRIAL] Boas-vindas (best-effort) falhou: {e}")
        return jsonify({"ok": True, "status": "trial", "expira_em": expira.isoformat(),
                        "dias_restantes": trial_dias, "app": slug}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"ERRO (TRIAL): {str(e)}")
        return jsonify({"ok": False, "motivo": "erro_interno"}), 500
