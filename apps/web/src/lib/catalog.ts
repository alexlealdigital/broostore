/** Busca, filtros e ordenacao do catalogo (funcoes puras, testaveis). */
import { discountPercent } from './format';
import type { Area, Product, RatingsMap } from '@/types';

export type SortKey = 'relevancia' | 'menor-preco' | 'maior-preco' | 'mais-novos';

export const SORT_OPTIONS: ReadonlyArray<{ value: SortKey; label: string }> = [
  { value: 'relevancia', label: 'Relevância' },
  { value: 'menor-preco', label: 'Menor preço' },
  { value: 'maior-preco', label: 'Maior preço' },
  { value: 'mais-novos', label: 'Mais novos' },
];

export function parseSort(value: string | null | undefined): SortKey {
  return SORT_OPTIONS.some((o) => o.value === value) ? (value as SortKey) : 'relevancia';
}

/** minusculas, sem acentos e sem espacos duplicados: "Ação  Rápida" -> "acao rapida". */
export function normalizeText(value: string): string {
  return (value ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

/** Pontuacao de relevancia para uma busca (0 = nao combina). Todos os termos precisam aparecer. */
export function matchScore(product: Product, query: string): number {
  const terms = normalizeText(query).split(' ').filter(Boolean);
  if (terms.length === 0) return 1;
  const title = normalizeText(product.title);
  const author = normalizeText(product.author);
  const category = normalizeText(product.category);
  const desc = normalizeText(product.descricao);
  let total = 0;
  for (const term of terms) {
    let s = 0;
    if (title.startsWith(term)) s = 10;
    else if (title.includes(term)) s = 8;
    else if (author.includes(term)) s = 5;
    else if (category.includes(term)) s = 3;
    else if (desc.includes(term)) s = 1;
    if (s === 0) return 0;
    total += s;
  }
  return total;
}

export interface CatalogFilters {
  area: Area | null;
  query: string;
  category: string | null;
  /** inclui produtos 18+ ? */
  includeAdult: boolean;
}

export function filterProducts(products: Product[], f: CatalogFilters): Product[] {
  return products.filter((p) => {
    if (f.area && p.area !== f.area) return false;
    if (f.category && p.category !== f.category) return false;
    if (!f.includeAdult && p.classificacao === '18') return false;
    return matchScore(p, f.query) > 0;
  });
}

/** Qualidade "social": nota media ponderada pelo volume de avaliacoes. */
function qualityScore(p: Product, ratings: RatingsMap): number {
  const r = ratings[String(p.id)];
  return r ? r.average * Math.log(1 + r.count) : 0;
}

export function sortProducts(products: Product[], sort: SortKey, query: string, ratings: RatingsMap): Product[] {
  // O catalogo ja chega "mais novos primeiro"; o indice original serve de desempate estavel.
  const indexed = products.map((p, i) => ({ p, i }));
  const byIndex = (a: { i: number }, b: { i: number }) => a.i - b.i;

  switch (sort) {
    case 'menor-preco':
      indexed.sort((a, b) => a.p.price - b.p.price || byIndex(a, b));
      break;
    case 'maior-preco':
      indexed.sort((a, b) => b.p.price - a.p.price || byIndex(a, b));
      break;
    case 'mais-novos':
      indexed.sort((a, b) => {
        const da = a.p.createdAt ? Date.parse(a.p.createdAt) : NaN;
        const db = b.p.createdAt ? Date.parse(b.p.createdAt) : NaN;
        if (!Number.isNaN(da) && !Number.isNaN(db) && da !== db) return db - da;
        return byIndex(a, b);
      });
      break;
    default: {
      const hasQuery = normalizeText(query).length > 0;
      indexed.sort((a, b) => {
        const sa = hasQuery ? matchScore(a.p, query) : 0;
        const sb = hasQuery ? matchScore(b.p, query) : 0;
        if (sa !== sb) return sb - sa;
        const qa = qualityScore(a.p, ratings) + discountPercent(a.p.price, a.p.originalPrice) / 50;
        const qb = qualityScore(b.p, ratings) + discountPercent(b.p.price, b.p.originalPrice) / 50;
        if (qa !== qb) return qb - qa;
        return byIndex(a, b);
      });
    }
  }
  return indexed.map((x) => x.p);
}

/** Categorias (campo `category`) presentes na lista, em ordem alfabetica, com contagem. */
export function categoriesOf(products: Product[]): Array<{ name: string; count: number }> {
  const map = new Map<string, number>();
  for (const p of products) map.set(p.category, (map.get(p.category) ?? 0) + 1);
  return [...map.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
}

export function countByArea(products: Product[], includeAdult: boolean): Record<Area, number> {
  const out: Record<Area, number> = { digitais: 0, fisicos: 0, aplicativos: 0 };
  for (const p of products) {
    if (!includeAdult && p.classificacao === '18') continue;
    out[p.area] += 1;
  }
  return out;
}

/** Produtos relacionados: mesma area, exclui o atual, prioriza mesma categoria/autor. */
export function relatedProducts(all: Product[], current: Product, includeAdult: boolean, limit = 4): Product[] {
  return all
    .filter((p) => p.id !== current.id && p.area === current.area && (includeAdult || p.classificacao !== '18'))
    .map((p, i) => ({
      p,
      i,
      score: (p.category === current.category ? 2 : 0) + (p.author && p.author === current.author ? 1 : 0),
    }))
    .sort((a, b) => b.score - a.score || a.i - b.i)
    .slice(0, limit)
    .map((x) => x.p);
}
