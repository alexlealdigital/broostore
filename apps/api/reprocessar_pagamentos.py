"""Atalho na raiz de apps/api: ``python reprocessar_pagamentos.py [dias] [--executar]``.

A lógica vive em ``scripts/reprocessar_pagamentos.py``.
"""
import sys

from scripts.reprocessar_pagamentos import reprocessar

__all__ = ["reprocessar"]

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reprocessar(dias=int(args[0]) if args else 7, executar="--executar" in sys.argv)
