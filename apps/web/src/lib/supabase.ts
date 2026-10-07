import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { config } from './config';

/**
 * Cliente Supabase somente leitura (chave anon, publica por desenho).
 * Sem sessao: a loja nao faz login, entao nao ha nada para persistir no navegador.
 */
let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient {
  if (!client) {
    client = createClient(config.supabaseUrl, config.supabaseAnonKey, {
      auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
    });
  }
  return client;
}
