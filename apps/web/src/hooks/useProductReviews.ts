import { useCallback, useEffect, useState } from 'react';
import { distributionOf, fetchProductReviews, submitRating } from '@/lib/products';
import type { Distribution, LoadStatus } from '@/types';

const EMPTY: Distribution = { counts: [0, 0, 0, 0, 0], total: 0, average: 0 };

function ratedKey(productId: number) {
  return `broo_rated_${productId}`;
}

function readRated(productId: number): number | null {
  try {
    const v = Number(localStorage.getItem(ratedKey(productId)));
    return v >= 1 && v <= 5 ? v : null;
  } catch {
    return null;
  }
}

/** Avaliacoes de um produto + envio de nota (uma por navegador, via localStorage como conveniencia). */
export function useProductReviews(productId: number | null) {
  const [distribution, setDistribution] = useState<Distribution>(EMPTY);
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [myRating, setMyRating] = useState<number | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (productId === null) return;
    let cancelled = false;
    setStatus('loading');
    setMyRating(readRated(productId));
    fetchProductReviews(productId)
      .then((rows) => {
        if (cancelled) return;
        setDistribution(distributionOf(rows));
        setStatus('success');
      })
      .catch(() => {
        if (!cancelled) setStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, [productId, attempt]);

  const rate = useCallback(
    async (rating: number) => {
      if (productId === null || sending) return;
      setSending(true);
      setSendError(null);
      try {
        await submitRating(productId, rating);
        setMyRating(rating);
        try {
          localStorage.setItem(ratedKey(productId), String(rating));
        } catch {
          /* ignora */
        }
        setAttempt((n) => n + 1);
      } catch (err) {
        setSendError(err instanceof Error ? err.message : 'Não foi possível enviar sua avaliação.');
      } finally {
        setSending(false);
      }
    },
    [productId, sending],
  );

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { distribution, status, myRating, sending, sendError, rate, retry };
}
