import { render } from '@testing-library/react';
import { Route, Router } from 'wouter';
import { memoryLocation } from 'wouter/memory-location';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@/hooks/useCheckoutProduct', () => ({
  useCheckoutProduct: () => ({ state: { status: 'loading' }, slow: false, retry: () => undefined }),
}));

import Comprar from './Comprar';

describe('Comprar (compatibilidade com o BrooStock)', () => {
  it('/comprar?produto=ID&email=... redireciona para /comprar/ID preservando os demais parametros', () => {
    const { hook, history } = memoryLocation({ path: '/comprar?produto=12&email=a%40b.com&nome=Ana&return=https%3A%2F%2Fapp.test%2F', record: true });
    render(
      <Router hook={hook}>
        <Route path="/comprar/:id" component={Comprar} />
        <Route path="/comprar" component={Comprar} />
      </Router>,
    );
    const last = history?.[history.length - 1] ?? '';
    expect(last.startsWith('/comprar/12')).toBe(true);
    expect(last).toContain('email=a%40b.com');
    expect(last).toContain('nome=Ana');
    expect(last).toContain('return=');
    expect(last).not.toContain('produto=');
  });
});
