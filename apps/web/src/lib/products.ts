/**
 * Acesso a dados (Supabase) e normalizacao de linhas para o modelo da UI.
 * Regra de visibilidade igual a do site antigo: `active != false` e id 99 (produto interno) oculto.
 */
import { areaDoTipo, normalizarClassificacao, normalizarTipo } from './categorias';
import { toNumber } from './format';
import { getSupabase } from './supabase';
import type { Distribution, Product, ProductRow, RatingsMap, ReviewRow } from '@/types';

/** Colunas que o site antigo ja selecionava (todas existem no banco). */
export const CATALOG_COLUMNS =
  'id, title, author, price, original_price, image_url, category, link, descricao, active, classificacao, tipo, frete, created_at';

const HIDDEN_IDS = new Set([99]);

export class DataError extends Error {
  constructor(message: string, readonly cause?: unknown) {
    super(message);
    this.name = 'DataError';
  }
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function optionalText(value: unknown): string | null {
  const t = text(value);
  return t ? t : null;
}

/** Produto visivel na loja? (`active` nulo/ausente conta como visivel; so `false` esconde.) */
export function isVisible(row: Pick<ProductRow, 'id' | 'active'>): boolean {
  const id = Number(row.id);
  if (HIDDEN_IDS.has(id)) return false;
  return row.active !== false;
}

/** Converte uma linha crua (qualquer coluna pode faltar) em `Product`. Retorna null se o id for invalido. */
export function normalizeProduct(row: ProductRow): Product | null {
  const id = Number(row.id);
  if (!Number.isFinite(id)) return null;
  const price = toNumber(row.price) ?? 0;
  const original = toNumber(row.original_price);
  const tipo = normalizarTipo(row.tipo) || 'ebook';
  const estoque = toNumber(row.estoque);
  return {
    id,
    title: text(row.title) || 'Produto sem título',
    author: text(row.author),
    price,
    originalPrice: original !== null && original > price ? original : null,
    imageUrl: optionalText(row.image_url),
    category: text(row.category) || 'Outros',
    descricao: text(row.descricao),
    classificacao: normalizarClassificacao(row.classificacao),
    tipo,
    area: areaDoTipo(tipo),
    frete: toNumber(row.frete) ?? 0,
    createdAt: optionalText(row.created_at),
    link: optionalText(row.link),
    pesoKg: toNumber(row.peso_kg),
    alturaCm: toNumber(row.altura_cm),
    larguraCm: toNumber(row.largura_cm),
    comprimentoCm: toNumber(row.comprimento_cm),
    paginas: row.paginas !== null && row.paginas !== undefined && String(row.paginas).trim() ? String(row.paginas).trim() : null,
    intro: optionalText(row.intro),
    sobreAutor: optionalText(row.sobre_autor),
    peso: optionalText(row.peso),
    dimensoes: optionalText(row.dimensoes),
    prazoProducao: optionalText(row.prazo_prod),
    specs: optionalText(row.specs),
    estoque: estoque !== null ? estoque : null,
  };
}

export function normalizeProducts(rows: ProductRow[] | null | undefined): Product[] {
  const out: Product[] = [];
  for (const row of rows ?? []) {
    if (!row || !isVisible(row)) continue;
    const p = normalizeProduct(row);
    if (p) out.push(p);
  }
  return out;
}

/** Lista o catalogo (mais novos primeiro). Se alguma coluna nao existir, tenta de novo com `*`. */
export async function fetchCatalog(): Promise<Product[]> {
  const sb = getSupabase();
  const run = (columns: string) =>
    sb.from('products').select(columns).neq('active', false).neq('id', 99).order('created_at', { ascending: false });

  let { data, error } = await run(CATALOG_COLUMNS);
  if (error) {
    // Coluna ausente (ex.: created_at) nao pode derrubar a loja: tenta com `*` e sem ordenacao.
    const retry = await sb.from('products').select('*').neq('active', false).neq('id', 99);
    data = retry.data;
    error = retry.error;
  }
  if (error || !data) throw new DataError('Não foi possível carregar os produtos.', error);
  return normalizeProducts(data as unknown as ProductRow[]);
}

/** `hidden` = existe mas esta inativo/oculto; `missing` = nao existe no Supabase. */
export type ProductLookup = { found: true; product: Product } | { found: false; reason: 'missing' | 'hidden' };

/** Busca um produto com TODAS as colunas (`*`), assim colunas extras opcionais aparecem sem quebrar nada. */
export async function fetchProduct(id: number): Promise<ProductLookup> {
  if (!Number.isFinite(id)) return { found: false, reason: 'missing' };
  if (HIDDEN_IDS.has(id)) return { found: false, reason: 'hidden' };
  const { data, error } = await getSupabase().from('products').select('*').eq('id', id).maybeSingle();
  if (error) throw new DataError('Não foi possível carregar o produto.', error);
  if (!data) return { found: false, reason: 'missing' };
  if (!isVisible(data as ProductRow)) return { found: false, reason: 'hidden' };
  const product = normalizeProduct(data as ProductRow);
  return product ? { found: true, product } : { found: false, reason: 'missing' };
}

/* ---------- avaliacoes ---------- */

function validRating(value: unknown): number | null {
  const n = toNumber(value);
  return n !== null && n >= 1 && n <= 5 ? n : null;
}

export function summarizeRatings(rows: ReviewRow[] | null | undefined): RatingsMap {
  const acc: Record<string, { sum: number; count: number }> = {};
  for (const r of rows ?? []) {
    const rating = validRating(r?.rating);
    if (rating === null || r.product_id === null || r.product_id === undefined) continue;
    const key = String(r.product_id);
    const slot = (acc[key] ??= { sum: 0, count: 0 });
    slot.sum += rating;
    slot.count += 1;
  }
  const map: RatingsMap = {};
  for (const [key, { sum, count }] of Object.entries(acc)) map[key] = { average: sum / count, count };
  return map;
}

export function distributionOf(rows: ReviewRow[] | null | undefined): Distribution {
  const counts: Distribution['counts'] = [0, 0, 0, 0, 0];
  let sum = 0;
  let total = 0;
  for (const r of rows ?? []) {
    const rating = validRating(r?.rating);
    if (rating === null) continue;
    const idx = Math.min(5, Math.max(1, Math.round(rating))) - 1;
    counts[idx] = (counts[idx] ?? 0) + 1;
    sum += rating;
    total += 1;
  }
  return { counts, total, average: total ? sum / total : 0 };
}

/** Todas as avaliacoes (o site antigo tambem lia a tabela inteira). Falha => mapa vazio. */
export async function fetchRatings(): Promise<RatingsMap> {
  const { data, error } = await getSupabase().from('reviews').select('product_id, rating');
  if (error || !data) return {};
  return summarizeRatings(data as ReviewRow[]);
}

export async function fetchProductReviews(productId: number): Promise<ReviewRow[]> {
  const { data, error } = await getSupabase().from('reviews').select('product_id, rating').eq('product_id', productId);
  if (error) throw new DataError('Não foi possível carregar as avaliações.', error);
  return (data ?? []) as ReviewRow[];
}

export async function submitRating(productId: number, rating: number): Promise<void> {
  const value = Math.round(rating);
  if (value < 1 || value > 5) throw new DataError('Avaliação inválida.');
  const { error } = await getSupabase().from('reviews').insert([{ product_id: productId, rating: value }]);
  if (error) throw new DataError('Não foi possível enviar sua avaliação.', error);
}

/* ---------- contato ---------- */

export interface ContatoInput {
  nome: string;
  email: string;
  assunto: string;
  mensagem: string;
}

/** Mesmo insert do site antigo: tabela `contatos` com { nome, email, assunto, mensagem }. */
export async function submitContato(input: ContatoInput): Promise<void> {
  const { error } = await getSupabase().from('contatos').insert({
    nome: input.nome.trim(),
    email: input.email.trim(),
    assunto: input.assunto.trim(),
    mensagem: input.mensagem.trim(),
  });
  if (error) throw new DataError('Não foi possível enviar sua mensagem.', error);
}
