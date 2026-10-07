/**
 * Montagem dos corpos enviados a POST /api/cobrancas e /api/cobrancas-cartao.
 *
 * Regras de seguranca:
 *  - numero do cartao, validade, CVV e nome do titular NUNCA entram em nenhum payload nosso:
 *    somente o `token` gerado pelo Mercado Pago (mp.createCardToken) viaja ate a API;
 *  - o CPF segue apenas no pagamento com cartao, porque o backend o exige em
 *    payer.identification (ver app.py, create_cobranca_cartao). Se um dia o backend deixar de exigir,
 *    remova o campo `cpf` de `buildCardPayload`.
 *  - preco, frete e desconto sao recalculados no servidor; o que enviamos e so a escolha do cliente.
 */
import { onlyDigits } from './format';
import type { CardPayload, Endereco, PixPayload } from '@/types';

export interface CustomerData {
  nome: string;
  email: string;
  telefone: string;
}

export interface ShippingData {
  endereco: Endereco;
  /** valor exibido da opcao escolhida (o servidor recota e valida) */
  frete: number;
  freteServicoId: string | null;
}

export interface BasePaymentInput {
  productId: number;
  customer: CustomerData;
  cupomId: number | null;
  shipping?: ShippingData | null;
}

function shippingFields(shipping: ShippingData | null | undefined) {
  if (!shipping) return {};
  return {
    endereco: shipping.endereco,
    frete: shipping.frete,
    frete_servico_id: shipping.freteServicoId,
    cep_destino: shipping.endereco.cep,
  };
}

export function buildPixPayload(input: BasePaymentInput): PixPayload {
  return {
    email: input.customer.email.trim(),
    nome: input.customer.nome.trim(),
    telefone: input.customer.telefone.trim(),
    product_id: input.productId,
    cupom_id: input.cupomId,
    ...shippingFields(input.shipping),
  };
}

export interface CardPaymentInput extends BasePaymentInput {
  token: string;
  paymentMethodId: string;
  issuerId: string | number | null;
  installments: number;
  /** CPF do titular (somente digitos). */
  cpf: string;
}

export function buildCardPayload(input: CardPaymentInput): CardPayload {
  return {
    token: input.token,
    payment_method_id: input.paymentMethodId,
    issuer_id: input.issuerId,
    installments: Number.isFinite(input.installments) && input.installments > 0 ? Math.floor(input.installments) : 1,
    email: input.customer.email.trim(),
    nome: input.customer.nome.trim(),
    telefone: input.customer.telefone.trim(),
    cpf: onlyDigits(input.cpf),
    product_id: input.productId,
    cupom_id: input.cupomId,
    ...shippingFields(input.shipping),
  };
}
