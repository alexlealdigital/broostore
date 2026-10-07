"""Blueprints (um por assunto) e registro no app."""
from . import (admin_dashboard, cobrancas, compressao, contato, cupons, frete,
               licencas, produtos, ranking, static_files, webhook)

# static_files por último: contém a rota coringa ``/<path:path>``.
_ORDEM = (produtos, licencas, cupons, cobrancas, webhook, contato, frete,
          ranking, compressao, admin_dashboard, static_files)


def register_blueprints(app):
    for modulo in _ORDEM:
        app.register_blueprint(modulo.bp)
