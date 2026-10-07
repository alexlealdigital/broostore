import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, createApiClient } from './api';

const BASE = 'https://api.test';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('api client', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('GET devolve o JSON tipado', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse({ status: 'success', id: 7, nome: 'Plano', preco: 19.9, tipo: 'assinatura' }));
    const api = createApiClient({ baseUrl: BASE, fetchImpl: fetchImpl as unknown as typeof fetch });
    const p = await api.getProduto(7);
    expect(p.nome).toBe('Plano');
    expect(fetchImpl).toHaveBeenCalledWith(`${BASE}/api/produto/7`, expect.objectContaining({ method: 'GET' }));
  });

  it('POST envia JSON e Content-Type', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse({ status: 'success', cupom: { id: 1, codigo: 'X' }, calculo: { valor_original: 10, desconto: 1, valor_final: 9 } }),
    );
    const api = createApiClient({ baseUrl: BASE, fetchImpl: fetchImpl as unknown as typeof fetch });
    await api.validarCupom({ codigo: 'X', produto_id: 1, valor_original: 10 });
    const [, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    expect(JSON.parse(init.body as string)).toEqual({ codigo: 'X', produto_id: 1, valor_original: 10 });
  });

  it('erro HTTP usa a mensagem do servidor', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse({ status: 'error', message: 'Cupom expirado' }, 400));
    const api = createApiClient({ baseUrl: BASE, fetchImpl: fetchImpl as unknown as typeof fetch });
    const err = await api.validarCupom({ codigo: 'X', produto_id: 1, valor_original: 10 }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ kind: 'http', status: 400, message: 'Cupom expirado' });
  });

  it('aceita "mensagem" (cartao) e tem fallback por status', async () => {
    const a = createApiClient({ baseUrl: BASE, fetchImpl: (async () => jsonResponse({ mensagem: 'Recusado' }, 400)) as unknown as typeof fetch });
    await expect(a.getProduto(1)).rejects.toMatchObject({ message: 'Recusado' });
    const b = createApiClient({ baseUrl: BASE, fetchImpl: (async () => new Response('<html>boom</html>', { status: 502 })) as unknown as typeof fetch });
    await expect(b.getProduto(1)).rejects.toMatchObject({ kind: 'http', status: 502, message: expect.stringContaining('servidor') });
  });

  it('corpo de sucesso que nao e JSON => erro de parse', async () => {
    const api = createApiClient({ baseUrl: BASE, fetchImpl: (async () => new Response('nao-json', { status: 200 })) as unknown as typeof fetch });
    await expect(api.getProduto(1)).rejects.toMatchObject({ kind: 'parse' });
  });

  it('falha de rede => erro "network"', async () => {
    const api = createApiClient({ baseUrl: BASE, fetchImpl: (async () => Promise.reject(new TypeError('Failed to fetch'))) as unknown as typeof fetch });
    await expect(api.getProduto(1)).rejects.toMatchObject({ kind: 'network' });
  });

  it('timeout aborta a requisicao e devolve erro "timeout"', async () => {
    const fetchImpl = vi.fn(
      (_url: string, init: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
        }),
    );
    const api = createApiClient({ baseUrl: BASE, fetchImpl: fetchImpl as unknown as typeof fetch });
    const promise = api.getProduto(1, { timeoutMs: 1000 });
    const assertion = expect(promise).rejects.toMatchObject({ kind: 'timeout' });
    await vi.advanceTimersByTimeAsync(1001);
    await assertion;
  });

  it('chama onSlow quando a resposta demora (servidor acordando) e nao chama se for rapida', async () => {
    let release: (r: Response) => void = () => undefined;
    const slowFetch = vi.fn(() => new Promise<Response>((resolve) => (release = resolve)));
    const api = createApiClient({ baseUrl: BASE, fetchImpl: slowFetch as unknown as typeof fetch });
    const onSlow = vi.fn();
    const promise = api.getProduto(1, { onSlow, slowAfterMs: 2000 });
    await vi.advanceTimersByTimeAsync(1500);
    expect(onSlow).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(600);
    expect(onSlow).toHaveBeenCalledTimes(1);
    release(jsonResponse({ id: 1, nome: 'x', preco: 1 }));
    await expect(promise).resolves.toMatchObject({ id: 1 });

    const fast = createApiClient({ baseUrl: BASE, fetchImpl: (async () => jsonResponse({ id: 1, nome: 'x', preco: 1 })) as unknown as typeof fetch });
    const onSlow2 = vi.fn();
    await fast.getProduto(1, { onSlow: onSlow2, slowAfterMs: 2000 });
    await vi.advanceTimersByTimeAsync(5000);
    expect(onSlow2).not.toHaveBeenCalled();
  });

  it('cancelamento externo vira erro "aborted"', async () => {
    const fetchImpl = vi.fn(
      (_url: string, init: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
        }),
    );
    const api = createApiClient({ baseUrl: BASE, fetchImpl: fetchImpl as unknown as typeof fetch });
    const controller = new AbortController();
    const promise = api.getProduto(1, { signal: controller.signal });
    controller.abort();
    await expect(promise).rejects.toMatchObject({ kind: 'aborted' });
  });

  describe('cotarFrete', () => {
    it('devolve opcoes parseadas e ordenadas', async () => {
      const fetchImpl = vi.fn(async () =>
        jsonResponse({ status: 'success', opcoes: [{ id: 2, empresa: 'A', nome: 'Rapido', preco: 50, prazo: 2 }, { id: 1, empresa: 'A', nome: 'Barato', preco: 20, prazo: 7 }] }),
      );
      const api = createApiClient({ baseUrl: BASE, fetchImpl: fetchImpl as unknown as typeof fetch });
      const opts = await api.cotarFrete('01310100', 5);
      expect(opts.map((o) => o.id)).toEqual(['1', '2']);
      const [, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
      expect(JSON.parse(init.body as string)).toEqual({ cep_destino: '01310100', product_id: 5 });
    });
    it('lista vazia vira erro com mensagem amigavel', async () => {
      const api = createApiClient({ baseUrl: BASE, fetchImpl: (async () => jsonResponse({ status: 'success', opcoes: [] })) as unknown as typeof fetch });
      await expect(api.cotarFrete('01310100', 5)).rejects.toMatchObject({ message: 'Nenhuma opção de frete para este CEP.' });
    });
    it('propaga a mensagem do servidor em erro HTTP', async () => {
      const api = createApiClient({ baseUrl: BASE, fetchImpl: (async () => jsonResponse({ status: 'error', message: 'Produto sem medidas cadastradas: peso_kg.' }, 422)) as unknown as typeof fetch });
      await expect(api.cotarFrete('01310100', 5)).rejects.toMatchObject({ status: 422, message: 'Produto sem medidas cadastradas: peso_kg.' });
    });
  });

  describe('statusCobranca (endpoint aditivo)', () => {
    it('le {status, pago}', async () => {
      const api = createApiClient({ baseUrl: BASE, fetchImpl: (async () => jsonResponse({ status: 'approved', pago: true })) as unknown as typeof fetch });
      await expect(api.statusCobranca('abc')).resolves.toEqual({ supported: true, data: { status: 'approved', pago: true } });
    });
    it('404 => nao suportado (degrada em silencio)', async () => {
      const api = createApiClient({ baseUrl: BASE, fetchImpl: (async () => new Response('Not Found', { status: 404 })) as unknown as typeof fetch });
      await expect(api.statusCobranca('abc')).resolves.toEqual({ supported: false, reason: 'not-found' });
    });
    it('erro de rede/500 => nao suportado com motivo "error" (nunca lanca)', async () => {
      const a = createApiClient({ baseUrl: BASE, fetchImpl: (async () => Promise.reject(new TypeError('x'))) as unknown as typeof fetch });
      await expect(a.statusCobranca('abc')).resolves.toEqual({ supported: false, reason: 'error' });
      const b = createApiClient({ baseUrl: BASE, fetchImpl: (async () => jsonResponse({}, 500)) as unknown as typeof fetch });
      await expect(b.statusCobranca('abc')).resolves.toEqual({ supported: false, reason: 'error' });
    });
    it('codifica a referencia na URL', async () => {
      const fetchImpl = vi.fn(async () => jsonResponse({ status: 'pending', pago: false }));
      const api = createApiClient({ baseUrl: BASE, fetchImpl: fetchImpl as unknown as typeof fetch });
      await api.statusCobranca('12:ab/cd');
      expect((fetchImpl.mock.calls[0] as unknown as [string])[0]).toBe(`${BASE}/api/cobrancas/12%3Aab%2Fcd/status`);
    });
  });
});
