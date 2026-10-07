# CHANGELOG — API (refatoração dos dois arquivos grandes para um pacote testado)

Origem: `app.py` (1555 linhas), `worker.py` (646), `Dashboard_api.py`, `notificar_expiracao.py`,
`seed_*.py` do repositório antigo `broorread`. Prioridade absoluta: **não quebrar a produção**.

## 1. Refatoração sem mudança de comportamento

* `app.py` → pacote `broostore_api/` (blueprints por assunto, serviços, modelos únicos, config única).
  `app.py` virou um shim (`app = create_app()`), então `gunicorn app:app` continua igual.
* `worker.py` virou shim que reexporta `process_mercado_pago_webhook` (o web enfileira **por nome**,
  `worker.process_mercado_pago_webhook`, e jobs já na fila do Redis durante um deploy continuam resolvendo).
* Todas as 18 rotas do `app.py` original mantêm caminho, métodos, status HTTP, formato JSON e mensagens
  (em português, textuais). Comprovado por testes de caracterização e pela **comparação golden**
  (`tests/golden/`): mesmas requisições contra o `app.py` original e contra a API nova, com os mesmos
  dublês; status, JSON, e-mails (assunto + HTML), payloads do Mercado Pago, chamadas ao Supabase/Melhor
  Envio, jobs enfileirados e linhas do banco idênticos.
* Modelos unificados (superset dos dois conjuntos que existiam). Tabelas e colunas **idênticas** (teste golden
  compara o metadata). Há uma única diferença de fato para o worker: ele agora enxerga a coluna
  `chaves_licenca.ativa_no_app` (ver `docs/RENDER.md`, SQL "antes da troca").
* Variáveis de ambiente lidas só em `config.py`, com os mesmos padrões (inclusive URL e chave **pública**
  anon do Supabase e o `SECRET_KEY` padrão — este agora gera um aviso no log). CORS: origens, métodos e
  headers idênticos.
* `connect_args={"prepare_threshold": None}` só é aplicado quando a URL é PostgreSQL (antes quebrava SQLite;
  é isso que tornava o código intestável). Em produção (Postgres) as opções do engine são as mesmas:
  web `pool_recycle=3600`, worker `300`.
* `db.create_all()` no boot, como antes (sem migrações).
* Logs: mesmas mensagens/prefixos, agora via `logging` em stdout.

## 2. Correções explícitas (únicas mudanças de comportamento intencionais)

### F1 — Pedido pago nunca se perde se o e-mail de entrega falhar
Antes (`worker.py` ~576-640): se `sucesso` fosse falso, o job fazia `rollback()` da licença/chave e **retornava
sem erro** → o RQ marcava como concluído, o Mercado Pago não reenviava o webhook (já recebera 200), o cliente
pagou e não recebia nada.
Agora, depois de confirmar `approved` no Mercado Pago:
1. trava a cobrança, **cumpre o pedido** (licença ativada/renovada ou chave reservada) e grava a cobrança como
   `approved` — **commit antes** de enviar o e-mail;
2. envia o e-mail; ok → `delivered` (status final que o ranking e o painel já usam, inalterado);
3. falhou → continua `approved` e o job **levanta** `EmailEntregaFalhou` para o RQ tentar de novo
   (`Retry(max=5, interval=[60, 300, 900, 3600, 7200])`, aplicado ao enfileirar pelo webhook e pelo cartão).
   O worker passou a iniciar com `with_scheduler=True` (necessário para retries com intervalo).
* **Idempotente**: o retry não reserva outra chave (procura `chaves_licenca.cobranca_id`) nem estende a licença
  de novo (procura `licencas.cobranca_id` **e** a marca `licenca_aplicada` em `cobrancas.observacoes`; a marca
  cobre o caso de uma compra posterior do mesmo cliente ter sobrescrito `licencas.cobranca_id`).
* "Estoque esgotado" e "Plano de assinatura não configurado" continuam **levantando** exceção como antes; o status
  fica **inalterado** e há um log claro `PEDIDO PAGO SEM ENTREGA`. Como agora há retry, repor o estoque/configurar
  o plano faz o pedido ser entregue sozinho na próxima tentativa.
* Compatibilidade de filtros de status: painel (`STATUS_PAGOS = approved, delivered`), compressão (`approved` ou
  `delivered`) e cron (olha só `licencas`) já aceitam `approved`; o **ranking** continua contando só `delivered`.
* Testes: `tests/test_jobs.py::test_f1_*`, `test_estoque_esgotado_*`, `test_assinatura_sem_plano_*`,
  `test_rq_real_worker_agenda_retry_*` (worker RQ de verdade com Redis falso), mutação verificada à mão
  (sem raise / sem commit antecipado / sem idempotência → testes falham).

### F2 — Dois webhooks simultâneos do mesmo pagamento não entregam em dobro
`SELECT ... FOR UPDATE` na cobrança (`with_for_update()`, no-op no SQLite) no início do processamento, com
releitura do status já com a trava (`populate_existing`); a trava é retomada antes do e-mail, então um segundo
worker espera e vê `delivered`. Testes: `test_f2_*` (espiona o `with_for_update`; simula outro processo
entregando entre a leitura e a trava). **Não verificável aqui:** a concorrência real em PostgreSQL.

