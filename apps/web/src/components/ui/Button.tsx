import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Link } from 'wouter';
import { Spinner } from './Spinner';
import { buttonClasses, type ButtonSize, type ButtonVariant } from './buttonStyles';

interface CommonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children?: ReactNode;
}

export interface ButtonProps extends CommonProps, Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className'> {
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', className, loading = false, disabled, children, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClasses(variant, size, className)}
      {...rest}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
});

interface ButtonLinkProps extends CommonProps {
  href: string;
  /** Link externo (<a> comum, com rel seguro). Abre em nova aba, exceto se `sameTab`. */
  external?: boolean;
  sameTab?: boolean;
  onClick?: () => void;
}

/** Link com aparencia de botao. Rotas internas usam o roteador; externas, <a> com rel seguro. */
export function ButtonLink({ href, external, sameTab, variant, size, className, children, onClick }: ButtonLinkProps) {
  const cls = buttonClasses(variant, size, className);
  if (external) {
    return (
      <a href={href} className={cls} target={sameTab ? undefined : '_blank'} rel="noopener noreferrer" onClick={onClick}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={cls} onClick={onClick}>
      {children}
    </Link>
  );
}
