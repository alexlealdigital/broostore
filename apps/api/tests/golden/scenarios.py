"""Sequências de requisições executadas IDÊNTICAS contra o original e contra a API nova."""
import io
import json
from datetime import date, datetime, timedelta

import pikepdf
from PIL import Image


# ---------------------------------------------------------------------------
# Dados iniciais (SQL puro, igual nos dois bancos)
# ---------------------------------------------------------------------------
def seed(s):
    now = datetime.utcnow()
    for pid, nome, preco, link, tipo in [
        (1, "E-book Um", 50.0, "https://dl/ebook1", "ebook"),
        (2, "Livro Impresso", 60.0, "", "fisico"),
        (3, "Jogo X", 80.0, "https://dl/jogo", "game"),
        (4, "App Y", 90.0, "https://dl/app", "app"),
        (7, "Moedas", 5.0, "", "ebook"),
        (10, "BrooStock Mensal", 129.9, "", "assinatura"),
        (11, "BrooStock Sem Plano", 10.0, "", "assinatura"),
        (99, "Compressão de PDF", 3.0, "", "ebook"),
        (98, "Compressão de Imagem", 3.0, "", "ebook"),
    ]:
        s.execute("INSERT INTO produtos (id,nome,preco,link_download,tipo) VALUES (:a,:b,:c,:d,:e)",
                  a=pid, b=nome, c=preco, d=link, e=tipo)
    s.execute("INSERT INTO planos_assinatura (produto_id,dias,rotulo) VALUES (10,30,'mensal')")
    for cod, nome in (("V1", "Vendedor Um"), ("V2", "Vendedor Dois"), ("V3", "Vendedor Tres")):
        s.execute("INSERT INTO vendedores (codigo_ranking,nome_vendedor) VALUES (:c,:n)", c=cod, n=nome)
    hoje = date.today()
    cupons = [
        (1, "PROMO10", "percentual", 10.0, None, hoje - timedelta(days=1), None, None, 0, True),
        (2, "FIXO5", "valor_fixo", 5.0, None, hoje - timedelta(days=1), None, None, 0, True),
        (3, "VELHO", "percentual", 50.0, None, hoje - timedelta(days=10), hoje - timedelta(days=1), None, 0, True),
        (4, "SOP3", "percentual", 20.0, 3, hoje - timedelta(days=1), None, None, 0, True),
        (5, "LIMITE", "percentual", 20.0, None, hoje - timedelta(days=1), None, 1, 1, True),
        (6, "OFF", "percentual", 20.0, None, hoje - timedelta(days=1), None, None, 0, False),
        (7, "FUTURO", "percentual", 20.0, None, hoje + timedelta(days=3), None, None, 0, True),
    ]
    for cid, cod, tipo, valor, prod, de, ate, umax, uat, ativo in cupons:
        s.execute("INSERT INTO cupons (id,codigo,tipo,valor,produto_id,valido_de,valido_ate,usos_maximos,usos_atuais,ativo,criado_em)"
                  " VALUES (:i,:c,:t,:v,:p,:de,:ate,:um,:ua,:a,:ce)",
                  i=cid, c=cod, t=tipo, v=valor, p=prod, de=de, ate=ate, um=umax, ua=uat, a=ativo, ce=now)
    for email, status, delta, plano in [("ativa@example.test", "ativa", 12, "mensal"),
                                        ("expirada@example.test", "ativa", -5, "mensal"),
                                        ("trial@example.test", "trial", 3, "trial")]:
        s.execute("INSERT INTO licencas (cliente_email,plano,status,inicia_em,expira_em,ultimo_pagamento_em)"
                  " VALUES (:e,:p,:s,:i,:x,:u)", e=email, p=plano, s=status, i=now, x=now + timedelta(days=delta, hours=1), u=now)
    # cobranças já existentes (ranking / compressão / dashboard)
    n = 0
    for ref, prod, status, valor, vend, obs in [
        ("ent-1", 1, "delivered", 50.0, "V1", None), ("ent-2", 1, "delivered", 50.0, "V1", None),
        ("ent-3", 3, "delivered", 80.0, "V2", None), ("pend-1", 1, "pending", 50.0, "V3", None),
        ("pdf-ok", 99, "approved", 3.0, None, None), ("pdf-entregue", 99, "delivered", 3.0, None, None),
        ("pdf-pend", 99, "pending", 3.0, None, None), ("img-ok", 98, "approved", 3.0, None, None),
        ("fis-1", 2, "delivered", 85.5, None, json.dumps({"endereco": {"cidade": "SP"}, "frete": 25.5,
                                                          "subtotal_produto": 60.0, "transportadora": "Correios PAC"})),
    ]:
        n += 1
        s.execute("INSERT INTO cobrancas (id,external_reference,cliente_nome,cliente_email,valor,valor_original,status,data_criacao,"
                  "product_id,vendedor_codigo,observacoes) VALUES (:i,:r,'Cli','c@example.test',:v,:v,:s,:d,:p,:vend,:o)",
                  i=n, r=ref, v=valor, s=status, d=now - timedelta(days=1), p=prod, vend=vend, o=obs)


