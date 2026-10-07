import { describe, expect, it } from 'vitest';
import { isCEP, isCPF, isCvv, isEmail, isFullName, isLuhnValid, isPhone, parseExpiry, safeHttpUrl } from './validators';

describe('isEmail', () => {
  it('aceita enderecos comuns', () => {
    expect(isEmail('a@b.com')).toBe(true);
    expect(isEmail(' leal@broo.com.br ')).toBe(true);
  });
  it('rejeita invalidos', () => {
    for (const v of ['', 'a', 'a@b', 'a@@b.com', 'a b@c.com', '@b.com']) expect(isEmail(v)).toBe(false);
  });
});

describe('isPhone', () => {
  it('celular e fixo com DDD', () => {
    expect(isPhone('(11) 99999-8888')).toBe(true);
    expect(isPhone('1133334444')).toBe(true);
  });
  it('rejeita curtos, longos e celular sem 9', () => {
    expect(isPhone('999998888')).toBe(false);
    expect(isPhone('119999988889')).toBe(false);
    expect(isPhone('11833334444')).toBe(false);
    expect(isPhone('0099999888')).toBe(false);
  });
});

describe('isCEP', () => {
  it('exige 8 digitos', () => {
    expect(isCEP('01310-100')).toBe(true);
    expect(isCEP('0131010')).toBe(false);
  });
});

describe('isCPF', () => {
  it('valida digitos verificadores', () => {
    expect(isCPF('123.456.789-09')).toBe(true);
    expect(isCPF('52998224725')).toBe(true);
  });
  it('rejeita invalidos e repetidos', () => {
    expect(isCPF('123.456.789-00')).toBe(false);
    expect(isCPF('111.111.111-11')).toBe(false);
    expect(isCPF('123')).toBe(false);
    expect(isCPF('')).toBe(false);
  });
});

describe('isLuhnValid', () => {
  it('aceita cartoes de teste conhecidos', () => {
    expect(isLuhnValid('4111 1111 1111 1111')).toBe(true);
    expect(isLuhnValid('5031 4332 1540 6351')).toBe(true); // cartao de teste do Mercado Pago
  });
  it('rejeita invalidos', () => {
    expect(isLuhnValid('4111 1111 1111 1112')).toBe(false);
    expect(isLuhnValid('1234')).toBe(false);
  });
});

describe('parseExpiry', () => {
  const now = new Date('2026-10-06T12:00:00Z');
  it('aceita validade futura ou do mes corrente', () => {
    expect(parseExpiry('12/30', now)).toEqual({ month: '12', year: '2030' });
    expect(parseExpiry('10/26', now)).toEqual({ month: '10', year: '2026' });
  });
  it('rejeita vencida, mes invalido e formato errado', () => {
    expect(parseExpiry('09/26', now)).toBeNull();
    expect(parseExpiry('12/25', now)).toBeNull();
    expect(parseExpiry('13/30', now)).toBeNull();
    expect(parseExpiry('00/30', now)).toBeNull();
    expect(parseExpiry('1230', now)).toBeNull();
    expect(parseExpiry('', now)).toBeNull();
  });
});

describe('isCvv / isFullName', () => {
  it('cvv 3 ou 4 digitos', () => {
    expect(isCvv('123')).toBe(true);
    expect(isCvv('1234')).toBe(true);
    expect(isCvv('12')).toBe(false);
  });
  it('nome', () => {
    expect(isFullName('Ana Maria')).toBe(true);
    expect(isFullName('Jo')).toBe(false);
    expect(isFullName('123')).toBe(false);
  });
});

describe('safeHttpUrl', () => {
  it('so aceita http(s)', () => {
    expect(safeHttpUrl('https://app.example.com/x?y=1')).toBe('https://app.example.com/x?y=1');
    expect(safeHttpUrl('javascript:alert(1)')).toBeNull();
    expect(safeHttpUrl('data:text/html,hi')).toBeNull();
    expect(safeHttpUrl('nao e url')).toBeNull();
    expect(safeHttpUrl(null)).toBeNull();
  });
});
