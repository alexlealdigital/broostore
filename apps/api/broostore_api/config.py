"""Configuração centralizada da API BrooStore.

TODAS as variáveis de ambiente são lidas AQUI (e só aqui), com os mesmos
valores padrão do código original (app.py / worker.py / Dashboard_api.py /
notificar_expiracao.py).

As variáveis são lidas em tempo de chamada (``get_settings()``), nunca em
tempo de import, para que os testes possam alterá-las com ``monkeypatch``.
"""
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("broostore")

# Diretório raiz do app (apps/api) e pasta de arquivos estáticos (servida pelo Flask).
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# ---------------------------------------------------------------------------
# Constantes idênticas às do original
# ---------------------------------------------------------------------------
# Origens liberadas no CORS (idênticas ao app.py original).
NETLIFY_ORIGIN_PROD = "https://rread.netlify.app"
RENDER_ORIGIN = "https://mercadopago-final.onrender.com"
NETLIFY_ORIGIN_TEST = "https://rankedsale.netlify.app"
BROOSTORE_ORIGIN = "https://broostore.netlify.app"
BROOSTOCK_ORIGIN = "https://brootechstock.netlify.app"  # app BrooStock (compra de chave no cadastro)

CORS_ORIGINS = [
    NETLIFY_ORIGIN_PROD,
    RENDER_ORIGIN,
    NETLIFY_ORIGIN_TEST,
    BROOSTORE_ORIGIN,
    BROOSTOCK_ORIGIN,
]
CORS_METHODS = ["GET", "POST", "OPTIONS"]
CORS_ALLOW_HEADERS = ["Content-Type", "Authorization", "X-Requested-With"]

# Valores padrão herdados do original (mantidos de propósito).
DEFAULT_SECRET_KEY = "asdf#FGSgvasgf$5$WGT"
DEFAULT_SUPABASE_URL = "https://gyepvrzkwesohbagpgfa.supabase.co"
# Chave PÚBLICA (anon) do Supabase — é pública por desenho, igual ao original.
DEFAULT_SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd5ZXB2cnprd2Vzb2hiYWdwZ2ZhIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NjEzMDk5OTAsImV4cCI6MjA3Njg4NTk5MH0.ePwzEE8FjikLiTyjbtJXUtIIwFRlaSf5RYe7iKMDnTA"
)
DEFAULT_DATABASE_URL = "sqlite:///cobrancas.db"
DEFAULT_REDIS_URL = "redis://localhost:6379"
DEFAULT_SMTP_SERVER = "smtp.zoho.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_MELHOR_ENVIO_URL = "https://www.melhorenvio.com.br/api/v2"
DEFAULT_MELHOR_ENVIO_EMAIL = "entrega.broo@zohomail.com"
DEFAULT_BROOSTOCK_URL = "https://brootechstock.netlify.app/login"

# Política de retry do job (F1): 5 tentativas com espera crescente (segundos).
JOB_RETRY_MAX = 5
JOB_RETRY_INTERVALS = [60, 300, 900, 3600, 7200]

# Nome do job enfileirado POR STRING (jobs já na fila do Redis dependem dele).
JOB_NAME = "worker.process_mercado_pago_webhook"


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    secret_key_is_default: bool
    redis_url_raw: Optional[str]
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: Optional[str]
    mercadopago_access_token: Optional[str]
    webhook_secret: Optional[str]
    webhook_validate_signature: bool
    email_user: Optional[str]
    email_password: Optional[str]
    smtp_server: str
    smtp_port_raw: object  # str (env) ou int (padrão); converta com smtp_port() dentro de try
    resend_api_key: Optional[str]
    melhor_envio_url: str
    melhor_envio_token: str
    melhor_envio_email: str
    cep_origem: str
    admin_token: str
    broostock_url: str
    port: int
    dashboard_origin: Optional[str]
    cors_extra_origins: tuple = ()

    @property
    def redis_url(self) -> str:
        """REDIS_URL com o padrão do serviço web (o worker exige a variável)."""
        return self.redis_url_raw or DEFAULT_REDIS_URL

    def smtp_port(self) -> int:
        """Pode levantar ValueError (como ``int(os.environ.get(...))`` no original)."""
        return int(self.smtp_port_raw)