def sb_produtos(s):
    s.world.http.add_product(1, title="E-book Um", price=50.0, link_pdf="https://dl/ebook1", tipo="ebook")
    s.world.http.add_product(2, title="Livro Impresso", price=60.0, link_pdf="", tipo="fisico", frete=20.0,
                             peso_kg=0.5, altura_cm=3, largura_cm=15, comprimento_cm=21)
    s.world.http.add_product(3, title="Jogo X", price=80.0, link_pdf="https://dl/jogo", tipo="game")
    s.world.http.add_product(7, title="Moedas", price=5.0, tipo="ebook")
    s.world.http.add_product(50, title="Produto Só no Supabase", price=15.0, link_pdf="https://x", tipo="ebook")
    s.world.http.add_product(51, title="Camiseta", price=100.0, tipo="fisico", frete=15.0,
                             peso_kg=0.3, altura_cm=2, largura_cm=20, comprimento_cm=30)
    s.world.http.add_product(52, title="Sem Medidas", price=10.0, tipo="fisico", peso_kg=0.3)


# ---------------------------------------------------------------------------
# Cenários
# ---------------------------------------------------------------------------
def licencas(s, mp):
    s.req("status sem email", "get", "/api/licenca/status")
    s.req("status desconhecido", "get", "/api/licenca/status?email=nunca@example.test")
    s.req("status ativa", "get", "/api/licenca/status?email=ATIVA@example.test")
    s.req("status expirada", "get", "/api/licenca/status?email=expirada@example.test")
    s.req("status trial", "get", "/api/licenca/status?email=trial@example.test")
    s.req("trial sem email", "post", "/api/licenca/trial", json={})
    s.req("trial novo", "post", "/api/licenca/trial", json={"email": " Novo@Example.test "})
    s.req("trial repetido 409", "post", "/api/licenca/trial", json={"email": "novo@example.test"})
    s.req("trial de quem já tem licença", "post", "/api/licenca/trial", json={"email": "ativa@example.test"})
    s.req("trial via query", "post", "/api/licenca/trial?email=query@example.test")
    s.req("status pós-trial", "get", "/api/licenca/status?email=novo@example.test")
    s.world.smtp.fail_connect = True
    s.req("trial com SMTP fora", "post", "/api/licenca/trial", json={"email": "smtpfora@example.test"})
    s.snapshot("licencas")


