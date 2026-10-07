import { Loader2 } from 'lucide-react';

/** Aviso amigavel quando a API (plano free) demora para responder. */
export function SlowNotice({ show, className }: { show: boolean; className?: string }) {
  if (!show) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-start gap-3 rounded-lg border border-brand-200 bg-brand-50 p-3 text-sm text-brand-900 ${className ?? ''}`}
    >
      <Loader2 aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-brand-600" />
      <p>
        <span className="font-semibold">Acordando o servidor...</span> Isso pode levar alguns segundos na primeira vez. Não feche esta página.
      </p>
    </div>
  );
}
