import { useCallback, useEffect, useState } from 'react';
import { fetchProduct } from '@/lib/products';
import type { Product } from '@/types';

export type ProductDetailState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'not-found' }
  | { status: 'success'; product: Product };

/** Carrega um produto (todas as colunas) do Supabase. */
export function useProductDetail(id: number | null) {
  const [state, setState] = useState<ProductDetailState>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (id === null || !Number.isFinite(id)) {
      setState({ status: 'not-found' });
      return;
    }
    let cancelled = false;
    setState({ status: 'loading' });
    fetchProduct(id)
      .then((res) => {
        if (cancelled) return;
        setState(res.found ? { status: 'success', product: res.product } : { status: 'not-found' });
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'error' });
      });
    return () => {
      cancelled = true;
    };
  }, [id, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { state, retry };
}
