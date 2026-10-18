"""E-mails transacionais da BrooStore.

  * SMTP (Zoho por padrão): entrega de produto, pedido físico, licença de app (BrooStock e
    os próximos, textos em apps_config), boas-vindas do teste grátis e avisos de expiração (cron).
  * Resend: formulário de contato.

Todos os textos/HTML foram portados SEM alteração de conteúdo. Cada função de
envio retorna True/False (nunca levanta), como no original.
"""
import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import resend

from .. import apps_config
from ..config import get_settings

logger = logging.getLogger("broostore")

CONTATO_DESTINO = "profalexleal@gmail.com"


def _brl(valor) -> str:
    """Valor no padrao brasileiro (1234.5 -> 1.234,50). Cosmetico: so o texto do e-mail."""
    try:
        txt = f"{float(valor):,.2f}"
    except (TypeError, ValueError):
        return str(valor)
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def _credenciais():
    """(servidor, usuário, senha) ou None se EMAIL_USER/EMAIL_PASSWORD não existirem."""
    settings = get_settings()
    if settings.email_user is None or settings.email_password is None:
        return None
    return settings.smtp_server, settings.email_user, settings.email_password


def _enviar_smtp(msg, smtp_server, email_user, email_pass, timeout, ssl_na_465=False):
    """Envia via SMTP. STARTTLS por padrão; ``ssl_na_465`` (só o e-mail de produto
    físico, como no original) usa SMTP_SSL quando a porta é 465."""
    smtp_port = get_settings().smtp_port()
    if ssl_na_465 and smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=timeout) as server:
            server.login(email_user, email_pass)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=timeout) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.send_message(msg)


