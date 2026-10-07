/**
 * Configuracao publica da loja.
 * Todos os valores sao PUBLICOS por desenho (chave anon do Supabase, public key do
 * Mercado Pago): podem ficar no bundle. Segredos nunca entram aqui.
 */

function env(value: string | undefined, fallback: string): string {
  const v = (value ?? '').trim();
  return v.length > 0 ? v : fallback;
}

export const config = {
  supabaseUrl: env(import.meta.env.VITE_SUPABASE_URL, 'https://gyepvrzkwesohbagpgfa.supabase.co'),
  supabaseAnonKey: env(
    import.meta.env.VITE_SUPABASE_ANON_KEY,
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd5ZXB2cnprd2Vzb2hiYWdwZ2ZhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjEzMDk5OTAsImV4cCI6MjA3Njg4NTk5MH0.ePwzEE8FjikLiTyjbtJXUtIIwFRlaSf5RYe7iKMDnTA',
  ),
  apiUrl: env(import.meta.env.VITE_API_URL, 'https://mercadopago-final.onrender.com').replace(/\/+$/, ''),
  mpPublicKey: env(import.meta.env.VITE_MP_PUBLIC_KEY, 'APP_USR-6361a062-ffe7-4bc6-9970-01767001aecb'),
} as const;

/** Painel do autor (continua hospedado no Render). */
export const AUTHOR_PANEL_URL = 'https://mercadopago-final.onrender.com/static/autor-login.html';

export const SITE = {
  name: 'BrooStore',
  tagline: 'Ebooks, produtos físicos e aplicativos em um só lugar',
  supportEmail: 'profalexleal@gmail.com',
  instagram: 'https://www.instagram.com/lizards_games/',
} as const;

/** Tempo (ms) apos o qual um pedido a API e considerado "lento" (servidor free dormindo). */
export const API_SLOW_AFTER_MS = 4000;
/** Timeout generoso: o plano free do Render pode levar 30-60 s para acordar. */
export const API_TIMEOUT_MS = 90_000;
