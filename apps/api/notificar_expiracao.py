"""Job diário (Render Cron): ``python notificar_expiracao.py``.

Avisos de expiração de trial/assinatura. A lógica vive em ``scripts/notificar_expiracao.py``.
"""
from scripts.notificar_expiracao import run

__all__ = ["run"]

if __name__ == "__main__":
    run()
