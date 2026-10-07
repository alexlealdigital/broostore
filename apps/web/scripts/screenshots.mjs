// Testes visuais com Playwright + Chromium usando APENAS dados ficticios (mocks).
// Todas as chamadas de rede (Supabase, API de pagamentos, ViaCEP, SDK do Mercado Pago) sao interceptadas:
// nenhuma cobranca real e criada.
//
// Uso:
//   npm run build && npx vite preview --port 4173 &
//   node scripts/screenshots.mjs [pasta-de-saida]
//
// Requer o pacote `playwright` (instalado globalmente ou localmente) e um Chromium disponivel
// (PLAYWRIGHT_BROWSERS_PATH ou CHROMIUM_PATH).
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import { deflateSync } from 'node:zlib';
import { existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { freteOptions, products, reviews } from './mock-data.mjs';

async function loadPlaywright() {
  try {
    return await import('playwright');
  } catch {
    const root = execSync('npm root -g').toString().trim();
    return createRequire(`${root}/`)('playwright');
  }
}

const BASE = process.env.BASE_URL ?? 'http://localhost:4173';
const OUT = path.resolve(process.argv[2] ?? 'docs/screenshots');
mkdirSync(OUT, { recursive: true });

const CORS = {
  'access-control-allow-origin': '*',
  'access-control-allow-headers': '*',
  'access-control-allow-methods': 'GET,POST,OPTIONS',
};

const json = (route, body, status = 200) =>
  route.fulfill({ status, contentType: 'application/json', headers: CORS, body: JSON.stringify(body) });

/** PNG minimo (RGB 8 bits) sem dependencias, para gerar a imagem do QR ficticio. */
function encodePng(raw, size) {
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  const crc32 = (buf) => {
    let c = 0xffffffff;
    for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const chunk = (type, data) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(td));
    return Buffer.concat([len, td, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // RGB
  const rows = Buffer.alloc((size * 3 + 1) * size);
  for (let y = 0; y < size; y++) {
    rows[y * (size * 3 + 1)] = 0;
    raw.copy(rows, y * (size * 3 + 1) + 1, y * size * 3, (y + 1) * size * 3);
  }
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(rows)),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

/** Imagem de "QR" ficticio (nao escaneavel) so para a captura de tela. */
function fakeQrBase64() {
  const n = 29;
  const cell = 8;
  const size = n * cell;
  const raw = Buffer.alloc(size * size * 3, 255);
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const fill = (cx, cy, v) => {
    for (let y = 0; y < cell; y++)
      for (let x = 0; x < cell; x++) {
        const o = ((cy * cell + y) * size + cx * cell + x) * 3;
        raw[o] = raw[o + 1] = raw[o + 2] = v;
      }
  };
  for (let cy = 0; cy < n; cy++) for (let cx = 0; cx < n; cx++) if (rnd() > 0.52) fill(cx, cy, 0);
  const finder = (ox, oy) => {
    for (let y = -1; y < 8; y++)
      for (let x = -1; x < 8; x++) {
        const inside = x >= 0 && x <= 6 && y >= 0 && y <= 6;
        const edge = x === 0 || y === 0 || x === 6 || y === 6;
        const core = x >= 2 && x <= 4 && y >= 2 && y <= 4;
        if (ox + x < 0 || oy + y < 0 || ox + x >= n || oy + y >= n) continue;
        fill(ox + x, oy + y, inside && (edge || core) ? 0 : 255);
      }
  };
  finder(0, 0);
  finder(n - 7, 0);
  finder(0, n - 7);
  return encodePng(raw, size).toString('base64');
}

const FAKE_MP_SDK = `
window.MercadoPago = class {
  constructor(key, opts) { this.key = key; }
  async getPaymentMethods({ bin }) { return { results: [{ id: 'visa', name: 'Visa', thumbnail: '' }] }; }
  async getIssuers() { return [{ id: 25 }]; }
  async getInstallments({ amount }) {
    const a = Number(amount);
    return [{ payer_costs: [1, 2, 3, 6, 12].map((n) => ({ installments: n, installment_amount: a / n, recommended_message: n + 'x de R$ ' + (a / n).toFixed(2).replace('.', ',') + (n <= 3 ? ' sem juros' : '') })) }];
  }
  async createCardToken() { return { id: 'tok_mock_123' }; }
};`;

export async function installMocks(context, opts = {}) {
  const qr = fakeQrBase64();
  const state = { statusPaid: false, calls: [] };

  await context.route('**/rest/v1/**', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    if (req.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: CORS });
    const table = url.pathname.split('/').pop();
    if (opts.supabaseError) return json(route, { message: 'mock error' }, 500);
    if (req.method() === 'POST') return route.fulfill({ status: 201, headers: CORS, body: '' });
    if (table === 'products') {
      let list = products.filter((p) => p.active !== false && p.id !== 99);
      const idEq = url.searchParams.get('id');
      if (idEq?.startsWith('eq.')) list = list.filter((p) => String(p.id) === idEq.slice(3));
      const accept = req.headers()['accept'] ?? '';
      if (accept.includes('pgrst.object')) {
        return list[0] ? json(route, list[0]) : json(route, { message: 'not found' }, 406);
      }
      return json(route, list);
    }
    if (table === 'reviews') {
      const pid = url.searchParams.get('product_id');
      const list = pid?.startsWith('eq.') ? reviews.filter((r) => String(r.product_id) === pid.slice(3)) : reviews;
      return json(route, list);
    }
    return json(route, []);
  });

  await context.route(/onrender\.com\//, async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    if (req.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: CORS });
    const p = url.pathname;
    const body = req.postData() ? JSON.parse(req.postData()) : null;
    state.calls.push({ method: req.method(), path: p, body });
    if (p.startsWith('/api/produto/')) {
      const id = Number(p.split('/').pop());
      return id === 500
        ? json(route, { status: 'success', id: 500, nome: 'BrooStock Plano Anual', preco: 199, tipo: 'assinatura' })
        : json(route, { status: 'error', message: 'Produto não encontrado.' }, 404);
    }
    if (p === '/api/validar-cupom') {
      return body?.codigo === 'BROO10'
        ? json(route, {
            status: 'success',
            cupom: { id: 4, codigo: 'BROO10', tipo: 'percentual', valor: 10 },
            calculo: { valor_original: body.valor_original, desconto: body.valor_original * 0.1, valor_final: body.valor_original * 0.9, percentual_aplicado: 10 },
          })
        : json(route, { status: 'error', message: 'Cupom não encontrado' }, 404);
    }
    if (p === '/api/cotar-frete') return json(route, { status: 'success', opcoes: freteOptions, total_disponivel: 6 });
    if (p === '/api/cobrancas') {
      const product = products.find((x) => x.id === body.product_id);
      const total = (product?.price ?? 50) + (body.frete ?? 0);
      return json(
        route,
        {
          status: 'success',
          qr_code_base64: qr,
          qr_code_text: '00020126580014br.gov.bcb.pix0136123e4567-e89b-12d3-a456-426614174000520400005303986540' + total.toFixed(2) + '5802BR5909BrooStore6009SAO PAULO62070503***6304ABCD',
          payment_id: 111,
          cobranca: { external_reference: 'mock-ref-1' },
          total_cobrado: total,
        },
        201,
      );
    }
    if (p === '/api/cobrancas-cartao') {
      return json(route, { status: 'approved', mensagem: 'Pagamento aprovado! Você receberá o produto por e-mail em instantes.', total_cobrado: 59 }, 201);
    }
    if (p.startsWith('/api/cobrancas/') && p.endsWith('/status')) {
      if (opts.noStatusEndpoint) return json(route, { message: 'not found' }, 404);
      return json(route, { status: state.statusPaid ? 'approved' : 'pending', pago: state.statusPaid });
    }
    return json(route, { message: 'rota nao mockada' }, 404);
  });

  await context.route('https://viacep.com.br/**', (route) =>
    json(route, { logradouro: 'Avenida Paulista', bairro: 'Bela Vista', localidade: 'São Paulo', uf: 'SP' }),
  );
  await context.route('https://sdk.mercadopago.com/**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/javascript', headers: CORS, body: FAKE_MP_SDK }),
  );
  return state;
}

