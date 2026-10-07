import { Lock, Package } from 'lucide-react';
import { ProductImage } from '@/components/product/ProductImage';
import { TipoBadge } from '@/components/product/Badges';
import type { CheckoutProduct } from '@/hooks/useCheckoutProduct';
import { AREA_INFO } from '@/lib/categorias';
import { formatBRL } from '@/lib/format';
import { freteNome } from '@/lib/frete';
import type { Totals } from '@/lib/totals';
import type { FreteOption } from '@/types';

interface Props {
  product: CheckoutProduct;
  totals: Totals;
  couponCode?: string | null;
  frete: FreteOption | null;
}

function Row({ label, value, tone }: { label: string; value: string; tone?: 'green' }) {
  return (
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <dt className="text-ink-muted">{label}</dt>
      <dd className={tone === 'green' ? 'font-semibold text-emerald-700' : 'font-medium text-ink'}>{value}</dd>
    </div>
  );
}

export function OrderSummary({ product, totals, couponCode, frete }: Props) {
  const fisico = product.area === 'fisicos';
  return (
    <aside aria-label="Resumo do pedido" className="rounded-2xl border border-surface-line bg-white p-4 shadow-card sm:p-5">
      <h2 className="text-base font-bold text-ink">Resumo do pedido</h2>

      <div className="mt-4 flex gap-3">
        <ProductImage
          src={product.imageUrl}
          alt={`Capa de ${product.title}`}
          tipo={product.tipo}
          className="h-20 w-16 shrink-0 rounded-lg border border-surface-line"
        />
        <div className="min-w-0">
          <TipoBadge tipo={product.tipo} />
          <p className="mt-1 line-clamp-2 text-sm font-semibold leading-5 text-ink">{product.title}</p>
          {product.author && <p className="truncate text-xs text-ink-muted">Por {product.author}</p>}
        </div>
      </div>

      <dl className="mt-4 space-y-2 border-t border-surface-line pt-4">
        <Row label="Produto" value={formatBRL(totals.price)} />
        {totals.discount > 0 && <Row label={couponCode ? `Cupom ${couponCode}` : 'Desconto'} value={`-${formatBRL(totals.discount)}`} tone="green" />}
        {fisico && <Row label={frete ? `Frete (${freteNome(frete)})` : 'Frete'} value={frete ? formatBRL(totals.frete) : 'Informe o CEP'} />}
        <div className="flex items-baseline justify-between gap-3 border-t border-surface-line pt-3">
          <dt className="text-base font-bold text-ink">Total</dt>
          <dd className="text-2xl font-extrabold tracking-tight text-brand-700" data-testid="order-total">
            {formatBRL(totals.total)}
          </dd>
        </div>
      </dl>

      <p className="mt-4 flex items-start gap-2 rounded-lg bg-surface p-3 text-xs leading-5 text-ink-muted">
        {fisico ? (
          <Package aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />
        ) : (
          <Lock aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />
        )}
        {AREA_INFO[product.area].entrega}.
        {fisico ? ' Você recebe um e-mail de confirmação e entramos em contato sobre o envio.' : ' Você recebe tudo no e-mail informado.'}
      </p>
    </aside>
  );
}
