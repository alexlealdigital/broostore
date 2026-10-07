# seed_chave_broostock.py
# ---------------------------------------------------------------------------
# No repositório original este arquivo era uma CÓPIA EXATA de seed_planos_broostock.py
# (mesmo conteúdo, mesmo efeito). Foi mantido por compatibilidade: executa o mesmo seed.
#     python scripts/seed_chave_broostock.py
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

# Permite executar de qualquer pasta (``python scripts/x.py``): põe apps/api no sys.path.
_RAIZ = str(Path(__file__).resolve().parent.parent)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from scripts.seed_planos_broostock import main  # noqa: E402

if __name__ == "__main__":
    main()
