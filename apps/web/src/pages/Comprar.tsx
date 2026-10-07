import { ArrowLeft } from 'lucide-react';
import { Link, Redirect, useParams, useSearchParams } from 'wouter';
import { CheckoutForm } from '@/components/checkout/CheckoutForm';
import { SlowNotice } from '@/components/checkout/SlowNotice';
import { ButtonLink } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState, ErrorState } from '@/components/ui/StateViews';
import { useCheckoutProduct } from '@/hooks/useCheckoutProduct';
import { usePageMeta } from '@/hooks/usePageMeta';
import { isEmail, safeHttpUrl } from '@/lib/validators';

function parseId(raw: string | null | undefined): number | null {
  return raw && /^\d+$/.test(raw.trim()) ? Number(raw.trim()) : null;
}

function CheckoutSkeleton({ slow }: { slow: boolean }) {
  return (
    <div role="status" aria-label="Carregando checkout" className="space-y-5">
      <SlowNotice show={slow} />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="order-2 space-y-5 lg:order-1">
          <Skeleton className="h-56 w-full rounded-2xl" />
          <Skeleton className="h-72 w-full rounded-2xl" />
        </div>
        <Skeleton className="order-1 h-60 w-full rounded-2xl lg:order-2" />
      </div>
    </div>
  );
}

function CheckoutFlow({ id }: { id: number | null }) {
  usePageMeta('Finalizar compra');
  const [params] = useSearchParams();
  const { state, slow, retry } = useCheckoutProduct(id);

  // Parametros usados pelo BrooStock: email (pre-preenchido e travado), nome e return (link de volta).
  const emailParam = (params.get('email') ?? '').trim();
  const prefill = { email: isEmail(emailParam) ? emailParam : null, nome: (params.get('nome') ?? '').trim() };
  const returnUrl = safeHttpUrl(params.get('return'));

  const back =
    returnUrl !== null ? (
      <a
        href={returnUrl}
        className="inline-flex items-center gap-1.5 rounded text-sm font-medium text-ink-muted hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      >
        <ArrowLeft aria-hidden="true" className="h-4 w-4" /> Voltar
      </a>
    ) : id !== null ? (
      <Link
        href={`/produto/${id}`}
        className="inline-flex items-center gap-1.5 rounded text-sm font-medium text-ink-muted hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      >
        <ArrowLeft aria-hidden="true" className="h-4 w-4" /> Voltar ao produto
      </Link>
    ) : (
      <Link href="/loja" className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-muted hover:text-brand-700">
        <ArrowLeft aria-hidden="true" className="h-4 w-4" /> Voltar para a loja
      </Link>
    );

  return (
    <Container className="py-6 sm:py-8">
      <div className="mb-5">{back}</div>
      <h1 className="mb-6 text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">Finalizar compra</h1>

      {state.status === 'loading' && <CheckoutSkeleton slow={slow} />}

      {state.status === 'error' && <ErrorState title="Não conseguimos carregar o produto" onRetry={retry}>{state.message}</ErrorState>}

      {(state.status === 'invalid' || state.status === 'not-found' || state.status === 'unavailable') && (
        <EmptyState
          title={state.status === 'unavailable' ? 'Produto indisponível' : state.status === 'invalid' ? 'Produto não informado' : 'Produto não encontrado'}
          action={<ButtonLink href="/loja">Ver a loja</ButtonLink>}
        >
          {state.status === 'invalid'
            ? 'Escolha um produto na loja para continuar com a compra.'
            : 'Este produto não está disponível para compra no momento.'}
        </EmptyState>
      )}

      {state.status === 'success' && <CheckoutForm key={state.product.id} product={state.product} prefill={prefill} returnUrl={returnUrl} />}
    </Container>
  );
}

/**
 * /comprar/:id  (canonica)  e  /comprar?produto=ID&email=&nome=&return=  (compatibilidade com o BrooStock).
 * A forma antiga e redirecionada para a canonica preservando os demais parametros.
 */
export default function Comprar() {
  const { id } = useParams<{ id?: string }>();
  const [params] = useSearchParams();
  const legacyId = parseId(params.get('produto'));

  if (!id && legacyId !== null) {
    const rest = new URLSearchParams(params);
    rest.delete('produto');
    const qs = rest.toString();
    return <Redirect to={`/comprar/${legacyId}${qs ? `?${qs}` : ''}`} replace />;
  }
  return <CheckoutFlow id={parseId(id)} />;
}
