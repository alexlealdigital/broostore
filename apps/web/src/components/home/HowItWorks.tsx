import { CreditCard, Download, Search } from 'lucide-react';
import { Container } from '@/components/ui/Container';
import { SectionHeading } from '@/components/ui/SectionHeading';

const STEPS = [
  { icon: Search, title: '1. Escolha', text: 'Navegue por ebooks, produtos físicos e aplicativos e veja detalhes e avaliações.' },
  { icon: CreditCard, title: '2. Pague', text: 'PIX com QR Code ou cartão de crédito parcelado, em ambiente seguro do Mercado Pago.' },
  { icon: Download, title: '3. Receba', text: 'Digitais e licenças chegam por e-mail. Produtos físicos são enviados para o seu endereço.' },
];

export function HowItWorks() {
  return (
    <section aria-labelledby="como-funciona" className="mt-16">
      <Container>
        <SectionHeading id="como-funciona" title="Como funciona" subtitle="Comprar na BrooStore leva poucos minutos." />
        <ol className="grid gap-4 md:grid-cols-3">
          {STEPS.map(({ icon: Icon, title, text }) => (
            <li key={title} className="rounded-2xl border border-surface-line bg-white p-5 shadow-card">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                <Icon aria-hidden="true" className="h-5 w-5" />
              </span>
              <h3 className="mt-4 text-base font-bold text-ink">{title}</h3>
              <p className="mt-1.5 text-sm leading-6 text-ink-muted">{text}</p>
            </li>
          ))}
        </ol>
      </Container>
    </section>
  );
}
