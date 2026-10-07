import { cn } from '@/lib/cn';

/** Bloco cinza com brilho animado (respeita prefers-reduced-motion via index.css). */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn('skeleton rounded-md bg-gray-200', className)} />;
}
