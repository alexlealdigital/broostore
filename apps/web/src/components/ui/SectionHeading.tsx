import type { ReactNode } from 'react';
import { Link } from 'wouter';
import { ArrowRight } from 'lucide-react';

export function SectionHeading({
  title,
  subtitle,
  href,
  linkLabel = 'Ver todos',
  id,
  actions,
}: {
  title: string;
  subtitle?: string;
  href?: string;
  linkLabel?: string;
  id?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5 flex items-end justify-between gap-4">
      <div className="min-w-0">
        <h2 id={id} className="text-xl font-bold tracking-tight text-ink sm:text-2xl">
          {title}
        </h2>
        {subtitle && <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>}
      </div>
      {actions}
      {href && (
        <Link
          href={href}
          className="inline-flex shrink-0 items-center gap-1 rounded text-sm font-semibold text-brand-700 hover:text-brand-800 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          {linkLabel}
          <ArrowRight aria-hidden="true" className="h-4 w-4" />
        </Link>
      )}
    </div>
  );
}