def _montar(assunto, email_user, destinatario, corpo_html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = email_user
    msg["To"] = destinatario
    msg.attach(MIMEText(corpo_html, "html"))
    return msg


# ---------------------------------------------------------------------------
# Teste grátis (web)
# ---------------------------------------------------------------------------
def enviar_boas_vindas(destinatario, expira_em, app_slug=apps_config.APP_PADRAO):
    """E-mail de boas-vindas do teste grátis. Best-effort: nunca derruba o cadastro.
    Reaproveita o mesmo SMTP (Zoho) usado pelo worker/avisos de expiração.
    Textos e links vêm de apps_config (um app novo não exige mudar este código)."""
    cred = _credenciais()
    if cred is None:
        logger.warning("[TRIAL] Boas-vindas NÃO enviada: SMTP (EMAIL_USER/EMAIL_PASSWORD) não configurado no serviço.")
        return False
    smtp_server, email_user, email_pass = cred

    cfg = apps_config.config_ou_generica(app_slug)
    nome = cfg["nome"]
    expira_str = expira_em.strftime("%d/%m/%Y")
    passos = "\n      ".join(f"<li>{p}</li>" for p in cfg.get("boas_vindas_passos", []))
    bloco_passos = (f'''
    <p style="margin-top:18px;"><strong>Comece por aqui:</strong></p>
    <ol style="color:#cdd7e3;line-height:1.7;padding-left:18px;">
      {passos}
    </ol>''') if passos else ""
    html = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;background:#0d1b2a;color:#e0e6ed;padding:24px;">
  <div style="max-width:560px;margin:0 auto;background:#14213d;border-radius:12px;padding:28px;">
    <h2 style="color:#48cae4;margin-top:0;">Bem-vindo ao {nome}! 🎉</h2>
    <p>Seu <strong>teste grátis de {cfg['trial_dias']} dias</strong> está ativo. Você pode usar o sistema completo
       até <strong>{expira_str}</strong>, sem cartão e sem compromisso.</p>{bloco_passos}
    <p style="text-align:center;margin:26px 0;">
      <a href="{apps_config.url_painel(app_slug)}" style="background:#15bcd6;color:#012;text-decoration:none;font-weight:bold;padding:12px 22px;border-radius:8px;display:inline-block;">Abrir o {nome}</a>
    </p>
    <p style="font-size:0.85em;color:#9fb0c3;">Quando quiser, é só assinar para continuar usando depois do teste. Qualquer dúvida, estamos por aqui.</p>
  </div>
</body></html>"""

    try:
        msg = _montar(f"Bem-vindo ao {nome} — seus {cfg['trial_dias']} dias grátis começaram 🎉",
                      email_user, destinatario, html)
        _enviar_smtp(msg, smtp_server, email_user, email_pass, timeout=15)
        logger.info(f"[TRIAL] Boas-vindas ({cfg['slug']}) enviada para {destinatario}.")
        return True
    except Exception as e:
        logger.error(f"[TRIAL] Falha ao enviar boas-vindas para {destinatario}: {e}")
        return False


# ---------------------------------------------------------------------------
# Entrega de pedidos (worker)
# ---------------------------------------------------------------------------
def enviar_email_produto_fisico(destinatario, nome_cliente, valor, nome_produto, cobranca):
    """Envia email de confirmação de pedido para produto físico."""
    cred = _credenciais()
    if cred is None:
        logger.error("[WORKER] ERRO: Credenciais de email não configuradas.")
        return False
    smtp_server, email_user, email_pass = cred

    assunto = f'BrooStore: Pedido "{nome_produto}" confirmado! 📦'

    # Tenta recuperar endereço do campo observacoes ou metadados da cobrança
    endereco_html = ""
    try:
        meta = json.loads(cobranca.observacoes or "{}")
        end = meta.get("endereco", {})
        if end:
            endereco_html = f"""
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:15px;margin:20px 0;">
                <h3 style="margin:0 0 10px;color:#374151;">📍 Endereço de Entrega</h3>
                <p style="margin:3px 0;color:#374151;">{end.get('rua','')} {end.get('numero','')}{', '+end.get('complemento','') if end.get('complemento') else ''}</p>
                <p style="margin:3px 0;color:#374151;">{end.get('bairro','')} — {end.get('cidade','')} / {end.get('estado','')}</p>
                <p style="margin:3px 0;color:#374151;">CEP: {end.get('cep','')}</p>
            </div>"""
    except Exception:
        pass

    instrucoes = f"""
        <p>Agradecemos por escolher a <strong>BrooStore</strong>! Seu pagamento de <strong>R$ {_brl(valor)}</strong> foi confirmado.</p>
        <h2 style="color:#27ae60;">Pedido recebido com sucesso! 🎉</h2>
        <p>Seu pedido de <strong>{nome_produto}</strong> foi confirmado e está sendo preparado.</p>
        {endereco_html}
        <div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;padding:15px;margin:20px 0;">
            <p style="margin:0;color:#92400e;"><strong>⏱️ Próximos passos:</strong><br>
            Entraremos em contato em breve para confirmar os detalhes do envio e o prazo de entrega.</p>
        </div>
        <p style="color:#6b7280;font-size:0.9em;">Em caso de dúvidas, responda este e-mail.</p>
    """

    corpo_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body{{font-family:Arial,sans-serif;line-height:1.6;color:#333;margin:0;padding:0;background:#f4f4f4;}}
.container{{max-width:600px;margin:20px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 4px 6px rgba(0,0,0,.1);}}
.header{{background:#3B82F6;padding:30px;text-align:center;color:white;}}
.content{{padding:30px;}}
.footer{{background:#f9fafb;padding:20px;text-align:center;font-size:.9em;color:#6b7280;border-top:1px solid #e5e7eb;}}
</style></head><body>
<div class="container">
  <div class="header"><h1>✅ Parabéns pela sua compra!</h1></div>
  <div class="content">
    <p>Olá, {nome_cliente},</p>
    {instrucoes}
  </div>
  <div class="footer">
    <strong>BrooStore</strong><br>
    Pedido ID: {cobranca.id}<br>
    Em caso de dúvidas, responda este e-mail.
  </div>
</div>
</body></html>"""

    try:
        msg = _montar(assunto, email_user, destinatario, corpo_html)
        _enviar_smtp(msg, smtp_server, email_user, email_pass, timeout=10, ssl_na_465=True)
        logger.info(f"[WORKER] Email físico enviado para {destinatario}")
        return True
    except Exception as e:
        logger.error(f"[WORKER] Erro ao enviar email físico: {e}")
        return False


def enviar_email_confirmacao(destinatario, nome_cliente, valor, link_produto, cobranca, nome_produto, chave_acesso=None,
                             expira_em=None, rotulo_plano=None, renovada=False):
    """Envia email de entrega do produto.

    ``expira_em``/``rotulo_plano``/``renovada`` só vêm para chaves geradas na compra
    (planos_chave): mostram a validade e avisam quando a chave foi renovada. Chave do estoque
    pré-carregado chega sem eles e o e-mail continua exatamente o de sempre."""
    cred = _credenciais()
    if cred is None:
        logger.error("[WORKER] ERRO: Credenciais de email não configuradas.")
        return False
    smtp_server, email_user, email_pass = cred

    if chave_acesso and nome_produto == "Compressão de PDF":
        assunto = "BrooStore: Seu código de compressão de PDF chegou! 🗜️"
        instrucoes_entrega = f"""
            <p>Agradecemos por escolher a <strong>BrooStore</strong>! Seu pagamento de <strong>R$ {_brl(valor)}</strong> foi confirmado.</p>
            <h2 style="color: #fca311;">Seu código de liberação está aqui! 🔑</h2>
            <p>Cole este código na página de compressão para baixar seu PDF reduzido:</p>
            <div style="background-color: #1a1400; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0; border: 2px dashed #fca311;">
                <code style="font-size: 1.1em; font-weight: bold; color: #fca311; display: block; word-break: break-all;">{chave_acesso}</code>
            </div>
            <div style="text-align: center; margin: 25px 0;">
                <a href="https://mercadopago-final.onrender.com/comprimir-pdf.html" style="background-color: #fca311; color: #000; padding: 14px 28px; text-decoration: none; border-radius: 25px; font-weight: bold;">🗜️ Ir para o Compressor</a>
            </div>
            <p style="font-size:0.85em; color:#888;">Este código é de uso único e válido por 24 horas.</p>
        """
    elif chave_acesso and (rotulo_plano or expira_em or renovada):
        plano_txt = f" ({rotulo_plano})" if rotulo_plano else ""
        if expira_em:
            validade_html = (f'<p style="text-align:center;margin:0 0 6px;">Licença{plano_txt} válida até '
                             f'<strong>{expira_em.strftime("%d/%m/%Y")}</strong>.</p>')
        else:
            validade_html = f'<p style="text-align:center;margin:0 0 6px;">Licença{plano_txt} <strong>vitalícia</strong>.</p>'

        if renovada:
            assunto = f"BrooStore: Sua licença de \"{nome_produto}\" foi renovada! 🔄"
            titulo_chave = "Licença renovada! 🔄"
            aviso_chave = "<p>Sua chave continua a <strong>mesma</strong> — não precisa digitar nada de novo. A validade já foi estendida.</p>"
        else:
            assunto = f"BrooStore: Sua chave de acesso para \"{nome_produto}\" chegou! 🚀"
            titulo_chave = "Sua Chave de Acesso está aqui! 🔑"
            aviso_chave = "<p>Copie a chave acima e cole no app quando ele pedir. Se precisar baixar:</p>"

        instrucoes_entrega = f"""
            <p>Agradecemos por escolher a <strong>BrooStore</strong>! Seu pagamento de <strong>R$ {_brl(valor)}</strong> foi confirmado.</p>
            <h2 style="color: #27ae60;">{titulo_chave}</h2>
            <div style="background-color: #e0f2f1; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0 8px; border: 2px dashed #27ae60;">
                <code style="font-size: 1.5em; font-weight: bold; color: #14213d; display: block; word-break: break-all;">{chave_acesso}</code>
            </div>
            {validade_html}
            {aviso_chave}
            <div style="text-align: center; margin: 25px 0;">
                <a href="{link_produto}" style="background-color: #27ae60; color: white; padding: 14px 28px; text-decoration: none; border-radius: 25px; font-weight: bold;">📥 Baixar o Instalador</a>
            </div>
            <p style="font-size:0.85em; color:#888;">Guarde este e-mail: a chave é pessoal. Avisaremos antes da licença vencer.</p>
        """
    elif chave_acesso:
        assunto = f"BrooStore: Sua chave de acesso para \"{nome_produto}\" chegou! 🚀"
        instrucoes_entrega = f"""
            <p>Agradecemos por escolher a <strong>BrooStore</strong>! Seu pagamento de <strong>R$ {_brl(valor)}</strong> foi confirmado.</p>
            <h2 style="color: #27ae60;">Sua Chave de Acesso está aqui! 🔑</h2>
            <div style="background-color: #e0f2f1; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0; border: 2px dashed #27ae60;">
                <code style="font-size: 1.5em; font-weight: bold; color: #14213d; display: block; word-break: break-all;">{chave_acesso}</code>
            </div>
            <p>Copie a chave acima e use-a no instalador. Se precisar baixar:</p>
            <div style="text-align: center; margin: 25px 0;">
                <a href="{link_produto}" style="background-color: #27ae60; color: white; padding: 14px 28px; text-decoration: none; border-radius: 25px; font-weight: bold;">📥 Baixar o Instalador</a>
            </div>
        """
    else:
        assunto = f"BrooStore: Seu e-book \"{nome_produto}\" está pronto! 🎉"
        instrucoes_entrega = f"""
            <p>Agradecemos por escolher a <strong>BrooStore</strong>! Seu pagamento de <strong>R$ {_brl(valor)}</strong> foi confirmado.</p>
            <h2>Agora é hora de devorar o conteúdo!</h2>
            <div style="text-align: center; margin: 25px 0;">
                <a href="{link_produto}" style="background-color: #f59e0b; color: #14213d; padding: 14px 28px; text-decoration: none; border-radius: 25px; font-weight: bold;">📥 Baixar Meu E-book</a>
            </div>
        """

    corpo_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
    .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
    .header {{ background-color: #3B82F6; padding: 30px; text-align: center; color: white; }}
    .header h1 {{ margin: 0; font-size: 1.8em; }}
    .content {{ padding: 30px; }}
    .footer {{ background-color: #f9fafb; padding: 20px; text-align: center; font-size: 0.9em; color: #6b7280; border-top: 1px solid #e5e7eb; }}
    code {{ font-family: monospace; background-color: #f3f4f6; padding: 2px 5px; border-radius: 3px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header"><h1>✅ Parabéns pela sua compra!</h1></div>
    <div class="content">
      <p>Olá, {nome_cliente},</p>
      {instrucoes_entrega}
    </div>
    <div class="footer">
      <strong>BrooStore</strong><br>
      Pedido ID: {cobranca.id}<br>
      Em caso de dúvidas, responda este e-mail.
    </div>
  </div>
</body>
</html>"""

    msg = _montar(assunto, email_user, destinatario, corpo_html)

    try:
        _enviar_smtp(msg, smtp_server, email_user, email_pass, timeout=10)
        logger.info(f"[WORKER] Email enviado para {destinatario}")
        return True
    except Exception as exc:
        logger.error(f"[WORKER] Falha no envio SMTP: {exc}")
        return False


def enviar_email_licenca(destinatario, nome_cliente, rotulo_plano, expira_em, app_slug=apps_config.APP_PADRAO):
    """Envia e-mail confirmando a ativação/renovação da licença de um app
    (nome e endereço vêm de apps_config)."""
    cred = _credenciais()
    if cred is None:
        logger.error("[WORKER] ERRO: Credenciais de email não configuradas.")
        return False
    smtp_server, email_user, email_pass = cred

    validade_str = expira_em.strftime("%d/%m/%Y")
    plano_str = (rotulo_plano or "assinatura").capitalize()
    nome_app = apps_config.config_ou_generica(app_slug)["nome"]
    assunto = f"{nome_app}: Sua licença está ativa! 🚀"
    corpo_html = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;background:#0d1b2a;color:#e0e6ed;padding:24px;">
  <div style="max-width:560px;margin:0 auto;background:#14213d;border-radius:12px;padding:28px;">
    <h2 style="color:#48cae4;margin-top:0;">Licença {nome_app} ativada ✅</h2>
    <p>Olá, {nome_cliente or 'cliente'}!</p>
    <p>Recebemos seu pagamento e sua licença do <strong>{nome_app}</strong> já está ativa.</p>
    <div style="background:#0d1b2a;border:1px solid #2a3b55;border-radius:8px;padding:16px;margin:16px 0;">
      <p style="margin:4px 0;">Plano: <strong>{plano_str}</strong></p>
      <p style="margin:4px 0;">Válida até: <strong>{validade_str}</strong></p>
    </div>
    <p>Acesse o {nome_app} com o <strong>mesmo e-mail desta compra</strong> ({destinatario}) para usar a ferramenta liberada.</p>
    <p style="text-align:center;margin:22px 0;"><a href="{apps_config.url_login(app_slug)}" style="background:#15bcd6;color:#012;text-decoration:none;font-weight:bold;padding:12px 22px;border-radius:8px;display:inline-block;">Abrir o {nome_app}</a></p>
    <p style="font-size:0.85em;color:#9fb0c3;">Quando a licença estiver perto de expirar, avisaremos por e-mail para você renovar.</p>
  </div>
</body></html>"""

    msg = _montar(assunto, email_user, destinatario, corpo_html)

    try:
        _enviar_smtp(msg, smtp_server, email_user, email_pass, timeout=10)
        logger.info(f"[WORKER] Email de licença enviado para {destinatario}")
        return True
    except Exception as exc:
        logger.error(f"[WORKER] Falha no envio SMTP (licença): {exc}")
        return False


# ---------------------------------------------------------------------------
# Avisos de expiração (cron)
# ---------------------------------------------------------------------------
def html_aviso(titulo: str, paragrafo: str, cta_label: str, cta_url: str = None) -> str:
    cta_url = cta_url or get_settings().broostock_url
    return f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;background:#0d1b2a;color:#e0e6ed;padding:24px;">
  <div style="max-width:560px;margin:0 auto;background:#14213d;border-radius:12px;padding:28px;">
    <h2 style="color:#48cae4;margin-top:0;">{titulo}</h2>
    <p>{paragrafo}</p>
    <p style="text-align:center;margin:24px 0;">
      <a href="{cta_url}" style="background:#15bcd6;color:#012;text-decoration:none;font-weight:bold;padding:12px 22px;border-radius:8px;display:inline-block;">{cta_label}</a>
    </p>
    <p style="font-size:0.85em;color:#9fb0c3;">Se você já renovou ou assinou, pode ignorar este aviso.</p>
  </div>
</body></html>"""


def enviar_aviso(destinatario: str, assunto: str, corpo_html: str) -> bool:
    cred = _credenciais()
    if cred is None:
        logger.error("[CRON] ERRO: credenciais de e-mail não configuradas.")
        return False
    smtp_server, email_user, email_pass = cred

    msg = _montar(assunto, email_user, destinatario, corpo_html)
    try:
        _enviar_smtp(msg, smtp_server, email_user, email_pass, timeout=15)
        return True
    except Exception as exc:
        logger.error(f"[CRON] Falha no envio SMTP para {destinatario}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Contato (Resend)
# ---------------------------------------------------------------------------
def enviar_contato(nome, email_remetente, assunto, mensagem):
    """Envia a mensagem do formulário de contato via Resend.

    Retorna ``"sem_api_key"``, ``"ok"`` ou ``"falha"`` (Resend respondeu sem ``id``).
    Exceções do Resend propagam (a rota as trata, como no original).
    """
    resend.api_key = get_settings().resend_api_key
    if not resend.api_key:
        return "sem_api_key"

    params = {
        "from": "BrooStore <onboarding@resend.dev>",
        "to": CONTATO_DESTINO,
        "reply_to": email_remetente,
        "subject": f"Contato BrooStore: {assunto}",
        "html": f"<p>De: {nome} ({email_remetente})</p><hr><p>{mensagem}</p>"
    }

    email = resend.Emails.send(params)

    if email.get("id"):
        return "ok"
    return "falha"
