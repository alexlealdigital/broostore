# BrooStore

Marketplace de produtos digitais (ebooks/PDFs), fisicos e aplicativos/jogos/assinaturas.

| Pasta | O que e | Roda em |
|---|---|---|
| [`apps/web`](apps/web) | Loja (React + TypeScript + Vite + Tailwind) | Netlify |
| [`apps/api`](apps/api) | API de pagamentos, licencas e entrega (Flask + RQ) | Render |
| [`docs`](docs) | Arquitetura, virada para producao, SQL | - |

Pagamentos: Mercado Pago (PIX e cartao). Frete: Melhor Envio. Dados: Supabase. E-mails: SMTP/Resend.

## Comecar

- **Entender o desenho:** [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md)
- **Colocar no ar (passo a passo):** [`docs/CUTOVER.md`](docs/CUTOVER.md)
- **Loja:** [`apps/web/README.md`](apps/web/README.md) - **API:** [`apps/api/README.md`](apps/api/README.md)

```bash
# loja
cd apps/web && npm install && npm run dev
# api (testes)
cd apps/api && pip install -r requirements.txt -r requirements-dev.txt && pytest
```

## Subir alteracoes ao GitHub

De dois cliques em `push-github.bat` (Windows). Ele cuida de init, remote, rebase e push.
