import { ArrowRight } from 'lucide-react';
import { Link } from 'wouter';
import { AREAS, AREA_INFO } from '@/lib/categorias';
import { cn } from '@/lib/cn';
import { pluralize } from '@/lib/format';
import type { Area } from '@/types';

const accents: Record<Area, { icon: string; ring: string; chip: string }> = {
  digitais: { icon: 'bg-brand-600 text-white', ring: 'hover:border-brand-300', chip: 'text-brand-700' },
  fisicos: { icon: 'bg-accent-500 text-ink', ring: 'hover:border-accent-400', chip: 'text-accent-700' },
  aplicativos: { icon: 'bg-violet-600 text-white', ring: 'hover:border-violet-300', chip: 'text-violet-700' },
};

/** Tres entradas grandes para as areas da loja. */
export function AreaCards({ counts }: { counts?: Record<Area, number> }) {
  return (
    <ul className="grid gap-4 md:grid-cols-3">
      {AREAS.map((area) => {
        const info = AREA_INFO[area];
        const Icon = info.icon;
        const a = accents[area];
        const count = counts?.[area];
        return (
          <li key={area}>
            <Link
              href={`/loja?area=${area}`}
              className={cn(
                'group flex h-full flex-col rounded-2xl border border-surface-line bg-white p-5 shadow-card transition duration-200 hover:-translate-y-0.5 hover:shadow-card-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 sm:p-6',
                a.ring,
              )}
            >
              <span className={cn('mb-4 flex h-12 w-12 items-center justify-center rounded-xl shadow-sm', a.icon)}>
                <Icon aria-hidden="true" className="h-6 w-6" />
              </span>
              <h3 className="text-xl font-bold text-ink">{info.label}</h3>
              <p className="mt-1.5 flex-1 text-sm leading-6 text-ink-muted">{info.descricao}</p>
              <span className={cn('mt-4 inline-flex items-center gap-1.5 text-sm font-semibold', a.chip)}>
                {count !== undefined ? `${count} ${pluralize(count, 'produto', 'produtos')}` : 'Ver produtos'}
                <ArrowRight aria-hidden="true" className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