def normalize_db_url(url: Optional[str]) -> str:
    """Mesma normalização do original (psycopg3)."""
    url = url if url is not None else DEFAULT_DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def is_postgres(url: str) -> bool:
    return url.startswith("postgresql")


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in ("1", "true")


def _split_origins(value: Optional[str]) -> tuple:
    """CORS_EXTRA_ORIGINS: lista separada por virgula (barra final ignorada)."""
    return tuple(o.strip().rstrip("/") for o in (value or "").split(",") if o.strip())


def get_settings() -> Settings:
    env = os.environ
    secret_key = env.get("SECRET_KEY", DEFAULT_SECRET_KEY)
    return Settings(
        database_url=normalize_db_url(env.get("DATABASE_URL", DEFAULT_DATABASE_URL)),
        secret_key=secret_key,
        secret_key_is_default=("SECRET_KEY" not in env),
        redis_url_raw=env.get("REDIS_URL"),
        supabase_url=env.get("SUPABASE_URL", DEFAULT_SUPABASE_URL),
        supabase_anon_key=env.get("SUPABASE_ANON_KEY", DEFAULT_SUPABASE_ANON_KEY),
        supabase_service_role_key=env.get("SUPABASE_SERVICE_ROLE_KEY"),
        mercadopago_access_token=env.get("MERCADOPAGO_ACCESS_TOKEN"),
        webhook_secret=env.get("WEBHOOK_SECRET"),
        webhook_validate_signature=_truthy(env.get("WEBHOOK_VALIDATE_SIGNATURE")),
        email_user=env.get("EMAIL_USER"),
        email_password=env.get("EMAIL_PASSWORD"),
        smtp_server=env.get("SMTP_SERVER", DEFAULT_SMTP_SERVER),
        smtp_port_raw=env.get("SMTP_PORT", DEFAULT_SMTP_PORT),
        resend_api_key=env.get("RESEND_API_KEY"),
        melhor_envio_url=env.get("MELHOR_ENVIO_URL", DEFAULT_MELHOR_ENVIO_URL),
        melhor_envio_token=env.get("MELHOR_ENVIO_TOKEN", ""),
        melhor_envio_email=env.get("MELHOR_ENVIO_EMAIL", DEFAULT_MELHOR_ENVIO_EMAIL),
        cep_origem=env.get("CEP_ORIGEM", ""),
        admin_token=env.get("ADMIN_TOKEN", ""),
        broostock_url=env.get("BROOSTOCK_URL", DEFAULT_BROOSTOCK_URL),
        port=int(env.get("PORT", 5000)),
        dashboard_origin=env.get("DASHBOARD_ORIGIN") or None,
        cors_extra_origins=_split_origins(env.get("CORS_EXTRA_ORIGINS")),
    )


def build_engine_options(database_url: str, pool_recycle: int) -> dict:
    """Opções do engine SQLAlchemy.

    ``prepare_threshold=None`` desliga os prepared statements do psycopg3
    (compatível com pooler em modo "transaction"). Só existe no psycopg/Postgres,
    então só é aplicado quando a URL é PostgreSQL (SQLite quebraria).
    """
    options = {"pool_pre_ping": True, "pool_recycle": pool_recycle}
    if is_postgres(database_url):
        options["connect_args"] = {"prepare_threshold": None}
    return options


def build_flask_config(settings: Settings, role: str = "web") -> dict:
    """Config do Flask. O web recicla conexões a cada 3600s, o worker a cada 300s (como no original)."""
    pool_recycle = 300 if role == "worker" else 3600
    return {
        "SQLALCHEMY_DATABASE_URI": settings.database_url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": settings.secret_key,
        "SQLALCHEMY_ENGINE_OPTIONS": build_engine_options(settings.database_url, pool_recycle),
    }


def warn_if_default_secret(settings: Settings) -> None:
    if settings.secret_key_is_default:
        logger.warning(
            "[CONFIG] SECRET_KEY não definida: usando o valor padrão embutido no código. "
            "Defina SECRET_KEY no Render (Environment) para produção."
        )


_logging_configured = False


def configure_logging() -> None:
    """Logs em stdout com o texto puro da mensagem (igual aos ``print`` do original)."""
    global _logging_configured
    if _logging_configured:
        return
    _logging_configured = True
    log = logging.getLogger("broostore")
    if not log.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = True  # sem handlers no root em produção => sem duplicação; pytest/caplog funciona
