# BrooStore - arquitetura

```
 Cliente (navegador)
   |
   |  HTML/JS estatico                          dados publicos (somente leitura)
   v                                                    ^
 Netlify  --------------  apps/web  (React+TS) --------+--> Supabase (products, reviews)
   |
   |  /api/*  (JSON)
   v
 Render  --  apps/api  (Flask)  ----> Mercado Pago (PIX, cartao, webhook)
   |  \                         ----> Melhor Envio (frete)
   |   \                        ----> SMTP/Resend (e-mails)
   |    '--> fila Redis (RQ) --> worker (entrega, licenca, e-mail)
   v
 Postgres (cobrancas, licencas, cupons, ...)
```

## Pastas

| Pasta | O que e | Onde roda |
|---|---|---|
| `apps/web` | Loja (React, TypeScript, Vite, Tailwind) | Netlify |
| `apps/api` | API Flask + worker RQ, organizada em modulos | Render |
| `docs` | Guias e SQL | - |

## Regras que mantem o sistema estavel

1. **Contrato da API nao quebra.** As rotas `/api/*` existentes mantem o mesmo
   caminho, metodo e formato de resposta. O BrooStock, o `comprar.html` e o
   Mercado Pago dependem delas. Rotas novas sao sempre ADITIVAS.
2. **Refatorar e mudar comportamento nunca no mesmo commit.**
3. **Preco, frete e desconto sao sempre calculados no servidor.** O navegador
   so exibe.
4. **Segredos so em variaveis de ambiente** (Render/Netlify). Nada no codigo.
5. **Rollback = `git revert`** do commit e novo deploy.

## Tipos de produto (campo `tipo` da tabela `products`)

| Area na loja | Valores de `tipo` |
|---|---|
| Digitais | `ebook` (e qualquer valor desconhecido) |
| Fisicos | `fisico` |
| Aplicativos | `game`, `app`, `assinatura` |

A regra esta em um unico arquivo: `apps/web/src/lib/categorias.ts`.

## Variaveis de ambiente por servico

| Onde | Onde configurar | Referencia |
|---|---|---|
| Frontend (so valores publicos `VITE_*`) | Netlify | `apps/web/.env.example` |
| API, worker e cron (segredos) | Render | `apps/api/docs/RENDER.md`, `apps/api/.env.example` |

## Roteiro do projeto

1. **Agora:** loja nova + API refatorada com 4 correcoes de robustez (ver `apps/api/docs/CHANGELOG-API.md`).
2. **Em seguida:** virada controlada (`docs/CUTOVER.md`) e testes reais de baixo valor.
3. **Depois:** licencas por aplicativo (BrooStock e demais SaaS) vendidas pela BrooStore, com a
   verificacao feita no servidor; modernizar o painel de autores e as paginas que ainda estao em `apps/api/static`.
