import { describe, expect, it } from 'vitest';
import {
  categoriesOf,
  countByArea,
  filterProducts,
  matchScore,
  normalizeText,
  parseSort,
  relatedProducts,
  sortProducts,
} from './catalog';
import { normalizeProduct } from './products';
import type { Product, ProductRow } from '@/types';

function make(row: ProductRow): Product {
  const p = normalizeProduct(row);
  if (!p) throw new Error('fixture invalida');
  return p;
}

const products: Product[] = [
  make({ id: 1, title: 'Guia da Eleição 2026', author: 'Ana Souza', price: 29.9, original_price: 49.9, category: 'Política', tipo: 'ebook', created_at: '2026-05-01' }),
  make({ id: 2, title: 'Livro Impresso: Estratégia', author: 'Bruno Lima', price: 79, category: 'Política', tipo: 'fisico', created_at: '2026-04-01' }),
  make({ id: 3, title: 'Fighter 3D', author: 'Lizards Games', price: 9.9, category: 'Games', tipo: 'game', created_at: '2026-06-01' }),
  make({ id: 4, title: 'Receitas Rápidas', author: 'Carla', price: 19.9, category: 'Culinária', tipo: 'ebook', classificacao: '18', created_at: '2026-03-01' }),
  make({ id: 5, title: 'BrooStock Pro', author: 'Broo', price: 59, category: 'Apps', tipo: 'assinatura', created_at: '2026-02-01' }),
];

describe('normalizeText', () => {
  it('remove acentos, caixa e espacos extras', () => {
    expect(normalizeText('  Ação   RÁPIDA ')).toBe('acao rapida');
  });
});

describe('busca', () => {
  it('ignora acentos e caixa', () => {
    expect(matchScore(products[0]!, 'eleicao')).toBeGreaterThan(0);
    expect(matchScore(products[0]!, 'ELEIÇÃO')).toBeGreaterThan(0);
  });
  it('exige todos os termos', () => {
    expect(matchScore(products[0]!, 'guia eleicao')).toBeGreaterThan(0);
    expect(matchScore(products[0]!, 'guia xyz')).toBe(0);
  });
  it('titulo vale mais que autor', () => {
    expect(matchScore(products[2]!, 'fighter')).toBeGreaterThan(matchScore(products[2]!, 'lizards'));
  });
  it('busca vazia combina com tudo', () => {
    expect(matchScore(products[0]!, '  ')).toBe(1);
  });
});

describe('filterProducts', () => {
  const base = { area: null, query: '', category: null, includeAdult: true } as const;
  it('por area', () => {
    expect(filterProducts(products, { ...base, area: 'aplicativos' }).map((p) => p.id)).toEqual([3, 5]);
    expect(filterProducts(products, { ...base, area: 'fisicos' }).map((p) => p.id)).toEqual([2]);
    expect(filterProducts(products, { ...base, area: 'digitais' }).map((p) => p.id)).toEqual([1, 4]);
  });
  it('por categoria e busca', () => {
    expect(filterProducts(products, { ...base, category: 'Política' }).map((p) => p.id)).toEqual([1, 2]);
    expect(filterProducts(products, { ...base, query: 'bruno' }).map((p) => p.id)).toEqual([2]);
  });
  it('esconde 18+ por padrao', () => {
    expect(filterProducts(products, { ...base, includeAdult: false }).map((p) => p.id)).not.toContain(4);
  });
});

describe('sortProducts', () => {
  const none = {};
  it('menor e maior preco', () => {
    expect(sortProducts(products, 'menor-preco', '', none).map((p) => p.id)).toEqual([3, 4, 1, 5, 2]);
    expect(sortProducts(products, 'maior-preco', '', none).map((p) => p.id)).toEqual([2, 5, 1, 4, 3]);
  });
  it('mais novos usa created_at', () => {
    expect(sortProducts(products, 'mais-novos', '', none).map((p) => p.id)).toEqual([3, 1, 2, 4, 5]);
  });
  it('relevancia: busca primeiro, depois avaliacoes e desconto', () => {
    const ratings = { '5': { average: 5, count: 20 } };
    expect(sortProducts(products, 'relevancia', '', ratings)[0]?.id).toBe(5);
    // com busca, o melhor casamento de texto vence
    expect(sortProducts(products, 'relevancia', 'fighter', ratings)[0]?.id).toBe(3);
  });
  it('nao altera o array original', () => {
    const copy = [...products];
    sortProducts(products, 'menor-preco', '', none);
    expect(products).toEqual(copy);
  });
  it('parseSort valida o parametro', () => {
    expect(parseSort('menor-preco')).toBe('menor-preco');
    expect(parseSort('xyz')).toBe('relevancia');
    expect(parseSort(null)).toBe('relevancia');
  });
});

describe('agregados', () => {
  it('categoriesOf conta e ordena', () => {
    expect(categoriesOf(products)).toEqual([
      { name: 'Apps', count: 1 },
      { name: 'Culinária', count: 1 },
      { name: 'Games', count: 1 },
      { name: 'Política', count: 2 },
    ]);
  });
  it('countByArea respeita 18+', () => {
    expect(countByArea(products, true)).toEqual({ digitais: 2, fisicos: 1, aplicativos: 2 });
    expect(countByArea(products, false)).toEqual({ digitais: 1, fisicos: 1, aplicativos: 2 });
  });
  it('relatedProducts: mesma area, sem o atual, sem 18+', () => {
    const rel = relatedProducts(products, products[0]!, false, 4);
    expect(rel).toEqual([]); // unico digital restante e 18+
    expect(relatedProducts(products, products[0]!, true, 4).map((p) => p.id)).toEqual([4]);
    expect(relatedProducts(products, products[2]!, false, 4).map((p) => p.id)).toEqual([5]);
  });
});
