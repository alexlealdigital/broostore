/**
 * FONTE UNICA DA VERDADE da taxonomia de produtos.
 *
 *   products.tipo            -> area da loja
 *   ebook (e QUALQUER outro) -> digitais
 *   fisico                   -> fisicos
 *   game | app | assinatura  -> aplicativos
 *
 * O valor e sempre normalizado com trim().toLowerCase() antes de comparar.
 * Mantenha este arquivo em sincronia com docs/ARQUITETURA.md.
 */
import {
  AppWindow,
  BookOpen,
  Gamepad2,
  KeyRound,
  Package,
  Repeat,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import type { Area } from '@/types';

export const AREAS: readonly Area[] = ['digitais', 'fisicos', 'aplicativos'] as const;

/** Tipos que pertencem a cada area (alem do default digital para valores desconhecidos). */
export const TIPOS_FISICOS: readonly string[] = ['fisico'];
export const TIPOS_APLICATIVOS: readonly string[] = ['game', 'app', 'assinatura'];

export interface AreaInfo {
  slug: Area;
  /** Rotulo plural, usado em abas e titulos. */
  label: string;
  /** Texto curto para o card de entrada da home. */
  descricao: string;
  /** Como o cliente recebe o produto. */
  entrega: string;
  icon: LucideIcon;
}

export const AREA_INFO: Record<Area, AreaInfo> = {
  digitais: {
    slug: 'digitais',
    label: 'Digitais',
    descricao: 'Ebooks e PDFs para ler agora, com envio imediato por e-mail.',
    entrega: 'Entrega imediata por e-mail',
    icon: BookOpen,
  },
  fisicos: {
    slug: 'fisicos',
    label: 'Físicos',
    descricao: 'Livros e produtos que chegam na sua casa, com frete calculado pelo CEP.',
    entrega: 'Frete calculado pelo CEP',
    icon: Package,
  },
  aplicativos: {
    slug: 'aplicativos',
    label: 'Aplicativos',
    descricao: 'Games, apps e assinaturas com licença enviada por e-mail.',
    entrega: 'Licença enviada por e-mail',
    icon: AppWindow,
  },
};

/** trim().toLowerCase(); null/undefined viram string vazia. */
export function normalizarTipo(tipo: unknown): string {
  return typeof tipo === 'string' ? tipo.trim().toLowerCase() : '';
}

/** Area da loja a que um `tipo` pertence. Desconhecido ou vazio => digitais. */
export function areaDoTipo(tipo: unknown): Area {
  const t = normalizarTipo(tipo);
  if (TIPOS_FISICOS.includes(t)) return 'fisicos';
  if (TIPOS_APLICATIVOS.includes(t)) return 'aplicativos';
  return 'digitais';
}

/** Valida o parametro `?area=`; devolve null quando ausente/invalido (= todas). */
export function parseArea(value: string | null | undefined): Area | null {
  const v = normalizarTipo(value);
  return (AREAS as readonly string[]).includes(v) ? (v as Area) : null;
}

export interface TipoInfo {
  /** tipo normalizado */
  tipo: string;
  area: Area;
  label: string;
  icon: LucideIcon;
}

const TIPO_LABELS: Record<string, { label: string; icon: LucideIcon }> = {
  ebook: { label: 'Ebook', icon: BookOpen },
  fisico: { label: 'Físico', icon: Package },
  game: { label: 'Game', icon: Gamepad2 },
  app: { label: 'App', icon: AppWindow },
  assinatura: { label: 'Assinatura', icon: Repeat },
};

/** Rotulo e icone do tipo para badges. Tipos desconhecidos aparecem como "Digital". */
export function tipoInfo(tipo: unknown): TipoInfo {
  const t = normalizarTipo(tipo);
  const known = TIPO_LABELS[t];
  if (known) return { tipo: t, area: areaDoTipo(t), ...known };
  return { tipo: t || 'ebook', area: 'digitais', label: 'Digital', icon: Zap };
}

export type Entrega = 'email-link' | 'email-licenca' | 'frete';

/** Regra de entrega do negocio: digital -> link por e-mail; app/assinatura -> licenca; fisico -> frete. */
export function entregaDaArea(area: Area): Entrega {
  if (area === 'fisicos') return 'frete';
  if (area === 'aplicativos') return 'email-licenca';
  return 'email-link';
}

export function entregaDoTipo(tipo: unknown): Entrega {
  return entregaDaArea(areaDoTipo(tipo));
}

export const ENTREGA_ICON: Record<Entrega, LucideIcon> = {
  'email-link': Zap,
  'email-licenca': KeyRound,
  frete: Package,
};

/** Classificacao indicativa: valores aceitos e rotulos. Desconhecido => "L". */
export const CLASSIFICACOES = ['L', '10', '12', '14', '16', '18'] as const;
export type Classificacao = (typeof CLASSIFICACOES)[number];

export function normalizarClassificacao(value: unknown): Classificacao {
  const v = typeof value === 'string' || typeof value === 'number' ? String(value).trim().toUpperCase() : '';
  const limpo = v.replace(/\+|ANOS/g, '').trim();
  return (CLASSIFICACOES as readonly string[]).includes(limpo) ? (limpo as Classificacao) : 'L';
}

export function rotuloClassificacao(c: Classificacao): string {
  return c === 'L' ? 'L' : `${c}+`;
}

export function descricaoClassificacao(c: Classificacao): string {
  return c === 'L' ? 'Classificação indicativa: livre para todos os públicos' : `Classificação indicativa: ${c} anos`;
}
