/** Parsing defensivo das opcoes de frete devolvidas por POST /api/cotar-frete. */
import { toNumber } from './format';
import type { FreteOption } from '@/types';

/**
 * Aceita `{ status: 'success', opcoes: [{ id, empresa, nome, preco, prazo, destaque }] }`.
 * Ignora entradas invalidas (sem id ou preco), converte tipos e ordena do mais barato ao mais caro.
 */
export function parseFreteOptions(data: unknown): FreteOption[] {
  if (!data || typeof data !== 'object') return [];
  const d = data as Record<string, unknown>;
  if (d.status !== undefined && d.status !== 'success') return [];
  if (!Array.isArray(d.opcoes)) return [];

  const result: FreteOption[] = [];
  for (const raw of d.opcoes as unknown[]) {
    if (!raw || typeof raw !== 'object') continue;
    const o = raw as Record<string, unknown>;
    const id = typeof o.id === 'string' || typeof o.id === 'number' ? String(o.id).trim() : '';
    const preco = toNumber(o.preco);
    if (!id || preco === null || preco < 0) continue;
    const prazo = toNumber(o.prazo);
    result.push({
      id,
      empresa: typeof o.empresa === 'string' ? o.empresa.trim() : '',
      nome: typeof o.nome === 'string' ? o.nome.trim() : '',
      preco,
      prazo: prazo !== null && prazo > 0 ? Math.round(prazo) : null,
      destaque: typeof o.destaque === 'string' ? o.destaque.trim() : '',
    });
  }
  return result.sort((a, b) => a.preco - b.preco);
}

export function prazoLabel(prazo: number | null): string {
  if (!prazo) return 'Prazo a confirmar';
  return prazo === 1 ? '1 dia útil' : `${prazo} dias úteis`;
}

export function freteNome(o: FreteOption): string {
  return [o.empresa, o.nome].filter(Boolean).join(' ') || 'Frete';
}
