"""
notificar_expiracao — Job diário (Render Cron) que envia e-mails de aviso:

  • Trial (teste grátis): avisa faltando até 2 dias e quando expira.
  • Assinatura paga: avisa faltando até 7 dias e quando expira.

Cada estágio é enviado UMA vez (controlado pela coluna licencas.ultimo_aviso).
Reaproveita o banco do BrooStock e o mesmo SMTP do worker.

Execução (comando do cron inalterado, a partir de apps/api): python notificar_expiracao.py
Também funciona: python scripts/notificar_expiracao.py
"""
import sys
from pathlib import Path

# Permite executar de qualquer pasta (``python scripts/x.py``): põe apps/api no sys.path.
_RAIZ = str(Path(__file__).resolve().parent.parent)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import logging
from datetime import datetime

from broostore_api import create_app
from broostore_api.extensions import db
from broostore_api.models import Licenca
from broostore_api.services.email import enviar_aviso, html_aviso

logger = logging.getLogger("broostore")


def run(app=None):
    enviados = 0
    app = app or create_app(role="worker")
    with app.app_context():
        agora = datetime.utcnow()
        licencas = Licenca.query.filter(Licenca.expira_em.isnot(None)).all()

        for lic in licencas:
            if not lic.expira_em:
                continue
            status = (lic.status or "").lower()
            if status not in ("trial", "ativa"):
                continue  # já expirada/cancelada: não reavisa

            email = (lic.cliente_email or "").strip()
            if not email:
                continue

            dias = (lic.expira_em - agora).days
            expira_str = lic.expira_em.strftime("%d/%m/%Y")
            venceu = lic.expira_em <= agora
            stage = assunto = corpo = None

            if status == "trial":
                if venceu and lic.ultimo_aviso != "expirado":
                    stage = "expirado"
                    assunto = "Seu teste grátis do BrooStock terminou"
                    corpo = html_aviso(
                        "Seu teste grátis terminou",
                        "Esperamos que tenha gostado do BrooStock! Para voltar a acessar seu estoque e seu painel financeiro, escolha um plano e ative sua assinatura.",
                        "Assinar agora",
                    )
                elif (not venceu) and dias <= 2 and lic.ultimo_aviso not in ("2d", "expirado"):
                    stage = "2d"
                    quando = "hoje" if dias <= 0 else (f"em {dias} dia" + ("s" if dias > 1 else ""))
                    assunto = "Seu teste grátis do BrooStock está acabando ⏳"
                    corpo = html_aviso(
                        "Seu teste está acabando",
                        f"Seu teste grátis termina <strong>{quando}</strong> ({expira_str}). Assine para não perder o acesso e continuar de onde parou.",
                        "Assinar e continuar",
                    )

            elif status == "ativa":
                if venceu and lic.ultimo_aviso != "expirado":
                    stage = "expirado"
                    assunto = "Sua licença do BrooStock expirou"
                    corpo = html_aviso(
                        "Sua licença expirou",
                        "Sua assinatura do BrooStock chegou ao fim. Renove para reativar o acesso ao seu estoque e painel.",
                        "Renovar agora",
                    )
                elif (not venceu) and dias <= 7 and lic.ultimo_aviso not in ("7d", "expirado"):
                    stage = "7d"
                    quando = "hoje" if dias <= 0 else (f"em {dias} dia" + ("s" if dias > 1 else ""))
                    assunto = "Sua licença do BrooStock vai expirar"
                    corpo = html_aviso(
                        "Sua licença vai expirar",
                        f"Sua assinatura expira <strong>{quando}</strong> ({expira_str}). Renove para manter o acesso sem interrupção.",
                        "Renovar agora",
                    )

            if not stage:
                continue

            if enviar_aviso(email, assunto, corpo):
                lic.ultimo_aviso = stage
                if stage == "expirado":
                    lic.status = "expirado"
                try:
                    db.session.commit()
                    enviados += 1
                    logger.info(f"[CRON] Aviso '{stage}' enviado para {email} (expira {expira_str}).")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"[CRON] ERRO ao salvar aviso de {email}: {e}")
            else:
                db.session.rollback()

    logger.info(f"[CRON] Concluído. {enviados} e-mail(s) enviado(s).")
    return enviados


if __name__ == "__main__":
    run()
