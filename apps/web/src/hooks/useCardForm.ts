import { useCallback, useEffect, useRef, useState } from 'react';
import { validateCard, type CardForm, type FieldErrors } from '@/lib/checkoutValidation';
import { formatBRL, formatCPF, formatCardNumber, formatExpiry, onlyDigits } from '@/lib/format';
import { lookupBin, type BinInfo } from '@/lib/mercadopago';
import type { CardInput } from './useCheckoutPayment';

const EMPTY: CardForm = { number: '', expiry: '', cvv: '', holder: '', cpf: '' };

export const CARD_FIELD_ORDER = ['number', 'expiry', 'cvv', 'holder', 'cpf'];

/**
 * Estado do formulario de cartao + consulta de bandeira/parcelas (Mercado Pago SDK).
 * O SDK so e carregado quando `enabled` (aba Cartao aberta). Os dados do cartao ficam apenas em memoria.
 */
export function useCardForm(total: number, enabled: boolean) {
  const [values, setValues] = useState<CardForm>(EMPTY);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [bin, setBin] = useState<BinInfo | null>(null);
  const [installments, setInstallments] = useState(1);
  const [sdkError, setSdkError] = useState<string | null>(null);
  const lookupId = useRef(0);

  const digits = onlyDigits(values.number);
  const binKey = digits.length >= 6 ? digits.slice(0, 6) : '';

  useEffect(() => {
    if (!enabled || !binKey) {
      setBin(null);
      return;
    }
    const id = ++lookupId.current;
    lookupBin(binKey, total, formatBRL)
      .then((info) => {
        if (id !== lookupId.current) return;
        setSdkError(null);
        setBin(info);
        setInstallments((current) => (info?.installments.some((i) => i.value === current) ? current : 1));
      })
      .catch((err: unknown) => {
        if (id !== lookupId.current) return;
        setBin(null);
        setSdkError(err instanceof Error ? err.message : 'Não foi possível consultar o cartão.');
      });
  }, [binKey, total, enabled]);

  const setField = useCallback((field: keyof CardForm, raw: string) => {
    let value = raw;
    if (field === 'number') value = formatCardNumber(raw);
    else if (field === 'expiry') value = formatExpiry(raw);
    else if (field === 'cvv') value = onlyDigits(raw).slice(0, 4);
    else if (field === 'cpf') value = formatCPF(raw);
    else if (field === 'holder') value = raw.toUpperCase();
    setValues((v) => ({ ...v, [field]: value }));
    setErrors((e) => (e[field] ? { ...e, [field]: '' } : e));
  }, []);

  /** Valida e devolve os dados prontos para o SDK; `null` se houver erros (que ficam em `errors`). */
  const validate = useCallback(async (): Promise<CardInput | null> => {
    const { errors: e, expiry } = validateCard(values);
    setErrors(e);
    if (Object.keys(e).length > 0 || !expiry) return null;

    let info = bin;
    if (!info) {
      try {
        info = await lookupBin(onlyDigits(values.number).slice(0, 6), total, formatBRL);
      } catch {
        info = null;
      }
      if (info) setBin(info);
    }
    if (!info) {
      setErrors({ number: 'Não foi possível identificar a bandeira do cartão. Confira o número informado.' });
      return null;
    }
    return {
      number: onlyDigits(values.number),
      holder: values.holder,
      month: expiry.month,
      year: expiry.year,
      cvv: values.cvv,
      cpf: onlyDigits(values.cpf),
      paymentMethodId: info.paymentMethodId,
      issuerId: info.issuerId,
      installments,
    };
  }, [values, bin, total, installments]);

  return { values, errors, bin, installments, setInstallments, setField, validate, sdkError };
}
