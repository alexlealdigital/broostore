import { Link } from 'wouter';
import { cn } from '@/lib/cn';

export function Logo({ className, onDark }: { className?: string; onDark?: boolean }) {
  return (
    <Link
      href="/"
      aria-label="BrooStore, página inicial"
      className={cn('inline-flex items-center gap-2.5 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2', className)}
    >
      <img src="/192_192.png" alt="" width={36} height={36} className="h-9 w-9 rounded-lg shadow-sm" />
      <span className={cn('text-xl font-extrabold tracking-tight', onDark ? 'text-white' : 'text-brand-700')}>
        Broo<span className={onDark ? 'text-brand-200' : 'text-brand-500'}>Store</span>
      </span>
    </Link>
  );
}
