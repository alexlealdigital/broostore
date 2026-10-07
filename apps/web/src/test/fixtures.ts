import { normalizeProduct } from '@/lib/products';
import type { Product, ProductRow } from '@/types';

export function makeProduct(row: Partial<ProductRow> & { id: number }): Product {
  const p = normalizeProduct({ title: 'Guia da Eleição', author: 'Ana Souza', price: 29.9, category: 'Política', tipo: 'ebook', ...row });
  if (!p) throw new Error('fixture invalida');
  return p;
}
