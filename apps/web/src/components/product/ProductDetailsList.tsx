import { BookOpen, Boxes, Clock, Ruler, Weight, type LucideIcon } from 'lucide-react';
import type { Product } from '@/types';

interface Row {
  icon: LucideIcon;
  label: string;
  value: string;
}

/** Ficha tecnica: so mostra campos que realmente existem no banco. */
export function ProductDetailsList({ product }: { product: Product }) {
  const rows: Row[] = [];
  if (product.paginas) rows.push({ icon: BookOpen, label: 'Páginas', value: product.paginas });

  if (product.area === 'fisicos') {
    const peso = product.peso ?? (product.pesoKg ? `${String(product.pesoKg).replace('.', ',')} kg` : null);
    if (peso) rows.push({ icon: Weight, label: 'Peso', value: peso });

    const { alturaCm: a, larguraCm: l, comprimentoCm: c } = product;
    const dims = product.dimensoes ?? (a && l && c ? `${c} x ${l} x ${a} cm` : null);
    if (dims) rows.push({ icon: Ruler, label: 'Dimensões', value: dims });

    if (product.prazoProducao) rows.push({ icon: Clock, label: 'Prazo de produção', value: product.prazoProducao });
    if (product.estoque) rows.push({ icon: Boxes, label: 'Estoque', value: `${product.estoque} em estoque` });
  }

  if (rows.length === 0) return null;
  return (
    <dl className="grid gap-px overflow-hidden rounded-xl border border-surface-line bg-surface-line sm:grid-cols-2">
      {rows.map(({ icon: Icon, label, value }) => (
        <div key={label} className="flex items-center gap-3 bg-white px-4 py-3">
          <Icon aria-hidden="true" className="h-4 w-4 shrink-0 text-brand-600" />
          <dt className="text-sm text-ink-muted">{label}</dt>
          <dd className="ml-auto text-right text-sm font-semibold text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
