import { InputField, SelectField } from '@/components/ui/Field';
import { Alert } from '@/components/ui/Alert';
import type { CardForm, FieldErrors } from '@/lib/checkoutValidation';
import type { BinInfo } from '@/lib/mercadopago';

interface Props {
  values: CardForm;
  errors: FieldErrors;
  bin: BinInfo | null;
  installments: number;
  sdkError: string | null;
  onChange: (field: keyof CardForm, value: string) => void;
  onInstallments: (n: number) => void;
}

/** Campos do cartao. Os valores ficam so em memoria e vao direto ao Mercado Pago (tokenizacao). */
export function CardFields({ values, errors, bin, installments, sdkError, onChange, onInstallments }: Props) {
  return (
    <div className="grid gap-4">
      <InputField
        id="ck-card-number"
        label="Número do cartão"
        name="cc-number"
        inputMode="numeric"
        autoComplete="cc-number"
        required
        placeholder="0000 0000 0000 0000"
        maxLength={23}
        value={values.number}
        error={errors.number}
        onChange={(e) => onChange('number', e.target.value)}
        trailing={bin?.thumbnail ? <img src={bin.thumbnail} alt="" className="h-5 w-auto" /> : undefined}
      />
      <div className="grid grid-cols-2 gap-4">
        <InputField
          id="ck-card-expiry"
          label="Validade"
          name="cc-exp"
          inputMode="numeric"
          autoComplete="cc-exp"
          required
          placeholder="MM/AA"
          maxLength={5}
          value={values.expiry}
          error={errors.expiry}
          onChange={(e) => onChange('expiry', e.target.value)}
        />
        <InputField
          id="ck-card-cvv"
          label="CVV"
          name="cc-csc"
          inputMode="numeric"
          autoComplete="cc-csc"
          required
          placeholder="123"
          maxLength={4}
          value={values.cvv}
          error={errors.cvv}
          onChange={(e) => onChange('cvv', e.target.value)}
        />
      </div>
      <InputField
        id="ck-card-name"
        label="Nome no cartão"
        name="cc-name"
        autoComplete="cc-name"
        required
        placeholder="NOME COMO ESTÁ NO CARTÃO"
        value={values.holder}
        error={errors.holder}
        onChange={(e) => onChange('holder', e.target.value)}
      />
      <InputField
        id="ck-card-cpf"
        label="CPF do titular"
        name="cpf"
        inputMode="numeric"
        autoComplete="off"
        required
        placeholder="000.000.000-00"
        maxLength={14}
        value={values.cpf}
        error={errors.cpf}
        onChange={(e) => onChange('cpf', e.target.value)}
      />
      {bin && bin.installments.length > 0 && (
        <SelectField
          id="ck-card-installments"
          label="Parcelamento"
          value={String(installments)}
          onChange={(e) => onInstallments(Number(e.target.value))}
        >
          {bin.installments.map((i) => (
            <option key={i.value} value={i.value}>
              {i.label}
            </option>
          ))}
        </SelectField>
      )}
      {sdkError && <Alert tone="warning">{sdkError}</Alert>}
    </div>
  );
}