def produto_sync_cupom(s, mp):
    sb_produtos(s)
    s.req("produto 1", "get", "/api/produto/1")
    s.req("produto 404", "get", "/api/produto/12345")
    s.req("sync sem id", "post", "/api/sync-produto", json={})
    s.req("sync inexistente", "post", "/api/sync-produto", json={"product_id": 4040})
    s.req("sync cria 50", "post", "/api/sync-produto", json={"product_id": 50})
    s.req("sync atualiza 1", "post", "/api/sync-produto", json={"product_id": 1})
    s.req("produto 50", "get", "/api/produto/50")
    for label, body in [
        ("cupom pct", {"codigo": " promo10", "produto_id": 1, "valor_original": 50}),
        ("cupom fixo", {"codigo": "fixo5", "produto_id": 1, "valor_original": 3}),
        ("cupom sem codigo", {"codigo": "", "produto_id": 1, "valor_original": 50}),
        ("cupom sem produto", {"codigo": "promo10"}),
        ("cupom inexistente", {"codigo": "naoexiste", "produto_id": 1, "valor_original": 50}),
        ("cupom expirado", {"codigo": "velho", "produto_id": 1, "valor_original": 50}),
        ("cupom outro produto", {"codigo": "sop3", "produto_id": 1, "valor_original": 50}),
        ("cupom produto certo", {"codigo": "sop3", "produto_id": 3, "valor_original": 80}),
        ("cupom limite", {"codigo": "limite", "produto_id": 1, "valor_original": 50}),
        ("cupom inativo", {"codigo": "off", "produto_id": 1, "valor_original": 50}),
        ("cupom futuro", {"codigo": "futuro", "produto_id": 1, "valor_original": 50}),
        ("cupom valor invalido", {"codigo": "promo10", "produto_id": 1, "valor_original": "abc"}),
    ]:
        s.req(label, "post", "/api/validar-cupom", json=body)
    s.snapshot("produtos", "cupons")


def cobranca_pix(s, mp):
    sb_produtos(s)
    base = {"email": "cli@example.test", "nome": "Maria Silva", "product_id": 1}
    s.req("pix vazio", "post", "/api/cobrancas", json={})
    s.req("pix sem produto", "post", "/api/cobrancas", json={"email": "a@b.c"})
    s.req("pix email invalido", "post", "/api/cobrancas", json={**base, "email": "semarroba"})
    s.req("pix telefone invalido", "post", "/api/cobrancas", json={**base, "telefone": "123"})
    s.req("pix digital", "post", "/api/cobrancas", json=base)
    s.req("pix cupom+vendedor", "post", "/api/cobrancas", json={**base, "cupom_id": 1, "vendedor_codigo": "V1", "telefone": "(11) 98888-7777"})
    s.req("pix cupom fixo", "post", "/api/cobrancas", json={**base, "cupom_id": 2})
    s.req("pix cupom inativo (aparece mesmo assim)", "post", "/api/cobrancas", json={**base, "cupom_id": 6})
    s.req("pix cupom outro produto", "post", "/api/cobrancas", json={**base, "cupom_id": 4})
    s.req("pix cupom inexistente", "post", "/api/cobrancas", json={**base, "cupom_id": 999})
    s.req("pix vendedor invalido", "post", "/api/cobrancas", json={**base, "vendedor_codigo": "NAO"})
    s.req("pix moedas usuario", "post", "/api/cobrancas", json={**base, "product_id": 7, "usuario_id": "user-9"})
    s.req("pix produto 1 com usuario_id", "post", "/api/cobrancas", json={**base, "usuario_id": "user-9"})
    s.req("pix fisico com servico", "post", "/api/cobrancas", json={**base, "product_id": 2, "frete_servico_id": 2,
                                                                   "endereco": {"cep": "01310-100", "rua": "Av Paulista", "numero": "1"}})
    s.req("pix fisico sem servico", "post", "/api/cobrancas", json={**base, "product_id": 2})
    s.req("pix fisico servico inexistente", "post", "/api/cobrancas", json={**base, "product_id": 2, "frete_servico_id": 99, "cep_destino": "01310100"})
    s.req("pix fisico cotacao 401", "post", "/api/cobrancas", json={**base, "product_id": 2, "frete_servico_id": 1, "cep_destino": "01310100"})
    s.req("pix produto novo do supabase", "post", "/api/cobrancas", json={**base, "product_id": 50})
    s.req("pix produto inexistente", "post", "/api/cobrancas", json={**base, "product_id": 4040})
    s.req("pix product_id invalido", "post", "/api/cobrancas", json={**base, "product_id": "abc"})
    s.world.mp.create_override = {"status": 400, "response": {"message": "invalid amount"}}
    s.req("pix erro MP", "post", "/api/cobrancas", json=base)
    s.world.mp.create_override = None
    mp.delenv("MERCADOPAGO_ACCESS_TOKEN")
    s.req("pix sem token", "post", "/api/cobrancas", json=base)
    mp.setenv("MERCADOPAGO_ACCESS_TOKEN", "TEST-fake-mp-token")
    s.world.http.supabase_down = True
    s.req("pix supabase fora (produto local)", "post", "/api/cobrancas", json=base)
    s.req("pix supabase fora fisico local 503", "post", "/api/cobrancas", json={**base, "product_id": 2})
    s.snapshot("cobrancas", "cupons", "produtos")


