import { describe, expect, it } from 'vitest';
import {
  discountPercent,
  formatBRL,
  formatCEP,
  formatCPF,
  formatCardNumber,
  formatExpiry,
  formatPhone,
  formatRating,
  onlyDigits,
  toNumber,
} from './format';

describe('formatBRL', () => {
  it('formata em reais', () => {
    expect(formatBRL(29.9)).toBe('R$ 29,90');
    expect(formatBRL(1234.5)).toBe('R$ 1.234,50');
    expect(formatBRL(0)).toBe('R$ 0,00');
  });
  it('valores invalidos viram zero', () => {
    expect(formatBRL(NaN)).toBe('R$ 0,00');
    expect(formatBRL(null)).toBe('R$ 0,00');
    expect(formatBRL(undefined)).toBe('R$ 0,00');
  });
});

describe('toNumber', () => {
  it('converte numeros e strings pt-BR/en', () => {
    expect(toNumber(10)).toBe(10);
    expect(toNumber('29,90')).toBe(29.9);
    expect(toNumber('29.90')).toBe(29.9);
    expect(toNumber('1.234,56')).toBe(1234.56);
  });
  it('invalidos => null', () => {
    expect(toNumber('')).toBeNull();
    expect(toNumber('abc')).toBeNull();
    expect(toNumber(NaN)).toBeNull();
    expect(toNumber(undefined)).toBeNull();
    expect(toNumber({})).toBeNull();
  });
});

describe('discountPercent', () => {
  it('calcula percentual inteiro', () => {
    expect(discountPercent(50, 100)).toBe(50);
    expect(discountPercent(29.9, 39.9)).toBe(25);
  });
  it('sem desconto valido => 0', () => {
    expect(discountPercent(50, null)).toBe(0);
    expect(discountPercent(50, 50)).toBe(0);
    expect(discountPercent(60, 50)).toBe(0);
  });
});

describe('mascaras', () => {
  it('onlyDigits', () => {
    expect(onlyDigits('(11) 99999-9999')).toBe('11999999999');
  });
  it('CPF', () => {
    expect(formatCPF('12345678909')).toBe('123.456.789-09');
    expect(formatCPF('123456')).toBe('123.456');
    expect(formatCPF('1234567890123')).toBe('123.456.789-01');
    expect(formatCPF('')).toBe('');
  });
  it('telefone', () => {
    expect(formatPhone('11999998888')).toBe('(11) 99999-8888');
    expect(formatPhone('1133334444')).toBe('(11) 3333-4444');
    expect(formatPhone('119')).toBe('(11) 9');
    expect(formatPhone('1')).toBe('(1');
    expect(formatPhone('')).toBe('');
  });
  it('CEP', () => {
    expect(formatCEP('01310100')).toBe('01310-100');
    expect(formatCEP('01310')).toBe('01310');
    expect(formatCEP('0131010099')).toBe('01310-100');
  });
  it('cartao e validade', () => {
    expect(formatCardNumber('4111111111111111')).toBe('4111 1111 1111 1111');
    expect(formatCardNumber('4111 11')).toBe('4111 11');
    expect(formatExpiry('1230')).toBe('12/30');
    expect(formatExpiry('12')).toBe('12');
    expect(formatExpiry('123')).toBe('12/3');
  });
  it('nota', () => {
    expect(formatRating(4.5)).toBe('4,5');
    expect(formatRating(5)).toBe('5,0');
  });
});
