import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, api } from '@/lib/api';
import { isCEP } from '@/lib/validators';
import { useSlowNotice } from './useSlowNotice';
import type { FreteOption } from '@/types';

export type FreteState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; options: FreteOption[] };

/**
 * Cotacao de frete (POST /api/cotar-frete). Chame `quote(cep)` quando o CEP estiver completo;
 * a primeira opcao (mais barata) vem pre-selecionada. Respostas antigas sao descartadas.
 */
export function useFrete(productId: number | null) {
  const [state, setState] = useState<FreteState>({ status: 'idle' });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { slow, onSlow, reset } = useSlowNotice();
  const controllerRef = useRef<AbortController | null>(null);

  const clear = useCallback(() => {
    controllerRef.current?.abort();
    setState({ status: 'idle' });
    setSelectedId(null);
    reset();
  }, [reset]);

  const quote = useCallback(
    async (cep: string) => {
      if (productId === null || !isCEP(cep)) return;
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      setState({ status: 'loading' });
      setSelectedId(null);
      try {
        const options = await api.cotarFrete(cep.replace(/\D/g, ''), productId, { onSlow, signal: controller.signal });
        if (controller.signal.aborted) return;
        setState({ status: 'ready', options });
        setSelectedId(options[0]?.id ?? null);
      } catch (err) {
        if (err instanceof ApiError && err.kind === 'aborted') return;
        setState({
          status: 'error',
          message: err instanceof ApiError ? err.message : 'Erro ao calcular o frete. Tente novamente.',
        });
      } finally {
        if (controllerRef.current === controller) reset();
      }
    },
    [productId, onSlow, reset],
  );

  useEffect(() => () => controllerRef.current?.abort(), []);

  const selected = state.status === 'ready' ? (state.options.find((o) => o.id === selectedId) ?? null) : null;
  return { state, slow, selected, selectedId, select: setSelectedId, quote, clear };
}
