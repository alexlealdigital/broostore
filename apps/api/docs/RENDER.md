# Render — como apontar os serviços atuais para o monorepo (e como voltar atrás)

**Regra de ouro:** NÃO crie serviços novos e NÃO aplique um Blueprint (`render.yaml`). Os serviços
existentes continuam **com os mesmos nomes e URLs** — a URL pública `mercadopago-final.onrender.com`
é usada por outros apps (CORS, `comprar.html`, e-mails, Mercado Pago). Só trocamos **de onde o código
vem** (repositório/pasta). Por isso este repositório não tem `render.yaml`.

> O que está aqui foi escrito a partir do `render.yaml` e dos arquivos do repositório antigo. Os nomes
> exatos dos serviços e os valores atuais no painel você confere na tela de cada serviço; os botões do
> painel do Render podem mudar de nome com o tempo. O comportamento no Render real **não foi testado**
> (ver "O que não dá para verificar fora do Render" no fim).

## Serviços (todos já existem — não mexa em banco nem Redis)

| Serviço | Tipo | Comando de start | Root Directory |
|---|---|---|---|
| API (URL `mercadopago-final.onrender.com`; no `render.yaml` antigo: `mercadopago-api`) | Web Service | `gunicorn app:app --timeout 300 --workers 2` | `apps/api` |
| Worker (no `render.yaml` antigo: `mercadopago-worker`) | Background Worker | `python worker.py` | `apps/api` |
| Cron de avisos (se existir no seu painel) | Cron Job | `python notificar_expiracao.py` | `apps/api` |
| Postgres e Redis | — | não mudam | — |

Build Command:

* **Web:** o antigo era `chmod +x build.sh && ./build.sh` (instala o Ghostscript e roda
  `pip install -r requirements.txt`). O `build.sh` foi copiado para `apps/api` sem alteração, então
  você pode **manter** o comando como está. (O Ghostscript não é usado pelo código — a compressão usa
  `pikepdf` — então `pip install -r requirements.txt` também basta; só mude se quiser.)
* **Worker e Cron:** `pip install -r requirements.txt` (igual ao antigo).

> `Procfile`: existe só por compatibilidade (as duas linhas originais). O Render **não** usa o Procfile;
> vale o "Start Command" do painel. Atenção: o Procfile antigo dizia `--timeout 120` e o `render.yaml`
> dizia `--timeout 300`; use o do `render.yaml` (`--timeout 300 --workers 2`), que é o que está acima.

## Variáveis de ambiente

**Não precisa mudar nenhuma.** A lista completa (com os padrões) está em `.env.example`. As únicas
novas, **todas opcionais**:

| Variável | Para quê | Padrão |
|---|---|---|
| `WEBHOOK_VALIDATE_SIGNATURE` | `true`/`1` liga a validação da assinatura do webhook do Mercado Pago | desligada (= comportamento atual) |
| `ADMIN_TOKEN` | habilita `GET /api/admin/dashboard` (header `X-Admin-Token`) | vazio (endpoint responde 401) |
| `CORS_EXTRA_ORIGINS` | dominios extras do frontend (separados por virgula), alem dos ja liberados | nenhum |
| `DASHBOARD_ORIGIN` | origem (CORS) do painel financeiro, se ele rodar em outro domínio | não liberada |

Sugestão: defina `SECRET_KEY` no painel se ainda não definiu (sem ela, a API usa um valor padrão
embutido no código e escreve um aviso no log a cada boot).

### Antes de ligar `WEBHOOK_VALIDATE_SIGNATURE`

1. No painel do Mercado Pago (Webhooks), confirme que o "segredo da assinatura" é o mesmo valor de `WEBHOOK_SECRET`.
2. Defina `WEBHOOK_VALIDATE_SIGNATURE=true`, faça um pagamento real de **valor baixo** (PIX de R$ 1) e
   veja nos logs se o webhook entrou (e a entrega aconteceu). Se aparecer `401 Assinatura inválida`,
   volte a variável para `false` (ou apague) — o efeito é imediato após o redeploy.

## SQL para rodar ANTES da troca (cole no SQL Editor do Supabase / psql do Render)

Os modelos agora são unificados: o worker passa a ler a coluna `ativa_no_app` de `chaves_licenca`
(antes só o `app.py` a declarava, e ele nunca consultava essa tabela). Se a coluna ainda não existir
no seu banco, a reserva de chaves (jogos/apps) falharia. Este comando é seguro (não faz nada se já existir):

```sql
ALTER TABLE chaves_licenca
  ADD COLUMN IF NOT EXISTS ativa_no_app BOOLEAN NOT NULL DEFAULT FALSE;
```

Conferência opcional (todas estas colunas devem aparecer):

```sql
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_name IN ('cobrancas','chaves_licenca','licencas','sales','cupons','produtos','vendedores','planos_assinatura')
ORDER BY table_name, ordinal_position;
```

(A tabela `sales` já existe em produção porque o worker antigo a criava; o `db.create_all()` do
boot só cria o que faltar, nunca altera tabelas existentes.)

## Como trocar o serviço do repositório antigo para o monorepo

Faça primeiro com **calma, num horário de pouco movimento**, e um serviço por vez.

1. **Pré-checagem (2 min):** rode no banco

   ```sql
   SELECT id, external_reference, product_id, status, data_criacao
   FROM cobrancas
   WHERE status = 'approved' AND data_criacao > now() - interval '2 days'
   ORDER BY data_criacao DESC;
   ```

   Hoje o `approved` só aparece em cobranças de cartão recém-criadas (aguardando o worker). Anote o
   resultado: serve de referência para depois.