def cobranca_cartao(s, mp):
    sb_produtos(s)
    base = {"token": "tok_card", "payment_method_id": "visa", "installments": 3, "email": "cli@example.test",
            "nome": "Maria da Silva Souza", "cpf": "123.456.789-00", "product_id": 1}
    s.req("cartao vazio", "post", "/api/cobrancas-cartao", json={})
    s.req("cartao sem token", "post", "/api/cobrancas-cartao", json={**base, "token": ""})
    s.req("cartao email invalido", "post", "/api/cobrancas-cartao", json={**base, "email": "x"})
    s.req("cartao sem produto", "post", "/api/cobrancas-cartao", json={**base, "product_id": None})
    s.req("cartao aprovado", "post", "/api/cobrancas-cartao", json={**base, "issuer_id": "24"})
    s.world.mp.card_status, s.world.mp.card_status_detail = "rejected", "cc_rejected_insufficient_amount"
    s.req("cartao rejeitado", "post", "/api/cobrancas-cartao", json=base)
    s.world.mp.card_status, s.world.mp.card_status_detail = "in_process", "pending_contingency"
    s.req("cartao em analise", "post", "/api/cobrancas-cartao", json=base)
    s.world.mp.card_status, s.world.mp.card_status_detail = "approved", "accredited"
    s.req("cartao com cupom", "post", "/api/cobrancas-cartao", json={**base, "cupom_id": 1})
    s.req("cartao fisico com frete", "post", "/api/cobrancas-cartao", json={**base, "product_id": 51, "cupom_id": 2, "frete_servico_id": 1,
                                                                           "endereco": {"cep": "01001000", "cidade": "SP"}})
    s.req("cartao nome unico", "post", "/api/cobrancas-cartao", json={**base, "nome": "Maria"})
    s.req("cartao produto inexistente", "post", "/api/cobrancas-cartao", json={**base, "product_id": 4040})
    s.world.mp.create_override = {"status": 400, "response": {"message": "cc_rejected_bad_filled_card_number"}}
    s.req("cartao erro MP", "post", "/api/cobrancas-cartao", json=base)
    s.world.mp.create_override = {"status": 500, "response": {"x": 1}}
    s.req("cartao erro MP corpo", "post", "/api/cobrancas-cartao", json=base)
    s.world.mp.create_override = None
    mp.delenv("MERCADOPAGO_ACCESS_TOKEN")
    s.req("cartao sem token MP", "post", "/api/cobrancas-cartao", json=base)
    s.snapshot("cobrancas", "cupons")


def contato(s, mp):
    body = {"nome": "Ana", "email": "ana@example.test", "assunto": "Dúvida", "mensagem": "Olá!"}
    s.req("contato ok", "post", "/api/contato", json=body)
    s.req("contato campo faltando", "post", "/api/contato", json={**body, "assunto": ""})
    s.world.resend["response"] = {}
    s.req("contato sem id", "post", "/api/contato", json=body)
    s.world.resend["response"] = {"id": "x"}
    s.world.resend["raises"] = RuntimeError("resend caiu")
    s.req("contato excecao", "post", "/api/contato", json=body)
    s.world.resend["raises"] = None
    mp.delenv("RESEND_API_KEY")
    s.req("contato sem api key", "post", "/api/contato", json=body)
    s.snapshot()


