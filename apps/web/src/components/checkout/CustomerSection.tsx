import { InputField } from '@/components/ui/Field';
import type { CustomerForm, FieldErrors } from '@/lib/checkoutValidation';
import { formatPhone } from '@/lib/format';

interface Props {
  values: CustomerForm;
  errors: FieldErrors;
  onChange: (field: keyof CustomerForm, value: string) => void;
  emailLocked: boolean;
  emailHint: string;
}

export function CustomerSection({ values, errors, onChange, emailLocked, emailHint }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <InputField
        id="ck-nome"
        label="Nome completo"
        name="nome"
        autoComplete="name"
        required
        className="sm:col-span-2"
        value={values.nome}
        error={errors.nome}
        onChange={(e) => onChange('nome', e.target.value)}
        placeholder="Como no seu documento"
      />
      <InputField
        id="ck-email"
        label="E-mail"
        name="email"
        type="email"
        autoComplete="email"
        inputMode="email"
        required
        value={values.email}
        error={errors.email}
        readOnly={emailLocked}
        hint={emailHint}
        onChange={(e) => onChange('email', e.target.value)}
        placeholder="voce@email.com"
      />
      <InputField
        id="ck-telefone"
        label="Telefone (com DDD)"
        name="telefone"
        type="tel"
        autoComplete="tel-national"
        inputMode="tel"
        required
        value={values.telefone}
        error={errors.telefone}
        onChange={(e) => onChange('telefone', formatPhone(e.target.value))}
        placeholder="(11) 99999-9999"
        maxLength={15}
      />
    </div>
  );
}
