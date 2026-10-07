import { CheckCircle2 } from 'lucide-react';
import { useId } from 'react';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { StarInput, Stars } from '@/components/ui/Stars';
import { useProductReviews } from '@/hooks/useProductReviews';
import { formatRating, pluralize } from '@/lib/format';

export function ReviewsSection({ productId }: { productId: number }) {
  const { distribution, status, myRating, sending, sendError, rate, retry } = useProductReviews(productId);
  const labelId = useId();
  const { counts, total, average } = distribution;

  return (
    <section id="avaliacoes" aria-labelledby="avaliacoes-titulo" className="scroll-mt-32">
      <h2 id="avaliacoes-titulo" className="text-xl font-bold text-ink">
        Avaliações
      </h2>

      <div className="mt-4 grid gap-6 rounded-2xl border border-surface-line bg-white p-5 shadow-card sm:p-6 md:grid-cols-[auto_1fr_1fr] md:items-center">
        {status === 'loading' ? (
          <div className="col-span-full space-y-3" role="status" aria-label="Carregando avaliações">
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
          </div>
        ) : status === 'error' ? (
          <div className="col-span-full">
            <Alert tone="warning" title="Não foi possível carregar as avaliações">
              <button type="button" onClick={retry} className="font-semibold underline">
                Tentar novamente
              </button>
            </Alert>
          </div>
        ) : (
          <>
            <div className="text-center md:px-4 md:text-left">
              <p className="text-5xl font-extrabold tracking-tight text-ink">{total ? formatRating(average) : '-'}</p>
              <Stars value={average} size={20} className="mt-1" />
              <p className="mt-1 text-sm text-ink-muted">
                {total ? `${total} ${pluralize(total, 'avaliação', 'avaliações')}` : 'Ainda sem avaliações'}
              </p>
            </div>

            <ul className="grid gap-1.5" aria-label="Distribuição das notas">
              {[5, 4, 3, 2, 1].map((n) => {
                const count = counts[n - 1] ?? 0;
                const pct = total ? (count / total) * 100 : 0;
                return (
                  <li key={n} className="flex items-center gap-2 text-xs text-ink-muted">
                    <span className="w-14 shrink-0">
                      {n} {pluralize(n, 'estrela', 'estrelas')}
                    </span>
                    <span className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
                      <span className="block h-full rounded-full bg-accent-500" style={{ width: `${pct}%` }} />
                    </span>
                    <span className="w-6 text-right tabular-nums">{count}</span>
                  </li>
                );
              })}
            </ul>

            <div className="border-t border-surface-line pt-5 md:border-l md:border-t-0 md:pl-6 md:pt-0">
              <p id={labelId} className="text-sm font-semibold text-ink">
                {myRating ? 'Obrigado pela sua avaliação!' : 'Já conhece este produto? Avalie'}
              </p>
              {myRating ? (
                <p className="mt-2 flex items-center gap-2 text-sm text-emerald-700">
                  <CheckCircle2 aria-hidden="true" className="h-4 w-4" />
                  Você deu {myRating} {pluralize(myRating, 'estrela', 'estrelas')}.
                </p>
              ) : (
                <div className="mt-2">
                  <StarInput value={null} onChange={(n) => void rate(n)} disabled={sending} labelledBy={labelId} />
                  <p className="mt-1.5 text-xs text-ink-muted">Toque em uma estrela para enviar sua nota.</p>
                </div>
              )}
              {sendError && (
                <Alert tone="error" className="mt-3">
                  {sendError}{' '}
                  <Button size="sm" variant="ghost" onClick={retry} className="h-auto p-0 underline">
                    Recarregar
                  </Button>
                </Alert>
              )}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
