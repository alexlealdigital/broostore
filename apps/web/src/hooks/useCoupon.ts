import { useCallback, useRef, useState } from 'react';
import { ApiError, api } from '@/lib/api';
import { formatBRL } from '@/lib/format';
import { useSlowNotice } from './useSlowNotice';
import type { CupomCalculo, CupomInfo } from '@/types';

export type CouponState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'applied'; cupom: CupomInfo; calculo: CupomCalculo };

export function couponDescription(cupom: CupomInfo, calculo: CupomCalculo): string {
  if (cupom.descricao) return cupom.descricao;
  if (cupom.tipo === 'percentual' && typeof cupom.valor === 'number') return `${Math.round(cupom.valor)}% de desconto`;
  return `${formatBRL(calculo.desconto)} de desconto`;
}

/** Cupom validado pelo servidor (POST /api/validar-cupom). O desconto exibido e o calculado pelo servidor. */
export function useCoupon(productId: number | null, price: number) {
  const [state, setState] = useState<CouponState>({ status: 'idle' });
  const { slow, onSlow, reset } = useSlowNotice();
  const controllerRef = useRef<AbortController | null>(null);

  const apply = useCallback(
    async (rawCode: string) => {
      const codigo = rawCode.trim().toUpperCase();
      if (!codigo) {
        setState({ status: 'error', message: 'Digite um cupom.' });
        return;
      }
      if (productId === null) {
        setState({ status: 'error', message: 'Produto não identificado.' });
        return;
      }
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      setState({ status: 'loading' });
      try {
        const res = await api.validarCupom(
          { codigo, produto_id: productId, valor_original: price },
          { onSlow, signal: controller.signal },
        );
        if (res.status !== 'success' || !res.cupom || !res.calculo) {
          setState({ status: 'error', message: 'Cupom inválido.' });
          return;
        }
        setState({ status: 'applied', cupom: res.cupom, calculo: res.calculo });
      } catch (err) {
        if (err instanceof ApiError && err.kind === 'aborted') return;
        setState({
          status: 'error',
          message: err instanceof ApiError && err.kind === 'http' ? err.message : 'Erro ao validar o cupom. Tente novamente.',
        });
      } finally {
        reset();
      }
    },
    [productId, price, onSlow, reset],
  );

  const remove = useCallback(() => {
    controllerRef.current?.abort();
    setState({ status: 'idle' });
  }, []);

  return { state, slow, apply, remove };
}
