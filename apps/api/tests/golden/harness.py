"""Infraestrutura da comparação GOLDEN: carrega o código ORIGINAL (com um único patch para rodar em
SQLite) e executa as mesmas requisições contra ele e contra a API nova, com os mesmos dublês."""
import importlib.util
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text

from tests.fakes import UUID_RE

ORIGINAL_DIR = Path(__file__).resolve().parent / "original"
STATIC_SRC = Path(__file__).resolve().parents[2] / "static"

PATCH_APP = ('    "connect_args": {"prepare_threshold": None},\n', "")
PATCH_WORKER = (', "connect_args": {"prepare_threshold": None}}', "}")

TMP_RE = re.compile(r"/tmp/tmp\w+")
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?")
VOLATILE_KEYS = {"data_criacao", "expira_em", "gerado_em", "inicia_em", "ultimo_pagamento_em", "criado_em",
                 "vendida_em", "created_at", "data"}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _patched_copy(src_name, patch, dest):
    src = (ORIGINAL_DIR / src_name).read_text(encoding="utf-8")
    old, new = patch
    assert old in src, f"patch não encontrado em {src_name}"
    dest.write_text(src.replace(old, new, 1), encoding="utf-8")


class Original:
    """O app.py + worker.py + Dashboard_api.py originais rodando em SQLite temporário."""

    def __init__(self, tmp_path, monkeypatch):
        self.dir = tmp_path / "original"
        self.dir.mkdir()
        shutil.copytree(STATIC_SRC, self.dir / "static")
        self.db_url = f"sqlite:///{self.dir / 'orig.db'}"
        monkeypatch.setenv("DATABASE_URL", self.db_url)
        _patched_copy("app.py", PATCH_APP, self.dir / "orig_app.py")
        _patched_copy("worker.py", PATCH_WORKER, self.dir / "orig_worker.py")
        shutil.copy(ORIGINAL_DIR / "Dashboard_api.py", self.dir / "orig_dashboard.py")
        self.app_module = _load("orig_app", self.dir / "orig_app.py")
        self.worker_module = _load("orig_worker", self.dir / "orig_worker.py")
        self.dashboard_module = _load("orig_dashboard", self.dir / "orig_dashboard.py")
        # o blueprint do painel nunca foi registrado no app.py original: registramos só para comparar
        self.dashboard_module._engine = create_engine(self.db_url)
        self.app_module.app.register_blueprint(self.dashboard_module.dashboard_bp)
        self.app = self.app_module.app
        self.db = self.app_module.db
        self.client = self.app.test_client()

    def attach_queue(self, queue, monkeypatch):
        import rq
        self.app_module.q = queue
        monkeypatch.setattr(rq, "Queue", lambda connection=None, **kw: queue)

    def run_job(self, payment_id):
        return self.worker_module.process_mercado_pago_webhook(payment_id)

    def close(self):
        for name in ("orig_app", "orig_worker", "orig_dashboard"):
            sys.modules.pop(name, None)
        with self.app.app_context():
            self.db.session.remove()
            self.db.engine.dispose()
        with self.worker_module.app.app_context():
            self.worker_module.db.session.remove()
            self.worker_module.db.engine.dispose()
        self.dashboard_module._engine.dispose()


# ---------------------------------------------------------------------------
# Normalização e registro
# ---------------------------------------------------------------------------
def _sem_marca_de_idempotencia(raw):
    """A API nova acrescenta a chave 'licenca_aplicada' em cobrancas.observacoes (idempotência do retry, F1)."""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data.pop("licenca_aplicada", None)
            return json.dumps(data, sort_keys=True) if data else None
    except Exception:
        pass
    return raw


