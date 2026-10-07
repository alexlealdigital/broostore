"""Licenças / assinaturas do BrooStock."""
import json
import logging
from datetime import datetime, timedelta

from ..extensions import db
from ..models import Licenca, PlanoAssinatura

logger = logging.getLogger("broostore")

TRIAL_DIAS = 7

# Marca em ``cobrancas.observacoes`` (JSON) indicando que ESTA cobrança já
# estendeu/ativou a licença (idempotência do retry — ver services/entrega.py).
MARCA_LICENCA_APLICADA = "licenca_aplicada"


def licenca_esta_ativa(licenca, agora=None):
    agora = agora or datetime.utcnow()
    return bool(licenca.status in ("ativa", "trial") and licenca.expira_em and licenca.expira_em > agora)


def ativar_ou_renovar_licenca(produto, cobranca):
    """Cria ou estende a licença do cliente (renovação manual).
    Retorna (licenca, rotulo_plano) ou (None, None) se não houver plano configurado."""
    plano = db.session.get(PlanoAssinatura, produto.id)
    if not plano:
        logger.error(f"[WORKER] ERRO: produto {produto.id} é 'assinatura' mas não tem plano em planos_assinatura.")
        return None, None

    email = (cobranca.cliente_email or "").strip().lower()
    agora = datetime.utcnow()

    licenca = (Licenca.query
               .filter_by(cliente_email=email)
               .order_by(Licenca.id.desc())
               .first())

    # Renovação: se ainda está válida, soma a partir da data de expiração;
    # caso contrário, conta a partir de agora.
    base = licenca.expira_em if (licenca and licenca.expira_em and licenca.expira_em > agora) else agora
    nova_expira = base + timedelta(days=plano.dias)

    if licenca:
        licenca.plano = plano.rotulo
        licenca.status = "ativa"
        licenca.expira_em = nova_expira
        licenca.ultimo_pagamento_em = agora
        licenca.cobranca_id = cobranca.id
        licenca.produto_id = produto.id
        licenca.ultimo_aviso = None  # rearma os avisos de expiração para o novo período
    else:
        licenca = Licenca(
            cliente_email=email,
            plano=plano.rotulo,
            status="ativa",
            inicia_em=agora,
            expira_em=nova_expira,
            ultimo_pagamento_em=agora,
            cobranca_id=cobranca.id,
            produto_id=produto.id,
            ultimo_aviso=None,
        )
        db.session.add(licenca)

    db.session.flush()
    logger.info(f"[WORKER] Licença {plano.rotulo} de {email} válida até {nova_expira.date()}")
    return licenca, plano.rotulo


def _parse_obs(raw):
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def licenca_ja_aplicada(cobranca):
    """True se esta cobrança já ativou/estendeu a licença (retry idempotente)."""
    if Licenca.query.filter_by(cobranca_id=cobranca.id).first() is not None:
        return True
    return bool(_parse_obs(cobranca.observacoes).get(MARCA_LICENCA_APLICADA))


def marcar_licenca_aplicada(cobranca):
    obs = _parse_obs(cobranca.observacoes)
    obs[MARCA_LICENCA_APLICADA] = True
    cobranca.observacoes = json.dumps(obs)


def licenca_da_cobranca(cobranca):
    """Licença usada no e-mail de um retry: a vinculada à cobrança ou a mais recente do e-mail."""
    licenca = Licenca.query.filter_by(cobranca_id=cobranca.id).first()
    if licenca is None:
        email = (cobranca.cliente_email or "").strip().lower()
        licenca = (Licenca.query.filter_by(cliente_email=email)
                   .order_by(Licenca.id.desc()).first())
    return licenca
