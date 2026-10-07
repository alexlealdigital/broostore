import { CreditCard, Mail, ShieldCheck, Truck, type LucideIcon } from 'lucide-react';
import { Container } from '@/components/ui/Container';

const ITEMS: Array<{ icon: LucideIcon; title: string; text: string }> = [
  { icon: ShieldCheck, title: 'Pagamento seguro', text: 'Processado pelo Mercado Pago' },
  { icon: CreditCard, title: 'PIX e cartão', text: 'Pague do jeito que preferir' },
  { icon: Mail, title: 'Entrega por e-mail', text: 'Imediata para produtos digitais' },
  { icon: Truck, title: 'Frete calculado', text: 'Pelo CEP, nos produtos físicos' },
];

export function TrustStrip() {
  return (
    <section aria-label="Garantias da loja" className="border-y border-surface-line bg-white">
      <Container>
        <ul className="grid grid-cols-1 gap-x-6 gap-y-4 py-5 sm:grid-cols-2 lg:grid-cols-4">
          {ITEMS.map(({ icon: Icon, title, text }) => (
            <li key={title} className="flex items-center gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                <Icon aria-hidden="true" className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-ink">{title}</p>
                <p className="text-xs text-ink-muted">{text}</p>
              </div>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
