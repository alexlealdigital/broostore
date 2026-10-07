/** Autopreenchimento de endereco via ViaCEP (https://viacep.com.br). */
import { onlyDigits } from './format';

export interface ViaCepAddress {
  rua: string;
  bairro: string;
  cidade: string;
  estado: string;
}

/**
 * Retorna o endereco do CEP, `null` se o CEP nao existe, e lanca erro se o servico falhar.
 * `fetchImpl` e injetavel para testes.
 */
export async function lookupCep(
  cep: string,
  opts: { signal?: AbortSignal; fetchImpl?: typeof fetch } = {},
): Promise<ViaCepAddress | null> {
  const digits = onlyDigits(cep);
  if (digits.length !== 8) return null;
  const doFetch = opts.fetchImpl ?? globalThis.fetch.bind(globalThis);
  const res = await doFetch(`https://viacep.com.br/ws/${digits}/json/`, { signal: opts.signal });
  if (!res.ok) throw new Error(`ViaCEP respondeu ${res.status}`);
  const data = (await res.json()) as Record<string, unknown>;
  if (data.erro) return null;
  const str = (v: unknown) => (typeof v === 'string' ? v : '');
  return {
    rua: str(data.logradouro),
    bairro: str(data.bairro),
    cidade: str(data.localidade),
    estado: str(data.uf).toUpperCase(),
  };
}
