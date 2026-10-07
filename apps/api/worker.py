#!/usr/bin/env python3
"""Worker RQ da BrooStore (entry point: ``python worker.py``).

Mantém o nome importável ``worker.process_mercado_pago_webhook``: o web enfileira o
job POR STRING e jobs que já estavam no Redis durante um deploy precisam continuar
resolvendo. A lógica vive em ``broostore_api/jobs.py``.
"""
from broostore_api.jobs import process_mercado_pago_webhook
from broostore_api.worker_main import main

__all__ = ["process_mercado_pago_webhook", "main"]  # o nome do job NÃO pode ser removido

if __name__ == "__main__":
    main()