function findChromium() {
  const candidates = [
    process.env.CHROMIUM_PATH,
    '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    '/opt/pw-browsers/chromium/chrome',
  ].filter(Boolean);
  return candidates.find((c) => existsSync(c));
}

async function main() {
  const { chromium } = await loadPlaywright();
  const browser = await chromium.launch({ executablePath: findChromium(), args: ['--no-sandbox'] });
  const widths = [
    { name: 'desktop', width: 1280, height: 900 },
    { name: 'mobile', width: 390, height: 844 },
  ];
  const results = [];

  for (const vp of widths) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      deviceScaleFactor: 1,
      locale: 'pt-BR',
      permissions: ['clipboard-read', 'clipboard-write'],
    });
    const state = await installMocks(context);
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(String(e)));
    page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));

    const shot = async (name, { full = true, wait } = {}) => {
      if (wait) await page.waitForSelector(wait, { timeout: 15000 });
      // percorre a pagina para disparar o carregamento das imagens lazy
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += 500) {
          window.scrollTo(0, y);
          await new Promise((r) => setTimeout(r, 40));
        }
        window.scrollTo(0, 0);
      });
      await page.waitForTimeout(400);
      const file = path.join(OUT, `${vp.name}-${name}.png`);
      await page.screenshot({ path: file, fullPage: full });
      results.push(file);
    };
    const go = (p) => page.goto(BASE + p, { waitUntil: 'networkidle' });

    await go('/');
    await shot('01-home', { wait: 'article' });

    await go('/loja');
    await shot('02-loja-todos', { wait: 'article' });
    await go('/loja?area=digitais');
    await shot('03-loja-digitais', { wait: 'article' });
    await go('/loja?area=fisicos');
    await shot('04-loja-fisicos', { wait: 'article' });
    await go('/loja?area=aplicativos');
    await shot('05-loja-aplicativos', { wait: 'article' });
    await go('/loja?q=zzzz');
    await shot('06-loja-vazio', { wait: 'text=Nenhum produto encontrado' });

    await go('/produto/1');
    await shot('07-produto-digital', { wait: 'h1' });
    await go('/produto/7');
    await shot('08-produto-fisico', { wait: 'h1' });
    await go('/produto/12');
    await shot('09-produto-app', { wait: 'h1' });

    await go('/comprar/1');
    await page.fill('#ck-nome', 'Ana Souza');
    await page.fill('#ck-email', 'ana@exemplo.com');
    await page.fill('#ck-telefone', '11999998888');
    await shot('10-checkout-digital', { wait: '#ck-nome' });
    await page.click('button:has-text("Gerar QR Code PIX")');
    await page.waitForSelector('text=Pague com PIX');
    await shot('11-checkout-pix', { wait: 'img[alt^="QR Code"]' });
    await page.click('button:has-text("Copiar código")');
    await page.waitForSelector('text=Código copiado');
    state.statusPaid = true;
    await page.waitForSelector('text=Pagamento confirmado', { timeout: 15000 });
    await shot('12-checkout-pago');

    await go('/comprar/7');
    await page.fill('#ck-nome', 'Ana Souza');
    await page.fill('#ck-email', 'ana@exemplo.com');
    await page.fill('#ck-telefone', '11999998888');
    await page.fill('#ck-cep', '01310100');
    await page.waitForSelector('input[name="frete"]');
    await page.fill('#ck-numero', '1000');
    await shot('13-checkout-fisico-frete', { wait: '#ck-numero' });

    await go('/comprar?produto=12&email=cliente%40broostock.com&nome=Cliente%20App&return=https%3A%2F%2Fbrootechstock.netlify.app%2F');
    await page.waitForSelector('#ck-nome');
    await page.fill('#ck-telefone', '11999998888');
    await page.fill('#ck-cupom', 'BROO10');
    await page.click('button:has-text("Aplicar")');
    await page.waitForSelector('text=Cupom BROO10 aplicado');
    await page.click('[role="tab"]:has-text("Cartão")');
    await page.fill('#ck-card-number', '4111111111111111');
    await page.waitForSelector('#ck-card-installments');
    await page.fill('#ck-card-expiry', '1230');
    await page.fill('#ck-card-cvv', '123');
    await page.fill('#ck-card-name', 'Cliente Teste');
    await page.fill('#ck-card-cpf', '12345678909');
    await shot('14-checkout-cartao');

    await go('/autores');
    await shot('15-autores', { wait: 'h1' });
    await go('/contato');
    await shot('16-contato', { wait: 'h1' });
    await go('/termos');
    await shot('17-termos', { wait: 'h1' });
    await go('/rota-que-nao-existe');
    await shot('18-404', { wait: 'text=Página não encontrada' });

    // estado de erro do Supabase
    const ctx2 = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, locale: 'pt-BR' });
    await installMocks(ctx2, { supabaseError: true });
    const p2 = await ctx2.newPage();
    await p2.goto(BASE + '/loja', { waitUntil: 'networkidle' });
    await p2.waitForSelector('text=Não conseguimos carregar os produtos');
    await p2.screenshot({ path: path.join(OUT, `${vp.name}-19-erro.png`) });
    await ctx2.close();

    if (errors.length) console.log(`[${vp.name}] erros de console/pagina:`, errors);
    await context.close();
  }
  await browser.close();
  console.log(`${results.length} capturas em ${OUT}`);
}

if (process.argv[1] && import.meta.url === new URL(`file://${path.resolve(process.argv[1])}`).href) {
  main().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
