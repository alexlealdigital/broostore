import { Search } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';
import { useLocation, useSearchParams } from 'wouter';
import { cn } from '@/lib/cn';

/** Busca do cabecalho: envia para /loja?q=... (mantem a aba/area atual quando ja esta na loja). */
export function HeaderSearch({ className }: { className?: string }) {
  const [location, navigate] = useLocation();
  const [params] = useSearchParams();
  const onShop = location === '/loja';
  const urlQuery = onShop ? (params.get('q') ?? '') : '';
  const [value, setValue] = useState(urlQuery);

  // Mantem o campo em sincronia com a URL (ex.: botao voltar, limpar filtros).
  useEffect(() => setValue(urlQuery), [urlQuery]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const next = new URLSearchParams();
    const q = value.trim();
    if (q) next.set('q', q);
    if (onShop) {
      const area = params.get('area');
      if (area) next.set('area', area);
    }
    const qs = next.toString();
    navigate(`/loja${qs ? `?${qs}` : ''}`);
  };

  return (
    <form role="search" onSubmit={submit} className={cn('relative', className)}>
      <label htmlFor="header-search" className="sr-only">
        Buscar produtos
      </label>
      <Search aria-hidden="true" className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
      <input
        id="header-search"
        type="search"
        enterKeyHint="search"
        autoComplete="off"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Buscar ebooks, apps, livros..."
        className="h-11 w-full rounded-xl border border-surface-line bg-surface-alt pl-10 pr-24 text-sm text-ink placeholder:text-ink-muted transition focus:border-brand-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/30 [&::-webkit-search-cancel-button]:hidden"
      />
      <button
        type="submit"
        className="absolute right-1.5 top-1/2 h-8 -translate-y-1/2 rounded-lg bg-brand-600 px-3.5 text-xs font-semibold text-white transition hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1"
      >
        Buscar
      </button>
    </form>
  );
}
