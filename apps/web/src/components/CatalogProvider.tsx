import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { CatalogContext, type CatalogState } from '@/hooks/useCatalog';
import { fetchCatalog, fetchRatings } from '@/lib/products';
import type { LoadStatus, Product, RatingsMap } from '@/types';

export function CatalogProvider({ children }: { children: ReactNode }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [ratings, setRatings] = useState<RatingsMap>({});
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    // Avaliacoes sao complementares: se falharem, a loja segue sem estrelas.
    const ratingsPromise = fetchRatings().catch(() => ({}) as RatingsMap);
    fetchCatalog()
      .then(async (list) => {
        const r = await ratingsPromise;
        if (cancelled) return;
        setProducts(list);
        setRatings(r);
        setStatus('success');
      })
      .catch(() => {
        if (!cancelled) setStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  const value = useMemo<CatalogState>(() => ({ products, ratings, status, reload }), [products, ratings, status, reload]);

  return <CatalogContext.Provider value={value}>{children}</CatalogContext.Provider>;
}
