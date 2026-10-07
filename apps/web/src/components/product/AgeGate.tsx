import { ShieldAlert } from 'lucide-react';
import { Button, ButtonLink } from '@/components/ui/Button';

export function AgeGate({ onConfirm }: { onConfirm: () => void }) {
  return (
    <div className="mx-auto max-w-lg rounded-2xl border border-amber-200 bg-white p-8 text-center shadow-card">
      <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-50 text-amber-600">
        <ShieldAlert aria-hidden="true" className="h-7 w-7" />
      </span>
      <h1 className="mt-4 text-xl font-bold text-ink">Conteúdo para maiores de 18 anos</h1>
      <p className="mt-2 text-sm text-ink-muted">
        Este produto é classificado como 18+. Confirme que você tem 18 anos ou mais para visualizá-lo.
      </p>
      <div className="mt-6 flex flex-col justify-center gap-2 sm:flex-row">
        <Button onClick={onConfirm}>Sim, tenho 18 anos ou mais</Button>
        <ButtonLink href="/loja" variant="secondary">
          Voltar para a loja
        </ButtonLink>
      </div>
    </div>
  );
}
