import { CreditCard, Lock, ShieldCheck } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { useCardForm } from '@/hooks/useCardForm';
import type { CheckoutProduct } from '@/hooks/useCheckoutProduct';
import { useCheckoutPayment } from '@/hooks/useCheckoutPayment';
import { useCoupon } from '@/hooks/useCoupon';
import { useFrete } from '@/hooks/useFrete';
import { loadMercadoPagoSdk } from '@/lib/mercadopago';
import {
  validateAddress,
  validateCustomer,
  type CustomerForm,
  type FieldErrors,
} from '@/lib/checkoutValidation';
import type { BasePaymentInput } from '@/lib/checkoutPayload';
import { formatBRL, onlyDigits } from '@/lib/format';
import { lookupCep } from '@/lib/viacep';
import { computeTotals } from '@/lib/totals';
import type { Endereco } from '@/types';
import { CardFields } from './CardFields';
import { CouponSection } from './CouponSection';
import { CustomerSection } from './CustomerSection';
import { OrderSummary } from './OrderSummary';
import { PaymentReview, PaymentSuccess } from './PaymentSuccess';
import { PaymentTabs, type PaymentMethod } from './PaymentTabs';
import { PixPayment } from './PixPayment';
import { Section } from './Section';
import { ShippingSection } from './ShippingSection';
import { SlowNotice } from './SlowNotice';

export interface CheckoutPrefill {
  email: string | null;
  nome: string;
}

interface Props {
  product: CheckoutProduct;
  prefill: CheckoutPrefill;
  returnUrl: string | null;
}

const EMPTY_ADDRESS: Endereco = { cep: '', rua: '', numero: '', complemento: '', bairro: '', cidade: '', estado: '' };

