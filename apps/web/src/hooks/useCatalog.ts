import { createContext, useContext } from 'react';
import type { LoadStatus, Product, RatingsMap } from '@/types';

export interface CatalogState {
  products: Product[];
  ratings: RatingsMap;
  status: LoadStatus;
  reload: () => void;
}

export const CatalogContext = createContext<CatalogState | null>(null);

/** Catalogo carregado uma vez (Supabase) e compartilhado entre as paginas. */
export function useCatalog(): CatalogState {
  const ctx = useContext(CatalogContext);
  if (!ctx) throw new Error('useCatalog deve ser usado dentro de <CatalogProvider>.');
  return ctx;
}
