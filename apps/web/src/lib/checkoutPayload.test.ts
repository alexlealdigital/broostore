import { describe, expect, it } from 'vitest';
import { buildCardPayload, buildPixPayload } from './checkoutPayload';

const customer = { nome: ' Ana Souza ', email: ' ana@ex.com ', telefone: '(11) 99999-8888' };
const shipping = {
  endereco: { cep: '01310-100', rua: 'Av. Paulista', numero: '1000', complemento: '', bairro: 'Bela Vista', cidade: 'São Paulo', estado: 'SP' },
  frete: 21.9,
  freteServicoId: '1',
};

describe('buildPixPayload', () => {
  it('digital: campos basicos, sem endereco/frete', () => {
    expect(buildPixPayload({ productId: 3, customer, cupomId: null })).toEqual({
      email: 'ana@ex.com',
      nome: 'Ana Souza',
      telefone: '(11) 99999-8888',
      product_id: 3,
      cupom_id: null,
    });
  });
  it('fisico: inclui endereco, frete, servico e cep_destino', () => {
    const p = buildPixPayload({ productId: 3, customer, cupomId: 9, shipping });
    expect(p).toMatchObject({ cupom_id: 9, endereco: shipping.endereco, frete: 21.9, frete_servico_id: '1', cep_destino: '01310-100' });
  });
});

describe('buildCardPayload', () => {
  const payload = buildCardPayload({
    productId: 3,
    customer,
    cupomId: null,
    shipping,
    token: 'tok_123',
    paymentMethodId: 'visa',
    issuerId: 25,
    installments: 3,
    cpf: '123.456.789-09',
  });

  it('leva o token, bandeira, parcelas e CPF apenas em digitos', () => {
    expect(payload).toMatchObject({ token: 'tok_123', payment_method_id: 'visa', issuer_id: 25, installments: 3, cpf: '12345678909' });
  });

  it('NAO contem numero, validade, cvv ou nome do titular do cartao', () => {
    const keys = Object.keys(payload);
    for (const forbidden of ['card_number', 'cardNumber', 'number', 'numero_cartao', 'cvv', 'security_code', 'securityCode', 'expiry', 'validade', 'expiration', 'cardholder', 'holder']) {
      expect(keys).not.toContain(forbidden);
    }
    const json = JSON.stringify(payload);
    expect(json).not.toMatch(/4111\s?1111/);
  });

  it('parcelas invalidas viram 1', () => {
    expect(buildCardPayload({ productId: 1, customer, cupomId: null, token: 't', paymentMethodId: 'visa', issuerId: null, installments: 0, cpf: '1' }).installments).toBe(1);
    expect(buildCardPayload({ productId: 1, customer, cupomId: null, token: 't', paymentMethodId: 'visa', issuerId: null, installments: NaN, cpf: '1' }).installments).toBe(1);
  });
});
