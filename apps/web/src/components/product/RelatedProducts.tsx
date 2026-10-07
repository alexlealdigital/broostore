import { useMemo } from 'react';
import { SectionHeading } from '@/components/ui/SectionHeading';
import { useAdultContent } from '@/hooks/useAdultContent';
import { useCatalog } from '@/hooks/useCatalog';
import { relatedProducts } from '@/lib/catalog';
import { AREA_INFO } from '@/lib/categorias';
import type { Product } from '@/types';
import { ProductGrid } from './ProductGrid';

export function RelatedProducts({ product }: { product: Product }) {
  const { products, ratings, status } = useCatalog();
  const { allowed } = useAdultContent();
  const related = useMemo(() => relatedProducts(products, product, allowed, 4), [products, product, allowed]);

  if (status !== 'success' || related.length === 0) return null;
  return (
    <section aria-labelledby="relacionados" className="mt-14">
      <SectionHeading
        id="relacionados"
        title={`Mais em ${AREA_INFO[product.area].label}`}
        subtitle="Outros produtos que podem te interessar."
        href={`/loja?area=${product.area}`}
      />
      <ProductGrid products={related} ratings={ratings} />
    </section>
  );
}
