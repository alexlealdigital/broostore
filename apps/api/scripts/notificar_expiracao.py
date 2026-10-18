"""
notificar_expiracao — Job diário (Render Cron) que envia e-mails de aviso:

  • Trial (teste grátis): avisa faltando até 2 dias e quando expira.
  • Assinatura paga: avisa faltando até 7 dias e quando expira.
  • Chaves de licença com duração (planos_chave): avisa faltando até 7 dias e quando vence.

Cada estágio é enviado UMA vez (controlado pelas colunas ultimo_aviso). Os textos e o link de
cada aviso vêm de apps_config (um app novo não muda este código). No fim, reenvia ao Supabase
de cada app as licenças vigentes (cura qualquer falha pontual do espelho; apps sem as variáveis
<APP>_SUPABASE_* são ignorados). Reaproveita o banco da BrooStore e o mesmo SMTP do worker.

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

from broostore_api import apps_config, create_app
from broostore_api.config import get_settings
from broostore_api.extensions import db
from broostore_api.models import ChaveLicenca, Licenca, Produto
from broostore_api.services.email import enviar_aviso, html_aviso
from broostore_api.services.sync_licencas import config_do_app, sincronizar_licenca

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

            # Textos e link do aviso vêm do registro de apps
            cfg = apps_config.config_ou_generica(lic.app_slug)
            nome = cfg["nome"]
            link_app = apps_config.url_login(cfg["slug"])

            dias = (lic.expira_em - agora).days
            expira_str = lic.expira_em.strftime("%d/%m/%Y")
            venceu = lic.expira_em <= agora
            stage = assunto = corpo = None

            if status == "trial":
                if venceu and lic.ultimo_aviso != "expirado":
                    stage = "expirado"
                    assunto = f"Seu teste grátis do {nome} terminou"
                    corpo = html_aviso(
                        "Seu teste grátis terminou",
                        f"Esperamos que tenha gostado do {nome}! Para voltar a acessar {cfg['uso']}, escolha um plano e ative sua assinatura.",
                        "Assinar agora", link_app,
                    )
                elif (not venceu) and dias <= 2 and lic.ultimo_aviso not in ("2d", "expirado"):
                    stage = "2d"
                    quando = "hoje" if dias <= 0 else (f"em {dias} dia" + ("s" if dias > 1 else ""))
                    assunto = f"Seu teste grátis do {nome} está acabando ⏳"
                    corpo = html_aviso(
                        "Seu teste está acabando",
                        f"Seu teste grátis termina <strong>{quando}</strong> ({expira_str}). Assine para não perder o acesso e continuar de onde parou.",
                        "Assinar e continuar", link_app,
                    )

            elif status == "ativa":
                if venceu and lic.ultimo_aviso != "expirado":
                    stage = "expirado"
                    assunto = f"Sua licença do {nome} expirou"
                    corpo = html_aviso(
                        "Sua licença expirou",
                        f"Sua assinatura do {nome} chegou ao fim. Renove para reativar o acesso a {cfg['uso']}.",
                        "Renovar agora", link_app,
                    )
                elif (not venceu) and dias <= 7 and lic.ultimo_aviso not in ("7d", "expirado"):
                    stage = "7d"
                    quando = "hoje" if dias <= 0 else (f"em {dias} dia" + ("s" if dias > 1 else ""))
                    assunto = f"Sua licença do {nome} vai expirar"
                    corpo = html_aviso(
                        "Sua licença vai expirar",
                        f"Sua assinatura expira <strong>{quando}</strong> ({expira_str}). Renove para manter o acesso sem interrupção.",
                        "Renovar agora", link_app,
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
                    logger.info(f"[CRON] Aviso '{stage}' ({cfg['slug']}) enviado para {email} (expira {expira_str}).")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"[CRON] ERRO ao salvar aviso de {email}: {e}")
            else:
                db.session.rollback()

        enviados += _avisar_chaves(agora)
        _reconciliar_apps(agora)

    logger.info(f"[CRON] Concluído. {enviados} e-mail(s) enviado(s).")
    return enviados


def _avisar_chaves(agora):
    """Avisos de vencimento das chaves de licença com duração (planos_chave)."""
    enviados = 0
    loja_url = get_settings().loja_url
    chaves = (ChaveLicenca.query
              .filter(ChaveLicenca.vendida == True,      # noqa: E712
                      ChaveLicenca.revogada == False,    # noqa: E712
                      ChaveLicenca.expira_em.isnot(None))
              .all())
    for ch in chaves:
        email = (ch.cliente_email or "").strip()
        if not email:
            continue
        produto = db.session.get(Produto, ch.produto_id)
        nome_app = produto.nome if produto else "seu app"
        dias = (ch.expira_em - agora).days
        expira_str = ch.expira_em.strftime("%d/%m/%Y")
        venceu = ch.expira_em <= agora
        stage = assunto = corpo = None

        if venceu and ch.ultimo_aviso != "expirado":
            stage = "expirado"
            assunto = f"Sua licença de {nome_app} expirou"
            corpo = html_aviso(
                "Sua licença expirou",
                f"A licença de <strong>{nome_app}</strong> chegou ao fim em {expira_str}. "
                "Renove com o mesmo e-mail da compra: sua chave continua a mesma e a validade é estendida.",
                "Renovar agora", loja_url,
            )
        elif (not venceu) and dias <= 7 and ch.ultimo_aviso not in ("7d", "expirado"):
            stage = "7d"
            quando = "hoje" if dias <= 0 else (f"em {dias} dia" + ("s" if dias > 1 else ""))
            assunto = f"Sua licença de {nome_app} vai expirar"
            corpo = html_aviso(
                "Sua licença vai expirar",
                f"A licença de <strong>{nome_app}</strong> expira <strong>{quando}</strong> ({expira_str}). "
                "Renove com o mesmo e-mail da compra para manter o acesso: sua chave continua a mesma.",
                "Renovar agora", loja_url,
            )

        if not stage:
            continue

        if enviar_aviso(email, assunto, corpo):
            ch.ultimo_aviso = stage
            try:
                db.session.commit()
                enviados += 1
                logger.info(f"[CRON] Aviso de chave '{stage}' enviado para {email} (expira {expira_str}).")
            except Exception as e:
                db.session.rollback()
                logger.error(f"[CRON] ERRO ao salvar aviso de chave de {email}: {e}")
        else:
            db.session.rollback()
    return enviados


def _reconciliar_apps(agora):
    """Reenvia ao Supabase de CADA app toda licença vigente dele (best-effort)."""
    espelhadas = {}
    sem_config = set()
    vigentes = Licenca.query.filter(Licenca.expira_em > agora,
                                    Licenca.status.in_(("ativa", "trial"))).all()
    for lic in vigentes:
        slug = apps_config.normalizar_slug(lic.app_slug)
        if slug in sem_config:
            continue
        if not config_do_app(slug)[0]:
            sem_config.add(slug)
            logger.warning(f"[CRON] App '{slug}': variáveis {slug.upper()}_SUPABASE_URL/_SERVICE_KEY "
                           f"ausentes — sem reconciliação.")
            continue
        if sincronizar_licenca(slug, lic.cliente_email, lic.expira_em,
                               lic.plano, is_trial=(lic.status == "trial")):
            espelhadas[slug] = espelhadas.get(slug, 0) + 1
    for slug, n in sorted(espelhadas.items()):
        logger.info(f"[CRON] {n} licença(s) de '{slug}' reconciliada(s) com o Supabase do app.")


if __name__ == "__main__":
    run()
