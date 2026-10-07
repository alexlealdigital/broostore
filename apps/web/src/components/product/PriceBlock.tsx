import { cn } from '@/lib/cn';
import { discountPercent, formatBRL } from '@/lib/format';

interface Props {
  price: number;
  originalPrice: number | null;
  size?: 'sm' | 'lg';
  className?: string;
  /** exibe o selo -N% ao lado do preco (cards ja mostram o selo na capa) */
  showBadge?: boolean;
}

/** Preco atual, preco original riscado e selo de desconto. */
export function PriceBlock({ price, originalPrice, size = 'sm', className, showBadge = true }: Props) {
  const pct = discountPercent(price, originalPrice);
  const free = price <= 0;
  return (
    <div className={cn('flex flex-wrap items-baseline gap-x-2 gap-y-0.5', className)}>
      <span className={cn('font-extrabold tracking-tight text-ink', size === 'lg' ? 'text-3xl' : 'text-lg')}>
        {free ? 'Grátis' : formatBRL(price)}
      </span>
      {pct > 0 && originalPrice && (
        <>
          <span className={cn('text-ink-muted line-through', size === 'lg' ? 'text-base' : 'text-xs')}>
            <span className="sr-only">De </span>
            {formatBRL(originalPrice)}
          </span>
          {showBadge && (
            <span
              className={cn(
                'rounded-md bg-accent-500 font-bold text-ink',
                size === 'lg' ? 'px-2 py-0.5 text-sm' : 'px-1.5 py-0.5 text-[11px]',
              )}
            >
              -{pct}%
            </span>
          )}
        </>
      )}
    </div>
  );
}
