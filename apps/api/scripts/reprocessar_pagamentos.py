# reprocessar_pagamentos.py
# ---------------------------------------------------------------------------
# Recupera pedidos PAGOS que ficaram sem entrega porque a fila (Redis) estava
# fora do ar na hora do pagamento. Para cada cobrança ainda não entregue dos
# últimos N dias, pergunta ao Mercado Pago se existe pagamento APROVADO com
# aquele external_reference e, se existir, roda o mesmo processamento do worker
# (entrega o produto, manda o e-mail, ativa a licença).
#
# É seguro rodar mais de uma vez: o processamento ignora cobrança já entregue.
#
# Onde: painel do Render, aba "Shell" do worker (ou da API), a partir de apps/api:
#     python scripts/reprocessar_pagamentos.py            # só LISTA (não entrega nada)
#     python scripts/reprocessar_pagamentos.py 7          # idem, olhando os últimos 7 dias
#     python scripts/reprocessar_pagamentos.py 7 --executar   # entrega de verdade
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

# Permite executar de qualquer pasta (``python scripts/x.py``): põe apps/api no sys.path.
_RAIZ = str(Path(__file__).resolve().parent.parent)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from datetime import datetime, timedelta

from broostore_api import jobs
from broostore_api.config import get_settings
from broostore_api.models import Cobranca
from broostore_api.services import mercadopago as mp_service


def _aprovados(sdk, external_reference):
    """Pagamentos aprovados do Mercado Pago para uma cobrança."""
    resp = sdk.payment().search({"external_reference": str(external_reference)})
    if resp.get("status") != 200:
        raise RuntimeError(f"Mercado Pago respondeu {resp.get('status')} ao buscar {external_reference}")
    resultados = (resp.get("response") or {}).get("results") or []
    return [p for p in resultados if p.get("status") == "approved"]


def reprocessar(dias=7, executar=False, sdk=None, processar=None):
    """Devolve (ids_das_cobrancas_pagas_sem_entrega, quantas_foram_processadas).
    ``sdk`` e ``processar`` existem para teste."""
    if sdk is None:
        token = get_settings().mercadopago_access_token
        if not token:
            raise SystemExit("MERCADOPAGO_ACCESS_TOKEN não configurado neste serviço.")
        sdk = mp_service.get_sdk(token)
    processar = processar or jobs.process_mercado_pago_webhook

    desde = datetime.utcnow() - timedelta(days=dias)
    pagas, entregues = [], 0
    with jobs.get_job_app().app_context():
        pendentes = (Cobranca.query
                     .filter(Cobranca.status != "delivered", Cobranca.data_criacao >= desde)
                     .order_by(Cobranca.id.asc()).all())
        print(f"Cobranças não entregues nos últimos {dias} dia(s): {len(pendentes)}")
        refs = [(c.id, c.external_reference, c.cliente_email, c.valor, c.status) for c in pendentes]

    for cid, ref, email, valor, status in refs:
        try:
            aprovados = _aprovados(sdk, ref)
        except Exception as exc:
            print(f"  [ERRO] cobrança {cid} ({ref}): {exc}")
            continue
        if not aprovados:
            continue  # nunca foi paga (PIX não pago, cartão recusado...): nada a fazer
        pagas.append(cid)
        pid = aprovados[0]["id"]
        print(f"  PAGO e não entregue: cobrança {cid} | {email} | R$ {valor:.2f} | status local={status} | pagamento MP={pid}")
        if executar:
            try:
                processar(pid)
                entregues += 1
            except Exception as exc:
                print(f"    [ERRO] ao entregar a cobrança {cid}: {exc}")

    print("=" * 60)
    print(f"  Pagas e sem entrega : {len(pagas)}")
    if executar:
        print(f"  Processadas agora   : {entregues}")
    elif pagas:
        print("  Nada foi entregue (modo lista). Rode de novo com --executar para entregar.")
    print("=" * 60)
    return pagas, entregues


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reprocessar(dias=int(args[0]) if args else 7, executar="--executar" in sys.argv)
