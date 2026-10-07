import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

const control =
  'block w-full rounded-lg border bg-white px-3 text-sm text-ink placeholder:text-gray-400 shadow-sm transition-colors ' +
  'focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 ' +
  'disabled:cursor-not-allowed disabled:bg-surface-alt disabled:text-ink-muted [&[readonly]]:bg-surface-alt [&[readonly]]:text-ink-soft';

function controlClass(error?: string | null, extra?: string) {
  return cn(control, error ? 'border-red-400 focus:border-red-500 focus:ring-red-500/30' : 'border-surface-line hover:border-gray-300', extra);
}

interface WrapperProps {
  label: string;
  hint?: ReactNode;
  error?: string | null;
  required?: boolean;
  className?: string;
  /** id do controle (gerado se omitido) */
  id?: string;
}

function FieldShell({
  id,
  label,
  hint,
  error,
  required,
  className,
  children,
}: WrapperProps & { id: string; children: ReactNode }) {
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-ink-soft">
        {label}
        {required && (
          <span className="ml-0.5 text-red-600" aria-hidden="true">
            *
          </span>
        )}
      </label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="mt-1.5 text-xs text-ink-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} role="alert" className="mt-1.5 text-xs font-medium text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}

function describedBy(id: string, hint?: ReactNode, error?: string | null) {
  if (error) return `${id}-error`;
  if (hint) return `${id}-hint`;
  return undefined;
}

export interface InputFieldProps extends WrapperProps, Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'className' | 'required'> {
  inputClassName?: string;
  /** conteudo a direita dentro do campo (ex.: icone) */
  trailing?: ReactNode;
}

export const InputField = forwardRef<HTMLInputElement, InputFieldProps>(function InputField(
  { label, hint, error, required, className, id, inputClassName, trailing, ...rest },
  ref,
) {
  const auto = useId();
  const inputId = id ?? auto;
  return (
    <FieldShell id={inputId} label={label} hint={hint} error={error} required={required} className={className}>
      <div className="relative">
        <input
          ref={ref}
          id={inputId}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(inputId, hint, error)}
          className={controlClass(error, cn('h-11', trailing ? 'pr-10' : undefined, inputClassName))}
          {...rest}
        />
        {trailing && <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-ink-muted">{trailing}</div>}
      </div>
    </FieldShell>
  );
});

export interface SelectFieldProps extends WrapperProps, Omit<SelectHTMLAttributes<HTMLSelectElement>, 'id' | 'className' | 'required'> {
  children: ReactNode;
}

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(function SelectField(
  { label, hint, error, required, className, id, children, ...rest },
  ref,
) {
  const auto = useId();
  const selectId = id ?? auto;
  return (
    <FieldShell id={selectId} label={label} hint={hint} error={error} required={required} className={className}>
      <select
        ref={ref}
        id={selectId}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(selectId, hint, error)}
        className={controlClass(error, 'h-11 pr-8')}
        {...rest}
      >
        {children}
      </select>
    </FieldShell>
  );
});

export interface TextareaFieldProps extends WrapperProps, Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'id' | 'className' | 'required'> {}

export const TextareaField = forwardRef<HTMLTextAreaElement, TextareaFieldProps>(function TextareaField(
  { label, hint, error, required, className, id, ...rest },
  ref,
) {
  const auto = useId();
  const areaId = id ?? auto;
  return (
    <FieldShell id={areaId} label={label} hint={hint} error={error} required={required} className={className}>
      <textarea
        ref={ref}
        id={areaId}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(areaId, hint, error)}
        className={controlClass(error, 'min-h-[140px] py-2.5')}
        {...rest}
      />
    </FieldShell>
  );
});
