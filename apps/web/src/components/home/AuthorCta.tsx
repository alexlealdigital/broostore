import { PenLine, Rocket, Wallet } from 'lucide-react';
import { ButtonLink } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';

const POINTS = [
  { icon: PenLine, text: 'Publique ebooks, produtos físicos, games e apps' },
  { icon: Wallet, text: 'Receba pelas vendas via Mercado Pago' },
  { icon: Rocket, text: 'Entrega automática por e-mail para o cliente' },
];

export function AuthorCta() {
  return (
    <section aria-labelledby="autor-cta-title" className="mt-16">
      <Container>
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-brand-800 to-brand-600 px-6 py-10 text-white shadow-card sm:px-10 sm:py-12">
          <div aria-hidden="true" className="absolute -right-10 -top-10 h-56 w-56 rounded-full bg-accent-500/25 blur-3xl" />
          <div className="relative grid gap-8 lg:grid-cols-[1.3fr_1fr] lg:items-center">
            <div>
              <h2 id="autor-cta-title" className="text-2xl font-extrabold tracking-tight sm:text-3xl">
                Publique seu trabalho na BrooStore
              </h2>
              <p className="mt-3 max-w-xl text-brand-100">
                Você escreve, cria ou desenvolve. A BrooStore cuida da vitrine, do pagamento seguro e da entrega para o seu cliente.
              </p>
              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <ButtonLink href="/autores" variant="accent" size="lg">
                  Quero vender na BrooStore
                </ButtonLink>
              </div>
            </div>
            <ul className="grid gap-3">
              {POINTS.map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-center gap-3 rounded-xl bg-white/10 px-4 py-3 text-sm ring-1 ring-inset ring-white/15">
                  <Icon aria-hidden="true" className="h-5 w-5 shrink-0 text-accent-400" />
                  {text}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Container>
    </section>
  );
}
