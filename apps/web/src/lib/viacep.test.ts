import { describe, expect, it, vi } from 'vitest';
import { lookupCep } from './viacep';

const ok = (body: unknown, status = 200) => vi.fn(async () => new Response(JSON.stringify(body), { status })) as unknown as typeof fetch;

describe('lookupCep', () => {
  it('mapeia o endereco', async () => {
    const f = ok({ logradouro: 'Avenida Paulista', bairro: 'Bela Vista', localidade: 'São Paulo', uf: 'sp' });
    await expect(lookupCep('01310-100', { fetchImpl: f })).resolves.toEqual({ rua: 'Avenida Paulista', bairro: 'Bela Vista', cidade: 'São Paulo', estado: 'SP' });
    expect(f).toHaveBeenCalledWith('https://viacep.com.br/ws/01310100/json/', expect.anything());
  });
  it('CEP inexistente => null', async () => {
    await expect(lookupCep('99999999', { fetchImpl: ok({ erro: true }) })).resolves.toBeNull();
  });
  it('CEP incompleto => null sem chamar a rede', async () => {
    const f = ok({});
    await expect(lookupCep('123', { fetchImpl: f })).resolves.toBeNull();
    expect(f).not.toHaveBeenCalled();
  });
  it('erro do servico lanca', async () => {
    await expect(lookupCep('01310100', { fetchImpl: ok({}, 500) })).rejects.toThrow();
  });
});
