import { PackageSearch, RefreshCw, ServerCrash } from 'lucide-react';
import type { ReactNode } from 'react';
import { Button } from './Button';

function Shell({ icon, title, children, action }: { icon: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center rounded-2xl border border-dashed border-surface-line bg-white px-6 py-12 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-brand-50 text-brand-600">{icon}</div>
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      {children && <div className="mt-1.5 text-sm text-ink-muted">{children}</div>}
      {action && <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <Shell icon={<PackageSearch aria-hidden="true" className="h-7 w-7" />} title={title} action={action}>
      {children}
    </Shell>
  );
}

export function ErrorState({
  title = 'Algo deu errado',
  children = 'Não foi possível carregar agora. Verifique sua conexão e tente novamente.',
  onRetry,
  action,
}: {
  title?: string;
  children?: ReactNode;
  onRetry?: () => void;
  action?: ReactNode;
}) {
  return (
    <div role="alert">
      <Shell
        icon={<ServerCrash aria-hidden="true" className="h-7 w-7" />}
        title={title}
        action={
          <>
            {onRetry && (
              <Button onClick={onRetry}>
                <RefreshCw aria-hidden="true" className="h-4 w-4" /> Tentar novamente
              </Button>
            )}
            {action}
          </>
        }
      >
        {children}
      </Shell>
    </div>
  );
}
