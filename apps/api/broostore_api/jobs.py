"""Job RQ: processa o pagamento aprovado do Mercado Pago e entrega o produto.

Fluxo (ver docs/CHANGELOG-API.md, F1 e F2):

  1. Consulta o pagamento no Mercado Pago; só segue se ``approved``.
  2. Localiza a cobrança pelo ``external_reference`` e a TRAVA (``SELECT ... FOR UPDATE``);
     se já estiver ``delivered`` encerra (F2: dois webhooks simultâneos não entregam 2x).
  3. CUMPRE o pedido (licença ativada/renovada ou chave reservada) e grava a cobrança
     como ``approved`` — COMMIT ANTES de enviar o e-mail (F1: pedido pago nunca se perde).
  4. Reabre a trava, envia o e-mail; sucesso => ``delivered``; falha => continua ``approved``
     e o job LEVANTA exceção para o RQ tentar de novo (``Retry`` definido ao enfileirar).
     O retry é idempotente: não reserva outra chave nem estende a licença novamente.
  5. Registra a venda (``sales`` local + Supabase) — best-effort, como no original.

O nome importável ``worker.process_mercado_pago_webhook`` (usado pelo web para enfileirar
POR STRING) é mantido pelo shim ``worker.py`` na raiz do app.
"""
import logging
import time

from .config import get_settings
from .extensions import db
from .models import Cobranca, Sale
from .services import entrega as entrega_service
from .services import mercadopago as mp_service
from .services.supabase_rest import registrar_venda_no_supabase

logger = logging.getLogger("broostore")

_job_app = None


class EmailEntregaFalhou(Exception):
    """O pagamento foi aprovado e cumprido, mas o e-mail de entrega falhou (RQ fará retry)."""


def get_job_app():
    """App Flask do worker (criado uma vez por processo)."""
    global _job_app
    if _job_app is None:
        from . import create_app
        _job_app = create_app(role="worker")
    return _job_app


def set_job_app(app):
    """Define o app usado pelo job (testes)."""
    global _job_app
    _job_app = app


def _travar_cobranca(cobranca_id):
    """Relê a cobrança com ``FOR UPDATE`` (no-op no SQLite) para ver o status mais recente."""
    return (db.session.query(Cobranca)
            .filter(Cobranca.id == cobranca_id)
            .with_for_update()
            .populate_existing()
            .first())


def _buscar_cobranca(external_ref):
    """Busca por external_reference com até 5 tentativas (a cobrança pode ainda estar sendo gravada)."""
    cobranca = None
    for tentativa in range(5):
        cobranca = Cobranca.query.filter_by(external_reference=str(external_ref)).first()
        if cobranca:
            break
        if tentativa < 4:
            logger.info(f"[WORKER] Tentativa {tentativa+1}: cobrança não encontrada, aguardando 2s...")
            time.sleep(2)
            db.session.expire_all()
    return cobranca


