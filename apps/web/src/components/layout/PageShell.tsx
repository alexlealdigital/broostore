import type { ReactNode } from 'react';
import { Container } from '@/components/ui/Container';
import { cn } from '@/lib/cn';

/** Estrutura padrao das paginas institucionais. */
export function PageShell({
  title,
  intro,
  children,
  narrow = true,
}: {
  title: string;
  intro?: string;
  children: ReactNode;
  narrow?: boolean;
}) {
  return (
    <>
      <div className="border-b border-surface-line bg-gradient-to-b from-brand-50 to-white">
        <Container className={cn('py-10 sm:py-14', narrow && 'max-w-4xl')}>
          <h1 className="text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">{title}</h1>
          {intro && <p className="mt-3 max-w-2xl text-base leading-7 text-ink-muted sm:text-lg">{intro}</p>}
        </Container>
      </div>
      <Container className={cn('py-10', narrow && 'max-w-4xl')}>{children}</Container>
    </>
  );
}

/** Tipografia para texto corrido (termos, privacidade). */
export function Prose({ children }: { children: ReactNode }) {
  return (
    <div className="space-y-4 text-[15px] leading-7 text-ink-soft [&_a]:font-medium [&_a]:text-brand-700 [&_a]:underline [&_h2]:mt-8 [&_h2]:text-xl [&_h2]:font-bold [&_h2]:text-ink [&_li]:ml-5 [&_li]:list-disc [&_li]:pl-1">
      {children}
    </div>
  );
}
