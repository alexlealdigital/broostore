# sincronizar_licencas_app.py
# ---------------------------------------------------------------------------
# Carga inicial: envia TODAS as licenças de UM app (trial e pagas) do banco da
# BrooStore para a tabela `licenses` do Supabase DAQUELE app.
#
# Rode UMA vez por app, antes do passo "exigir licença" (RLS) desse app, e
# quando quiser conferir. É idempotente — pode rodar de novo sem duplicar nada.
#
# Onde: painel do Render, aba "Shell" do serviço, a partir de apps/api:
#     python scripts/sincronizar_licencas_app.py            # app padrão: broostock
#     python scripts/sincronizar_licencas_app.py meuapp     # outro app
# Pré-requisito: <APP>_SUPABASE_URL e <APP>_SUPABASE_SERVICE_KEY configuradas
# nesse serviço (ex.: BROOSTOCK_SUPABASE_URL / BROOSTOCK_SUPABASE_SERVICE_KEY).
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

# Permite executar de qualquer pasta (``python scripts/x.py``): põe apps/api no sys.path.
_RAIZ = str(Path(__file__).resolve().parent.parent)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from datetime import datetime

from broostore_api import apps_config, create_app
from broostore_api.models import Licenca
from broostore_api.services.sync_licencas import config_do_app, sincronizar_licenca


def main(slug=None, app=None):
    """Devolve (total, enviadas, vencidas, falhas). Levanta SystemExit se faltar configuração."""
    slug = apps_config.normalizar_slug(slug)
    if not apps_config.obter_app(slug):
        raise SystemExit(f"App '{slug}' não está em apps_config.APPS. Cadastre-o antes.")
    if not config_do_app(slug)[0]:
        raise SystemExit(f"Configure {slug.upper()}_SUPABASE_URL e {slug.upper()}_SUPABASE_SERVICE_KEY no Render antes.")

    app = app or create_app(role="worker")
    with app.app_context():
        agora = datetime.utcnow()
        todas = Licenca.query.filter_by(app_slug=slug).all()
        ok = falhas = vencidas = 0
        for lic in todas:
            vigente = bool(lic.status in ("ativa", "trial") and lic.expira_em and lic.expira_em > agora)
            if not vigente:
                vencidas += 1
            # licenças vencidas também sobem (ativa=False), para o painel refletir a realidade
            if sincronizar_licenca(slug, lic.cliente_email, lic.expira_em, lic.plano,
                                   is_trial=(lic.status == "trial"), ativa=vigente):
                ok += 1
            else:
                falhas += 1
        print("====================================================")
        print(f"  App                            : {slug}")
        print(f"  Licenças no banco da BrooStore : {len(todas)}")
        print(f"  Enviadas ao Supabase do app    : {ok}")
        print(f"  Já vencidas/inativas (ativa=F) : {vencidas}")
        print(f"  Falhas                         : {falhas}")
        print("====================================================")
        if falhas:
            raise SystemExit("Houve falhas — NÃO rode o passo de RLS ainda. Veja os logs acima.")
        return len(todas), ok, vencidas, falhas


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
