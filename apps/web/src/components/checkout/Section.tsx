import type { ReactNode } from 'react';

/** Cartao numerado de uma etapa do checkout. */
export function Section({ step, title, children, aside }: { step: number; title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section aria-labelledby={`sec-${step}`} className="min-w-0 rounded-2xl border border-surface-line bg-white p-4 shadow-card sm:p-6">
      <div className="mb-4 flex items-center gap-3">
        <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white">
          {step}
        </span>
        <h2 id={`sec-${step}`} className="text-base font-bold text-ink sm:text-lg">
          {title}
        </h2>
        {aside && <div className="ml-auto">{aside}</div>}
      </div>
      {children}
    </section>
  );
}