def cotar_frete(s, mp):
    sb_produtos(s)
    s.req("frete sem cep", "post", "/api/cotar-frete", json={"product_id": 51})
    s.req("frete sem produto", "post", "/api/cotar-frete", json={"cep": "01001000"})
    s.req("frete produto inexistente", "post", "/api/cotar-frete", json={"cep": "01001000", "product_id": 4040})
    s.req("frete nao fisico", "post", "/api/cotar-frete", json={"cep": "01001000", "product_id": 1})
    s.req("frete sem medidas", "post", "/api/cotar-frete", json={"cep": "01001000", "product_id": 52})
    s.req("frete ok", "post", "/api/cotar-frete", json={"cep_destino": "01001-000", "product_id": 51})
    s.req("frete cep invalido", "post", "/api/cotar-frete", json={"cep": "123", "product_id": 51})
    for status in (401, 403, 500):
        s.world.http.me_status = status
        s.req(f"frete ME {status}", "post", "/api/cotar-frete", json={"cep": "01001000", "product_id": 51})
    s.world.http.me_status = 200
    s.world.http.me_raises = ConnectionError("timeout")
    s.req("frete ME excecao", "post", "/api/cotar-frete", json={"cep": "01001000", "product_id": 51})
    s.world.http.me_raises = None
    s.world.http.me_body = [{"id": 9, "name": "X", "error": "indisponível"}]
    s.req("frete nenhuma transportadora", "post", "/api/cotar-frete", json={"cep": "01001000", "product_id": 51})
    s.world.http.me_body = [{"id": i, "name": f"S{i}", "company": {"name": "E"}, "price": str(10 + i * 3), "delivery_time": 10 - i} for i in range(7)]
    s.req("frete muitas opcoes", "post", "/api/cotar-frete", json={"cep": "01001000", "product_id": 51})
    s.world.http.supabase_down = True
    s.req("frete supabase fora", "post", "/api/cotar-frete", json={"cep": "01001000", "product_id": 51})
    # (MELHOR_ENVIO_TOKEN ausente não entra aqui: o original lê essa variável no import do módulo,
    #  a API nova a lê a cada chamada; em produção a variável já existe no boot, então é equivalente.
    #  O caso "sem token" é coberto em tests/test_frete.py.)
    s.snapshot()


def ranking_vendedores(s, mp):
    s.req("vendedores", "get", "/api/vendedores")
    s.req("ranking", "get", "/api/ranking")
    s.snapshot()


def webhook(s, mp):
    s.req("webhook ok", "post", "/api/webhook", json={"type": "payment", "data": {"id": "123"}})
    s.req("webhook sem id", "post", "/api/webhook", json={"data": {}})
    s.req("webhook id numerico", "post", "/api/webhook", json={"data": {"id": 456}})
    s.snapshot()


def _pdf():
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (2500, 1500), (10, 120, 200)).save(buf, format="PNG")
    return buf.getvalue()


