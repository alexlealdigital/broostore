# BrooStore Web (loja)

Vitrine e checkout da BrooStore. React 18 + TypeScript + Vite 5 + Tailwind CSS 3 + wouter, dados no Supabase (somente leitura)
e pagamentos pela API Flask no Render (PIX e cartao via Mercado Pago).

## Rodar localmente

```bash
cd apps/web
npm install
npm run dev          # http://localhost:5173
```

Scripts: `npm run type-check` | `npm run lint` | `npm test` | `npm run build` | `npm run preview`.

## Variaveis de ambiente

Todas sao **publicas** (vao para o navegador) e ja tem padrao em `src/lib/config.ts`; so crie um `.env` para trocar.
Veja `.env.example`.

| Variavel | Para que serve |
|---|---|
| `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` | Leitura de `products`, `reviews` e insercao em `reviews`/`contatos` |
| `VITE_API_URL` | API de pagamentos (Render) |
| `VITE_MP_PUBLIC_KEY` | Public key do Mercado Pago (SDK, tokenizacao do cartao) |

## Rotas

`/` | `/loja?area=digitais\|fisicos\|aplicativos&q=&categoria=&ordem=` | `/produto/:id` | `/comprar/:id` | `/sobre` | `/contato` |
`/autores` | `/termos` | `/privacidade` | 404.

Compatibilidade com o BrooStock: `/comprar?produto=ID&email=&nome=&return=` e redirecionado para `/comprar/ID?...`
(e-mail pre-preenchido e travado, link "Voltar" apontando para `return`; so aceita URLs http/https).

## Taxonomia (`src/lib/categorias.ts`)

`products.tipo` (normalizado com `trim().toLowerCase()`): `ebook` e qualquer valor desconhecido/vazio = **digitais**;
`fisico` = **fisicos**; `game`, `app`, `assinatura` = **aplicativos**. Qualquer regra nova de tipo entra so nesse arquivo
(e em `docs/ARQUITETURA.md`).

## Estrutura

```
src/
  lib/         api, supabase, products (dados), catalog (filtros/ordenacao), categorias, format, validators,
               checkoutPayload, checkoutValidation, totals, frete, viacep, mercadopago (SDK lazy), poller
  hooks/       useCatalog, useProductDetail, useProductReviews, useCheckoutProduct, useCoupon, useFrete,
               useCardForm, useCheckoutPayment, usePixStatus, ...
  components/  ui (primitivos), layout, product, home, checkout
  pages/       uma por rota
```

## Seguranca do pagamento

- Numero, validade e CVV do cartao vao **somente** para o Mercado Pago (`createCardToken`); a API recebe apenas o `token`.
- O CPF do titular segue para `POST /api/cobrancas-cartao` porque o backend atual o exige (`payer.identification`).
  Para parar de enviar, remova `cpf` em `buildCardPayload` (`src/lib/checkoutPayload.ts`) quando o backend deixar de exigir.
- Preco, desconto e frete sao recalculados no servidor; a tela apenas exibe o que a API devolve.
- Nada sensivel e salvo em `localStorage` (so a preferencia 18+ na sessao e "ja avaliei este produto").
- Nao ha service worker (de proposito; o cache de service workers ja causou problemas antes). So ha `manifest.webmanifest`.

## Testes e mocks

`npm test` roda o Vitest (jsdom + Testing Library). Cobertura principal: mapeamento de categorias, formatadores e
validadores (CPF, telefone, CEP, cartao/Luhn, validade), cliente de API (erro HTTP, rede, timeout, "servidor lento",
endpoint de status ausente), parsing de frete, catalogo (busca sem acento, filtros, ordenacao), poller do PIX
(intervalo, pausa com aba oculta, limite de 15 min) e os fluxos de checkout (PIX, cartao, cupom, frete) em componente.

**Nenhum teste chama a API real**: `src/components/checkout/*.test.tsx` fazem `vi.mock('@/lib/api')` (e do SDK do Mercado Pago),
e `api.test.ts` injeta um `fetch` falso. Nunca aponte testes para `/api/cobrancas` ou `/api/cobrancas-cartao` reais.

### Capturas de tela (visual)

`scripts/screenshots.mjs` abre a loja com Playwright e **intercepta toda a rede** (Supabase, API, ViaCEP e SDK do Mercado Pago)
usando os dados ficticios de `scripts/mock-data.mjs`.

```bash
npm run build && npx vite preview --port 4173 &
node scripts/screenshots.mjs docs/screenshots     # precisa do pacote `playwright` e de um Chromium
```

As imagens em `docs/screenshots/` foram geradas assim (dados ficticios).

## Deploy (Netlify)

O `netlify.toml` na raiz do repositorio ja define `base = apps/web`, `npm ci && npm run build`, `publish = dist`,
fallback de SPA (`/* -> /index.html`) e cache longo para `/assets/*`. Basta conectar o repositorio.
Variaveis `VITE_*` sao opcionais (ha padroes no codigo).

**CORS:** a API Flask so libera as origens listadas em `app.py` (hoje `https://broostore.netlify.app`, entre outras).
Se a nova loja for publicada em outro dominio, inclua-o nessa lista.

## Dependencias de backend

- `GET /api/cobrancas/<external_reference>/status` (aditivo): usado para detectar o pagamento do PIX. Se responder 404
  ou falhar, a tela degrada para a mensagem estatica "voce recebera um e-mail".
- `POST /api/cobrancas` deve continuar devolvendo `cobranca.external_reference`.
