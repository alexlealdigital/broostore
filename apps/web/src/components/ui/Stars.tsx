import { Star } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/cn';
import { formatRating, pluralize } from '@/lib/format';

/** Estrelas somente leitura, com preenchimento fracionado. */
export function Stars({ value, size = 16, className }: { value: number; size?: number; className?: string }) {
  const clamped = Math.max(0, Math.min(5, value));
  return (
    <span className={cn('inline-flex items-center gap-0.5', className)} aria-hidden="true">
      {[0, 1, 2, 3, 4].map((i) => {
        const fill = Math.max(0, Math.min(1, clamped - i));
        return (
          <span key={i} className="relative inline-block" style={{ width: size, height: size }}>
            <Star width={size} height={size} className="absolute inset-0 text-gray-300" strokeWidth={1.75} />
            <span className="absolute inset-0 overflow-hidden" style={{ width: `${fill * 100}%` }}>
              <Star width={size} height={size} className="fill-accent-500 text-accent-500" strokeWidth={1.75} />
            </span>
          </span>
        );
      })}
    </span>
  );
}

/** Nota media + contagem, com texto acessivel. */
export function RatingSummaryInline({ average, count, size = 14 }: { average: number; count: number; size?: number }) {
  if (count === 0) {
    return <span className="text-xs text-ink-muted">Sem avaliações</span>;
  }
  return (
    <span
      className="inline-flex items-center gap-1.5"
      aria-label={`Nota ${formatRating(average)} de 5, ${count} ${pluralize(count, 'avaliação', 'avaliações')}`}
    >
      <Stars value={average} size={size} />
      <span aria-hidden="true" className="text-xs text-ink-muted">
        {formatRating(average)} ({count})
      </span>
    </span>
  );
}

/** Seletor de nota (radiogroup) navegavel por teclado. */
export function StarInput({
  value,
  onChange,
  disabled,
  labelledBy,
}: {
  value: number | null;
  onChange: (rating: number) => void;
  disabled?: boolean;
  labelledBy?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const shown = hover ?? value ?? 0;
  return (
    <div role="radiogroup" aria-labelledby={labelledBy} className="inline-flex items-center gap-1" onMouseLeave={() => setHover(null)}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n} ${pluralize(n, 'estrela', 'estrelas')}`}
          disabled={disabled}
          onClick={() => onChange(n)}
          onMouseEnter={() => setHover(n)}
          onFocus={() => setHover(n)}
          onBlur={() => setHover(null)}
          className="rounded p-0.5 transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Star
            aria-hidden="true"
            width={30}
            height={30}
            strokeWidth={1.75}
            className={cn(n <= shown ? 'fill-accent-500 text-accent-500' : 'text-gray-300')}
          />
        </button>
      ))}
    </div>
  );
}
