# Virada para o repositorio novo (passo a passo)

Objetivo: colocar o monorepo no ar **sem derrubar a loja que funciona hoje**. Ate o ultimo passo,
o sistema antigo continua intacto. Cada passo tem um jeito de voltar atras.

## 0. Antes de tudo (so leitura, 5 min)

1. No Supabase da BrooStore, rode `docs/sql/01_diagnostico_broostore.sql` e me envie o resultado.
2. No painel do Render, anote (sem me mandar segredos): o valor de `SMTP_PORT`, e **para onde aponta o
   `DATABASE_URL`** (Postgres do Render ou do Supabase). A porta 465 exige SSL direto; o codigo usa
   STARTTLS, que funciona com 587. Se estiver 465 e os e-mails ja saem hoje, nao mexa; me avise.

## 1. Subir o codigo para o GitHub

1. Crie o repositorio vazio `broostore` (privado) no GitHub.
2. Extraia o zip, abra a pasta e de dois cliques em `push-github.bat`. Informe a URL do repositorio.
3. Confira no GitHub: pastas `apps/web`, `apps/api`, `docs`.

## 2. Frontend no Netlify (sem risco: e um site novo)

1. Netlify -> Add new site -> Import from Git -> repositorio `broostore`. O `netlify.toml` da raiz ja define tudo.
2. (Opcional) Variaveis `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_MP_PUBLIC_KEY`.
   Os padroes ja apontam para a producao atual.
3. Abra o site novo (`algo.netlify.app`) e navegue: Home, Loja (3 abas), Produto.
   **O checkout so funciona de verdade depois do passo 3 (CORS)**, ou se o dominio for `broostore.netlify.app`.
4. Se o dominio novo for diferente dos ja liberados, adicione no Render a variavel
   `CORS_EXTRA_ORIGINS=https://seu-site-novo.netlify.app` (varios separados por virgula).

## 3. Banco: coluna nova (OBRIGATORIO antes de trocar o Render)

Rode `docs/sql/03_pre_cutover_render.sql` **no banco do `DATABASE_URL`**. Sem isso, a entrega de chave
de jogos/apps falha. E seguro: nao altera dados.

## 4. Produto de teste de R$ 1,00

Rode `docs/sql/02_produto_teste_1_real.sql` no Supabase. Depois teste em `/comprar/98`.

## 5. API no Render (o passo que mexe em producao)

Recomendado: **criar um servico novo** em paralelo, nao editar o antigo.

1. Render -> New Web Service -> repositorio `broostore`, **Root Directory = `apps/api`**.
   Build e Start Command: copie os do servico antigo (detalhes em `apps/api/docs/RENDER.md`; start: `gunicorn app:app --timeout 300 --workers 2`).
2. Copie TODAS as variaveis de ambiente do servico antigo (inclusive o worker e o cron).
3. Crie o worker (`python worker.py`) apontando para o mesmo repo/pasta, e o cron `python notificar_expiracao.py`.
4. Teste o servico novo pela URL dele: `GET /api/produto/98` deve responder JSON.
5. Aponte `VITE_API_URL` do site novo para a URL do servico novo e faca os testes do passo 6.
6. So quando tudo estiver validado: no Mercado Pago, troque a URL de webhook para o servico novo
   (e desligue o antigo depois de alguns dias).

**Rollback:** a URL antiga continua viva ate voce desliga-la. Voltar = apontar `VITE_API_URL` e o webhook de volta.

## 6. Testes reais com valor baixo (voce executa)

Use o produto 98 (R$ 1,00). Marque cada item:

- [ ] PIX: gerar QR, pagar, a tela muda para "Pagamento confirmado" sozinha (polling de 4 s) e o e-mail chega.
- [ ] Cartao de credito: aprovado, e-mail chega. Tente tambem um cartao recusado: mensagem amigavel.
- [ ] Cupom invalido: aviso claro, valor nao muda.
- [ ] Um produto **fisico** barato: CEP preenche o endereco, frete aparece, pedido registrado.
- [ ] Um **jogo/app**: chave de licenca chega por e-mail.
- [ ] Celular real (Android/iPhone): checkout completo.
- [ ] Servidor "dormindo" (Render gratis): primeira chamada mostra "acordando o servidor", sem erro.

Se algo falhar, me envie o print + o horario; os logs do Render dizem o resto.

## 7. Endurecer (depois dos testes)

- `WEBHOOK_VALIDATE_SIGNATURE=true` (com `WEBHOOK_SECRET` configurado no Render e no Mercado Pago).
  Confirme com um PIX de R$ 1,00 que o webhook continua sendo aceito; se parar, volte para `false`.
- Desative o produto de teste (bloco "DESATIVAR" do SQL 02).
- Dominio proprio no Netlify e atualizacao do `og:image` para a URL absoluta.
