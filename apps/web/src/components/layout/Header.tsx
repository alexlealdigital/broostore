import { Menu, Store, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useLocation } from 'wouter';
import { Container } from '@/components/ui/Container';
import { cn } from '@/lib/cn';
import { Logo } from './Logo';
import { HeaderSearch } from './HeaderSearch';

const NAV = [
  { href: '/loja', label: 'Loja' },
  { href: '/autores', label: 'Para autores' },
  { href: '/sobre', label: 'Sobre' },
  { href: '/contato', label: 'Contato' },
];

/** Cabecalho fixo. Altura de 4.25rem no desktop (CategoryTabs usa o mesmo valor para ficar colado). */
export function Header() {
  const [location] = useLocation();
  const [open, setOpen] = useState(false);

  useEffect(() => setOpen(false), [location]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  return (
    <header className="sticky top-0 z-40 border-b border-surface-line bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/85">
      <Container>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2.5 py-2.5 md:h-[4.25rem] md:flex-nowrap md:py-0">
          <Logo className="mr-auto md:mr-0" />

          <HeaderSearch className="order-last w-full md:order-none md:mx-4 md:max-w-xl md:flex-1" />

          <nav aria-label="Principal" className="hidden items-center gap-1 md:flex">
            {NAV.filter((n) => n.href !== '/loja').map((n) => (
              <Link
                key={n.href}
                href={n.href}
                aria-current={location === n.href ? 'page' : undefined}
                className={cn(
                  'rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-surface-alt hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
                  location === n.href ? 'text-brand-700' : 'text-ink-soft',
                )}
              >
                {n.label}
              </Link>
            ))}
          </nav>

          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-ink-soft transition hover:bg-surface-alt focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 md:hidden"
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? 'Fechar menu' : 'Abrir menu'}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X aria-hidden="true" className="h-5 w-5" /> : <Menu aria-hidden="true" className="h-5 w-5" />}
          </button>
        </div>

        {open && (
          <nav id="mobile-menu" aria-label="Menu" className="animate-fade-in border-t border-surface-line py-2 md:hidden">
            <ul className="grid gap-1">
              {NAV.map((n) => (
                <li key={n.href}>
                  <Link
                    href={n.href}
                    className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium text-ink-soft hover:bg-surface-alt hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                  >
                    {n.href === '/loja' && <Store aria-hidden="true" className="h-4 w-4" />}
                    {n.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        )}
      </Container>
    </header>
  );
}
