"""Cumprimento do pedido (reserva de chave / ativação de licença) e e-mail de entrega.

O cumprimento é IDEMPOTENTE: se a cobrança já tem chave reservada (``chaves_licenca.cobranca_id``)
ou já aplicou a licença, uma nova execução (retry do RQ) não reserva outra chave nem
estende a licença de novo — apenas devolve os dados para reenviar o e-mail.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..extensions import db
from ..models import ChaveLicenca, PlanoAssinatura
from . import email as email_service
from . import licencas as licencas_service

logger = logging.getLogger("broostore")

PRODUTO_COMPRESSAO_PDF = 99


class EntregaErro(Exception):
    """Falha de cumprimento (estoque esgotado, plano não configurado). O job re-levanta."""


@dataclass
class Cumprimento:
    chave_entregue: Optional[str] = None
    licenca_expira_em: Optional[datetime] = None
    rotulo_plano: Optional[str] = None
    ja_cumprido: bool = False  # True quando é um retry e nada novo foi reservado/estendido


def cumprir_pedido(produto, cobranca) -> Cumprimento:
    """Reserva a chave / ativa a licença do pedido (sem commit; o chamador comita)."""
    resultado = Cumprimento()

    # Produto 99 = Compressão de PDF: envia o external_reference como código de liberação
    if produto.id == PRODUTO_COMPRESSAO_PDF:
        resultado.chave_entregue = cobranca.external_reference
        logger.info(f"[WORKER] Produto PDF Compressão — enviando código: {resultado.chave_entregue}")

    elif produto.tipo == "assinatura":
        if licencas_service.licenca_ja_aplicada(cobranca):
            logger.info(f"[WORKER] Licença da cobrança {cobranca.id} já aplicada. Não estende de novo.")
            licenca = licencas_service.licenca_da_cobranca(cobranca)
            plano = db.session.get(PlanoAssinatura, produto.id)
            resultado.licenca_expira_em = licenca.expira_em
            resultado.rotulo_plano = plano.rotulo if plano else licenca.plano
            resultado.ja_cumprido = True
        else:
            logger.info(f"[WORKER] Ativando/renovando licença para {produto.nome}...")
            licenca_ativa, rotulo_plano = licencas_service.ativar_ou_renovar_licenca(produto, cobranca)
            if not licenca_ativa:
                db.session.rollback()
                raise EntregaErro(f"Plano de assinatura não configurado para produto {produto.id}")
            licencas_service.marcar_licenca_aplicada(cobranca)
            resultado.licenca_expira_em = licenca_ativa.expira_em
            resultado.rotulo_plano = rotulo_plano

    elif produto.tipo in ["game", "app"]:
        existente = ChaveLicenca.query.filter_by(cobranca_id=cobranca.id).first()
        if existente is not None:
            logger.info(f"[WORKER] Chave já reservada para a cobrança {cobranca.id}. Não reserva outra.")
            resultado.chave_entregue = existente.chave_serial
            resultado.ja_cumprido = True
        else:
            logger.info(f"[WORKER] Reservando chave para {produto.nome}...")
            chave_obj = ChaveLicenca.query.filter(
                ChaveLicenca.produto_id == produto.id,
                ChaveLicenca.vendida == False  # noqa: E712
            ).order_by(ChaveLicenca.id.asc()).with_for_update().first()

            if chave_obj:
                chave_obj.vendida = True
                chave_obj.vendida_em = datetime.utcnow()
                chave_obj.cobranca_id = cobranca.id
                chave_obj.cliente_email = cobranca.cliente_email
                resultado.chave_entregue = chave_obj.chave_serial
                db.session.add(chave_obj)
                logger.info(f"[WORKER] Chave reservada: {resultado.chave_entregue[:10]}...")
            else:
                logger.error("[WORKER] ERRO: Estoque esgotado!")
                db.session.rollback()
                raise EntregaErro(f"Estoque esgotado: {produto.id}")

    return resultado


def enviar_email_entrega(cobranca, produto, cumprimento: Cumprimento) -> bool:
    """Escolhe e envia o e-mail certo para o tipo do produto. True se enviado."""
    tipo_produto = getattr(produto, 'tipo', 'digital') or 'digital'

    # Produto físico: confirmação de pedido com endereço (sem link de download)
    if tipo_produto == 'fisico':
        return email_service.enviar_email_produto_fisico(
            destinatario=cobranca.cliente_email,
            nome_cliente=cobranca.cliente_nome,
            valor=cobranca.valor,
            nome_produto=produto.nome,
            cobranca=cobranca,
        )
    if tipo_produto == 'assinatura':
        return email_service.enviar_email_licenca(
            destinatario=cobranca.cliente_email,
            nome_cliente=cobranca.cliente_nome,
            rotulo_plano=cumprimento.rotulo_plano,
            expira_em=cumprimento.licenca_expira_em,
        )
    return email_service.enviar_email_confirmacao(
        destinatario=cobranca.cliente_email,
        nome_cliente=cobranca.cliente_nome,
        valor=cobranca.valor,
        link_produto=produto.link_download,
        cobranca=cobranca,
        nome_produto=produto.nome,
        chave_acesso=cumprimento.chave_entregue
    )
