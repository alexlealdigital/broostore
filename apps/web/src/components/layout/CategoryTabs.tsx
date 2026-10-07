import { LayoutGrid } from 'lucide-react';
import { Link, useLocation, useSearchParams } from 'wouter';
import { Container } from '@/components/ui/Container';
import { AREAS, AREA_INFO, parseArea } from '@/lib/categorias';
import { cn } from '@/lib/cn';

const tab =
  'inline-flex h-11 shrink-0 items-center gap-1.5 border-b-2 px-2.5 text-sm sm:gap-2 sm:px-3 font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500';

/** Abas de categoria sob o cabecalho. Rolagem horizontal no celular. */
export function CategoryTabs() {
  const [location] = useLocation();
  const [params] = useSearchParams();
  const onShop = location === '/loja';
  const area = onShop ? parseArea(params.get('area')) : null;

  return (
    <nav aria-label="Categorias" className="border-b border-surface-line bg-white md:sticky md:top-[4.25rem] md:z-30">
      <Container>
        <ul className="-mx-1 flex overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <li>
            <Link
              href="/loja"
              aria-current={onShop && !area ? 'page' : undefined}
              className={cn(tab, onShop && !area ? 'border-brand-600 text-brand-700' : 'border-transparent text-ink-soft hover:text-brand-700')}
            >
              <LayoutGrid aria-hidden="true" className="h-4 w-4" />
              Todos
            </Link>
          </li>
          {AREAS.map((a) => {
            const info = AREA_INFO[a];
            const Icon = info.icon;
            const active = area === a;
            return (
              <li key={a}>
                <Link
                  href={`/loja?area=${a}`}
                  aria-current={active ? 'page' : undefined}
                  className={cn(tab, active ? 'border-brand-600 text-brand-700' : 'border-transparent text-ink-soft hover:text-brand-700')}
                >
                  <Icon aria-hidden="true" className="h-4 w-4" />
                  {info.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </Container>
    </nav>
  );
}
