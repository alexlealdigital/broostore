/** Validadores de formulario (pt-BR). Funcoes puras; retornam boolean ou mensagem de erro. */
import { onlyDigits } from './format';

export const UFS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
  'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
] as const;

export function isEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test((value ?? '').trim());
}

/** Telefone brasileiro com DDD: 10 ou 11 digitos, DDD valido (11-99). */
export function isPhone(value: string): boolean {
  const d = onlyDigits(value);
  if (d.length < 10 || d.length > 11) return false;
  const ddd = Number(d.slice(0, 2));
  if (ddd < 11) return false;
  // celular (11 digitos) comeca com 9
  if (d.length === 11 && d[2] !== '9') return false;
  return true;
}

export function isCEP(value: string): boolean {
  return onlyDigits(value).length === 8;
}

/** CPF com digitos verificadores. Rejeita sequencias repetidas (111.111.111-11). */
export function isCPF(value: string): boolean {
  const d = onlyDigits(value);
  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
  const calc = (len: number): number => {
    let sum = 0;
    for (let i = 0; i < len; i++) sum += Number(d[i]) * (len + 1 - i);
    const rest = (sum * 10) % 11;
    return rest === 10 ? 0 : rest;
  };
  return calc(9) === Number(d[9]) && calc(10) === Number(d[10]);
}

/** Algoritmo de Luhn para numero de cartao. */
export function isLuhnValid(value: string): boolean {
  const d = onlyDigits(value);
  if (d.length < 13 || d.length > 19) return false;
  let sum = 0;
  let alt = false;
  for (let i = d.length - 1; i >= 0; i--) {
    let n = Number(d[i]);
    if (alt) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
    alt = !alt;
  }
  return sum % 10 === 0;
}

export interface ParsedExpiry {
  month: string;
  /** ano com 4 digitos */
  year: string;
}

/** Valida "MM/AA" e rejeita cartao vencido. `now` injetavel para testes. */
export function parseExpiry(value: string, now: Date = new Date()): ParsedExpiry | null {
  const m = /^(\d{2})\/(\d{2})$/.exec((value ?? '').trim());
  if (!m) return null;
  const month = Number(m[1]);
  const year = 2000 + Number(m[2]);
  if (month < 1 || month > 12) return null;
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1;
  if (year < currentYear || (year === currentYear && month < currentMonth)) return null;
  if (year > currentYear + 20) return null;
  return { month: m[1] as string, year: String(year) };
}

export function isCvv(value: string): boolean {
  const d = onlyDigits(value);
  return d.length === 3 || d.length === 4;
}

export function isFullName(value: string): boolean {
  const v = (value ?? '').trim();
  return v.length >= 3 && /\p{L}/u.test(v);
}

/** Aceita apenas http(s); evita "javascript:" em links vindos da query string. */
export function safeHttpUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.toString() : null;
  } catch {
    return null;
  }
}
