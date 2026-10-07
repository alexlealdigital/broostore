import type { ReactNode } from 'react';
import { Skeleton } from '@/components/ui/Skeleton';
import type { Product, RatingsMap } from '@/types';
import { ProductCard } from './ProductCard';

const GRID = 'grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-4';

export function ProductGrid({ products, ratings, children }: { products: Product[]; ratings: RatingsMap; children?: ReactNode }) {
  return (
    <div className={GRID}>
      {products.map((p) => (
        <ProductCard key={p.id} product={p} rating={ratings[String(p.id)]} />
      ))}
      {children}
    </div>
  );
}

export function ProductCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border border-surface-line bg-white shadow-card">
      <Skeleton className="aspect-[4/5] w-full rounded-none" />
      <div className="space-y-2.5 p-3 sm:p-4">
        <Skeleton className="h-3 w-1/3" />
        <Skeleton className="h-4 w-11/12" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="mt-3 h-6 w-1/3" />
      </div>
    </div>
  );
}

export function ProductGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className={GRID} role="status" aria-label="Carregando produtos">
      {Array.from({ length: count }, (_, i) => (
        <ProductCardSkeleton key={i} />
      ))}
    </div>
  );
}
