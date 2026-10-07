import { ChevronRight, CreditCard, Lock, ShoppingCart } from 'lucide-react';
import { Link, useParams } from 'wouter';
import { AgeGate } from '@/components/product/AgeGate';
import { ClassificacaoBadge, TipoBadge } from '@/components/product/Badges';
import { PriceBlock } from '@/components/product/PriceBlock';
import { ProductDetailsList } from '@/components/product/ProductDetailsList';
import { ProductImage } from '@/components/product/ProductImage';
import { RelatedProducts } from '@/components/product/RelatedProducts';
import { ReviewsSection } from '@/components/product/ReviewsSection';
import { TypeInfo } from '@/components/product/TypeInfo';
import { ButtonLink } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { Skeleton } from '@/components/ui/Skeleton';
import { RatingSummaryInline } from '@/components/ui/Stars';
import { EmptyState, ErrorState } from '@/components/ui/StateViews';
import { useAdultContent } from '@/hooks/useAdultContent';
import { useCatalog } from '@/hooks/useCatalog';
import { usePageMeta } from '@/hooks/usePageMeta';
import { useProductDetail } from '@/hooks/useProductDetail';
import { AREA_INFO } from '@/lib/categorias';
import { formatBRL } from '@/lib/format';
import type { Product } from '@/types';

function ProductSkeleton() {
  return (
    <Container className="py-8" >
      <div role="status" aria-label="Carregando produto" className="grid gap-8 lg:grid-cols-[minmax(0,420px)_1fr] lg:gap-12">
        <Skeleton className="aspect-[4/5] w-full rounded-2xl" />
        <div className="space-y-4">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-9 w-3/4" />
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-10 w-1/3" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    </Container>
  );
}

