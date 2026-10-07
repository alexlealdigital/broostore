import { useMemo } from 'react';
import { AuthorCta } from '@/components/home/AuthorCta';
import { Hero } from '@/components/home/Hero';
import { HowItWorks } from '@/components/home/HowItWorks';
import { AreaCards } from '@/components/product/AreaCards';
import { ProductGrid, ProductGridSkeleton } from '@/components/product/ProductGrid';
import { TrustStrip } from '@/components/product/TrustStrip';
import { ButtonLink } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { SectionHeading } from '@/components/ui/SectionHeading';
import { EmptyState, ErrorState } from '@/components/ui/StateViews';
import { useAdultContent } from '@/hooks/useAdultContent';
import { useCatalog } from '@/hooks/useCatalog';
import { usePageMeta } from '@/hooks/usePageMeta';
import { countByArea } from '@/lib/catalog';
import { discountPercent } from '@/lib/format';

export default function Home() {
  usePageMeta();
  const { products, ratings, status, reload } = useCatalog();
  const { allowed } = useAdultContent();

  const visible = useMemo(() => (allowed ? products : products.filter((p) => p.classificacao !== '18')), [products, allowed]);
  const counts = useMemo(() => countByArea(products, allowed), [products, allowed]);
  const offers = useMemo(
    () => visible.filter((p) => discountPercent(p.price, p.originalPrice) > 0).slice(0, 4),
    [visible],
  );
  const latest = useMemo(() => visible.slice(0, 8), [visible]);
  const featured = useMemo(() => visible.filter((p) => p.imageUrl).slice(0, 3), [visible]);

  return (
    <>
      <Hero featured={featured} />
      <TrustStrip />

      <section aria-labelledby="categorias" className="mt-12">
        <Container>
          <SectionHeading id="categorias" title="Explore por categoria" subtitle="Escolha o que você procura." />
          <AreaCards counts={status === 'success' ? counts : undefined} />
        </Container>
      </section>

      {status === 'loading' && (
        <section className="mt-14" aria-label="Produtos">
          <Container>
            <SectionHeading title="Novidades" />
            <ProductGridSkeleton count={4} />
          </Container>
        </section>
      )}

      {status === 'error' && (
        <section className="mt-14">
          <Container>
            <ErrorState title="Não conseguimos carregar os produtos" onRetry={reload}>
              Pode ser uma instabilidade momentânea. Tente novamente em instantes.
            </ErrorState>
          </Container>
        </section>
      )}

      {status === 'success' && visible.length === 0 && (
        <section className="mt-14">
          <Container>
            <EmptyState title="Novos produtos em breve">
              Estamos preparando a vitrine. Volte logo ou conheça como publicar o seu trabalho.
            </EmptyState>
          </Container>
        </section>
      )}

      {status === 'success' && offers.length > 0 && (
        <section aria-labelledby="ofertas" className="mt-14">
          <Container>
            <SectionHeading id="ofertas" title="Ofertas da semana" subtitle="Preços reduzidos por tempo limitado." href="/loja" linkLabel="Ver loja" />
            <ProductGrid products={offers} ratings={ratings} />
          </Container>
        </section>
      )}

      {status === 'success' && latest.length > 0 && (
        <section aria-labelledby="novidades" className="mt-14">
          <Container>
            <SectionHeading id="novidades" title="Novidades" subtitle="Os lançamentos mais recentes da loja." href="/loja?ordem=mais-novos" />
            <ProductGrid products={latest} ratings={ratings} />
            <div className="mt-8 text-center">
              <ButtonLink href="/loja" variant="secondary" size="lg">
                Ver todos os produtos
              </ButtonLink>
            </div>
          </Container>
        </section>
      )}

      <HowItWorks />
      <AuthorCta />
    </>
  );
}
