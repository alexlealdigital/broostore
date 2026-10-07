import { Link } from 'wouter';
import { discountPercent } from '@/lib/format';
import { RatingSummaryInline } from '@/components/ui/Stars';
import type { Product, RatingSummary } from '@/types';
import { ClassificacaoBadge, TipoBadge } from './Badges';
import { PriceBlock } from './PriceBlock';
import { ProductImage } from './ProductImage';

export function ProductCard({ product, rating }: { product: Product; rating?: RatingSummary }) {
  const pct = discountPercent(product.price, product.originalPrice);
  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-xl border border-surface-line bg-white shadow-card transition duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-card-hover focus-within:ring-2 focus-within:ring-brand-500">
      <div className="relative aspect-[4/5] overflow-hidden bg-surface-alt">
        <ProductImage
          src={product.imageUrl}
          alt={`Capa de ${product.title}`}
          tipo={product.tipo}
          className="h-full w-full transition-transform duration-300 group-hover:scale-[1.03]"
        />
        <div className="absolute left-2 top-2">
          <ClassificacaoBadge value={product.classificacao} />
        </div>
        {pct > 0 && (
          <span className="absolute right-2 top-2 rounded-md bg-accent-500 px-2 py-1 text-xs font-extrabold text-ink shadow-sm">
            -{pct}%
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-3 sm:p-4">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-[11px] font-semibold uppercase tracking-wide text-ink-muted">{product.category}</span>
          <TipoBadge tipo={product.tipo} className="shrink-0" />
        </div>

        <h3 className="line-clamp-2 min-h-[2.5rem] text-sm font-semibold leading-5 text-ink sm:text-[15px]">
          {/* O link cobre o card inteiro (after:absolute) mantendo um unico alvo de foco por card */}
          <Link
            href={`/produto/${product.id}`}
            className="outline-none after:absolute after:inset-0 after:content-[''] group-hover:text-brand-700"
          >
            {product.title}
          </Link>
        </h3>

        <p className="truncate text-xs text-ink-muted">{product.author ? `Por ${product.author}` : 'Autor não informado'}</p>

        <RatingSummaryInline average={rating?.average ?? 0} count={rating?.count ?? 0} />

        <div className="mt-auto pt-2">
          <PriceBlock price={product.price} originalPrice={product.originalPrice} showBadge={false} />
        </div>
      </div>
    </article>
  );
}
