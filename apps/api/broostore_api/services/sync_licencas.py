"""Espelha a licença de um app (ex.: BrooStock) no Supabase DO PRÓPRIO APP.

Por quê: o BrooStock guarda os dados dos clientes num projeto Supabase separado, e as
regras de acesso (RLS) de lá só enxergam aquele banco. A informação "quem pagou" mora
aqui, no banco da BrooStore. Sem esta cópia, o bloqueio por assinatura vira só uma tela:
quem tem a conta logada consegue chamar o Supabase direto pelo console do navegador e
ignorar o gate. Com a tabela ``licenses`` alimentada por este módulo, a RLS do app exige
licença ativa em cada consulta.

Padrão replicável: cada app tem um par de variáveis de ambiente
    <APP>_SUPABASE_URL           ex.: BROOSTOCK_SUPABASE_URL
    <APP>_SUPABASE_SERVICE_KEY   ex.: BROOSTOCK_SUPABASE_SERVICE_KEY
Um app novo = mais duas variáveis, sem mudar código.

A sincronização é "melhor esforço": nunca levanta exceção e nunca derruba a entrega do
produto. Se falhar, o job diário (scripts/notificar_expiracao.py) ou o script
``sincronizar_licencas_app.py`` refaz.
"""
import logging
from datetime import datetime, timezone

import requests

from ..config import app_env

logger = logging.getLogger("broostore")

TIMEOUT_S = 8
TENTATIVAS = 2


def config_do_app(app_slug):
    """(url, service_key) do Supabase do app, ou (None, None) se faltar alguma variável."""
    prefixo = app_slug.strip().upper()
    url = (app_env(f"{prefixo}_SUPABASE_URL") or "").strip().rstrip("/")
    chave = (app_env(f"{prefixo}_SUPABASE_SERVICE_KEY") or "").strip()
    return (url, chave) if url and chave else (None, None)


def _iso_utc(dt):
    """datetime naive (que guardamos em UTC) -> ISO 8601 com fuso explícito."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def montar_payload(email, expira_em, plano, is_trial=False, ativa=True):
    return {
        "email": (email or "").strip().lower(),
        "ativa": bool(ativa),
        "plano": plano,
        "is_trial": bool(is_trial),
        "expira_em": _iso_utc(expira_em),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def sincronizar_licenca(app_slug, email, expira_em, plano, is_trial=False, ativa=True):
    """Upsert da licença no Supabase do app. Devolve True se gravou.

    Nunca levanta exceção: o chamador (job de pagamento, cadastro de trial) não pode
    falhar por causa de uma cópia auxiliar.
    """
    try:
        url, chave = config_do_app(app_slug)
        if not url:
            logger.warning(
                f"[SYNC] {app_slug}: variáveis {app_slug.upper()}_SUPABASE_URL/_SERVICE_KEY ausentes "
                f"— licença de {email} NÃO espelhada.")
            return False

        payload = montar_payload(email, expira_em, plano, is_trial, ativa)
        if not payload["email"]:
            return False

        headers = {
            "apikey": chave,
            "Authorization": f"Bearer {chave}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                r = requests.post(f"{url}/rest/v1/licenses?on_conflict=email",
                                  json=payload, headers=headers, timeout=TIMEOUT_S)
                if r.status_code in (200, 201, 204):
                    logger.info(f"[SYNC] {app_slug}: licença de {payload['email']} espelhada "
                                f"(expira {payload['expira_em']}).")
                    return True
                logger.error(f"[SYNC] {app_slug}: Supabase respondeu {r.status_code} "
                             f"(tentativa {tentativa}): {str(r.text)[:200]}")
            except Exception as exc:  # rede, timeout, DNS...
                logger.error(f"[SYNC] {app_slug}: falha de rede (tentativa {tentativa}): {exc}")
        return False
    except Exception as exc:  # garantia final: nunca propaga
        logger.error(f"[SYNC] {app_slug}: erro inesperado ao espelhar {email}: {exc}")
        return False
