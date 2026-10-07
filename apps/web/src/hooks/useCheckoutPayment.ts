import { useCallback, useRef, useState } from 'react';
import { ApiError, api } from '@/lib/api';
import { buildCardPayload, buildPixPayload, type BasePaymentInput } from '@/lib/checkoutPayload';
import { createCardToken, normalizeMpError } from '@/lib/mercadopago';
import { onlyDigits } from '@/lib/format';
import { useSlowNotice } from './useSlowNotice';
import type { PixResponse } from '@/types';

export type PaymentResult =
  | { kind: 'pix'; pix: PixResponse; externalReference: string | null; total: number | null }
  | { kind: 'paid'; via: 'pix' | 'cartao'; message?: string; total: number | null }
  | { kind: 'review'; message: string };

export interface CardInput {
  number: string;
  holder: string;
  month: string;
  /** ano com 4 digitos */
  year: string;
  cvv: string;
  cpf: string;
  paymentMethodId: string;
  issuerId: string | number | null;
  installments: number;
}

const DUPLICATE_WARNING =
  'Não conseguimos confirmar o resultado do pagamento. Para evitar cobrança em duplicidade, confira seu e-mail e o app do seu banco antes de tentar novamente.';

/** Orquestra geracao do PIX e pagamento com cartao. Nunca registra nem repassa dados do cartao ao nosso backend. */
export function useCheckoutPayment() {
  const [busy, setBusy] = useState<'pix' | 'cartao' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PaymentResult | null>(null);
  const { slow, onSlow, reset } = useSlowNotice();
  const lock = useRef(false);

  const payPix = useCallback(
    async (input: BasePaymentInput) => {
      if (lock.current) return;
      lock.current = true;
      setBusy('pix');
      setError(null);
      try {
        const res = await api.criarCobrancaPix(buildPixPayload(input), { onSlow });
        if (!res?.qr_code_text) throw new ApiError('parse', 'O servidor não devolveu o código PIX. Tente novamente.');
        setResult({
          kind: 'pix',
          pix: res,
          externalReference: res.cobranca?.external_reference ?? null,
          total: typeof res.total_cobrado === 'number' ? res.total_cobrado : null,
        });
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Não foi possível gerar o PIX. Tente novamente.');
      } finally {
        lock.current = false;
        setBusy(null);
        reset();
      }
    },
    [onSlow, reset],
  );

  const payCard = useCallback(
    async (input: BasePaymentInput, card: CardInput) => {
      if (lock.current) return;
      lock.current = true;
      setBusy('cartao');
      setError(null);
      try {
        // 1) token direto no Mercado Pago (dados do cartao nao passam pelo nosso servidor)
        let token: string;
        try {
          token = await createCardToken({
            number: onlyDigits(card.number),
            holder: card.holder.trim(),
            month: card.month,
            year: card.year,
            cvv: onlyDigits(card.cvv),
            cpf: onlyDigits(card.cpf),
          });
        } catch (err) {
          setError(normalizeMpError(err));
          return;
        }

        // 2) apenas o token segue para a API
        const payload = buildCardPayload({
          ...input,
          token,
          paymentMethodId: card.paymentMethodId,
          issuerId: card.issuerId,
          installments: card.installments,
          cpf: card.cpf,
        });
        try {
          const res = await api.criarCobrancaCartao(payload, { onSlow });
          if (res.status === 'approved') {
            setResult({
              kind: 'paid',
              via: 'cartao',
              message: res.mensagem,
              total: typeof res.total_cobrado === 'number' ? res.total_cobrado : null,
            });
          } else if (res.status === 'in_process' || res.status === 'pending') {
            setResult({ kind: 'review', message: res.mensagem || 'Pagamento em análise. Você receberá um e-mail assim que for aprovado.' });
          } else {
            setError(res.mensagem || 'Pagamento não aprovado. Verifique os dados do cartão ou tente outra forma de pagamento.');
          }
        } catch (err) {
          if (err instanceof ApiError && (err.kind === 'timeout' || err.kind === 'network' || err.kind === 'parse')) {
            setError(DUPLICATE_WARNING);
          } else {
            setError(err instanceof ApiError ? err.message : 'Pagamento recusado. Tente novamente.');
          }
        }
      } finally {
        lock.current = false;
        setBusy(null);
        reset();
      }
    },
    [onSlow, reset],
  );

  const clearResult = useCallback(() => setResult(null), []);
  const markPaid = useCallback((via: 'pix' | 'cartao', total: number | null) => setResult({ kind: 'paid', via, total }), []);

  return { busy, error, setError, result, slow, payPix, payCard, clearResult, markPaid };
}
