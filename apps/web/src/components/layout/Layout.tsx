import { useEffect, useRef, type ReactNode } from 'react';
import { useLocation } from 'wouter';
import { CategoryTabs } from './CategoryTabs';
import { CheckoutHeader } from './CheckoutHeader';
import { Footer } from './Footer';
import { Header } from './Header';

/** Casca da aplicacao: skip-link, cabecalho, conteudo e rodape. Checkout usa cabecalho enxuto. */
export function Layout({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  const mainRef = useRef<HTMLElement>(null);
  const isCheckout = location === '/comprar' || location.startsWith('/comprar/');

  // Nova rota => volta ao topo (mudancas apenas de query string nao rolam a pagina).
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0 });
  }, [location]);

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#conteudo"
        onClick={(e) => {
          e.preventDefault();
          mainRef.current?.focus();
          mainRef.current?.scrollIntoView();
        }}
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-brand-700 focus:shadow-pop"
      >
        Ir para o conteúdo
      </a>
      {isCheckout ? (
        <CheckoutHeader />
      ) : (
        <>
          <Header />
          <CategoryTabs />
        </>
      )}
      <main id="conteudo" ref={mainRef} tabIndex={-1} className="flex-1 outline-none">
        {children}
      </main>
      {!isCheckout && <Footer />}
      {isCheckout && (
        <footer className="border-t border-surface-line bg-white py-6 text-center text-xs text-ink-muted">
          Pagamentos processados pelo Mercado Pago. Seus dados de cartão nunca passam pelos nossos servidores.
        </footer>
      )}
    </div>
  );
}
