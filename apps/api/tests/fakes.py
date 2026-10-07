"""Dublês de teste: NENHUMA chamada real a Mercado Pago, Supabase, SMTP, Melhor Envio, Resend ou Redis."""
import copy
import re
import smtplib
from urllib.parse import parse_qs, urlparse

import requests

# ---------------------------------------------------------------------------
# Valores falsos de ambiente (nenhum segredo real)
# ---------------------------------------------------------------------------
FAKE_ENV = {
    "SECRET_KEY": "test-secret-key",
    "MERCADOPAGO_ACCESS_TOKEN": "TEST-fake-mp-token",
    "WEBHOOK_SECRET": "test-webhook-secret",
    "EMAIL_USER": "loja@example.test",
    "EMAIL_PASSWORD": "fake-email-password",
    "SMTP_SERVER": "smtp.example.test",
    "SMTP_PORT": "587",
    "RESEND_API_KEY": "re_fake_key",
    "SUPABASE_SERVICE_ROLE_KEY": "fake-service-role",
    "MELHOR_ENVIO_TOKEN": "fake-me-token",
    "CEP_ORIGEM": "01001-000",
    "ADMIN_TOKEN": "fake-admin-token",
}

ALL_ENV_VARS = [
    "DATABASE_URL", "SECRET_KEY", "REDIS_URL", "SUPABASE_URL", "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY", "MERCADOPAGO_ACCESS_TOKEN", "WEBHOOK_SECRET",
    "WEBHOOK_VALIDATE_SIGNATURE", "EMAIL_USER", "EMAIL_PASSWORD", "SMTP_SERVER", "SMTP_PORT",
    "RESEND_API_KEY", "MELHOR_ENVIO_URL", "MELHOR_ENVIO_TOKEN", "MELHOR_ENVIO_EMAIL", "CEP_ORIGEM",
    "ADMIN_TOKEN", "BROOSTOCK_URL", "PORT", "DASHBOARD_ORIGIN", "CORS_EXTRA_ORIGINS",
]


# ---------------------------------------------------------------------------
# HTTP (Supabase REST + Melhor Envio) — substitui requests.get / requests.post
# ---------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text or ("" if json_data is None else str(json_data))

    def json(self):
        if isinstance(self._json, Exception):
            raise self._json
        return copy.deepcopy(self._json)


def default_me_options():
    return [
        {"id": 1, "name": "PAC", "company": {"name": "Correios"}, "price": "25.50", "delivery_time": 8},
        {"id": 2, "name": "SEDEX", "company": {"name": "Correios"}, "price": "45.90", "delivery_time": 3},
        {"id": 3, "name": ".Package", "company": {"name": "Jadlog"}, "price": "31.00", "delivery_time": 5},
        {"id": 4, "name": "Indisponivel", "company": {"name": "X"}, "error": "Sem cobertura"},
    ]


class FakeHTTP:
    def __init__(self):
        self.reset()

    def reset(self):
        self.products = {}          # id -> linha completa da tabela products do Supabase
        self.supabase_down = False  # True => requests levanta ConnectionError
        self.sales_existing = set() # payment_ids já registrados no Supabase
        self.sales_posted = []
        self.sales_status = 201
        self.me_status = 200
        self.me_body = default_me_options()
        self.me_raises = None
        self.calls = []             # (metodo, url, kwargs)

    def add_product(self, id, title="Produto", price=10.0, link_pdf="https://dl.example.test/x", frete=0,
                    tipo="ebook", peso_kg=None, altura_cm=None, largura_cm=None, comprimento_cm=None):
        self.products[int(id)] = {
            "id": int(id), "title": title, "price": price, "link_pdf": link_pdf, "frete": frete, "tipo": tipo,
            "peso_kg": peso_kg, "altura_cm": altura_cm, "largura_cm": largura_cm, "comprimento_cm": comprimento_cm,
        }

    # -- requests.get ------------------------------------------------------
    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if self.supabase_down:
            raise requests.ConnectionError("supabase fora do ar (fake)")
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if parsed.path.endswith("/rest/v1/products"):
            pid = int(qs["id"][0].replace("eq.", ""))
            cols = qs.get("select", ["*"])[0].split(",")
            row = self.products.get(pid)
            rows = [{c: row.get(c) for c in cols}] if row else []
            return FakeResponse(200, rows)
        if parsed.path.endswith("/rest/v1/sales"):
            pay = qs["payment_id"][0].replace("eq.", "")
            return FakeResponse(200, [{"id": 1}] if pay in self.sales_existing else [])
        raise AssertionError(f"GET inesperado no teste: {url}")

    # -- requests.post -----------------------------------------------------
    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if url.endswith("/me/shipment/calculate"):
            if self.me_raises:
                raise self.me_raises
            return FakeResponse(self.me_status, self.me_body)
        if url.endswith("/rest/v1/sales"):
            self.sales_posted.append(kwargs.get("json"))
            return FakeResponse(self.sales_status, None, "ok")
        raise AssertionError(f"POST inesperado no teste: {url}")


