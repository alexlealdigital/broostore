import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type BadgeTone = 'neutral' | 'brand' | 'accent' | 'success' | 'danger' | 'dark';

const tones: Record<BadgeTone, string> = {
  neutral: 'bg-surface-alt text-ink-soft ring-1 ring-inset ring-surface-line',
  brand: 'bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-200',
  accent: 'bg-accent-500 text-ink',
  success: 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200',
  danger: 'bg-red-600 text-white',
  dark: 'bg-ink/85 text-white',
};

export function Badge({ tone = 'neutral', className, children }: { tone?: BadgeTone; className?: string; children: ReactNode }) {
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold leading-5', tones[tone], className)}>
      {children}
    </span>
  );
}
