/**
 * Cliente tipado da API de pagamentos (Flask no Render).
 *
 * - timeout generoso (o plano free pode levar 30-60 s para acordar);
 * - `onSlow` e chamado se a resposta demorar (para mostrar "acordando o servidor");
 * - erros normalizados em `ApiError` com `kind` e mensagem em portugues.
 */
import { API_SLOW_AFTER_MS, API_TIMEOUT_MS, config } from './config';
import { parseFreteOptions } from './frete';
import type {
  ApiProdutoResponse,
  CardPayload,
  CardResponse,
  CobrancaStatusResponse,
  FreteOption,
  PixPayload,
  PixResponse,
  ValidarCupomResponse,
} from '@/types';

export type ApiErrorKind = 'timeout' | 'network' | 'http' | 'parse' | 'aborted';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly data: unknown;

  constructor(kind: ApiErrorKind, message: string, status: number | null = null, data: unknown = null) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    this.data = data;
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  /** Timeout em ms (padrao API_TIMEOUT_MS). */
  timeoutMs?: number;
  /** Chamado uma vez se a resposta passar de `slowAfterMs`. */
  onSlow?: () => void;
  slowAfterMs?: number;
  /** Cancelamento externo (ex.: desmontar componente). */
  signal?: AbortSignal;
}

export interface ApiClientOptions {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
}

function messageFromBody(data: unknown): string | null {
  if (data && typeof data === 'object') {
    const d = data as Record<string, unknown>;
    for (const key of ['message', 'mensagem', 'error']) {
      const v = d[key];
      if (typeof v === 'string' && v.trim()) return v.trim();
    }
  }
  return null;
}

function defaultHttpMessage(status: number): string {
  if (status === 404) return 'Não encontramos o que você procurou.';
  if (status === 429) return 'Muitas tentativas. Aguarde um instante e tente de novo.';
  if (status >= 500) return 'O servidor teve um problema. Tente novamente em instantes.';
  return 'Não foi possível concluir a solicitação.';
}

export function createApiClient({ baseUrl = config.apiUrl, fetchImpl }: ApiClientOptions = {}) {
  const doFetch = (input: string, init: RequestInit): Promise<Response> =>
    (fetchImpl ?? globalThis.fetch.bind(globalThis))(input, init);

  async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    const { method = 'GET', body, timeoutMs = API_TIMEOUT_MS, onSlow, slowAfterMs = API_SLOW_AFTER_MS, signal } = opts;

    const controller = new AbortController();
    let timedOut = false;
    const timeoutId = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
    const slowId = onSlow ? setTimeout(onSlow, slowAfterMs) : null;

    const onExternalAbort = () => controller.abort();
    if (signal) {
      if (signal.aborted) controller.abort();
      else signal.addEventListener('abort', onExternalAbort, { once: true });
    }

    try {
      let response: Response;
      try {
        response = await doFetch(`${baseUrl}${path}`, {
          method,
          headers: body !== undefined ? { 'Content-Type': 'application/json', Accept: 'application/json' } : { Accept: 'application/json' },
          body: body !== undefined ? JSON.stringify(body) : undefined,
          signal: controller.signal,
        });
      } catch (err) {
        if (timedOut) {
          throw new ApiError('timeout', 'O servidor demorou demais para responder. Tente novamente.');
        }
        if (controller.signal.aborted || (err instanceof DOMException && err.name === 'AbortError')) {
          throw new ApiError('aborted', 'Solicitação cancelada.');
        }
        throw new ApiError('network', 'Sem conexão com o servidor. Verifique sua internet e tente novamente.');
      }

      let data: unknown = null;
      const text = await response.text().catch(() => '');
      if (text) {
        try {
          data = JSON.parse(text);
        } catch {
          if (response.ok) throw new ApiError('parse', 'Resposta inesperada do servidor.', response.status);
          data = null;
        }
      }

      if (!response.ok) {
        throw new ApiError('http', messageFromBody(data) ?? defaultHttpMessage(response.status), response.status, data);
      }
      return data as T;
    } finally {
      clearTimeout(timeoutId);
      if (slowId) clearTimeout(slowId);
      signal?.removeEventListener('abort', onExternalAbort);
    }
  }

  return {
    request,

    /** GET /api/produto/<id> (usado como fallback para produtos que nao estao no Supabase, ex.: planos). */
    getProduto: (id: number, opts?: RequestOptions) => request<ApiProdutoResponse>(`/api/produto/${id}`, opts),

    /** POST /api/validar-cupom */
    validarCupom: (
      payload: { codigo: string; produto_id: number; valor_original: number },
      opts?: RequestOptions,
    ) => request<ValidarCupomResponse>('/api/validar-cupom', { ...opts, method: 'POST', body: payload }),

    /** POST /api/cotar-frete -> opcoes de frete ja validadas/ordenadas. */
    async cotarFrete(cepDestino: string, productId: number, opts?: RequestOptions): Promise<FreteOption[]> {
      const data = await request<unknown>('/api/cotar-frete', {
        ...opts,
        method: 'POST',
        body: { cep_destino: cepDestino, product_id: productId },
      });
      const options = parseFreteOptions(data);
      if (options.length === 0) {
        throw new ApiError('http', messageFromBody(data) ?? 'Nenhuma opção de frete para este CEP.', 200, data);
      }
      return options;
    },

    /** POST /api/cobrancas (PIX). NUNCA chamado em testes sem mock. */
    criarCobrancaPix: (payload: PixPayload, opts?: RequestOptions) =>
      request<PixResponse>('/api/cobrancas', { ...opts, method: 'POST', body: payload }),

    /** POST /api/cobrancas-cartao. Recebe apenas o token do cartao. */
    criarCobrancaCartao: (payload: CardPayload, opts?: RequestOptions) =>
      request<CardResponse>('/api/cobrancas-cartao', { ...opts, method: 'POST', body: payload }),

    /**
     * GET /api/cobrancas/<ref>/status (endpoint aditivo).
     * Retorna `{ supported: false }` em 404/erro de rota para o chamador degradar em silencio.
     */
    async statusCobranca(
      externalReference: string,
      opts?: RequestOptions,
    ): Promise<{ supported: true; data: CobrancaStatusResponse } | { supported: false; reason: 'not-found' | 'error' }> {
      try {
        const data = await request<unknown>(`/api/cobrancas/${encodeURIComponent(externalReference)}/status`, {
          timeoutMs: 15_000,
          ...opts,
        });
        if (!data || typeof data !== 'object') return { supported: false, reason: 'error' };
        const d = data as Record<string, unknown>;
        return {
          supported: true,
          data: { status: typeof d.status === 'string' ? d.status : 'pending', pago: d.pago === true },
        };
      } catch (err) {
        if (err instanceof ApiError && err.kind === 'aborted') throw err;
        if (err instanceof ApiError && (err.status === 404 || err.status === 405)) {
          return { supported: false, reason: 'not-found' };
        }
        return { supported: false, reason: 'error' };
      }
    },
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;

/** Instancia padrao usada pelo app. */
export const api: ApiClient = createApiClient();
