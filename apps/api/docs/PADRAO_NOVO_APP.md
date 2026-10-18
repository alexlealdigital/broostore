# Padrão para vender um app novo

Cada app tem **sua própria licença e seus próprios planos** ("cada app separado"). A mesma pessoa pode ter
licença do BrooStock e de outro app; o teste grátis é um por e-mail **por app**.

Há dois modelos de venda, independentes:

* **Conta + e-mail** (como o BrooStock): o app consulta `/api/licenca/status`; a licença vive em `licencas`.
* **Chave digitada** (software instalado): a chave `BROO-XXXX-XXXX-XXXX-XXXX` é gerada na compra e validada em
  `/api/validar_chave`; fica em `chaves_licenca` (com `planos_chave` e `ativacoes_licenca`).

## O que cada peça faz

| Peça | Papel |
|---|---|
| `broostore_api/apps_config.py` | Registro dos apps: nome, endereço, dias de teste, textos dos e-mails |
| `licencas.app` / `planos_assinatura.app` | De qual app é cada licença/plano |
| `GET /api/licenca/status?email=&app=` e `POST /api/licenca/trial` | O app consulta/ativa teste. Sem `app` = `broostock`; app desconhecido = 400 |
| Job de compra (`jobs.py`) | Cria/renova a licença do app do plano, ou gera/renova a chave; manda o e-mail |
| `services/sync_licencas.py` | Copia a licença para o Supabase **do app** (`licenses`), onde a RLS exige licença ativa |
| `scripts/notificar_expiracao.py` | Avisos de vencimento (licenças e chaves) + reconcilia o Supabase de cada app |
| `scripts/reprocessar_pagamentos.py` | Entrega pedidos pagos que ficaram sem entrega (fila fora do ar) |

## Checklist: app novo por conta + e-mail (ex.: `meuapp`)

1. **Registro** — em `apps_config.py`, copie o exemplo em `APPS["meuapp"]` (nome, url, `trial_dias`, textos). Deploy.
2. **Planos na loja** — edite `PLANOS` em `scripts/seed_planos_app.py` e rode no Shell do Render (pasta `apps/api`):
   `python scripts/seed_planos_app.py meuapp` → anote os `id` impressos.
3. **Supabase do app novo** (SQL Editor): crie a tabela `licenses`, depois exija licença nas tabelas do app (RLS)
   **só depois** da carga inicial do passo 5.
4. **Variáveis no Render** (serviço web **e** worker): `MEUAPP_SUPABASE_URL` e `MEUAPP_SUPABASE_SERVICE_KEY`
   (service_role do projeto do app — nunca no GitHub nem no chat).
5. **Carga inicial** (se já houver licenças do app): `python scripts/sincronizar_licencas_app.py meuapp`.
6. **Frontend do app** — `APP_SLUG = "meuapp"`, os IDs dos planos (passo 2) e `app=meuapp` nas chamadas de status/trial.
7. **CORS** — nada a fazer: a origem vem de `apps_config` (campo `url`).
8. **Teste ponta a ponta** — cadastro → teste grátis → compra → licença ativa → vencimento → aviso por e-mail.

## Checklist: app instalado com chave

1. Edite `APPS` em `scripts/seed_apps_chaves.py` (nome, preço, link, dias, rótulo, nº de dispositivos, prefixo) e rode
   `python scripts/seed_apps_chaves.py`. Produto sem linha em `planos_chave` continua usando o estoque pré-carregado.
2. O app chama `POST /api/validar_chave` com `chave_serial`, `product_id` e um `device_id` estável, ao digitar a chave
   e a cada abertura (é assim que o vencimento é aplicado).
3. Suporte (header `X-Admin-Key` = `ADMIN_SECRET_KEY`): `GET /api/admin/chaves`, `POST /api/admin/chaves/emitir`,
   `/revogar` e `/resetar-dispositivos`.
