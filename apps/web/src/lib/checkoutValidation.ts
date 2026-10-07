/** Validacao dos formularios do checkout (funcoes puras). Chaves de erro = campo. */
import { onlyDigits } from './format';
import { isCPF, isCvv, isCEP, isEmail, isFullName, isLuhnValid, isPhone, parseExpiry, UFS, type ParsedExpiry } from './validators';
import type { Endereco } from '@/types';

export type FieldErrors = Record<string, string>;

export interface CustomerForm {
  nome: string;
  email: string;
  telefone: string;
}

export interface CardForm {
  number: string;
  expiry: string;
  cvv: string;
  holder: string;
  cpf: string;
}

export function validateCustomer(c: CustomerForm): FieldErrors {
  const e: FieldErrors = {};
  if (!isFullName(c.nome)) e.nome = 'Informe seu nome completo.';
  if (!isEmail(c.email)) e.email = 'Informe um e-mail válido.';
  if (!isPhone(c.telefone)) e.telefone = 'Informe um telefone com DDD.';
  return e;
}

export function validateAddress(a: Endereco): FieldErrors {
  const e: FieldErrors = {};
  if (!isCEP(a.cep)) e.cep = 'Informe um CEP com 8 dígitos.';
  if (!a.rua.trim()) e.rua = 'Informe a rua.';
  if (!a.numero.trim()) e.numero = 'Informe o número.';
  if (!a.bairro.trim()) e.bairro = 'Informe o bairro.';
  if (!a.cidade.trim()) e.cidade = 'Informe a cidade.';
  if (!(UFS as readonly string[]).includes(a.estado.trim().toUpperCase())) e.estado = 'Selecione o estado.';
  return e;
}

export function validateCard(c: CardForm, now: Date = new Date()): { errors: FieldErrors; expiry: ParsedExpiry | null } {
  const e: FieldErrors = {};
  if (!isLuhnValid(onlyDigits(c.number))) e.number = 'Número do cartão inválido.';
  const expiry = parseExpiry(c.expiry, now);
  if (!expiry) e.expiry = 'Validade inválida (MM/AA).';
  if (!isCvv(c.cvv)) e.cvv = 'CVV inválido.';
  if (!isFullName(c.holder)) e.holder = 'Informe o nome como está no cartão.';
  if (!isCPF(c.cpf)) e.cpf = 'CPF inválido.';
  return { errors: e, expiry };
}

/** Primeiro campo com erro, na ordem de exibicao, para mover o foco. */
export function firstErrorKey(errors: FieldErrors, order: string[]): string | null {
  return order.find((k) => errors[k]) ?? null;
}
