"""Atalho na raiz de apps/api: ``python sincronizar_licencas_app.py [slug-do-app]``.

A lógica vive em ``scripts/sincronizar_licencas_app.py``.
"""
import sys

from scripts.sincronizar_licencas_app import main

__all__ = ["main"]

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
