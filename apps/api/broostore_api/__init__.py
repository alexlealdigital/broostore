"""API de pagamentos/licenças da BrooStore (Flask + SQLAlchemy + RQ).

Uso:
    from broostore_api import create_app
    app = create_app()
"""
from importlib import import_module

from flask import Flask

from .config import (CORS_ALLOW_HEADERS, CORS_METHODS, CORS_ORIGINS, STATIC_DIR,
                     build_engine_options, build_flask_config, configure_logging,
                     get_settings, warn_if_default_secret)
from .extensions import cors, db

__all__ = ["create_app"]


def create_app(config_overrides=None, role="web"):
    """Fábrica do app.

    ``role="web"``: API completa (CORS + rotas), usada pelo gunicorn.
    ``role="worker"``: só banco/modelos (usada pelo job RQ e pelos scripts/cron);
    reciclagem de conexões a cada 300s, como no worker original.
    ``config_overrides``: dict aplicado sobre a config (testes).
    """
    configure_logging()
    settings = get_settings()

    app = Flask("broostore_api", static_folder=str(STATIC_DIR))
    config = build_flask_config(settings, role)
    if config_overrides:
        config.update(config_overrides)
        if "SQLALCHEMY_ENGINE_OPTIONS" not in config_overrides:
            pool_recycle = 300 if role == "worker" else 3600
            config["SQLALCHEMY_ENGINE_OPTIONS"] = build_engine_options(
                config["SQLALCHEMY_DATABASE_URI"], pool_recycle)
    app.config.update(config)

    if role == "web":
        warn_if_default_secret(settings)

    db.init_app(app)

    if role == "web":
        origins = list(CORS_ORIGINS)
        allow_headers = list(CORS_ALLOW_HEADERS)
        # Opcional: dominios proprios do frontend (ex.: https://www.broostore.com.br)
        origins.extend(o for o in settings.cors_extra_origins if o not in origins)
        if settings.dashboard_origin:
            # Opcional (padrão desligado): libera o painel financeiro em outra origem.
            origins.append(settings.dashboard_origin)
            allow_headers.append("X-Admin-Token")
        cors.init_app(
            app,
            origins=origins,
            methods=CORS_METHODS,
            allow_headers=allow_headers,
            supports_credentials=False,
        )
        from .blueprints import register_blueprints
        register_blueprints(app)

    # Criação das tabelas (como no original; sem framework de migração)
    import_module(".models", __package__)  # registra os modelos no metadata
    with app.app_context():
        db.create_all()

    return app
