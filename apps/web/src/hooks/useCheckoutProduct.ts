import { useCallback, useEffect, useState } from 'react';
import { ApiError, api } from '@/lib/api';
import { areaDoTipo, normalizarTipo } from '@/lib/categorias';
import { fetchProduct } from '@/lib/products';
import { useSlowNotice } from './useSlowNotice';
import type { Area } from '@/types';

export interface CheckoutProduct {
  id: number;
  title: string;
  price: number;
  tipo: string;
  area: Area;
  imageUrl: string | null;
  author: string;
  category: string;
  source: 'supabase' | 'api';
}

export type CheckoutProductState =
  | { status: 'loading' }
  | { status: 'invalid' }
  | { status: 'unavailable' }
  | { status: 'not-found' }
  | { status: 'error'; message: string }
  | { status: 'success'; product: CheckoutProduct };

/**
 * Produto do checkout. Fonte principal: Supabase (rapido, mesmo dado da vitrine).
 * Fallback: GET /api/produto/<id> para itens que nao estao no Supabase (ex.: planos do BrooStock).
 * O preco exibido e so informativo: a cobranca usa o preco que o servidor le do Supabase/banco.
 */
export function useCheckoutProduct(id: number | null) {
  const [state, setState] = useState<CheckoutProductState>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const { slow, onSlow, reset } = useSlowNotice();

  useEffect(() => {
    if (id === null || !Number.isFinite(id) || id <= 0) {
      setState({ status: 'invalid' });
      return;
    }
    const controller = new AbortController();
    let active = true;
    setState({ status: 'loading' });
    reset();

    (async () => {
      let missing = false;
      try {
        const res = await fetchProduct(id);
        if (!active) return;
        if (res.found) {
          const p = res.product;
          setState({
            status: 'success',
            product: {
              id: p.id,
              title: p.title,
              price: p.price,
              tipo: p.tipo,
              area: p.area,
              imageUrl: p.imageUrl,
              author: p.author,
              category: p.category,
              source: 'supabase',
            },
          });
          return;
        }
        if (res.reason === 'hidden') {
          setState({ status: 'unavailable' });
          return;
        }
        missing = true;
      } catch {
        // Supabase indisponivel: tenta a API antes de desistir.
      }

      try {
        const p = await api.getProduto(id, { onSlow, signal: controller.signal });
        if (!active) return;
        const tipo = normalizarTipo(p.tipo) || 'ebook';
        setState({
          status: 'success',
          product: {
            id: p.id ?? id,
            title: p.nome,
            price: Number(p.preco) || 0,
            tipo,
            area: areaDoTipo(tipo),
            imageUrl: null,
            author: '',
            category: '',
            source: 'api',
          },
        });
      } catch (err) {
        if (!active) return;
        if (err instanceof ApiError && err.kind === 'aborted') return;
        if (err instanceof ApiError && err.status === 404 && missing) {
          setState({ status: 'not-found' });
          return;
        }
        setState({ status: 'error', message: err instanceof ApiError ? err.message : 'Não foi possível carregar o produto.' });
      } finally {
        if (active) reset();
      }
    })();

    return () => {
      active = false;
      controller.abort();
    };
  }, [id, attempt, onSlow, reset]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { state, slow, retry };
}
