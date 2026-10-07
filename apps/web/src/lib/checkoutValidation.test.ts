import { describe, expect, it } from 'vitest';
import { firstErrorKey, validateAddress, validateCard, validateCustomer } from './checkoutValidation';

describe('validateCustomer', () => {
  it('ok', () => {
    expect(validateCustomer({ nome: 'Ana Souza', email: 'ana@ex.com', telefone: '(11) 99999-8888' })).toEqual({});
  });
  it('todos os campos invalidos', () => {
    expect(Object.keys(validateCustomer({ nome: '', email: 'x', telefone: '123' }))).toEqual(['nome', 'email', 'telefone']);
  });
});

describe('validateAddress', () => {
  const ok = { cep: '01310-100', rua: 'Av. Paulista', numero: '10', complemento: '', bairro: 'Bela Vista', cidade: 'São Paulo', estado: 'SP' };
  it('ok (complemento e opcional)', () => {
    expect(validateAddress(ok)).toEqual({});
  });
  it('exige campos e UF valida', () => {
    const errors = validateAddress({ ...ok, cep: '1', rua: '', numero: ' ', bairro: '', cidade: '', estado: 'XX' });
    expect(Object.keys(errors)).toEqual(['cep', 'rua', 'numero', 'bairro', 'cidade', 'estado']);
  });
});

describe('validateCard', () => {
  const now = new Date('2026-10-06T12:00:00Z');
  const ok = { number: '4111 1111 1111 1111', expiry: '12/30', cvv: '123', holder: 'ANA SOUZA', cpf: '123.456.789-09' };
  it('ok devolve a validade parseada', () => {
    const { errors, expiry } = validateCard(ok, now);
    expect(errors).toEqual({});
    expect(expiry).toEqual({ month: '12', year: '2030' });
  });
  it('acumula erros', () => {
    const { errors } = validateCard({ number: '1234', expiry: '01/20', cvv: '1', holder: '', cpf: '111.111.111-11' }, now);
    expect(Object.keys(errors)).toEqual(['number', 'expiry', 'cvv', 'holder', 'cpf']);
  });
});

describe('firstErrorKey', () => {
  it('respeita a ordem de exibicao', () => {
    expect(firstErrorKey({ cvv: 'x', number: 'y' }, ['number', 'expiry', 'cvv'])).toBe('number');
    expect(firstErrorKey({}, ['a'])).toBeNull();
  });
});