export function CheckoutForm({ product, prefill, returnUrl }: Props) {
  const fisico = product.area === 'fisicos';
  const formRef = useRef<HTMLFormElement>(null);

  const [customer, setCustomer] = useState<CustomerForm>({ nome: prefill.nome, email: prefill.email ?? '', telefone: '' });
  const [address, setAddress] = useState<Endereco>(EMPTY_ADDRESS);
  const [method, setMethod] = useState<PaymentMethod>('pix');
  const [customerErrors, setCustomerErrors] = useState<FieldErrors>({});
  const [addressErrors, setAddressErrors] = useState<FieldErrors>({});
  const [freteError, setFreteError] = useState<string | undefined>();
  const [cepStatus, setCepStatus] = useState<'idle' | 'loading' | 'not-found' | 'error' | 'found'>('idle');

  const coupon = useCoupon(product.id, product.price);
  const frete = useFrete(fisico ? product.id : null);
  const payment = useCheckoutPayment();

  const appliedCoupon = coupon.state.status === 'applied' ? coupon.state : null;
  const totals = useMemo(
    () => computeTotals(product.price, appliedCoupon?.calculo ?? null, fisico ? frete.selected : null),
    [product.price, appliedCoupon, fisico, frete.selected],
  );

  const cardActive = method === 'cartao' && !payment.result;
  const card = useCardForm(totals.total, cardActive);

  // SDK do Mercado Pago so e baixado quando o cliente abre a aba Cartao.
  useEffect(() => {
    if (cardActive) void loadMercadoPagoSdk().catch(() => undefined);
  }, [cardActive]);

  /* ---------- CEP: ViaCEP + cotacao de frete ---------- */
  const cepDigits = onlyDigits(address.cep);
  const { quote, clear: clearFrete } = frete;
  useEffect(() => {
    if (!fisico) return;
    if (cepDigits.length !== 8) {
      clearFrete();
      setCepStatus('idle');
      return;
    }
    const controller = new AbortController();
    setCepStatus('loading');
    setFreteError(undefined);
    void quote(cepDigits);
    lookupCep(cepDigits, { signal: controller.signal })
      .then((found) => {
        if (controller.signal.aborted) return;
        if (!found) {
          setCepStatus('not-found');
          return;
        }
        setCepStatus('found');
        setAddress((a) => ({ ...a, rua: found.rua || a.rua, bairro: found.bairro || a.bairro, cidade: found.cidade || a.cidade, estado: found.estado || a.estado }));
        setAddressErrors((e) => ({ ...e, rua: '', bairro: '', cidade: '', estado: '', cep: '' }));
        if (document.activeElement?.id === 'ck-cep') document.getElementById('ck-numero')?.focus();
      })
      .catch(() => {
        if (!controller.signal.aborted) setCepStatus('error');
      });
    return () => controller.abort();
  }, [cepDigits, fisico, quote, clearFrete]);

  const setCustomerField = useCallback((field: keyof CustomerForm, value: string) => {
    setCustomer((c) => ({ ...c, [field]: value }));
    setCustomerErrors((e) => (e[field] ? { ...e, [field]: '' } : e));
  }, []);

  const setAddressField = useCallback((field: keyof Endereco, value: string) => {
    setAddress((a) => ({ ...a, [field]: value }));
    setAddressErrors((e) => (e[field] ? { ...e, [field]: '' } : e));
  }, []);

  const focusFirstInvalid = () => {
    requestAnimationFrame(() => {
      const el = formRef.current?.querySelector<HTMLElement>('[aria-invalid="true"]');
      el?.focus();
      el?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    });
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (payment.busy) return;
    payment.setError(null);

    const cErr = validateCustomer(customer);
    const aErr = fisico ? validateAddress(address) : {};
    const fErr = fisico && !frete.selected && !aErr.cep ? 'Escolha uma opção de frete para continuar.' : undefined;
    setCustomerErrors(cErr);
    setAddressErrors(aErr);
    setFreteError(fErr);
    if (Object.keys(cErr).length > 0 || Object.keys(aErr).length > 0) {
      focusFirstInvalid();
      return;
    }
    if (fErr || (fisico && !frete.selected)) {
      if (!fErr) setFreteError('Aguarde o cálculo do frete e escolha uma opção.');
      document.getElementById('frete-label')?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      return;
    }

    const input: BasePaymentInput = {
      productId: product.id,
      customer,
      cupomId: appliedCoupon?.cupom.id ?? null,
      shipping:
        fisico && frete.selected
          ? { endereco: { ...address, cep: address.cep }, frete: frete.selected.preco, freteServicoId: frete.selected.id }
          : null,
    };

    if (method === 'pix') {
      await payment.payPix(input);
      return;
    }
    const cardInput = await card.validate();
    if (!cardInput) {
      focusFirstInvalid();
      return;
    }
    await payment.payCard(input, cardInput);
  };

  /* ---------- telas de resultado ---------- */
  const { result } = payment;

  if (result?.kind === 'paid') {
    return (
      <PaymentSuccess
        area={product.area}
        email={customer.email}
        productTitle={product.title}
        total={result.total ?? totals.total}
        message={result.message}
        returnUrl={returnUrl}
      />
    );
  }
  if (result?.kind === 'review') {
    return <PaymentReview message={result.message} returnUrl={returnUrl} />;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-start">
      <div className="order-2 min-w-0 lg:order-1">
        {result?.kind === 'pix' ? (
          <PixPayment
            pix={result.pix}
            externalReference={result.externalReference}
            total={result.total}
            email={customer.email}
            onPaid={() => payment.markPaid('pix', result.total ?? totals.total)}
            onNewCode={payment.clearResult}
          />
        ) : (
          <form ref={formRef} onSubmit={onSubmit} noValidate className="grid grid-cols-1 gap-5">
            <Section step={1} title="Seus dados">
              <CustomerSection
                values={customer}
                errors={customerErrors}
                onChange={setCustomerField}
                emailLocked={Boolean(prefill.email)}
                emailHint={
                  prefill.email
                    ? 'Vinculado à sua conta BrooStock.'
                    : product.area === 'aplicativos'
                      ? 'A licença fica vinculada a este e-mail.'
                      : 'Enviaremos a confirmação e o produto para este e-mail.'
                }
              />
            </Section>

            {fisico && (
              <Section step={2} title="Entrega">
                <ShippingSection
                  address={address}
                  errors={addressErrors}
                  onChange={setAddressField}
                  cepStatus={cepStatus}
                  frete={frete.state}
                  freteSlow={frete.slow}
                  selectedId={frete.selectedId}
                  onSelect={(id) => {
                    frete.select(id);
                    setFreteError(undefined);
                  }}
                  freteError={freteError}
                />
              </Section>
            )}

            <Section step={fisico ? 3 : 2} title="Cupom de desconto">
              <CouponSection state={coupon.state} slow={coupon.slow} onApply={(c) => void coupon.apply(c)} onRemove={coupon.remove} />
            </Section>

            <Section step={fisico ? 4 : 3} title="Pagamento">
              <PaymentTabs value={method} onChange={(m) => { setMethod(m); payment.setError(null); }} />

              <div className="mt-5">
                {method === 'pix' ? (
                  <div role="tabpanel" id="panel-pix" aria-labelledby="tab-pix" className="space-y-3 text-sm text-ink-muted">
                    <p>
                      Gere um QR Code e pague pelo app do seu banco. A confirmação é rápida e o produto é liberado assim que o pagamento é
                      identificado.
                    </p>
                  </div>
                ) : (
                  <div role="tabpanel" id="panel-cartao" aria-labelledby="tab-cartao">
                    <p className="mb-4 flex items-start gap-2 rounded-lg bg-surface p-3 text-xs leading-5 text-ink-muted">
                      <ShieldCheck aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                      Os dados do cartão são enviados diretamente ao Mercado Pago e nunca passam pelos nossos servidores.
                    </p>
                    <CardFields
                      values={card.values}
                      errors={card.errors}
                      bin={card.bin}
                      installments={card.installments}
                      sdkError={card.sdkError}
                      onChange={card.setField}
                      onInstallments={card.setInstallments}
                    />
                  </div>
                )}
              </div>

              <div className="mt-5 space-y-3">
                {payment.error && <Alert tone="error">{payment.error}</Alert>}
                <SlowNotice show={payment.slow && payment.busy !== null} />
                <Button type="submit" variant={method === 'pix' ? 'success' : 'primary'} size="lg" className="w-full" loading={payment.busy !== null}>
                  {payment.busy === 'pix' ? (
                    'Gerando PIX...'
                  ) : payment.busy === 'cartao' ? (
                    'Processando pagamento...'
                  ) : method === 'pix' ? (
                    <>
                      <Lock aria-hidden="true" className="h-4 w-4" /> Gerar QR Code PIX · {formatBRL(totals.total)}
                    </>
                  ) : (
                    <>
                      <CreditCard aria-hidden="true" className="h-4 w-4" /> Pagar {formatBRL(totals.total)} com cartão
                    </>
                  )}
                </Button>
                <p className="text-center text-xs text-ink-muted">
                  Ao continuar, você concorda com os{' '}
                  <a href="/termos" target="_blank" rel="noopener noreferrer" className="font-medium text-brand-700 underline">
                    Termos de uso
                  </a>{' '}
                  e a{' '}
                  <a href="/privacidade" target="_blank" rel="noopener noreferrer" className="font-medium text-brand-700 underline">
                    Política de privacidade
                  </a>
                  .
                </p>
              </div>
            </Section>
          </form>
        )}
      </div>

      <div className={`order-1 lg:sticky lg:top-6 lg:order-2 ${result?.kind === 'pix' ? 'hidden lg:block' : ''}`}>
        <OrderSummary
          product={product}
          totals={totals}
          couponCode={appliedCoupon?.cupom.codigo}
          frete={fisico ? frete.selected : null}
        />
      </div>
    </div>
  );
}
