import { describe, expect, it } from 'vitest';
import { computeTotals } from './totals';

const frete = { id: '1', empresa: 'Correios', nome: 'PAC', preco: 21.9, prazo: 8, destaque: '' };

describe('computeTotals', () => {
  it('sem cupom nem frete', () => {
    expect(computeTotals(50, null, null)).toEqual({ price: 50, discount: 0, subtotal: 50, frete: 0, total: 50 });
  });
  it('usa o valor_final devolvido pelo servidor', () => {
    const t = computeTotals(100, { valor_original: 100, desconto: 30, valor_final: 70 }, null);
    expect(t).toMatchObject({ discount: 30, subtotal: 70, total: 70 });
  });
  it('soma o frete escolhido', () => {
    const t = computeTotals(100, { valor_original: 100, desconto: 30, valor_final: 70 }, frete);
    expect(t.total).toBe(91.9);
  });
  it('evita erros de ponto flutuante', () => {
    expect(computeTotals(0.1, null, { ...frete, preco: 0.2 }).total).toBe(0.3);
  });
  it('desconto total (valor_final 0) mantem so o frete', () => {
    expect(computeTotals(10, { valor_original: 10, desconto: 10, valor_final: 0 }, frete).total).toBe(21.9);
  });
});
