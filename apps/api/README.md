# BrooStore API (`apps/api`)

API de pagamentos e licenças da BrooStore: **Flask + SQLAlchemy + fila RQ (Redis)**, rodando no Render.
Integra Mercado Pago (PIX e cartão), Supabase (REST), SMTP/Resend (e-mails) e Melhor Envio (frete).

> Esta pasta é a versão **refatorada** do repositório antigo (`broorread`: `app.py` + `worker.py`).
> O comportamento das rotas foi preservado; veja `docs/CHANGELOG-API.md` para o que mudou (4 correções
> explícitas) e para as observações que **não** foram alteradas.

## Estrutura

```
app.py                     # `app = create_app()`  -> o comando do Render continua `gunicorn app:app`
worker.py                  # `python worker.py` + nome importável worker.process_mercado_pago_webhook
notificar_expiracao.py     # cron: `python notificar_expiracao.py`
broostore_api/
  __init__.py              # create_app (fábrica)
  config.py                # TODAS as variáveis de ambiente, num lugar só
  extensions.py            # db, cors, fila RQ/Redis (conexão preguiçosa) + enfileirar_webhook()
  models.py                # modelos UNIFICADOS (web + worker), sem mudança de schema
  jobs.py                  # job RQ: process_mercado_pago_webhook
  worker_main.py           # inicialização do worker RQ
  blueprints/              # produtos, licencas, cupons, cobrancas, webhook, contato, frete,
                           # ranking, compressao, admin_dashboard, static_files
  services/                # mercadopago, email, supabase_rest, frete, licencas, entrega, cupons
scripts/                   # seed_planos_broostock.py, seed_chave_broostock.py, notificar_expiracao.py
static/                    # páginas da loja antiga (cópia idêntica do original)
tests/                     # pytest (unitários, caracterização, golden vs. código original)
docs/                      # RENDER.md (deploy/rollback), CHANGELOG-API.md
```

## Como rodar localmente

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env        # preencha só o que for usar (nada é obrigatório para subir a API)
python app.py               # http://localhost:5000  (banco SQLite local em instance/cobrancas.db)
```

Sem `DATABASE_URL` a API usa SQLite local. O Redis só é necessário para enfileirar entregas
(`/api/webhook` responde 503 enquanto o Redis estiver fora; o resto da API funciona).

Worker (precisa de `REDIS_URL`): `python worker.py`.

## Testes

```bash
python -m pytest -q                 # tudo (SQLite em arquivo temporário; nenhuma chamada externa real)
python -m pytest -q tests/golden    # só a comparação com o código original
python -m ruff check .              # lint
```

* Mercado Pago, Supabase, SMTP, Resend, Melhor Envio e Redis são **sempre simulados** (`tests/fakes.py`);
  a rede é bloqueada durante os testes.
* `tests/golden/` roda as mesmas requisições contra o `app.py` **original** (cópia em
  `tests/golden/original/`, com um único patch para rodar em SQLite) e contra a API nova, e exige
  respostas, e-mails, payloads e linhas de banco idênticos.

## Rotas

| Método | Caminho | Observação |
|---|---|---|
| GET | `/` , `/<arquivo>` | páginas estáticas (`static/`) |
| GET | `/api/produto/<id>` | detalhes do produto |
| POST | `/api/sync-produto` | sincroniza produto do Supabase |
| GET | `/api/licenca/status?email=` | status da licença BrooStock |
| POST | `/api/licenca/trial` | teste grátis de 7 dias |
| POST | `/api/validar-cupom` | valida cupom |
| POST | `/api/cobrancas` | cria cobrança PIX |
| POST | `/api/cobrancas-cartao` | cobrança com cartão |
| GET | `/api/cobrancas/<external_reference>/status` | **novo (F4)**: `{"status","pago"}` |
| POST | `/api/webhook` | webhook do Mercado Pago (enfileira a entrega) |
| POST | `/api/contato` | formulário de contato (Resend) |
| POST | `/api/cotar-frete` | cotação Melhor Envio |
| GET | `/api/vendedores` , `/api/ranking` | gamificação |
| POST | `/api/validar-codigo-compressao`, `/api/comprimir-pdf` | compressor de PDF (produto 99) |
| POST | `/api/validar-codigo-compressao-imagem`, `/api/comprimir-imagem` | compressor de imagem (produto 98) |
| GET | `/api/admin/dashboard` | painel financeiro (header `X-Admin-Token`) |

## Fluxo de uma compra

```
cliente -> POST /api/cobrancas (PIX)  ->  Mercado Pago cria o PIX  ->  cobrança "pending"
cliente paga -> Mercado Pago -> POST /api/webhook -> fila RQ (retry: 5x, 1min..2h)
worker: consulta o pagamento ("approved"?) -> trava a cobrança -> cumpre o pedido
        (licença / chave) -> grava "approved" -> envia e-mail -> grava "delivered"
        e-mail falhou? continua "approved" e o RQ tenta de novo (sem repetir chave/licença)
```

Status da cobrança: `pending`/`in_process`/`rejected` (Mercado Pago) → `approved` (pago e cumprido,
e-mail pendente) → `delivered` (e-mail enviado). A loja pode consultar `GET /api/cobrancas/<ref>/status`.

## Regras do projeto

1. **Rotas existentes não mudam** (caminho, método, status, JSON, mensagens em português).
2. Refatorar e mudar comportamento **nunca no mesmo commit**.
3. Variáveis de ambiente só são lidas em `broostore_api/config.py` (há um teste que garante isso);
   toda variável nova entra também em `.env.example`.
4. Segredos nunca no código nem nos testes.
5. Esquema do banco: `db.create_all()` no boot (sem migrações). Mudança de coluna = SQL manual no
   Supabase/Render. Recomendação futura: adotar Alembic.

Deploy e rollback no Render: `docs/RENDER.md`.
