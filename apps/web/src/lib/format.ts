/** Formatadores e mascaras (pt-BR). Funcoes puras, sem DOM. */

export function onlyDigits(value: string): string {
  return (value ?? '').replace(/\D/g, '');
}

const BRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

/** 1234.5 -> "R$ 1.234,50". Valores invalidos viram "R$ 0,00". */
export function formatBRL(value: number | null | undefined): string {
  const n = typeof value === 'number' && Number.isFinite(value) ? value : 0;
  // Intl usa NBSP entre o simbolo e o numero; normaliza para espaco comum (facilita testes/copia).
  return BRL.format(n).replace(/[\u00a0\u202f]/g, ' ');
}

/** Converte numero/string ("29,90", "29.90", 29.9) em number; invalido => null. */
export function toNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string') {
    const s = value.trim();
    if (!s) return null;
    // "1.234,56" -> 1234.56 ; "29,90" -> 29.90 ; "29.90" -> 29.90
    const normalized = s.includes(',') ? s.replace(/\./g, '').replace(',', '.') : s;
    const n = Number(normalized);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

/** Percentual de desconto inteiro (0 quando nao ha desconto valido). */
export function discountPercent(price: number, original: number | null | undefined): number {
  if (!original || original <= price || original <= 0) return 0;
  return Math.round(((original - price) / original) * 100);
}

export function formatCPF(value: string): string {
  const v = onlyDigits(value).slice(0, 11);
  if (v.length <= 3) return v;
  if (v.length <= 6) return `${v.slice(0, 3)}.${v.slice(3)}`;
  if (v.length <= 9) return `${v.slice(0, 3)}.${v.slice(3, 6)}.${v.slice(6)}`;
  return `${v.slice(0, 3)}.${v.slice(3, 6)}.${v.slice(6, 9)}-${v.slice(9)}`;
}

/** (11) 99999-9999 ou (11) 9999-9999 enquanto digita. */
export function formatPhone(value: string): string {
  const v = onlyDigits(value).slice(0, 11);
  if (v.length === 0) return '';
  if (v.length <= 2) return `(${v}`;
  if (v.length <= 6) return `(${v.slice(0, 2)}) ${v.slice(2)}`;
  if (v.length <= 10) return `(${v.slice(0, 2)}) ${v.slice(2, 6)}-${v.slice(6)}`;
  return `(${v.slice(0, 2)}) ${v.slice(2, 7)}-${v.slice(7)}`;
}

export function formatCEP(value: string): string {
  const v = onlyDigits(value).slice(0, 8);
  return v.length > 5 ? `${v.slice(0, 5)}-${v.slice(5)}` : v;
}

/** Numero do cartao em grupos de 4 (ate 19 digitos). */
export function formatCardNumber(value: string): string {
  return onlyDigits(value)
    .slice(0, 19)
    .replace(/(.{4})/g, '$1 ')
    .trim();
}

/** MM/AA enquanto digita. */
export function formatExpiry(value: string): string {
  const v = onlyDigits(value).slice(0, 4);
  return v.length >= 3 ? `${v.slice(0, 2)}/${v.slice(2)}` : v;
}

/** "2025-01-31T..." -> "31/01/2025" */
export function formatDateBR(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('pt-BR');
}

/** "4,5" com uma casa decimal. */
export function formatRating(value: number): string {
  return value.toFixed(1).replace('.', ',');
}

/** Singular/plural simples: pluralize(1,'avaliação','avaliações'). */
export function pluralize(n: number, singular: string, plural: string): string {
  return n === 1 ? singular : plural;
}
