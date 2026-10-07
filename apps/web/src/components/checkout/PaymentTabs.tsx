import { CreditCard, QrCode } from 'lucide-react';
import { useRef, type KeyboardEvent } from 'react';
import { cn } from '@/lib/cn';

export type PaymentMethod = 'pix' | 'cartao';

const TABS: Array<{ id: PaymentMethod; label: string; icon: typeof QrCode; hint: string }> = [
  { id: 'pix', label: 'PIX', icon: QrCode, hint: 'Aprovação na hora' },
  { id: 'cartao', label: 'Cartão', icon: CreditCard, hint: 'Crédito, parcelado' },
];

/** Seletor PIX/Cartao como tablist acessivel (setas movem o foco e selecionam). */
export function PaymentTabs({ value, onChange }: { value: PaymentMethod; onChange: (m: PaymentMethod) => void }) {
  const refs = useRef<Record<PaymentMethod, HTMLButtonElement | null>>({ pix: null, cartao: null });

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft' && e.key !== 'Home' && e.key !== 'End') return;
    e.preventDefault();
    const next: PaymentMethod = e.key === 'ArrowRight' || e.key === 'End' ? 'cartao' : 'pix';
    onChange(next);
    refs.current[next]?.focus();
  };

  return (
    <div role="tablist" aria-label="Forma de pagamento" onKeyDown={onKeyDown} className="grid grid-cols-2 gap-2">
      {TABS.map(({ id, label, icon: Icon, hint }) => {
        const selected = value === id;
        return (
          <button
            key={id}
            ref={(el) => {
              refs.current[id] = el;
            }}
            type="button"
            role="tab"
            id={`tab-${id}`}
            aria-selected={selected}
            aria-controls={`panel-${id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(id)}
            className={cn(
              'flex flex-col items-center gap-0.5 rounded-xl border-2 px-3 py-3 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2',
              selected ? 'border-brand-600 bg-brand-50 text-brand-800' : 'border-surface-line bg-white text-ink-soft hover:border-brand-300',
            )}
          >
            <span className="inline-flex items-center gap-2 text-sm font-bold">
              <Icon aria-hidden="true" className="h-5 w-5" />
              {label}
            </span>
            <span className="text-xs text-ink-muted">{hint}</span>
          </button>
        );
      })}
    </div>
  );
}
