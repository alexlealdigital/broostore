import { SearchX, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'wouter';
import { AdultToggle } from '@/components/product/AdultToggle';
import { ProductGrid, ProductGridSkeleton } from '@/components/product/ProductGrid';
import { Button } from '@/components/ui/Button';
import { Container } from '@/components/ui/Container';
import { SelectField } from '@/components/ui/Field';
import { EmptyState, ErrorState } from '@/components/ui/StateViews';
import { useAdultContent } from '@/hooks/useAdultContent';
import { useCatalog } from '@/hooks/useCatalog';
import { usePageMeta } from '@/hooks/usePageMeta';
import { SORT_OPTIONS, categoriesOf, filterProducts, parseSort, sortProducts } from '@/lib/catalog';
import { AREA_INFO, parseArea } from '@/lib/categorias';
import { pluralize } from '@/lib/format';

const PAGE_SIZE = 24;

export default function Loja() {
  const { products, ratings, status, reload } = useCatalog();
  const { allowed } = useAdultContent();
  const [params, setParams] = useSearchParams();
  const [limit, setLimit] = useState(PAGE_SIZE);

  const area = parseArea(params.get('area'));
  const query = (params.get('q') ?? '').trim();
  const sort = parseSort(params.get('ordem'));
  const requestedCategory = params.get('categoria');
  const areaInfo = area ? AREA_INFO[area] : null;

  usePageMeta(areaInfo ? areaInfo.label : 'Loja', areaInfo ? areaInfo.descricao : undefined);

  // Categorias disponiveis dentro da area atual (e do filtro 18+)
  const inArea = useMemo(() => filterProducts(products, { area, query: '', category: null, includeAdult: allowed }), [products, area, allowed]);
  const categories = useMemo(() => categoriesOf(inArea), [inArea]);
  const category = requestedCategory && categories.some((c) => c.name === requestedCategory) ? requestedCategory : null;

  const results = useMemo(() => {
    const filtered = filterProducts(products, { area, query, category, includeAdult: allowed });
    return sortProducts(filtered, sort, query, ratings);
  }, [products, area, query, category, allowed, sort, ratings]);

  const hasAdult = useMemo(() => products.some((p) => p.classificacao === '18'), [products]);

  // Voltar a primeira pagina quando os filtros mudam
  useEffect(() => setLimit(PAGE_SIZE), [area, query, category, sort, allowed]);

  const update = (patch: Record<string, string | null>) => {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(patch)) {
          if (v) next.set(k, v);
          else next.delete(k);
        }
        return next;
      },
      { replace: true },
    );
  };

  const hasFilters = Boolean(query || category);
  const clearFilters = () => update({ q: null, categoria: null });
  const shown = results.slice(0, limit);

  return (
    <Container className="py-8 sm:py-10">
      <div className="mb-6">
        <h1 className="text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">{areaInfo ? areaInfo.label : 'Todos os produtos'}</h1>
        <p className="mt-1.5 max-w-2xl text-sm text-ink-muted sm:text-base">
          {areaInfo ? areaInfo.descricao : 'Ebooks, produtos físicos, games, apps e assinaturas em um só lugar.'}
        </p>
      </div>

      {status === 'error' ? (
        <ErrorState title="Não conseguimos carregar os produtos" onRetry={reload}>
          Pode ser uma instabilidade momentânea. Tente novamente em instantes.
        </ErrorState>
      ) : (
        <>
          <div className="mb-5 rounded-2xl border border-surface-line bg-white p-3 shadow-card sm:p-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
              <SelectField
                label="Categoria"
                value={category ?? ''}
                onChange={(e) => update({ categoria: e.target.value || null })}
                disabled={status !== 'success'}
              >
                <option value="">Todas as categorias</option>
                {categories.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name} ({c.count})
                  </option>
                ))}
              </SelectField>
              <SelectField label="Ordenar por" value={sort} onChange={(e) => update({ ordem: e.target.value === 'relevancia' ? null : e.target.value })}>
                {SORT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </SelectField>
              {hasAdult && <AdultToggle />}
            </div>
          </div>

          <div className="mb-4 flex flex-wrap items-center gap-2" aria-live="polite">
            <p className="text-sm font-medium text-ink-soft">
              {status === 'loading' ? 'Carregando produtos...' : `${results.length} ${pluralize(results.length, 'produto encontrado', 'produtos encontrados')}`}
            </p>
            {query && (
              <button
                type="button"
                onClick={() => update({ q: null })}
                className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 ring-1 ring-inset ring-brand-200 hover:bg-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                Busca: {query}
                <X aria-hidden="true" className="h-3.5 w-3.5" />
                <span className="sr-only">Remover busca</span>
              </button>
            )}
            {category && (
              <button
                type="button"
                onClick={() => update({ categoria: null })}
                className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 ring-1 ring-inset ring-brand-200 hover:bg-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                {category}
                <X aria-hidden="true" className="h-3.5 w-3.5" />
                <span className="sr-only">Remover categoria</span>
              </button>
            )}
          </div>

          {status === 'loading' && <ProductGridSkeleton count={8} />}

          {status === 'success' && results.length === 0 && (
            <div className="py-6">
              <EmptyState
                title={hasFilters ? 'Nenhum produto encontrado' : 'Ainda não há produtos aqui'}
                action={
                  hasFilters ? (
                    <Button variant="secondary" onClick={clearFilters}>
                      <SearchX aria-hidden="true" className="h-4 w-4" /> Limpar filtros
                    </Button>
                  ) : undefined
                }
              >
                {hasFilters
                  ? 'Tente outros termos, remova os filtros ou explore outra categoria.'
                  : 'Novos produtos chegam em breve. Que tal explorar as outras categorias?'}
              </EmptyState>
            </div>
          )}

          {status === 'success' && results.length > 0 && (
            <>
              <ProductGrid products={shown} ratings={ratings} />
              {results.length > shown.length && (
                <div className="mt-8 text-center">
                  <Button variant="secondary" size="lg" onClick={() => setLimit((n) => n + PAGE_SIZE)}>
                    Mostrar mais ({results.length - shown.length})
                  </Button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </Container>
  );
}
