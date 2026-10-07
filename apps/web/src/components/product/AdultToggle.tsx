import { ShieldAlert } from 'lucide-react';
import { useId, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { useAdultContent } from '@/hooks/useAdultContent';
import { cn } from '@/lib/cn';

/** Alterna a exibicao de produtos 18+ (com confirmacao de idade). Estado so em sessionStorage. */
export function AdultToggle() {
  const { allowed, allow, revoke } = useAdultContent();
  const [asking, setAsking] = useState(false);
  const panelId = useId();

  const onToggle = () => {
    if (allowed) revoke();
    else setAsking((v) => !v);
  };

  return (
    <div>
      <button
        type="button"
        role="switch"
        aria-checked={allowed}
        aria-controls={asking ? panelId : undefined}
        onClick={onToggle}
        className="inline-flex items-center gap-2.5 rounded-lg px-1 py-1.5 text-sm text-ink-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      >
        <span
          aria-hidden="true"
          className={cn('relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors', allowed ? 'bg-brand-600' : 'bg-gray-300')}
        >
          <span className={cn('inline-block h-4 w-4 rounded-full bg-white shadow transition-transform', allowed ? 'translate-x-4' : 'translate-x-0.5')} />
        </span>
        Mostrar conteúdo +18
      </button>

      {asking && !allowed && (
        <div id={panelId} role="group" aria-label="Confirmação de idade" className="mt-2 max-w-md animate-fade-in rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="flex items-start gap-2 text-sm text-amber-900">
            <ShieldAlert aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
            Esta seção contém obras classificadas para maiores de 18 anos. Confirme que você tem 18 anos ou mais para continuar.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              size="sm"
              onClick={() => {
                allow();
                setAsking(false);
              }}
            >
              Sim, tenho 18 anos ou mais
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setAsking(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
