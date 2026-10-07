import { describe, expect, it } from 'vitest';
import { installmentLabel, normalizeMpError } from './mercadopago';

describe('normalizeMpError', () => {
  it('junta as descricoes do array do SDK sem repetir', () => {
    expect(normalizeMpError([{ code: '205', description: 'Digite o número do seu cartão.' }, { code: '205', description: 'Digite o número do seu cartão.' }, { code: '208', description: 'Escolha um mês.' }])).toBe(
      'Digite o número do seu cartão. Escolha um mês.',
    );
  });
  it('Error e objetos com message', () => {
    expect(normalizeMpError(new Error('falhou'))).toBe('falhou');
    expect(normalizeMpError({ message: 'oops' })).toBe('oops');
  });
  it('fallback amigavel', () => {
    expect(normalizeMpError([])).toMatch(/cartão/);
    expect(normalizeMpError(undefined)).toMatch(/cartão/);
  });
});

describe('installmentLabel', () => {
  it('usa recommended_message ou monta "Nx de R$"', () => {
    const fmt = (n: number) => `R$ ${n.toFixed(2).replace('.', ',')}`;
    expect(installmentLabel({ installments: 3, installment_amount: 10, recommended_message: '3x de R$ 10,00 sem juros' }, fmt)).toBe('3x de R$ 10,00 sem juros');
    expect(installmentLabel({ installments: 2, installment_amount: 15 }, fmt)).toBe('2x de R$ 15,00');
  });
});
