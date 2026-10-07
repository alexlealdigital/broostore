import { useCallback, useSyncExternalStore } from 'react';

/**
 * Preferencia "mostrar conteudo +18". Guardada so em sessionStorage (nao e dado sensivel)
 * e compartilhada entre componentes via useSyncExternalStore.
 */
const KEY = 'broo_adult_ok';
const listeners = new Set<() => void>();
let memory = false; // fallback quando o storage esta indisponivel

function read(): boolean {
  try {
    return sessionStorage.getItem(KEY) === '1' || memory;
  } catch {
    return memory;
  }
}

function write(value: boolean) {
  memory = value;
  try {
    if (value) sessionStorage.setItem(KEY, '1');
    else sessionStorage.removeItem(KEY);
  } catch {
    /* storage bloqueado: segue so em memoria */
  }
  listeners.forEach((l) => l());
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

export function useAdultContent() {
  const allowed = useSyncExternalStore(subscribe, read, () => false);
  const allow = useCallback(() => write(true), []);
  const revoke = useCallback(() => write(false), []);
  return { allowed, allow, revoke };
}
