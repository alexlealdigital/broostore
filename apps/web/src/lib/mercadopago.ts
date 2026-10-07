/**
 * Carregamento preguicoso do SDK do Mercado Pago (https://sdk.mercadopago.com/js/v2).
 * So e chamado pela pagina de checkout; o restante da loja nunca baixa o SDK.
 */
import { config } from './config';
import type { MpInstance, MpPayerCost } from '@/types';

export const MP_SDK_URL = 'https://sdk.mercadopago.com/js/v2';

let sdkPromise: Promise<void> | null = null;
let instance: MpInstance | null = null;

export function loadMercadoPagoSdk(): Promise<void> {
  if (typeof window === 'undefined') return Promise.reject(new Error('SDK indisponível fora do navegador.'));
  if (window.MercadoPago) return Promise.resolve();
  if (sdkPromise) return sdkPromise;

  sdkPromise = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = MP_SDK_URL;
    script.async = true;
    script.onload = () => (window.MercadoPago ? resolve() : reject(new Error('SDK do Mercado Pago não inicializou.')));
    script.onerror = () => {
      script.remove();
      sdkPromise = null; // permite nova tentativa
      reject(new Error('Não foi possível carregar o Mercado Pago. Verifique sua conexão.'));
    };
    document.head.appendChild(script);
  });
  return sdkPromise;
}

export async function getMp(): Promise<MpInstance> {
  if (instance) return instance;
  await loadMercadoPagoSdk();
  if (!window.MercadoPago) throw new Error('SDK do Mercado Pago não carregou.');
  if (!config.mpPublicKey) throw new Error('Public Key do Mercado Pago não configurada.');
  instance = new window.MercadoPago(config.mpPublicKey, { locale: 'pt-BR' });
  return instance;
}

export interface Installment {
  value: number;
  label: string;
}

export interface BinInfo {
  paymentMethodId: string;
  issuerId: string | number | null;
  thumbnail: string | null;
  installments: Installment[];
}

export function installmentLabel(cost: MpPayerCost, formatMoney: (n: number) => string): string {
  return cost.recommended_message?.trim() || `${cost.installments}x de ${formatMoney(Number(cost.installment_amount))}`;
}

/** BIN (6 primeiros digitos) -> bandeira, emissor e parcelas para o valor informado. */
export async function lookupBin(
  bin: string,
  amount: number,
  formatMoney: (n: number) => string,
): Promise<BinInfo | null> {
  const mp = await getMp();
  const methods = await mp.getPaymentMethods({ bin });
  const pm = methods?.results?.[0];
  if (!pm) return null;

  let issuerId: string | number | null = null;
  try {
    const issuers = await mp.getIssuers({ paymentMethodId: pm.id, bin });
    issuerId = issuers?.[0]?.id ?? null;
  } catch {
    issuerId = null;
  }

  let installments: Installment[] = [];
  try {
    const inst = await mp.getInstallments({ amount: amount.toFixed(2), bin, paymentMethodId: pm.id });
    installments = (inst?.[0]?.payer_costs ?? []).map((c) => ({
      value: c.installments,
      label: installmentLabel(c, formatMoney),
    }));
  } catch {
    installments = [];
  }
  return { paymentMethodId: pm.id, issuerId, thumbnail: pm.thumbnail ?? null, installments };
}

export interface CardTokenInput {
  number: string;
  holder: string;
  month: string;
  year: string;
  cvv: string;
  cpf: string;
}

/** Gera o token do cartao direto no Mercado Pago. Os dados do cartao nao passam pelo nosso servidor. */
export async function createCardToken(input: CardTokenInput): Promise<string> {
  const mp = await getMp();
  const token = await mp.createCardToken({
    cardNumber: input.number,
    cardholderName: input.holder,
    cardExpirationMonth: input.month,
    cardExpirationYear: input.year,
    securityCode: input.cvv,
    identificationType: 'CPF',
    identificationNumber: input.cpf,
  });
  if (!token?.id) throw new Error('Não foi possível validar o cartão. Confira os dados e tente novamente.');
  return token.id;
}

/**
 * O SDK rejeita com um array de `{ code, description }` (ou Error). Converte para uma mensagem em portugues.
 */
export function normalizeMpError(err: unknown): string {
  const fallback = 'Não foi possível validar o cartão. Confira os dados e tente novamente.';
  if (Array.isArray(err)) {
    const parts = err
      .map((e) => (e && typeof e === 'object' && 'description' in e ? String((e as { description: unknown }).description) : ''))
      .filter(Boolean);
    return parts.length ? [...new Set(parts)].join(' ') : fallback;
  }
  if (err instanceof Error && err.message) return err.message;
  if (err && typeof err === 'object' && 'message' in err && typeof (err as { message: unknown }).message === 'string') {
    return (err as { message: string }).message;
  }
  return fallback;
}
