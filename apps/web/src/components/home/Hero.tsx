import { BadgeCheck, ShieldCheck } from 'lucide-react';
import { ButtonLink } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { ProductImage } from '@/components/product/ProductImage';
import { AREAS, AREA_INFO } from '@/lib/categorias';
import { formatBRL } from '@/lib/format';
import { cn } from '@/lib/cn';
import type { Product } from '@/types';

const POINTS = ['PIX e cartão de crédito parcelado', 'Entrega digital imediata por e-mail', 'Frete calculado pelo CEP'];

function ShowcaseCard({ product, className }: { product: Product; className?: string }) {
  return (
    <div className={cn('w-44 overflow-hidden rounded-2xl bg-white p-2 shadow-pop ring-1 ring-black/5', className)}>
      <ProductImage src={product.imageUrl} alt={`Capa de ${product.title}`} tipo={product.tipo} className="aspect-[4/5] w-full rounded-xl" />
      <div className="px-1.5 pb-1 pt-2.5">
        <p className="line-clamp-1 text-xs font-semibold text-ink">{product.title}</p>
        <p className="text-sm font-extrabold text-brand-700">{formatBRL(product.price)}</p>
      </div>
    </div>
  );
}

function PlaceholderCard({ area, className }: { area: (typeof AREAS)[number]; className?: string }) {
  const info = AREA_INFO[area];
  const Icon = info.icon;
  return (
    <div
      aria-hidden="true"
      className={cn('flex w-44 flex-col items-center justify-center gap-3 rounded-2xl bg-white/95 p-6 shadow-pop ring-1 ring-black/5', className)}
    >
      <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
        <Icon className="h-8 w-8" />
      </span>
      <span className="text-sm font-bold text-ink">{info.label}</span>
    </div>
  );
}

export function Hero({ featured }: { featured: Product[] }) {
  const cards = featured.slice(0, 3);
  return (
    <section className="relative isolate overflow-hidden bg-gradient-to-br from-brand-800 via-brand-700 to-brand-500 text-white">
      <div aria-hidden="true" className="absolute -right-24 -top-24 -z-10 h-96 w-96 rounded-full bg-brand-400/30 blur-3xl" />
      <div aria-hidden="true" className="absolute -bottom-32 left-1/3 -z-10 h-80 w-80 rounded-full bg-accent-500/20 blur-3xl" />
      <Container className="grid items-center gap-10 py-12 sm:py-16 lg:grid-cols-[1.15fr_1fr] lg:py-20">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold ring-1 ring-inset ring-white/20">
            <ShieldCheck aria-hidden="true" className="h-3.5 w-3.5" />
            Pagamento seguro com Mercado Pago
          </p>
          <h1 className="mt-5 text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl lg:text-5xl">
            Ebooks, livros e aplicativos de autores brasileiros
          </h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-brand-100 sm:text-lg">
            Encontre sua próxima leitura, jogo ou ferramenta. Pague com PIX ou cartão e receba em segundos por e-mail, ou em casa, nos
            produtos físicos.
          </p>
          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <ButtonLink href="/loja" variant="accent" size="lg">
              Explorar a loja
            </ButtonLink>
            <ButtonLink
              href="/autores"
              size="lg"
              variant="ghost"
              className="border border-white/40 text-white hover:bg-white/10 hover:text-white focus-visible:ring-white focus-visible:ring-offset-brand-700"
            >
              Publicar meu trabalho
            </ButtonLink>
          </div>
          <ul className="mt-8 grid gap-2 text-sm text-brand-50">
            {POINTS.map((p) => (
              <li key={p} className="flex items-center gap-2">
                <BadgeCheck aria-hidden="true" className="h-4 w-4 shrink-0 text-accent-400" />
                {p}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative mx-auto hidden h-[22rem] w-full max-w-md lg:block" aria-hidden={cards.length === 0 ? true : undefined}>
          {(cards.length > 0 ? cards : []).map((p, i) => (
            <ShowcaseCard
              key={p.id}
              product={p}
              className={cn(
                'absolute',
                i === 0 && 'left-0 top-10 -rotate-6',
                i === 1 && 'left-1/2 top-0 z-10 -translate-x-1/2 rotate-2 scale-105',
                i === 2 && 'right-0 top-16 rotate-6',
              )}
            />
          ))}
          {cards.length === 0 &&
            AREAS.map((a, i) => (
              <PlaceholderCard
                key={a}
                area={a}
                className={cn(
                  'absolute',
                  i === 0 && 'left-0 top-10 -rotate-6',
                  i === 1 && 'left-1/2 top-0 z-10 -translate-x-1/2 rotate-2 scale-105',
                  i === 2 && 'right-0 top-16 rotate-6',
                )}
              />
            ))}
        </div>
      </Container>
    </section>
  );
}
