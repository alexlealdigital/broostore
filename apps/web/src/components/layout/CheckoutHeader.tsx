import { Lock } from 'lucide-react';
import { Container } from '@/components/ui/Container';
import { Logo } from './Logo';

/** Cabecalho enxuto do checkout: menos distracoes, reforco de seguranca. */
export function CheckoutHeader() {
  return (
    <header className="border-b border-surface-line bg-white">
      <Container>
        <div className="flex h-16 items-center justify-between">
          <Logo />
          <p className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700 sm:text-sm">
            <Lock aria-hidden="true" className="h-4 w-4" />
            Pagamento seguro
          </p>
        </div>
      </Container>
    </header>
  );
}