def norm(obj):
    if isinstance(obj, dict):
        return {k: ("<volatil>" if k in VOLATILE_KEYS and v is not None
                    else _sem_marca_de_idempotencia(v) if k == "observacoes" and isinstance(v, str)
                    else norm(v)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [norm(v) for v in obj]
    if isinstance(obj, datetime):
        return "<ts>"
    if isinstance(obj, str):
        return TMP_RE.sub("<tmp>", ISO_RE.sub("<ts>", UUID_RE.sub("<uuid>", obj)))
    return obj


class Side:
    """Um lado da comparação (original ou novo): cliente HTTP, dublês, e o log de tudo que aconteceu."""

    def __init__(self, name, app, db, client, world):
        self.name, self.app, self.db, self.client, self.world = name, app, db, client, world
        self.log = []

    def reset_world(self):
        w = self.world
        w.http.reset()
        w.mp.reset()
        w.smtp.reset()
        w.queue.jobs = []
        w.queue.fail_with = None
        w.resend["calls"].clear()
        w.resend["response"] = {"id": "email_fake_id"}
        w.resend["raises"] = None

    def req(self, label, method, url, **kw):
        r = getattr(self.client, method)(url, **kw)
        ctype = r.mimetype
        if ctype == "application/json":
            body = norm(r.get_json())
        elif ctype in ("application/pdf", "image/jpeg"):
            body = f"<{ctype} bytes>"
        else:
            body = f"<{ctype} len={len(r.data)}>"
        r.close()
        self.log.append((label, r.status_code, ctype, body))
        return r

    def execute(self, sql, **params):
        with self.app.app_context():
            self.db.session.execute(text(sql), params)
            self.db.session.commit()

    def rows(self, sql, **params):
        with self.app.app_context():
            result = self.db.session.execute(text(sql), params)
            data = [dict(r._mapping) for r in result]
            self.db.session.rollback()
            return norm(data)

    def snapshot(self, *tables):
        """Anexa ao log o conteúdo (normalizado) das tabelas e todos os efeitos colaterais dos dublês."""
        for t in tables:
            self.log.append((f"db:{t}", self.rows(f"SELECT * FROM {t} ORDER BY 1")))
        w = self.world
        self.log.append(("mp.created", norm([data for data, _ in w.mp.created])))
        self.log.append(("smtp", norm([{k: v for k, v in m.items()} for m in w.smtp.messages()]),
                         [c[:3] for c in w.smtp.connections]))
        self.log.append(("queue", [(j, a) for j, a, _ in w.queue.jobs]))
        self.log.append(("resend", norm(w.resend["calls"])))
        self.log.append(("http", norm([(m, u, {k: v for k, v in kw.items() if k != "headers"}) for m, u, kw in w.http.calls])))
        self.log.append(("sales_posted", w.http.sales_posted))


def _first_diff(x, y, path="item"):
    """Desce até o primeiro ponto em que os dois valores divergem (mensagem de erro legível)."""
    if isinstance(x, (list, tuple)) and isinstance(y, (list, tuple)) and len(x) == len(y):
        for i, (a, b) in enumerate(zip(x, y)):
            if a != b:
                return _first_diff(a, b, f"{path}[{i}]")
    if isinstance(x, dict) and isinstance(y, dict) and x.keys() == y.keys():
        for k in x:
            if x[k] != y[k]:
                return _first_diff(x[k], y[k], f"{path}.{k}")
    return path, x, y


_COSMETICO_BOTAO = (("[·] Baixar", "📥 Baixar"), ("[·] Ir para", "🗜️ Ir para"))


def _normaliza_cosmetico(x):
    """Diferenças ESTÉTICAS intencionais do e-mail (ver CHANGELOG-API): botão sem '[·]' e valor
    com vírgula (R$ 1,00). O original é normalizado para o formato novo; todo o resto é comparado igual."""
    import re
    if isinstance(x, str):
        for velho, novo in _COSMETICO_BOTAO:
            x = x.replace(velho, novo)
        return re.sub(r"(?<=<strong>)R\$ (\d+)\.(\d{2})(?=</strong>)",
                      lambda m: f"R$ {int(m.group(1)):,}".replace(",", ".") + "," + m.group(2), x)
    if isinstance(x, (list, tuple)):
        return type(x)(_normaliza_cosmetico(i) for i in x)
    if isinstance(x, dict):
        return {k: _normaliza_cosmetico(v) for k, v in x.items()}
    return x


def assert_same(original: Side, novo: Side):
    a, b = _normaliza_cosmetico(original.log), novo.log
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            path, vx, vy = _first_diff(x, y, f"log[{i}] {x[0] if x else ''}")
            raise AssertionError(f"DIFERENÇA em {path}:\n  ORIGINAL: {json.dumps(vx, ensure_ascii=False, default=str)[:1200]}\n"
                                 f"  NOVO    : {json.dumps(vy, ensure_ascii=False, default=str)[:1200]}")
    assert len(a) == len(b), f"tamanhos diferentes: original={len(a)} novo={len(b)}"
