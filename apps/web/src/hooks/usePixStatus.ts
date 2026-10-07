import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { createPoller, type Poller } from '@/lib/poller';

export type PixWatchState = 'checking' | 'unsupported' | 'timeout' | 'paid';

const PAID_STATUSES = new Set(['approved', 'delivered', 'paid']);
const MAX_CONSECUTIVE_ERRORS = 5;

export function isPaidStatus(data: { status: string; pago: boolean }): boolean {
  return data.pago === true || PAID_STATUSES.has(data.status.toLowerCase());
}

/**
 * Acompanha o PIX consultando GET /api/cobrancas/<ref>/status a cada 4 s (ate ~15 min, pausando com a aba oculta).
 * Se o endpoint nao existir (404) ou falhar repetidamente, vira "unsupported" e a tela mostra apenas a mensagem estatica.
 */
export function usePixStatus(externalReference: string | null | undefined, onPaid: () => void) {
  const [state, setState] = useState<PixWatchState>(externalReference ? 'checking' : 'unsupported');
  const pollerRef = useRef<Poller | null>(null);
  const onPaidRef = useRef(onPaid);
  onPaidRef.current = onPaid;

  useEffect(() => {
    if (!externalReference) {
      setState('unsupported');
      return;
    }
    setState('checking');
    let errors = 0;
    let finished = false;

    const poller = createPoller({
      intervalMs: 4000,
      maxDurationMs: 15 * 60 * 1000,
      onTimeout: () => {
        if (!finished) setState('timeout');
      },
      tick: async () => {
        const res = await api.statusCobranca(externalReference).catch(() => null);
        if (finished || res === null) return false;
        if (!res.supported) {
          if (res.reason === 'not-found' || ++errors >= MAX_CONSECUTIVE_ERRORS) {
            finished = true;
            setState('unsupported');
            return true;
          }
          return false;
        }
        errors = 0;
        if (isPaidStatus(res.data)) {
          finished = true;
          setState('paid');
          onPaidRef.current();
          return true;
        }
        return false;
      },
    });
    pollerRef.current = poller;
    poller.start();
    // primeira consulta imediata (detecta rapido se o endpoint existe)
    void poller.pollNow();

    return () => {
      finished = true;
      poller.stop();
      pollerRef.current = null;
    };
  }, [externalReference]);

  /** Verifica agora e, se o tempo esgotou, volta a monitorar. */
  const checkNow = useCallback(async () => {
    const poller = pollerRef.current;
    if (!poller) return;
    if (!poller.running) {
      setState((s) => (s === 'timeout' ? 'checking' : s));
      poller.start();
    }
    await poller.pollNow();
  }, []);

  return { state, checkNow };
}
