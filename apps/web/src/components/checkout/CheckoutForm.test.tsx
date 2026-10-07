import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Router } from 'wouter';
import { memoryLocation } from 'wouter/memory-location';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CheckoutProduct } from '@/hooks/useCheckoutProduct';

// A API de pagamentos SEMPRE e mockada: nenhum teste chama /api/cobrancas ou /api/cobrancas-cartao reais.
const apiMock = vi.hoisted(() => ({
  criarCobrancaPix: vi.fn(),
  criarCobrancaCartao: vi.fn(),
  validarCupom: vi.fn(),
  cotarFrete: vi.fn(),
  statusCobranca: vi.fn(),
  getProduto: vi.fn(),
}));
vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return { ...actual, api: apiMock };
});
vi.mock('@/lib/viacep', () => ({
  lookupCep: vi.fn(async () => ({ rua: 'Avenida Paulista', bairro: 'Bela Vista', cidade: 'São Paulo', estado: 'SP' })),
}));
vi.mock('@/lib/mercadopago', async (orig) => {
  const actual = await orig<typeof import('@/lib/mercadopago')>();
  return { ...actual, loadMercadoPagoSdk: vi.fn(async () => undefined) };
});

import { CheckoutForm } from './CheckoutForm';

const digital: CheckoutProduct = { id: 3, title: 'Guia da Eleição', price: 50, tipo: 'ebook', area: 'digitais', imageUrl: null, author: 'Ana', category: 'Política', source: 'supabase' };
const fisico: CheckoutProduct = { ...digital, id: 8, title: 'Livro Impresso', price: 80, tipo: 'fisico', area: 'fisicos' };

function setup(product: CheckoutProduct, prefill = { email: null as string | null, nome: '' }, returnUrl: string | null = null) {
  const { hook } = memoryLocation({ path: '/comprar/3' });
  return render(
    <Router hook={hook}>
      <CheckoutForm product={product} prefill={prefill} returnUrl={returnUrl} />
    </Router>,
  );
}

async function fillCustomer(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/Nome completo/), 'Ana Souza');
  await user.type(screen.getByLabelText(/^E-mail/), 'ana@ex.com');
  await user.type(screen.getByLabelText(/Telefone/), '11999998888');
}

beforeEach(() => {
  Object.values(apiMock).forEach((m) => m.mockReset());
  apiMock.statusCobranca.mockResolvedValue({ supported: false, reason: 'not-found' });
});

