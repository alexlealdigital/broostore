import { CheckCircle2, Tag, XCircle } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { SlowNotice } from './SlowNotice';
import { couponDescription, type CouponState } from '@/hooks/useCoupon';

interface Props {
  state: CouponState;
  slow: boolean;
  onApply: (code: string) => void;
  onRemove: () => void;
}

export function CouponSection({ state, slow, onApply, onRemove }: Props) {
  const [code, setCode] = useState('');
  const applied = state.status === 'applied';
  const loading = state.status === 'loading';

  return (
    <div>
      <label htmlFor="ck-cupom" className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-ink-soft">
        <Tag aria-hidden="true" className="h-4 w-4 text-brand-600" /> Tem um cupom? <span className="font-normal text-ink-muted">(opcional)</span>
      </label>
      <div className="flex gap-2">
        <input
          id="ck-cupom"
          type="text"
          value={applied ? state.cupom.codigo : code}
          disabled={applied || loading}
          maxLength={20}
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              if (!applied) onApply(code);
            }
          }}
          aria-describedby="ck-cupom-status"
          placeholder="Digite seu cupom"
          className="h-11 min-w-0 flex-1 rounded-lg border border-surface-line bg-white px-3 text-sm uppercase text-ink shadow-sm placeholder:normal-case placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/40 disabled:bg-surface-alt"
        />
        {applied ? (
          <Button variant="secondary" onClick={onRemove}>
            Remover
          </Button>
        ) : (
          <Button variant="secondary" loading={loading} onClick={() => onApply(code)}>
            Aplicar
          </Button>
        )}
      </div>
      <div id="ck-cupom-status" aria-live="polite" className="mt-2 text-sm empty:hidden">
        {state.status === 'applied' && (
          <p className="flex items-center gap-1.5 font-medium text-emerald-700">
            <CheckCircle2 aria-hidden="true" className="h-4 w-4" />
            Cupom {state.cupom.codigo} aplicado: {couponDescription(state.cupom, state.calculo)}
          </p>
        )}
        {state.status === 'error' && (
          <p className="flex items-center gap-1.5 font-medium text-red-600">
            <XCircle aria-hidden="true" className="h-4 w-4" />
            {state.message}
          </p>
        )}
      </div>
      <SlowNotice show={slow && loading} className="mt-2" />
    </div>
  );
}
