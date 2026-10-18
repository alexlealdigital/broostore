"""Chaves de licença com duração: geração na compra e renovação.

Um produto do tipo ``app``/``game`` que tem linha em ``planos_chave`` gera a chave NA COMPRA
(não existe "estoque esgotado"). Sem essa linha, vale o fluxo antigo: reserva uma chave
pré-carregada de ``chaves_licenca`` (ver services/entrega.py).

Regras:
  * plano com dias  -> comprar de novo com o mesmo e-mail RENOVA a chave existente
    (soma dias; se ainda estava válida, a partir do vencimento);
  * plano vitalício -> cada compra gera uma chave nova (duas compras = duas licenças).

Idempotência (retry do RQ, F1): a chave/renovação é comitada ANTES do e-mail. Uma chave NOVA
fica ligada à cobrança (``chaves_licenca.cobranca_id``); uma RENOVAÇÃO reaproveita a chave
antiga e por isso deixa a marca ``chave_aplicada`` em ``cobrancas.observacoes`` — assim um
retry nunca soma os dias duas vezes.
"""
import json
import logging
from datetime import datetime

from ..extensions import db
from ..models import ChaveLicenca, PlanoChave
from . import licencas as licencas_service
from .licencas_chave import calcular_expiracao, gerar_chave

logger = logging.getLogger("broostore")

MARCA_CHAVE_APLICADA = "chave_aplicada"      # serial da chave renovada por esta cobrança
MARCA_CHAVE_RENOVADA = "chave_renovada"      # True quando foi renovação


def plano_da_chave(produto_id):
    return db.session.get(PlanoChave, produto_id)


def chave_ja_aplicada(cobranca):
    """(chave, renovada) se esta cobrança já gerou/renovou uma chave; senão None."""
    nova = ChaveLicenca.query.filter_by(cobranca_id=cobranca.id).first()
    if nova is not None:
        return nova, False
    obs = licencas_service._parse_obs(cobranca.observacoes)
    serial = obs.get(MARCA_CHAVE_APLICADA)
    if serial:
        chave = ChaveLicenca.query.filter_by(chave_serial=serial).first()
        if chave is not None:
            return chave, bool(obs.get(MARCA_CHAVE_RENOVADA, True))
    return None


def _marcar_renovacao(cobranca, serial):
    obs = licencas_service._parse_obs(cobranca.observacoes)
    obs[MARCA_CHAVE_APLICADA] = serial
    obs[MARCA_CHAVE_RENOVADA] = True
    cobranca.observacoes = json.dumps(obs)


def gerar_ou_renovar_chave_app(produto, cobranca):
    """Gera (ou renova) a chave do app comprado.

    Retorna ``(chave, expira_em, rotulo, renovada)`` ou ``None`` quando o produto não tem
    plano em ``planos_chave`` (o chamador usa então o estoque pré-carregado).
    Não faz commit: o chamador comita (F1).
    """
    plano = plano_da_chave(produto.id)
    if not plano:
        return None

    email = (cobranca.cliente_email or "").strip().lower()
    agora = datetime.utcnow()

    existente = None
    if plano.dias:
        existente = (ChaveLicenca.query
                     .filter(ChaveLicenca.produto_id == produto.id,
                             ChaveLicenca.cliente_email == email,
                             ChaveLicenca.vendida == True,       # noqa: E712
                             ChaveLicenca.revogada == False,     # noqa: E712
                             ChaveLicenca.expira_em.isnot(None))
                     .order_by(ChaveLicenca.id.desc())
                     .with_for_update()
                     .first())

    if existente:
        existente.expira_em = calcular_expiracao(plano.dias, existente.expira_em, agora)
        existente.plano = plano.rotulo
        existente.ultimo_aviso = None  # rearma os avisos de vencimento
        db.session.add(existente)
        _marcar_renovacao(cobranca, existente.chave_serial)
        db.session.flush()
        logger.info(f"[WORKER] Chave de {email} renovada até {existente.expira_em.date()}")
        return existente, existente.expira_em, plano.rotulo, True

    serial = None
    for _ in range(5):
        candidata = gerar_chave(plano.prefixo)
        if not ChaveLicenca.query.filter_by(chave_serial=candidata).first():
            serial = candidata
            break
    if not serial:
        raise RuntimeError("Não foi possível gerar uma chave única após 5 tentativas.")

    expira = calcular_expiracao(plano.dias, None, agora)
    nova = ChaveLicenca(
        chave_serial=serial,
        produto_id=produto.id,
        vendida=True,
        vendida_em=agora,
        cobranca_id=cobranca.id,
        cliente_email=email,
        plano=plano.rotulo,
        expira_em=expira,
        revogada=False,
    )
    db.session.add(nova)
    db.session.flush()
    logger.info(f"[WORKER] Chave nova gerada para {email} (produto {produto.id}, "
                f"{'vitalícia' if expira is None else 'até ' + str(expira.date())})")
    return nova, expira, plano.rotulo, False
