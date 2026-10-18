"""Registro dos APPS vendidos por assinatura/licença (modelo "conta + e-mail", como o BrooStock).

É a ÚNICA fonte de verdade sobre cada app: nome, endereço, dias de teste grátis e
textos dos e-mails. Para cadastrar um app novo basta acrescentar uma entrada em ``APPS``
(ver docs/PADRAO_NOVO_APP.md). Nenhuma outra linha de código muda.

Convenção do "slug" (chave do dicionário): minúsculas, sem espaços, ex.: ``broostock``.
O mesmo slug é usado em:
  - ``licencas.app`` e ``planos_assinatura.app`` (banco da BrooStore);
  - ``?app=<slug>`` nas rotas ``/api/licenca/status`` e ``/api/licenca/trial``;
  - ``<SLUG>_SUPABASE_URL`` / ``<SLUG>_SUPABASE_SERVICE_KEY`` (variáveis do Render).
"""
import re

from .config import app_env, get_settings

APP_PADRAO = "broostock"  # usado quando o cliente antigo não manda ?app=

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,39}$")

APPS = {
    "broostock": {
        "nome": "BrooStock",
        "url": "https://brootechstock.netlify.app",       # origem (CORS) e base dos links
        "login_path": "/login",
        "painel_path": "/painel",
        "trial_dias": 7,
        "uso": "seu estoque e seu painel financeiro",     # "para voltar a acessar ___"
        "boas_vindas_passos": [
            "Cadastre seu primeiro produto (custo, preço e estoque mínimo).",
            "Registre uma venda em Movimentações.",
            "Veja seu lucro e sua margem no Painel.",
        ],
    },
    # Exemplo de app novo (descomente e ajuste):
    # "meuapp": {
    #     "nome": "MeuApp",
    #     "url": "https://meuapp.netlify.app",
    #     "login_path": "/login",
    #     "painel_path": "/painel",
    #     "trial_dias": 7,
    #     "uso": "suas planilhas e relatórios",
    #     "boas_vindas_passos": ["Crie seu primeiro projeto.", "Convide sua equipe."],
    # },
}


def slug_valido(slug):
    return bool(slug) and bool(_SLUG_RE.match(slug))


def normalizar_slug(valor):
    """Slug em minúsculas e sem espaços; vazio/None -> app padrão."""
    slug = (valor or "").strip().lower()
    return slug or APP_PADRAO


def obter_app(slug):
    """Config do app, ou None se o slug não está cadastrado."""
    return APPS.get(normalizar_slug(slug))


def config_ou_generica(slug):
    """Config do app; para um slug desconhecido (ex.: licença antiga de um app removido
    do registro) devolve uma config genérica, para o e-mail/aviso nunca quebrar."""
    slug = normalizar_slug(slug)
    cfg = APPS.get(slug)
    if cfg:
        return {**cfg, "slug": slug}
    return {
        "slug": slug,
        "nome": slug.capitalize(),
        "url": get_settings().loja_url,
        "login_path": "",
        "painel_path": "",
        "trial_dias": 7,
        "uso": "o app",
        "boas_vindas_passos": [],
    }


def url_login(slug):
    cfg = config_ou_generica(slug)
    # Compatibilidade: BROOSTOCK_URL (variável antiga do cron) continua valendo.
    override = app_env(f"{cfg['slug'].upper()}_URL")
    return override or (cfg["url"].rstrip("/") + cfg["login_path"])


def url_painel(slug):
    cfg = config_ou_generica(slug)
    return cfg["url"].rstrip("/") + cfg["painel_path"]


def origens_cors():
    """Origens dos apps cadastrados, para o CORS."""
    return sorted({c["url"].rstrip("/") for c in APPS.values() if c.get("url")})
