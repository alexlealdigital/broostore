/**
 * Resumo de valores exibido no checkout. O navegador so SOMA o que o servidor devolveu
 * (preco do produto, calculo do cupom e preco do frete escolhido): a cobranca real e recalculada no servidor.
 */
import type { CupomCalculo, FreteOption } from '@/types';

export interface Totals {
  /** preco de tabela do produto */
  price: number;
  /** desconto de cupom (>= 0) */
  discount: number;
  /** produto ja com desconto */
  subtotal: number;
  /** frete da opcao escolhida (0 quando nao ha) */
  frete: number;
  total: number;
}

const round2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;

export function computeTotals(price: number, calculo: CupomCalculo | null, frete: FreteOption | null): Totals {
  const subtotal = calculo ? Math.max(0, calculo.valor_final) : price;
  const discount = calculo ? Math.max(0, round2(price - subtotal)) : 0;
  const freteValue = frete ? Math.max(0, frete.preco) : 0;
  return { price, discount, subtotal: round2(subtotal), frete: round2(freteValue), total: round2(subtotal + freteValue) };
}
