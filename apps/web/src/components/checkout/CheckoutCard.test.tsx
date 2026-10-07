import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Router } from 'wouter';
import { memoryLocation } from 'wouter/memory-location';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CheckoutProduct } from '@/hooks/useCheckoutProduct';

const apiMock = vi.hoisted(() => ({
  criarCobrancaPix: vi.fn(),
  criarCobrancaCartao: vi.fn(),
  validarCupom: vi.fn(),
  cotarFrete: vi.fn(),
  statusCobranca: vi.fn(),
  getProduto: vi.fn(),
}));
const mp = vi.hoisted(() => ({
  lookupBin: vi.fn(),
  createCardToken: vi.fn(),
  loadMercadoPagoSdk: vi.fn(),
}));

vi.mock('@/lib/api', async (orig) => ({ ...(await orig<typeof import('@/lib/api')>()), api: apiMock }));
vi.mock('@/lib/mercadopago', async (orig) => ({ ...(await orig<typeof import('@/lib/mercadopago')>()), ...mp }));

import { CheckoutForm } from './CheckoutForm';

const product: CheckoutProduct = { id: 3, title: 'BrooStock Pro', price: 59, tipo: 'assinatura', area: 'aplicativos', imageUrl: null, author: '', category: '', source: 'api' };

function setup() {
  const { hook } = memoryLocation({ path: '/comprar/3' });
  return render(
    <Router hook={hook}>
      <CheckoutForm product={product} prefill={{ email: 'cliente@app.com', nome: 'Cliente' }} returnUrl="https://app.test/volta" />
    </Router>,
  );
}

async function fillCard(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/Telefone/), '11999998888');
  await user.click(screen.getByRole('tab', { name: /Cartão/ }));
  await user.type(screen.getByLabelText(/^Número do cartão/), '4111111111111111');
  await user.type(screen.getByLabelText(/^Validade/), '1230');
  await user.type(screen.getByLabelText(/^CVV/), '123');
  await user.type(screen.getByLabelText(/^Nome no cartão/), 'cliente teste');
  await user.type(screen.getByLabelText(/^CPF do titular/), '12345678909');
}

beforeEach(() => {
  Object.values(apiMock).forEach((m) => m.mockReset());
  Object.values(mp).forEach((m) => m.mockReset());
  mp.loadMercadoPagoSdk.mockResolvedValue(undefined);
  mp.lookupBin.mockResolvedValue({
    paymentMethodId: 'visa',
    issuerId: 25,
    thumbnail: null,
    installments: [
      { value: 1, label: '1x de R$ 59,00' },
      { value: 3, label: '3x de R$ 20,50' },
    ],
  });
  mp.createCardToken.mockResolvedValue('tok_abc');
});

describe('Pagamento com cartao', () => {
  it('mostra parcelas, tokeniza no Mercado Pago e envia a API SOMENTE o token (sem numero/validade/cvv)', async () => {
    const user = userEvent.setup();
    apiMock.criarCobrancaCartao.mockResolvedValue({ status: 'approved', mensagem: 'Pagamento aprovado!', total_cobrado: 59 });
    setup();
    await fillCard(user);
    expect(await screen.findByRole('combobox', { name: 'Parcelamento' })).toBeInTheDocument();
    await user.selectOptions(screen.getByRole('combobox', { name: 'Parcelamento' }), '3');

    await user.click(screen.getByRole('button', { name: /Pagar R\$ 59,00 com cartão/ }));
    expect(await screen.findByRole('heading', { name: 'Pagamento confirmado' })).toBeInTheDocument();
    expect(screen.getByText(/licença\/chave de acesso será enviada para cliente@app.com/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Voltar ao aplicativo' })).toHaveAttribute('href', 'https://app.test/volta');

    // dados crus vao so para o SDK
    expect(mp.createCardToken).toHaveBeenCalledWith({ number: '4111111111111111', holder: 'CLIENTE TESTE', month: '12', year: '2030', cvv: '123', cpf: '12345678909' });

    // a API recebe o token
    const payload = apiMock.criarCobrancaCartao.mock.calls[0]?.[0] as Record<string, unknown>;
    expect(payload).toMatchObject({ token: 'tok_abc', payment_method_id: 'visa', issuer_id: 25, installments: 3, product_id: 3, email: 'cliente@app.com' });
    const json = JSON.stringify(payload);
    expect(json).not.toContain('4111');
    expect(json).not.toContain('"cvv"');
    expect(json).not.toContain('12/30');
    expect(json).not.toContain('2030');
  });

  it('cartao recusado mostra a mensagem e permite tentar de novo', async () => {
    const user = userEvent.setup();
    apiMock.criarCobrancaCartao.mockResolvedValue({
      status: 'rejected',
      status_detail: 'cc_rejected_insufficient_amount',
      mensagem: 'Pagamento não aprovado (cc_rejected_insufficient_amount). Verifique os dados do cartão.',
    });
    setup();
    await fillCard(user);
    await user.click(screen.getByRole('button', { name: /Pagar R\$ 59,00 com cartão/ }));
    const alerta = await screen.findByRole('alert');
    expect(alerta).toHaveTextContent('Saldo ou limite insuficiente');
    expect(alerta).not.toHaveTextContent('cc_rejected');
    expect(screen.getByRole('button', { name: /Pagar R\$ 59,00 com cartão/ })).toBeEnabled();
  });

  it('pagamento em analise nao permite reenviar (evita cobranca duplicada)', async () => {
    const user = userEvent.setup();
    apiMock.criarCobrancaCartao.mockResolvedValue({ status: 'in_process', mensagem: 'Pagamento em análise.' });
    setup();
    await fillCard(user);
    await user.click(screen.getByRole('button', { name: /Pagar R\$ 59,00 com cartão/ }));
    expect(await screen.findByRole('heading', { name: 'Pagamento em análise' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Pagar/ })).not.toBeInTheDocument();
  });

  it('erro de tokenizacao do SDK nao chama a API', async () => {
    const user = userEvent.setup();
    mp.createCardToken.mockRejectedValue([{ code: '208', description: 'Escolha um mês.' }]);
    setup();
    await fillCard(user);
    await user.click(screen.getByRole('button', { name: /Pagar R\$ 59,00 com cartão/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Escolha um mês.');
    expect(apiMock.criarCobrancaCartao).not.toHaveBeenCalled();
  });

  it('timeout na API orienta a conferir o e-mail antes de repetir', async () => {
    const user = userEvent.setup();
    const { ApiError } = await import('@/lib/api');
    apiMock.criarCobrancaCartao.mockRejectedValue(new ApiError('timeout', 'demorou'));
    setup();
    await fillCard(user);
    await user.click(screen.getByRole('button', { name: /Pagar R\$ 59,00 com cartão/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('cobrança em duplicidade');
  });

  it('validacao local: cartao invalido nao chama o SDK', async () => {
    const user = userEvent.setup();
    setup();
    await user.type(screen.getByLabelText(/Telefone/), '11999998888');
    await user.click(screen.getByRole('tab', { name: /Cartão/ }));
    await user.type(screen.getByLabelText(/^Número do cartão/), '1234');
    await user.click(screen.getByRole('button', { name: /Pagar R\$ 59,00 com cartão/ }));
    expect(await screen.findByText('Número do cartão inválido.')).toBeInTheDocument();
    await waitFor(() => expect(mp.createCardToken).not.toHaveBeenCalled());
  });
});
