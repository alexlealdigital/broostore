import { cn } from '@/lib/cn';

export type ButtonVariant = 'primary' | 'accent' | 'secondary' | 'ghost' | 'danger' | 'success' | 'inverse';
export type ButtonSize = 'sm' | 'md' | 'lg';

const base =
  'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors duration-150 ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 ' +
  'disabled:cursor-not-allowed disabled:opacity-60 select-none whitespace-nowrap';

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-brand-600 text-white shadow-sm hover:bg-brand-700 active:bg-brand-800',
  accent: 'bg-accent-500 text-ink shadow-sm hover:bg-accent-400 active:bg-accent-600 focus-visible:ring-accent-500',
  secondary: 'border border-surface-line bg-white text-ink-soft shadow-sm hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700',
  ghost: 'text-ink-soft hover:bg-surface-alt hover:text-ink',
  danger: 'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500',
  success: 'bg-emerald-600 text-white shadow-sm hover:bg-emerald-700 focus-visible:ring-emerald-500',
  inverse: 'bg-white text-brand-700 shadow-sm hover:bg-brand-50 focus-visible:ring-white focus-visible:ring-offset-brand-700',
};

const sizes: Record<ButtonSize, string> = {
  sm: 'h-9 px-3 text-sm',
  md: 'h-11 px-4 text-sm',
  lg: 'h-12 px-6 text-base',
};

export function buttonClasses(variant: ButtonVariant = 'primary', size: ButtonSize = 'md', extra?: string): string {
  return cn(base, variants[variant], sizes[size], extra);
}
