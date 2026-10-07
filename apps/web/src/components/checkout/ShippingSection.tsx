import { Check, Truck } from 'lucide-react';
import { Alert } from '@/components/ui/Alert';
import { InputField, SelectField } from '@/components/ui/Field';
import { Spinner } from '@/components/ui/Spinner';
import type { FieldErrors } from '@/lib/checkoutValidation';
import type { FreteState } from '@/hooks/useFrete';
import { cn } from '@/lib/cn';
import { formatBRL, formatCEP } from '@/lib/format';
import { freteNome, prazoLabel } from '@/lib/frete';
import { UFS } from '@/lib/validators';
import type { Endereco } from '@/types';
import { SlowNotice } from './SlowNotice';

interface Props {
  address: Endereco;
  errors: FieldErrors;
  onChange: (field: keyof Endereco, value: string) => void;
  cepStatus: 'idle' | 'loading' | 'not-found' | 'error' | 'found';
  frete: FreteState;
  freteSlow: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
  freteError?: string;
}

export function ShippingSection({ address, errors, onChange, cepStatus, frete, freteSlow, selectedId, onSelect, freteError }: Props) {
  return (
    <div className="grid gap-4">
      <div className="grid gap-4 sm:grid-cols-[180px_1fr]">
        <InputField
          id="ck-cep"
          label="CEP"
          name="cep"
          autoComplete="postal-code"
          inputMode="numeric"
          required
          value={address.cep}
          error={errors.cep}
          maxLength={9}
          placeholder="00000-000"
          onChange={(e) => onChange('cep', formatCEP(e.target.value))}
          trailing={cepStatus === 'loading' ? <Spinner /> : cepStatus === 'found' ? <Check aria-hidden="true" className="h-4 w-4 text-emerald-600" /> : undefined}
          hint={
            cepStatus === 'not-found'
              ? 'CEP não encontrado no ViaCEP. Preencha o endereço manualmente.'
              : cepStatus === 'error'
                ? 'Não foi possível buscar o endereço. Preencha manualmente.'
                : 'Preenchemos o endereço e calculamos o frete.'
          }
        />
        <InputField
          id="ck-rua"
          label="Rua / Avenida"
          name="rua"
          autoComplete="address-line1"
          required
          value={address.rua}
          error={errors.rua}
          onChange={(e) => onChange('rua', e.target.value)}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-[120px_1fr_1fr]">
        <InputField
          id="ck-numero"
          label="Número"
          name="numero"
          autoComplete="off"
          required
          value={address.numero}
          error={errors.numero}
          onChange={(e) => onChange('numero', e.target.value)}
        />
        <InputField
          id="ck-complemento"
          label="Complemento"
          name="complemento"
          autoComplete="address-line2"
          value={address.complemento}
          onChange={(e) => onChange('complemento', e.target.value)}
          placeholder="Apto, bloco (opcional)"
        />
        <InputField
          id="ck-bairro"
          label="Bairro"
          name="bairro"
          autoComplete="address-level3"
          required
          value={address.bairro}
          error={errors.bairro}
          onChange={(e) => onChange('bairro', e.target.value)}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-[1fr_120px]">
        <InputField
          id="ck-cidade"
          label="Cidade"
          name="cidade"
          autoComplete="address-level2"
          required
          value={address.cidade}
          error={errors.cidade}
          onChange={(e) => onChange('cidade', e.target.value)}
        />
        <SelectField
          id="ck-estado"
          label="Estado"
          name="estado"
          autoComplete="address-level1"
          required
          value={address.estado}
          error={errors.estado}
          onChange={(e) => onChange('estado', e.target.value)}
        >
          <option value="">UF</option>
          {UFS.map((uf) => (
            <option key={uf} value={uf}>
              {uf}
            </option>
          ))}
        </SelectField>
      </div>

      <div aria-live="polite">
        <p id="frete-label" className="mb-2 flex items-center gap-2 text-sm font-medium text-ink-soft">
          <Truck aria-hidden="true" className="h-4 w-4 text-brand-600" /> Opções de frete
        </p>

        {frete.status === 'idle' && (
          <p className="rounded-lg border border-dashed border-surface-line bg-surface p-3 text-sm text-ink-muted">
            Informe o CEP para ver as opções de frete e prazo.
          </p>
        )}

        {frete.status === 'loading' && (
          <div className="space-y-3">
            <p className="flex items-center gap-2 rounded-lg bg-surface p-3 text-sm text-ink-muted">
              <Spinner className="text-brand-600" /> Calculando frete...
            </p>
            <SlowNotice show={freteSlow} />
          </div>
        )}

        {frete.status === 'error' && <Alert tone="error">{frete.message}</Alert>}

        {frete.status === 'ready' && (
          <div role="radiogroup" aria-labelledby="frete-label" className="grid gap-2">
            {frete.options.map((o) => {
              const checked = o.id === selectedId;
              return (
                <label
                  key={o.id}
                  className={cn(
                    'flex cursor-pointer items-center gap-3 rounded-xl border p-3 transition-colors focus-within:ring-2 focus-within:ring-brand-500',
                    checked ? 'border-brand-500 bg-brand-50' : 'border-surface-line bg-white hover:border-brand-300',
                  )}
                >
                  <input
                    type="radio"
                    name="frete"
                    value={o.id}
                    checked={checked}
                    onChange={() => onSelect(o.id)}
                    className="h-4 w-4 shrink-0 accent-brand-600"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                      <span className="text-sm font-semibold text-ink">{freteNome(o)}</span>
                      {o.destaque && (
                        <span className="rounded-full bg-emerald-600 px-2 py-0.5 text-[10px] font-semibold text-white">{o.destaque}</span>
                      )}
                    </span>
                    <span className="block text-xs text-ink-muted">{prazoLabel(o.prazo)}</span>
                  </span>
                  <span className="text-sm font-bold text-ink">{formatBRL(o.preco)}</span>
                </label>
              );
            })}
          </div>
        )}

        {freteError && <p role="alert" className="mt-2 text-xs font-medium text-red-600">{freteError}</p>}
      </div>
    </div>
  );
}