2. Rode o `ALTER TABLE` acima.
3. Anote os valores atuais de cada serviço (Settings → Build Command, Start Command, Branch, Root Directory)
   — são os valores para o **rollback**. Tire um print.
4. **Worker primeiro.** Painel do Render → serviço do worker → **Settings → Build & Deploy**:
   * **Repository**: troque (Edit/Change) para o repositório do monorepo (`broostore`), mesma branch de produção.
   * **Root Directory**: `apps/api`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `python worker.py`
   * Salve e faça o deploy. Nos logs devem aparecer `[WORKER] ✅ Redis conectado.`, `Tabelas verificadas` e `Worker iniciado`.
   * Jobs que já estavam na fila (enfileirados pelo código antigo, por nome `worker.process_mercado_pago_webhook`)
     continuam funcionando: o nome do job foi mantido.
5. **Web:** serviço da API → mesma tela:
   * **Repository**: monorepo; **Root Directory**: `apps/api`
   * **Build Command**: o atual (`chmod +x build.sh && ./build.sh`) ou `pip install -r requirements.txt`
   * **Start Command**: `gunicorn app:app --timeout 300 --workers 2`
   * Deploy. Teste na URL pública (a mesma de sempre):
     * `GET https://mercadopago-final.onrender.com/` → página inicial;
     * `GET .../api/produto/1` → JSON do produto;
     * `GET .../api/licenca/status?email=teste@exemplo.com` → JSON;
     * `GET .../api/cobrancas/qualquer/status` → 404 `Cobrança não encontrada.` (rota nova funcionando).
6. **Cron** (se existir): mesma troca de repositório/root; comando `python notificar_expiracao.py`.
7. **Smoke test real** (um pagamento PIX de valor baixo): gere a cobrança, pague, confirme o e-mail e
   `GET /api/cobrancas/<external_reference>/status` → `{"status":"delivered","pago":true}`.
8. Depois de alguns dias estável, desligue o auto-deploy do repositório antigo (ou arquive-o). Não apague
   antes: ele é o seu plano de rollback.

Observações:

* Com Root Directory definido, só commits dentro de `apps/api` disparam deploy desse serviço
  (mudanças em `apps/web` não derrubam a API).
* Os logs continuam com os mesmos prefixos (`[WORKER]`, `[CARTAO]`, `[TRIAL]`, `[CRON]`...).

## Como fazer ROLLBACK (voltar para o código antigo)

Leva alguns minutos e **não mexe em banco nem em Redis**.

1. **Antes de voltar**, rode a consulta da pré-checagem. Se houver cobranças `approved` cujo e-mail ainda
   **não foi enviado** (as que o novo worker deixou aguardando retry), deixe o worker novo terminar ou
   resolva-as antes: o código antigo não conhece essa etapa e poderia reservar uma segunda chave num
   job repetido. Na dúvida, espere o fim dos retries (até ~3,5 h) ou me chame.
2. Em cada serviço (worker, web, cron): **Settings → Build & Deploy → Repository** → reconecte o
   repositório **antigo** (`broorread`), mesma branch.
3. **Root Directory**: deixe **vazio** (como era).
4. Restaure Build/Start Command com os valores anotados no passo 3 da troca (Start do web:
   `gunicorn app:app --timeout 300 --workers 2`; do worker: `python worker.py`).
5. Faça o deploy (Manual Deploy → "Clear build cache & deploy" se o primeiro deploy der erro de cache).
6. Confira os logs e a URL pública.

Compatibilidade de dados no rollback: o código novo só **acrescenta** informação — status `approved` (já
existia no cartão) e, em assinaturas, a chave `licenca_aplicada` dentro do JSON `cobrancas.observacoes`
(o código antigo e o painel ignoram chaves desconhecidas). Nenhuma tabela/coluna foi alterada (o
`ALTER TABLE ... ativa_no_app` apenas garante uma coluna que o código antigo já declarava).

## Cobranças "presas" em `approved` (monitoramento)

Se o e-mail de entrega continuar falhando depois das 5 tentativas (1 min, 5 min, 15 min, 1 h, 2 h),
o job vai para a lista de falhas do RQ e a cobrança fica em `approved` — **o cliente já está
liberado** (licença ativa / chave reservada) mas sem e-mail. Para listar:

```sql
SELECT id, external_reference, cliente_email, product_id, valor, data_criacao
FROM cobrancas
WHERE status = 'approved' AND data_criacao < now() - interval '4 hours'
ORDER BY data_criacao;
```

Resolva o motivo (normalmente credenciais SMTP: `EMAIL_USER`/`EMAIL_PASSWORD`) e reenfileire o job
com o `payment_id` do Mercado Pago pelo shell do worker, se necessário:
`python -c "from broostore_api.extensions import enfileirar_webhook as e; e('<payment_id>')"`
(o job é idempotente: não duplica chave nem licença).
Cobranças pagas que ficam em `pending` com erro "Estoque esgotado" / "Plano de assinatura não
configurado" nos logs do worker também voltam a ser processadas pelos retries depois que você repõe o
estoque/configura o plano.

## Seeds (Shell do Render, dentro de `apps/api`)

```
python scripts/seed_planos_broostock.py
```

(`scripts/seed_chave_broostock.py` é a mesma coisa: no repositório antigo os dois arquivos eram idênticos.)

## O que não dá para verificar fora do Render

* O comportamento real do painel do Render ao trocar o repositório/Root Directory.
* Redis real, scheduler do RQ em produção (o worker agora sobe com `with_scheduler=True`, necessário
  para os retries com intervalo; validado só com Redis falso em memória), Mercado Pago, SMTP (Zoho),
  Supabase e Melhor Envio reais.
* PostgreSQL real com a trava `SELECT ... FOR UPDATE` (nos testes o banco é SQLite, onde ela não faz nada).
