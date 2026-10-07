import { descricaoClassificacao, normalizarClassificacao, rotuloClassificacao, tipoInfo, type Classificacao } from '@/lib/categorias';
import { cn } from '@/lib/cn';

/** Cores no padrao da classificacao indicativa brasileira. */
const classifColors: Record<Classificacao, string> = {
  L: 'bg-emerald-600 text-white',
  '10': 'bg-sky-600 text-white',
  '12': 'bg-yellow-400 text-ink',
  '14': 'bg-orange-500 text-white',
  '16': 'bg-red-600 text-white',
  '18': 'bg-gray-900 text-white',
};

export function ClassificacaoBadge({ value, className }: { value: string; className?: string }) {
  const c = normalizarClassificacao(value);
  return (
    <span
      title={descricaoClassificacao(c)}
      aria-label={descricaoClassificacao(c)}
      className={cn(
        'inline-flex h-7 min-w-7 items-center justify-center rounded-md px-1.5 text-xs font-extrabold shadow-sm ring-1 ring-white/70',
        classifColors[c],
        className,
      )}
    >
      {rotuloClassificacao(c)}
    </span>
  );
}

const tipoColors: Record<string, string> = {
  digitais: 'bg-brand-50 text-brand-700 ring-brand-200',
  fisicos: 'bg-amber-50 text-amber-800 ring-amber-200',
  aplicativos: 'bg-violet-50 text-violet-700 ring-violet-200',
};

export function TipoBadge({ tipo, className }: { tipo: string; className?: string }) {
  const info = tipoInfo(tipo);
  const Icon = info.icon;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold leading-5 ring-1 ring-inset',
        tipoColors[info.area],
        className,
      )}
    >
      <Icon aria-hidden="true" className="h-3 w-3" />
      {info.label}
    </span>
  );
}