### F3 — Webhook mais robusto
* Validação de assinatura atrás de `WEBHOOK_VALIDATE_SIGNATURE` (`true`/`1`). **Padrão DESLIGADO = comportamento
  original** (a checagem estava comentada). Ligada e inválida → `401 {"status":"error","message":"Assinatura inválida"}`.
  Manifesto do Mercado Pago: `id:<data.id>;request-id:<x-request-id>;ts:<ts>;` (HMAC-SHA256 com `WEBHOOK_SECRET`).
* `request.get_json(silent=True)`: corpo inválido não derruba mais (responde 200 sem enfileirar; antes: 500).
* Fila indisponível (Redis fora) → `503 {"status":"error","message":"Fila indisponível, tente novamente"}`
  (antes: 500 com `AttributeError`). O Mercado Pago tenta de novo. A conexão com o Redis agora é preguiçosa e
  se reconecta sozinha (nova tentativa a cada 30 s) — antes, se o Redis estivesse fora no boot, a fila ficava
  inutilizada até reiniciar o serviço.
* Testes: `tests/test_webhook.py::test_f3_*`, `test_webhook_fila_indisponivel_503`, `test_webhook_corpo_invalido_*`.

### F4 — Novo endpoint (aditivo) `GET /api/cobrancas/<external_reference>/status`
`200 {"status": <status>, "pago": <status in ("approved","delivered")>}`; desconhecida → `404
{"status":"error","message":"Cobrança não encontrada."}`. Sem dados pessoais; CORS igual às demais rotas;
`Cache-Control: no-store` (a loja nova faz polling). Testes: `tests/test_status_cobranca.py`.

### F5 — `/api/licenca/status` e demais rotas: sem mudança.

## 3. Decisões e desvios que você precisa conhecer

1. **`/api/admin/dashboard` agora existe.** No repositório antigo o blueprint `Dashboard_api.py` **nunca foi
   registrado** no `app.py` (o comentário dizia "2 linhas de registro", mas elas não existem): na produção atual
   essa URL cai na rota de estáticos e devolve 404. Como o layout pedido inclui o blueprint, ele foi registrado.
   Sem `ADMIN_TOKEN` ele responde sempre 401. Usa o engine compartilhado (`db.engine`) em vez de criar um
   próprio. CORS: para o painel chamar de outro domínio é preciso liberar a origem e o header `X-Admin-Token`;
   isso só acontece se você definir `DASHBOARD_ORIGIN` (padrão: nada muda no CORS). Se preferir **não** expor a
   rota por enquanto, é só remover `admin_dashboard` de `broostore_api/blueprints/__init__.py`.
2. `Dashboard_api.py` **não** foi recriado na raiz: nada importa esse módulo (o `app.py` original não o usava).
3. `build.sh` foi copiado sem alteração para manter o Build Command atual do Render funcionando
   (`chmod +x build.sh && ./build.sh`). Não há `render.yaml` de propósito (ver `docs/RENDER.md`).
4. Seeds agora ficam em `scripts/` (`python scripts/seed_planos_broostock.py`). `fix_sequence()` só roda em
   PostgreSQL (necessário para testar em SQLite). `seed_chave_broostock.py` era cópia idêntica de
   `seed_planos_broostock.py` — virou um alias.
5. Cron: `python notificar_expiracao.py` continua valendo; a lógica está em `scripts/notificar_expiracao.py`
   (e usa o `create_app(role="worker")`, sem Redis).
6. `MELHOR_ENVIO_*`, `CEP_ORIGEM` e `ADMIN_TOKEN` eram lidos no import dos módulos; agora são lidos a cada
   chamada. Em produção (variáveis definidas antes do boot) é equivalente.
7. Campo novo `licenca_aplicada` dentro do JSON de `cobrancas.observacoes` (só em compras de assinatura) —
   marca de idempotência do F1. Painel e e-mails ignoram chaves desconhecidas.
8. O código de `app.py` que estava duplicado (sync de produto, cupom, frete, observações) entre PIX e cartão
   foi extraído para `services/`; os logs de erro mantêm os textos distintos de cada rota.

## 4. Observações (não alteradas)

Coisas suspeitas que vi e **deixei exatamente como estavam** (nada aqui foi pedido para corrigir):

* **`/health` não existe.** O `render.yaml` antigo declarava `healthCheckPath: /health`, mas não há essa rota
  (`/health` cai nos estáticos → 404). Não configure health check apontando para `/health` sem criar a rota.
* **Códigos de compressão (PDF/imagem) são reutilizáveis.** `compressao_usada` / `compressao_img_usada` não
  são colunas: `cobranca.compressao_usada = True` não persiste, então "Este código já foi utilizado" nunca
  acontece. O e-mail promete "uso único e válido por 24 horas" — nada disso é aplicado. Também aceita
  cobranças com `product_id` nulo.