# ---------------------------------------------------------------------------
# Mercado Pago SDK
# ---------------------------------------------------------------------------
class MPState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.created = []            # [(payment_data, request_options)]
        self.payments = {}           # str(id) -> response dict (para payment().get)
        self.pix_status = "pending"
        self.card_status = "approved"
        self.card_status_detail = "accredited"
        self.create_override = None  # resposta fixa para create()
        self.get_raises = None
        self.get_override = None
        self.tokens = []
        self.next_id = 1000

    def set_payment(self, payment_id, status, external_reference):
        self.payments[str(payment_id)] = {
            "id": payment_id, "status": status, "external_reference": external_reference,
        }


class FakePayment:
    def __init__(self, state):
        self.state = state

    def create(self, data, request_options=None):
        st = self.state
        st.created.append((copy.deepcopy(data), request_options))
        if st.create_override is not None:
            return copy.deepcopy(st.create_override)
        st.next_id += 1
        pid = st.next_id
        if data.get("payment_method_id") == "pix":
            status = st.pix_status
            body = {"id": pid, "status": status,
                    "point_of_interaction": {"transaction_data": {
                        "qr_code": "00020126FAKEPIX", "qr_code_base64": "QkFTRTY0RkFLRQ=="}}}
        else:
            status = st.card_status
            body = {"id": pid, "status": status, "status_detail": st.card_status_detail}
        st.payments[str(pid)] = {"id": pid, "status": status, "external_reference": data.get("external_reference")}
        return {"status": 201, "response": body}

    def get(self, payment_id):
        if self.state.get_raises:
            raise self.state.get_raises
        if self.state.get_override is not None:
            return copy.deepcopy(self.state.get_override)
        found = self.state.payments.get(str(payment_id))
        if not found:
            return {"status": 404, "response": {"message": "Payment not found"}}
        return {"status": 200, "response": copy.deepcopy(found)}


def make_fake_sdk(state):
    class FakeSDK:
        def __init__(self, access_token=None, *args, **kwargs):
            state.tokens.append(access_token)

        def payment(self):
            return FakePayment(state)
    return FakeSDK


# ---------------------------------------------------------------------------
# SMTP
# ---------------------------------------------------------------------------
class SMTPState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.sent = []          # mensagens capturadas
        self.connections = []   # (tipo, host, port, timeout)
        self.logins = []
        self.starttls_calls = 0
        self.fail_login = False
        self.fail_connect = False
        self.fail_times = 0     # falha N vezes e depois funciona

    def messages(self):
        out = []
        for m in self.sent:
            payload = m.get_payload()[0].get_payload(decode=True).decode("utf-8")
            out.append({"subject": str(m["Subject"]), "to": str(m["To"]), "from": str(m["From"]), "html": payload})
        return out


def make_fake_smtp_classes(state):
    class FakeSMTP:
        kind = "SMTP"

        def __init__(self, host, port=0, timeout=None, **kwargs):
            if state.fail_connect:
                raise smtplib.SMTPConnectError(421, "servidor SMTP fora do ar (fake)")
            state.connections.append((self.kind, host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self, *a, **k):
            state.starttls_calls += 1

        def login(self, user, password):
            if state.fail_login:
                raise smtplib.SMTPAuthenticationError(535, b"credenciais invalidas (fake)")
            if state.fail_times > 0:
                state.fail_times -= 1
                raise smtplib.SMTPServerDisconnected("queda temporaria (fake)")
            state.logins.append(user)

        def send_message(self, msg, *a, **k):
            state.sent.append(msg)

    class FakeSMTP_SSL(FakeSMTP):
        kind = "SMTP_SSL"

    return FakeSMTP, FakeSMTP_SSL


# ---------------------------------------------------------------------------
# Fila RQ
# ---------------------------------------------------------------------------
class FakeQueue:
    """Captura ``enqueue(job_name, payment_id, retry=...)``; pode rodar os jobs inline."""

    def __init__(self):
        self.jobs = []
        self.fail_with = None

    def enqueue(self, job, *args, **kwargs):
        if self.fail_with:
            raise self.fail_with
        self.jobs.append((job, args, kwargs))
        return object()

    def run_all(self):
        """Executa inline os jobs pendentes importando o job PELO NOME (como o RQ faz)."""
        import importlib
        pending, self.jobs = self.jobs, []
        for job, args, _kwargs in pending:
            module_name, func_name = job.rsplit(".", 1)
            getattr(importlib.import_module(module_name), func_name)(*args)


class World:
    """Agrupa todos os dublês de um teste."""

    def __init__(self, http, mp, smtp, queue, resend_calls):
        self.http = http
        self.mp = mp
        self.smtp = smtp
        self.queue = queue
        self.resend = resend_calls  # dict: calls (lista), response, raises


UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