def process_mercado_pago_webhook(payment_id):
    """Processa pagamento aprovado do Mercado Pago."""
    with get_job_app().app_context():
        # 1. Verificar token
        access_token = get_settings().mercadopago_access_token
        if not access_token:
            logger.error("[WORKER] ERRO: MERCADOPAGO_ACCESS_TOKEN não configurado.")
            return

        # 2. Consultar Mercado Pago
        sdk = mp_service.get_sdk(access_token)
        try:
            resp = mp_service.consultar_pagamento(sdk, payment_id)
        except Exception as e:
            logger.error(f"[WORKER] Falha ao consultar MP: {e}")
            return

        if resp["status"] != 200:
            logger.error(f"[WORKER] MP respondeu {resp['status']}")
            raise RuntimeError(f"Erro na API do MP: {resp['status']}")

        payment = resp["response"]

        if payment.get("status") != "approved":
            logger.info(f"[WORKER] Pagamento {payment_id} não aprovado ({payment.get('status')}).")
            return

        # 3. Buscar cobrança pelo EXTERNAL_REFERENCE
        external_ref = payment.get("external_reference")
        if not external_ref:
            logger.error(f"[WORKER] ERRO: Pagamento {payment_id} sem external_reference.")
            return

        logger.info(f"[WORKER] Processando pagamento {payment_id} | ExtRef: {external_ref}")

        cobranca = _buscar_cobranca(external_ref)
        if not cobranca:
            logger.error(f"[WORKER] ERRO: Cobrança {external_ref} não encontrada.")
            return

        cobranca_id = cobranca.id

        # F2: trava a cobrança e reconfere o status já com a trava
        cobranca = _travar_cobranca(cobranca_id)
        if cobranca.status == "delivered":
            logger.info(f"[WORKER] Cobrança {cobranca.id} já foi entregue. Ignorando.")
            db.session.rollback()
            return

        # 4. Buscar produto
        produto = cobranca.produto
        if not produto:
            logger.error("[WORKER] ERRO: Produto não encontrado.")
            db.session.rollback()
            return

        # 5. F1 — cumprir o pedido (idempotente) e COMMITAR antes do e-mail
        try:
            cumprimento = entrega_service.cumprir_pedido(produto, cobranca)
        except entrega_service.EntregaErro as e:
            db.session.rollback()
            logger.error(
                f"[WORKER] ⚠️ PEDIDO PAGO SEM ENTREGA: cobrança {cobranca_id} (pagamento {payment_id}) "
                f"continua com status '{cobranca.status}'. Motivo: {e}. O job será repetido pelo RQ; "
                f"se persistir, resolva manualmente (reponha estoque / configure o plano)."
            )
            raise

        cobranca.status = "approved"
        db.session.add(cobranca)
        db.session.commit()
        logger.info(f"[WORKER] ✅ Pedido cumprido e cobrança {cobranca_id} marcada 'approved' (e-mail pendente).")

        # 6. Enviar e-mail (de novo sob trava: um segundo worker espera e vê 'delivered')
        cobranca = _travar_cobranca(cobranca_id)
        if cobranca.status == "delivered":
            logger.info(f"[WORKER] Cobrança {cobranca.id} já foi entregue. Ignorando.")
            db.session.rollback()
            return
        produto = cobranca.produto

        sucesso = entrega_service.enviar_email_entrega(cobranca, produto, cumprimento)

        # 7. Finalizar e registrar no Supabase
        if not sucesso:
            db.session.rollback()
            logger.error(
                f"[WORKER] ERRO: Falha no envio de email. Cobrança {cobranca_id} segue 'approved' "
                f"(pedido já cumprido); o RQ tentará reenviar."
            )
            raise EmailEntregaFalhou(
                f"Falha no envio do e-mail de entrega da cobrança {cobranca_id} (pagamento {payment_id})"
            )

        # 7a. PRIMEIRO commit o essencial: cobrança entregue (a licença/chave já foram
        #     comitadas no passo 5). Isso NÃO pode depender do registro de venda.
        try:
            cobranca.status = "delivered"
            db.session.add(cobranca)
            db.session.commit()
            logger.info("[WORKER] ✅ Cobrança/licença salvas.")
        except Exception as e:
            logger.error(f"[WORKER] ERRO ao salvar cobrança/licença: {e}")
            db.session.rollback()
            return

        # 7b. Registro de venda — best-effort, NÃO derruba a licença.
        #     Assinatura: os planos vivem em 'produtos', não em 'products'
        #     (a FK de 'sales' aponta para 'products'), então pulamos.
        if produto.tipo == "assinatura":
            logger.info("[WORKER] (assinatura) registro em 'sales' ignorado.")
        else:
            try:
                db.session.add(Sale(product_id=produto.id, amount=cobranca.valor))
                db.session.commit()
                logger.info("[WORKER] ✅ Venda salva no banco local.")
            except Exception as e:
                logger.warning(f"[WORKER] ⚠️ Não foi possível salvar em 'sales': {e}")
                db.session.rollback()

            supabase_ok = registrar_venda_no_supabase(
                product_id=produto.id,
                customer_email=cobranca.cliente_email,
                amount=cobranca.valor,
                payment_id=payment_id
            )
            if supabase_ok:
                logger.info("[WORKER] ✅ Dashboard atualizado!")
            else:
                logger.warning("[WORKER] ⚠️ Dashboard NÃO atualizado.")
