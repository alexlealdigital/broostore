import { describe, expect, it } from 'vitest';
import { distributionOf, isVisible, normalizeProduct, normalizeProducts, summarizeRatings } from './products';

describe('isVisible (mesma regra do site antigo)', () => {
  it('so esconde active === false e o id 99', () => {
    expect(isVisible({ id: 1, active: true })).toBe(true);
    expect(isVisible({ id: 1, active: null })).toBe(true);
    expect(isVisible({ id: 1 })).toBe(true);
    expect(isVisible({ id: 1, active: false })).toBe(false);
    expect(isVisible({ id: 99, active: true })).toBe(false);
    expect(isVisible({ id: '99' })).toBe(false);
  });
});

describe('normalizeProduct', () => {
  it('mapeia colunas conhecidas', () => {
    const p = normalizeProduct({
      id: 5,
      title: ' Livro X ',
      author: 'Ana',
      price: '29.90',
      original_price: 49.9,
      image_url: 'https://img/x.png',
      category: 'Politica',
      descricao: 'desc',
      classificacao: '12',
      tipo: ' FISICO ',
      frete: '10',
      peso_kg: 0.4,
    });
    expect(p).toMatchObject({
      id: 5,
      title: 'Livro X',
      price: 29.9,
      originalPrice: 49.9,
      imageUrl: 'https://img/x.png',
      classificacao: '12',
      tipo: 'fisico',
      area: 'fisicos',
      frete: 10,
      pesoKg: 0.4,
    });
  });

  it('nunca quebra com colunas ausentes', () => {
    const p = normalizeProduct({ id: 1 });
    expect(p).toMatchObject({
      title: 'Produto sem título',
      author: '',
      price: 0,
      originalPrice: null,
      imageUrl: null,
      category: 'Outros',
      classificacao: 'L',
      tipo: 'ebook',
      area: 'digitais',
      pesoKg: null,
      estoque: null,
      paginas: null,
    });
  });

  it('preco original menor ou igual ao preco e ignorado', () => {
    expect(normalizeProduct({ id: 1, price: 50, original_price: 50 })?.originalPrice).toBeNull();
    expect(normalizeProduct({ id: 1, price: 50, original_price: 20 })?.originalPrice).toBeNull();
  });

  it('id invalido => null', () => {
    expect(normalizeProduct({ id: 'abc' })).toBeNull();
  });

  it('tipos desconhecidos viram digitais; aplicativos mapeados', () => {
    expect(normalizeProduct({ id: 1, tipo: 'xyz' })?.area).toBe('digitais');
    expect(normalizeProduct({ id: 1, tipo: '' })?.area).toBe('digitais');
    expect(normalizeProduct({ id: 1, tipo: 'game' })?.area).toBe('aplicativos');
  });
});

describe('normalizeProducts', () => {
  it('remove inativos e o id 99, aceita null', () => {
    const list = normalizeProducts([{ id: 1, active: true }, { id: 2, active: false }, { id: 99 }, { id: 3 }]);
    expect(list.map((p) => p.id)).toEqual([1, 3]);
    expect(normalizeProducts(null)).toEqual([]);
  });
});

describe('avaliacoes', () => {
  const rows = [
    { product_id: 1, rating: 5 },
    { product_id: 1, rating: 4 },
    { product_id: '2', rating: 3 },
    { product_id: 1, rating: 'x' },
    { product_id: 1, rating: 9 },
  ];
  it('summarizeRatings agrupa por produto e ignora notas invalidas', () => {
    const map = summarizeRatings(rows);
    expect(map['1']).toEqual({ average: 4.5, count: 2 });
    expect(map['2']).toEqual({ average: 3, count: 1 });
  });
  it('distributionOf conta por estrela', () => {
    const d = distributionOf(rows.filter((r) => r.product_id === 1));
    expect(d.counts).toEqual([0, 0, 0, 1, 1]);
    expect(d.total).toBe(2);
    expect(d.average).toBe(4.5);
    expect(distributionOf([]).total).toBe(0);
  });
});