describe('Checkout digital (PIX)', () => {
  it('valida os campos antes de chamar a API', async () => {
    const user = userEvent.setup();
    setup(digital);
    await user.click(screen.getByRole('button', { name: /Gerar QR Code PIX/ }));
    expect(await screen.findByText('Informe seu nome completo.')).toBeInTheDocument();
    expect(screen.getByText('Informe um e-mail válido.')).toBeInTheDocument();
    expect(apiMock.criarCobrancaPix).not.toHaveBeenCalled();
  });

  it('gera o PIX, mostra QR e codigo, e copia com feedback', async () => {
    const user = userEvent.setup();
    const writeText = vi.fn(async () => undefined);
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
    apiMock.criarCobrancaPix.mockResolvedValue({
      status: 'success',
      qr_code_base64: 'QUJD',
      qr_code_text: '000201PIXCODE',
      cobranca: { external_reference: 'ref-123' },
      total_cobrado: 50,
    });
    setup(digital);
    await fillCustomer(user);
    await user.click(screen.getByRole('button', { name: /Gerar QR Code PIX/ }));

    expect(await screen.findByRole('heading', { name: 'Pague com PIX' })).toBeInTheDocument();
    expect(screen.getByAltText('QR Code PIX para pagamento')).toHaveAttribute('src', 'data:image/jpeg;base64,QUJD');
    expect(apiMock.criarCobrancaPix).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'ana@ex.com', nome: 'Ana Souza', product_id: 3, cupom_id: null }),
      expect.anything(),
    );

    await user.click(screen.getByRole('button', { name: /Copiar código/ }));
    expect(writeText).toHaveBeenCalledWith('000201PIXCODE');
    expect(await screen.findByText('Código copiado. Cole no app do seu banco.')).toBeInTheDocument();
  });

  it('endpoint de status ausente (404): mensagem estatica, sem erro', async () => {
    const user = userEvent.setup();
    apiMock.criarCobrancaPix.mockResolvedValue({ qr_code_base64: 'QUJD', qr_code_text: 'X', cobranca: { external_reference: 'r' } });
    setup(digital);
    await fillCustomer(user);
    await user.click(screen.getByRole('button', { name: /Gerar QR Code PIX/ }));
    expect(await screen.findByText(/Depois de pagar, é só aguardar o e-mail/)).toBeInTheDocument();
  });

  it('quando o status vira pago, mostra "Pagamento confirmado" com a regra do produto', async () => {
    const user = userEvent.setup();
    apiMock.statusCobranca.mockResolvedValue({ supported: true, data: { status: 'approved', pago: true } });
    apiMock.criarCobrancaPix.mockResolvedValue({ qr_code_base64: 'QUJD', qr_code_text: 'X', cobranca: { external_reference: 'r' }, total_cobrado: 50 });
    setup(digital);
    await fillCustomer(user);
    await user.click(screen.getByRole('button', { name: /Gerar QR Code PIX/ }));
    expect(await screen.findByRole('heading', { name: 'Pagamento confirmado' })).toBeInTheDocument();
    expect(screen.getByText(/Enviamos o link de download para ana@ex.com/)).toBeInTheDocument();
  });

  it('erro do servidor aparece e o botao volta a ficar disponivel', async () => {
    const user = userEvent.setup();
    const { ApiError } = await import('@/lib/api');
    apiMock.criarCobrancaPix.mockRejectedValue(new ApiError('http', 'Erro do Mercado Pago: indisponível', 500));
    setup(digital);
    await fillCustomer(user);
    await user.click(screen.getByRole('button', { name: /Gerar QR Code PIX/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Erro do Mercado Pago: indisponível');
    expect(screen.getByRole('button', { name: /Gerar QR Code PIX/ })).toBeEnabled();
  });
});

describe('Cupom', () => {
  it('mostra o desconto calculado pelo servidor e envia cupom_id', async () => {
    const user = userEvent.setup();
    apiMock.validarCupom.mockResolvedValue({
      status: 'success',
      cupom: { id: 4, codigo: 'BROO10', tipo: 'percentual', valor: 10 },
      calculo: { valor_original: 50, desconto: 5, valor_final: 45, percentual_aplicado: 10 },
    });
    apiMock.criarCobrancaPix.mockResolvedValue({ qr_code_base64: '', qr_code_text: 'X', cobranca: {} });
    setup(digital);
    await user.type(screen.getByRole('textbox', { name: /Tem um cupom/ }), 'broo10');
    await user.click(screen.getByRole('button', { name: 'Aplicar' }));
    expect(await screen.findByText(/Cupom BROO10 aplicado: 10% de desconto/)).toBeInTheDocument();
    expect(screen.getByTestId('order-total')).toHaveTextContent('R$ 45,00');
    expect(apiMock.validarCupom).toHaveBeenCalledWith({ codigo: 'BROO10', produto_id: 3, valor_original: 50 }, expect.anything());

    await fillCustomer(user);
    await user.click(screen.getByRole('button', { name: /Gerar QR Code PIX/ }));
    await waitFor(() => expect(apiMock.criarCobrancaPix).toHaveBeenCalled());
    expect(apiMock.criarCobrancaPix.mock.calls[0]?.[0]).toMatchObject({ cupom_id: 4 });
  });

  it('cupom invalido mostra a mensagem do servidor', async () => {
    const user = userEvent.setup();
    const { ApiError } = await import('@/lib/api');
    apiMock.validarCupom.mockRejectedValue(new ApiError('http', 'Cupom expirado', 400));
    setup(digital);
    await user.type(screen.getByRole('textbox', { name: /Tem um cupom/ }), 'x');
    await user.click(screen.getByRole('button', { name: 'Aplicar' }));
    expect(await screen.findByText('Cupom expirado')).toBeInTheDocument();
  });
});

describe('Checkout fisico', () => {
  it('CEP preenche o endereco, cota o frete, pre-seleciona o mais barato e envia endereco/frete no PIX', async () => {
    const user = userEvent.setup();
    apiMock.cotarFrete.mockResolvedValue([
      { id: '1', empresa: 'Correios', nome: 'PAC', preco: 21.9, prazo: 8, destaque: 'Mais barato' },
      { id: '2', empresa: 'Correios', nome: 'SEDEX', preco: 42.5, prazo: 3, destaque: 'Mais rapido' },
    ]);
    apiMock.criarCobrancaPix.mockResolvedValue({ qr_code_base64: 'QUJD', qr_code_text: 'X', cobranca: { external_reference: 'r' }, total_cobrado: 101.9 });
    setup(fisico);
    await fillCustomer(user);
    await user.type(screen.getByLabelText(/^CEP/), '01310100');

    await waitFor(() => expect(screen.getByLabelText(/Rua/)).toHaveValue('Avenida Paulista'));
    expect(screen.getByLabelText(/Cidade/)).toHaveValue('São Paulo');
    expect(apiMock.cotarFrete).toHaveBeenCalledWith('01310100', 8, expect.anything());

    const group = await screen.findByRole('radiogroup');
    const radios = within(group).getAllByRole('radio');
    expect(radios).toHaveLength(2);
    expect(radios[0]).toBeChecked();
    expect(screen.getByTestId('order-total')).toHaveTextContent('R$ 101,90');

    await user.click(radios[1] as HTMLElement);
    expect(screen.getByTestId('order-total')).toHaveTextContent('R$ 122,50');
    await user.click(radios[0] as HTMLElement);

    await user.type(screen.getByLabelText(/Número/), '1000');
    await user.click(screen.getByRole('button', { name: /Gerar QR Code PIX/ }));
    await waitFor(() => expect(apiMock.criarCobrancaPix).toHaveBeenCalled());
    expect(apiMock.criarCobrancaPix.mock.calls[0]?.[0]).toMatchObject({
      product_id: 8,
      frete: 21.9,
      frete_servico_id: '1',
      cep_destino: '01310-100',
      endereco: { cep: '01310-100', rua: 'Avenida Paulista', numero: '1000', bairro: 'Bela Vista', cidade: 'São Paulo', estado: 'SP' },
    });
  });

  it('nao permite pagar sem escolher frete', async () => {
    const user = userEvent.setup();
    setup(fisico);
    await fillCustomer(user);
    await user.click(screen.getByRole('button', { name: /Gerar QR Code PIX/ }));
    expect(await screen.findByText('Informe um CEP com 8 dígitos.')).toBeInTheDocument();
    expect(apiMock.criarCobrancaPix).not.toHaveBeenCalled();
  });

  it('erro de cotacao e exibido', async () => {
    const user = userEvent.setup();
    const { ApiError } = await import('@/lib/api');
    apiMock.cotarFrete.mockRejectedValue(new ApiError('http', 'Nenhuma transportadora disponível para este CEP.', 404));
    setup(fisico);
    await user.type(screen.getByLabelText(/^CEP/), '01310100');
    expect(await screen.findByText('Nenhuma transportadora disponível para este CEP.')).toBeInTheDocument();
  });
});

describe('BrooStock: e-mail pre-preenchido', () => {
  it('trava o e-mail e preenche o nome', () => {
    setup(digital, { email: 'cliente@app.com', nome: 'Cliente App' });
    expect(screen.getByLabelText(/^E-mail/)).toHaveValue('cliente@app.com');
    expect(screen.getByLabelText(/^E-mail/)).toHaveAttribute('readonly');
    expect(screen.getByLabelText(/Nome completo/)).toHaveValue('Cliente App');
    expect(screen.getByText('Vinculado à sua conta BrooStock.')).toBeInTheDocument();
  });
});
