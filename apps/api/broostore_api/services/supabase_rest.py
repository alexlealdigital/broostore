"""Acesso ao Supabase via REST (PostgREST).

  * Leitura de produtos (fonte da verdade de preço/frete/tipo) com a chave anon.
  * Sincronização do produto local a partir do Supabase (checkout PIX e cartão).
  * Registro de venda (tabela ``sales`` do Supabase) com a service role key.
"""
import logging

import requests

from ..config import get_settings
from ..extensions import db
from ..models import Produto

logger = logging.getLogger("broostore")

SELECT_CHECKOUT = "id,title,price,link_pdf,frete,tipo,peso_kg,altura_cm,largura_cm,comprimento_cm"
SELECT_SYNC = "id,title,price,link_pdf"
SELECT_FRETE = "id,price,tipo,peso_kg,altura_cm,largura_cm,comprimento_cm"


def _anon_headers():
    settings = get_settings()
    return {"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {settings.supabase_anon_key}"}


def buscar_produto_rows(product_id, select, timeout=None):
    """GET /rest/v1/products?id=eq.<id>&select=... -> lista de linhas (JSON).

    ``timeout`` só é enviado ao ``requests`` quando informado (como no original,
    onde apenas a cotação de frete usava timeout).
    """
    settings = get_settings()
    kwargs = {"headers": _anon_headers()}
    if timeout is not None:
        kwargs["timeout"] = timeout
    resp = requests.get(
        f"{settings.supabase_url}/rest/v1/products?id=eq.{product_id}&select={select}",
        **kwargs
    )
    return resp.json()


def sincronizar_produto_checkout(product_id, produto, log_erro):
    """Sincroniza preço/dados do produto com o Supabase antes de cobrar.

    Retorna ``(produto, tipo_autoritativo, frete_autoritativo, p_dados)``.
    Qualquer falha no Supabase é registrada em ``log_erro`` e NÃO interrompe o
    checkout (usa o produto local), exatamente como no original.
    """
    frete_autoritativo = None
    tipo_autoritativo = produto.tipo if produto else None
    p_dados = {}  # dados físicos do Supabase para recotação de frete
    try:
        rows = buscar_produto_rows(product_id, SELECT_CHECKOUT)
        if rows:
            p = rows[0]
            tipo_autoritativo = (p.get("tipo") or "ebook").strip().lower()
            frete_autoritativo = float(p.get("frete") or 0)
            p_dados = {
                "price": float(p.get("price") or 0),
                "peso_kg": p.get("peso_kg"), "altura_cm": p.get("altura_cm"),
                "largura_cm": p.get("largura_cm"), "comprimento_cm": p.get("comprimento_cm"),
            }
            if not produto:
                # Produto novo: cria localmente
                produto = Produto(
                    id=p["id"],
                    nome=p["title"],
                    preco=float(p["price"]),
                    link_download=p.get("link_pdf") or "",
                    tipo=tipo_autoritativo
                )
                db.session.add(produto)
            else:
                # Produto existente: sempre atualiza preço/link/tipo do Supabase
                produto.preco = float(p["price"])
                produto.nome = p["title"]
                produto.link_download = p.get("link_pdf") or produto.link_download
                produto.tipo = tipo_autoritativo
            db.session.commit()
    except Exception as e:
        logger.error(f"{log_erro}: {e}")
    return produto, tipo_autoritativo, frete_autoritativo, p_dados


def registrar_venda_no_supabase(product_id, customer_email, amount, payment_id):
    """Insere a venda na tabela sales do Supabase para o dashboard atualizar."""
    settings = get_settings()
    service_key = settings.supabase_service_role_key
    if not service_key:
        logger.error("[WORKER] ❌ ERRO: SUPABASE_SERVICE_ROLE_KEY não configurada!")
        return False

    try:
        url = f"{settings.supabase_url}/rest/v1/sales"
        headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

        # Verifica se payment_id já existe antes de inserir (proteção anti-duplicata)
        check_url = f"{settings.supabase_url}/rest/v1/sales?payment_id=eq.{payment_id}&select=id"
        check_resp = requests.get(check_url, headers=headers, timeout=10)
        if check_resp.status_code == 200 and check_resp.json():
            logger.warning(f"[WORKER] ⚠️ Venda {payment_id} já registrada no Supabase. Ignorando duplicata.")
            return True

        payload = {
            "product_id": int(product_id),
            "customer_email": str(customer_email),
            "amount": float(amount),
            "payment_id": str(payment_id),
            "status": "paid"
        }

        logger.info(f"[WORKER] Inserindo no Supabase: Produto {product_id}, Valor {amount}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        logger.info(f"[WORKER] Resposta Supabase: Status {response.status_code}")

        if response.status_code in [200, 201]:
            logger.info("[WORKER] ✅ Venda registrada no Supabase!")
            return True
        else:
            logger.error(f"[WORKER] ❌ Erro Supabase: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"[WORKER] ❌ Exceção ao conectar no Supabase: {e}")
        return False
