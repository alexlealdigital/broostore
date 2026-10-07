import { describe, expect, it } from 'vitest';
import { freteNome, parseFreteOptions, prazoLabel } from './frete';

describe('parseFreteOptions', () => {
  const good = {
    status: 'success',
    total_disponivel: 5,
    opcoes: [
      { id: 2, empresa: 'Correios', nome: 'SEDEX', preco: 42.5, prazo: 3, destaque: 'Mais rapido' },
      { id: 1, empresa: 'Correios', nome: 'PAC', preco: 21.9, prazo: 8, destaque: 'Mais barato' },
    ],
  };

  it('le o formato do backend e ordena pelo preco', () => {
    const opts = parseFreteOptions(good);
    expect(opts.map((o) => o.id)).toEqual(['1', '2']);
    expect(opts[0]).toEqual({ id: '1', empresa: 'Correios', nome: 'PAC', preco: 21.9, prazo: 8, destaque: 'Mais barato' });
  });

  it('converte tipos (preco string, prazo nulo, destaque ausente)', () => {
    const [o] = parseFreteOptions({ status: 'success', opcoes: [{ id: 'x1', empresa: 'Jadlog', nome: '.Package', preco: '30,10', prazo: null }] });
    expect(o).toMatchObject({ id: 'x1', preco: 30.1, prazo: null, destaque: '' });
  });

  it('descarta entradas invalidas', () => {
    const opts = parseFreteOptions({
      status: 'success',
      opcoes: [null, 'x', { nome: 'sem id', preco: 10 }, { id: 3, preco: 'abc' }, { id: 4, preco: -1 }, { id: 5, preco: 9.9 }],
    });
    expect(opts.map((o) => o.id)).toEqual(['5']);
  });

  it('respostas sem sucesso ou mal formadas => lista vazia', () => {
    expect(parseFreteOptions(null)).toEqual([]);
    expect(parseFreteOptions('x')).toEqual([]);
    expect(parseFreteOptions({ status: 'error', message: 'CEP invalido', opcoes: [] })).toEqual([]);
    expect(parseFreteOptions({ status: 'success' })).toEqual([]);
    expect(parseFreteOptions({ status: 'success', opcoes: 'nope' })).toEqual([]);
  });
});

describe('rotulos de frete', () => {
  it('prazo', () => {
    expect(prazoLabel(1)).toBe('1 dia útil');
    expect(prazoLabel(5)).toBe('5 dias úteis');
    expect(prazoLabel(null)).toBe('Prazo a confirmar');
  });
  it('nome', () => {
    expect(freteNome({ id: '1', empresa: 'Correios', nome: 'PAC', preco: 1, prazo: 1, destaque: '' })).toBe('Correios PAC');
    expect(freteNome({ id: '1', empresa: '', nome: '', preco: 1, prazo: 1, destaque: '' })).toBe('Frete');
  });
});