* **Cupom inválido ainda aparece na cobrança**: se o `cupom_id` existe mas está inativo/expirado/de outro
  produto, o desconto não é aplicado, porém o código do cupom entra na descrição enviada ao Mercado Pago, em
  `cupom_id` e em `desconto_aplicado` (com desconto 0).
* **Cupom consome uso na criação da cobrança** (mesmo que o PIX nunca seja pago) e o contador não é protegido
  contra concorrência (pode passar de `usos_maximos`).
* **Pagamento aprovado pode ser descartado em silêncio** em dois pontos que o F1 não cobre: falha ao consultar
  o Mercado Pago (`return` sem erro) e cobrança não encontrada após 5 tentativas (10 s).
* O PIX responde com `cobranca.id` e `data_criacao` **nulos** (`to_dict()` é chamado antes do commit).
* `POST /api/sync-produto` cria produtos novos sempre como `ebook` e nunca atualiza `tipo`; o checkout (PIX/cartão) atualiza.
* Chamadas ao Supabase em `/api/cobrancas`, `/api/cobrancas-cartao` e `/api/sync-produto` **sem timeout**
  (podem ficar presas até o timeout do gunicorn, 300 s).
* SMTP: só o e-mail de produto físico usa SSL na porta 465; os demais usam STARTTLS (587). O `render.yaml`
  antigo definia `SMTP_PORT=465` — com 465, os e-mails digitais/licença/boas-vindas **falhariam** (e agora
  seriam repetidos pelo RQ sem sucesso). Confirme que a variável do painel é 587 (ou ausente).
* `reservar chave`: `SELECT ... WHERE vendida=false ORDER BY id LIMIT 1 FOR UPDATE` no PostgreSQL pode devolver
  zero linhas (falso "estoque esgotado") quando duas compras disputam a mesma chave; com o retry do F1 isso se
  resolve sozinho. Melhoria futura: `FOR UPDATE SKIP LOCKED`.
* Pedido pago cujo job levanta "estoque esgotado"/"plano não configurado" fica **`pending`** no painel
  (por pedido explícito do F1 o status não muda) até a entrega.
* Falha ao gravar `delivered` depois de enviar o e-mail: o job loga e retorna (cobrança fica `approved`; sem novo e-mail).
* Formulário de contato injeta nome/mensagem sem escape no HTML do e-mail (destinatário: só você).
* `GET /api/vendedores` e `/api/ranking` abrem um `app_context()` aninhado dentro da requisição (mantido).
* `cpf` explicitamente `null` no cartão gera 500 (`None.replace`).
* `SECRET_KEY` padrão, URL e chave anon do Supabase estão no código (a anon é pública por desenho; o `SECRET_KEY`
  não é usado para sessões, mas deve ser definido no painel).
* Dependências sem versão fixa em `requirements.txt` (SQLAlchemy via Flask-SQLAlchemy, `rq`, `redis`, `resend`,
  `pikepdf`, `Pillow`): foram mantidas como estavam. Testado com Flask 3.0.0, SQLAlchemy 2.1.x, rq 2.12, redis 8.1.
  `Query.get()` (legado) ainda é usado e emite aviso de depreciação no SQLAlchemy 2.
* `Float` para dinheiro e `datetime.utcnow()` ingênuo (depreciado no Python 3.12+).
* `build.sh` instala Ghostscript via `apt-get`, que o código não usa.

## 5. Recomendações (fora deste passo)

* **Alembic** (ou outro controle de migrações) para parar de depender de `create_all()` e de SQL manual.
* Criar `GET /health` e, se quiser, configurar o health check do Render.
* Persistir o uso do código de compressão (coluna) se a regra "uso único" for desejada.
* Alertar (e-mail/Slack) quando um job entrar na lista de falhas do RQ ou houver cobrança `approved` antiga.
* Ligar `WEBHOOK_VALIDATE_SIGNATURE` depois do teste com pagamento real de valor baixo.
* Fixar versões de `rq`/`redis`/`SQLAlchemy` num segundo passo (uma mudança por vez).

## 6. Não migrado de propósito

`MUDANCAS_REALIZADAS.md`, `DEPLOY_RAPIDO.md`, `CHECKLIST_DEPLOY.md`, `VERCEL_VS_RENDER.md`, `test_local.sh`
(obsoletos) e o arquivo avulso `delivered` (cópia acidental/antiga de um worker). O `README.md` e o `render.yaml`
antigos foram substituídos por `README.md` e `docs/RENDER.md`.

## Ajuste estetico dos e-mails (apos o 1o teste real de PIX)

- Os botoes de download mostravam `[·]` (emoji perdido no original); agora usam 📥 / 🗜️.
- O valor no texto do e-mail aparecia como `R$ 1.00`; agora `R$ 1,00` (padrao brasileiro, milhar com ponto).
- So muda o texto dos e-mails. Nenhum valor, status ou rota mudou. Os testes de comparacao com o original
  normalizam apenas essas duas diferencas.