function ProductView({ product }: { product: Product }) {
  const { ratings } = useCatalog();
  const rating = ratings[String(product.id)];
  const area = AREA_INFO[product.area];
  usePageMeta(product.title, product.descricao ? product.descricao.slice(0, 155) : undefined);
  const buyHref = `/comprar/${product.id}`;

  return (
    <Container className="pb-28 pt-6 lg:pb-12">
      <nav aria-label="Você está em" className="mb-5">
        <ol className="flex flex-wrap items-center gap-1 text-xs text-ink-muted sm:text-sm">
          <li>
            <Link href="/" className="rounded hover:text-brand-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
              Início
            </Link>
          </li>
          <ChevronRight aria-hidden="true" className="h-3.5 w-3.5" />
          <li>
            <Link
              href={`/loja?area=${product.area}`}
              className="rounded hover:text-brand-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              {area.label}
            </Link>
          </li>
          <ChevronRight aria-hidden="true" className="h-3.5 w-3.5" />
          <li aria-current="page" className="max-w-[16rem] truncate font-medium text-ink-soft">
            {product.title}
          </li>
        </ol>
      </nav>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,420px)_1fr] lg:gap-12">
        <div className="lg:sticky lg:top-40 lg:self-start">
          <div className="relative mx-auto max-w-[15rem] overflow-hidden sm:max-w-sm rounded-2xl border border-surface-line bg-white shadow-card lg:max-w-none">
            <ProductImage
              src={product.imageUrl}
              alt={`Capa de ${product.title}`}
              tipo={product.tipo}
              loading="eager"
              className="aspect-[4/5] w-full"
            />
            <div className="absolute left-3 top-3">
              <ClassificacaoBadge value={product.classificacao} />
            </div>
          </div>
        </div>

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <TipoBadge tipo={product.tipo} />
            <span className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{product.category}</span>
          </div>

          <h1 className="mt-3 text-2xl font-extrabold leading-tight tracking-tight text-ink sm:text-3xl">{product.title}</h1>
          <p className="mt-1.5 text-sm text-ink-muted">{product.author ? `Por ${product.author}` : 'Autor não informado'}</p>

          <a href="#avaliacoes" className="mt-3 inline-block rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
            <RatingSummaryInline average={rating?.average ?? 0} count={rating?.count ?? 0} size={18} />
          </a>

          <div className="mt-6 rounded-2xl border border-surface-line bg-white p-5 shadow-card">
            <PriceBlock price={product.price} originalPrice={product.originalPrice} size="lg" />
            <p className="mt-1.5 flex items-center gap-1.5 text-xs text-ink-muted">
              <CreditCard aria-hidden="true" className="h-3.5 w-3.5" />
              PIX ou cartão de crédito{product.area === 'fisicos' ? ' · frete calculado no checkout' : ''}
            </p>
            <ButtonLink href={buyHref} variant="accent" size="lg" className="mt-4 w-full">
              <ShoppingCart aria-hidden="true" className="h-5 w-5" />
              Comprar agora
            </ButtonLink>
            <p className="mt-3 flex items-center justify-center gap-1.5 text-xs text-ink-muted">
              <Lock aria-hidden="true" className="h-3.5 w-3.5 text-emerald-600" />
              Compra segura com Mercado Pago
            </p>
          </div>

          <div className="mt-5">
            <TypeInfo tipo={product.tipo} />
          </div>

          {product.descricao && (
            <section aria-labelledby="descricao" className="mt-8">
              <h2 id="descricao" className="text-xl font-bold text-ink">
                Sobre este produto
              </h2>
              <p className="mt-3 whitespace-pre-line text-[15px] leading-7 text-ink-soft">{product.descricao}</p>
            </section>
          )}

          {product.intro && (
            <section aria-labelledby="intro" className="mt-6">
              <h2 id="intro" className="text-lg font-bold text-ink">
                Introdução
              </h2>
              <p className="mt-2 whitespace-pre-line text-[15px] leading-7 text-ink-soft">{product.intro}</p>
            </section>
          )}

          <div className="mt-6 empty:hidden">
            <ProductDetailsList product={product} />
          </div>

          {product.specs && (
            <section aria-labelledby="specs" className="mt-6">
              <h2 id="specs" className="text-lg font-bold text-ink">
                Especificações
              </h2>
              <p className="mt-2 whitespace-pre-line text-[15px] leading-7 text-ink-soft">{product.specs}</p>
            </section>
          )}

          {product.sobreAutor && (
            <section aria-labelledby="sobre-autor" className="mt-6">
              <h2 id="sobre-autor" className="text-lg font-bold text-ink">
                Sobre o autor
              </h2>
              <p className="mt-2 whitespace-pre-line text-[15px] leading-7 text-ink-soft">{product.sobreAutor}</p>
            </section>
          )}
        </div>
      </div>

      <div className="mt-14">
        <ReviewsSection productId={product.id} />
      </div>

      <RelatedProducts product={product} />

      {/* Barra de compra fixa no celular */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-surface-line bg-white/95 px-4 py-3 shadow-pop backdrop-blur lg:hidden">
        <div className="mx-auto flex max-w-xl items-center gap-3">
          <div className="min-w-0">
            <p className="truncate text-xs text-ink-muted">{product.title}</p>
            <p className="text-lg font-extrabold leading-tight text-ink">{product.price <= 0 ? 'Grátis' : formatBRL(product.price)}</p>
          </div>
          <ButtonLink href={buyHref} variant="accent" size="md" className="ml-auto shrink-0">
            Comprar agora
          </ButtonLink>
        </div>
      </div>
    </Container>
  );
}

export default function Produto() {
  const params = useParams<{ id: string }>();
  const id = /^\d+$/.test(params.id ?? '') ? Number(params.id) : null;
  const { state, retry } = useProductDetail(id);
  const { allowed, allow } = useAdultContent();

  if (state.status === 'loading') return <ProductSkeleton />;

  if (state.status === 'error') {
    return (
      <Container className="py-16">
        <ErrorState title="Não conseguimos carregar este produto" onRetry={retry} />
      </Container>
    );
  }

  if (state.status === 'not-found') {
    return (
      <Container className="py-16">
        <EmptyState
          title="Produto não encontrado"
          action={
            <ButtonLink href="/loja" variant="primary">
              Ver todos os produtos
            </ButtonLink>
          }
        >
          O produto pode ter sido removido ou o endereço está incorreto.
        </EmptyState>
      </Container>
    );
  }

  if (state.product.classificacao === '18' && !allowed) {
    return (
      <Container className="py-16">
        <AgeGate onConfirm={allow} />
      </Container>
    );
  }

  return <ProductView product={state.product} />;
}