def compressao(s, mp):
    s.req("val pdf sem codigo", "post", "/api/validar-codigo-compressao", json={"codigo": ""})
    for ref in ("pdf-ok", "pdf-entregue", "pdf-pend", "ent-1", "nada", "img-ok"):
        s.req(f"val pdf {ref}", "post", "/api/validar-codigo-compressao", json={"codigo": ref})
        s.req(f"val img {ref}", "post", "/api/validar-codigo-compressao-imagem", json={"codigo": ref})
    mf = {"content_type": "multipart/form-data"}
    s.req("pdf sem codigo", "post", "/api/comprimir-pdf", data={"pdf": (io.BytesIO(b"x"), "a.pdf")}, **mf)
    s.req("pdf sem arquivo", "post", "/api/comprimir-pdf", data={"codigo": "pdf-ok"}, **mf)
    s.req("pdf codigo invalido", "post", "/api/comprimir-pdf", data={"codigo": "pdf-pend", "pdf": (io.BytesIO(b"x"), "a.pdf")}, **mf)
    s.req("pdf ok", "post", "/api/comprimir-pdf", data={"codigo": "pdf-ok", "pdf": (io.BytesIO(_pdf()), "a.pdf")}, **mf)
    s.req("pdf corrompido", "post", "/api/comprimir-pdf", data={"codigo": "pdf-ok", "pdf": (io.BytesIO(b"lixo"), "a.pdf")}, **mf)
    s.req("img sem codigo", "post", "/api/comprimir-imagem", data={"imagem": (io.BytesIO(b"x"), "a.png")}, **mf)
    s.req("img sem arquivo", "post", "/api/comprimir-imagem", data={"codigo": "img-ok"}, **mf)
    s.req("img formato ruim", "post", "/api/comprimir-imagem", data={"codigo": "img-ok", "imagem": (io.BytesIO(b"x"), "a.gif")}, **mf)
    s.req("img codigo invalido", "post", "/api/comprimir-imagem", data={"codigo": "pdf-pend", "imagem": (io.BytesIO(b"x"), "a.png")}, **mf)
    s.req("img ok", "post", "/api/comprimir-imagem", data={"codigo": "img-ok", "imagem": (io.BytesIO(_png()), "a.png")}, **mf)
    s.snapshot("cobrancas")


def estaticos(s, mp):
    s.req("raiz", "get", "/")
    s.req("styles.css", "get", "/styles.css")
    s.req("static/script.js", "get", "/static/script.js")
    s.req("comprar.html", "get", "/comprar.html")
    s.req("inexistente", "get", "/nao-existe.html")
    s.req("rota api inexistente GET", "get", "/api/coisa-que-nao-existe")
    s.req("POST em rota desconhecida", "post", "/qualquer")
    s.req("GET em rota so-POST", "get", "/api/cobrancas")
    s.req("DELETE", "delete", "/api/produto/1")
    s.snapshot()


def cors(s, mp):
    for origin in ("https://rread.netlify.app", "https://mercadopago-final.onrender.com", "https://rankedsale.netlify.app",
                   "https://broostore.netlify.app", "https://brootechstock.netlify.app", "https://nao-permitida.example"):
        r = s.client.options("/api/cobrancas", headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                                        "Access-Control-Request-Headers": "Content-Type, Authorization"})
        s.log.append((f"preflight {origin}", r.status_code, r.headers.get("Access-Control-Allow-Origin"),
                      r.headers.get("Access-Control-Allow-Methods"), r.headers.get("Access-Control-Allow-Headers"),
                      r.headers.get("Access-Control-Allow-Credentials")))
        r = s.client.get("/api/produto/1", headers={"Origin": origin})
        s.log.append((f"GET {origin}", r.status_code, r.headers.get("Access-Control-Allow-Origin")))
    r = s.client.options("/api/cobrancas", headers={"Origin": "https://broostore.netlify.app", "Access-Control-Request-Method": "POST",
                                                    "Access-Control-Request-Headers": "X-Admin-Token"})
    s.log.append(("preflight X-Admin-Token", r.status_code, r.headers.get("Access-Control-Allow-Headers")))


def dashboard(s, mp):
    for periodo in ("", "?periodo=7d", "?periodo=30d", "?periodo=90d", "?periodo=todos"):
        s.req(f"dash {periodo}", "get", f"/api/admin/dashboard{periodo}", headers={"X-Admin-Token": "fake-admin-token"})
    s.req("dash sem token", "get", "/api/admin/dashboard")
    s.req("dash token errado", "get", "/api/admin/dashboard", headers={"X-Admin-Token": "x"})


SCENARIOS = {
    "licencas": licencas, "produto_sync_cupom": produto_sync_cupom, "cobranca_pix": cobranca_pix,
    "cobranca_cartao": cobranca_cartao, "contato": contato, "cotar_frete": cotar_frete,
    "ranking_vendedores": ranking_vendedores, "webhook": webhook, "compressao": compressao,
    "estaticos": estaticos, "cors": cors, "dashboard": dashboard,
}
