"use client";
import { useCallback, useSyncExternalStore } from "react";

/** Media query como fonte externa (sem setState em efeito). No servidor assume `false`. */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback((cb: () => void) => {
    const mq = window.matchMedia(query);
    mq.addEventListener("change", cb);
    return () => mq.removeEventListener("change", cb);
  }, [query]);
  return useSyncExternalStore(subscribe, () => window.matchMedia(query).matches, () => false);
}

const EVT = "nucleo-bdgd-storage";
// Fallback por aba: mesmo que o navegador bloqueie escrita no localStorage,
// a escolha deve surtir efeito imediato durante a sessão atual.
const volatileValues = new Map<string, string>();
function read(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return volatileValues.get(key) ?? null; }
}

/** Preferência persistida em localStorage (com fallback silencioso quando o armazenamento é bloqueado). */
export function useStoredValue(key: string, fallback: string): [string, (v: string) => void] {
  const subscribe = useCallback((cb: () => void) => {
    const on = (e: Event) => { if (!(e instanceof StorageEvent) || e.key === key) cb(); };
    window.addEventListener("storage", on);
    window.addEventListener(EVT, on);
    return () => { window.removeEventListener("storage", on); window.removeEventListener(EVT, on); };
  }, [key]);
  const value = useSyncExternalStore(subscribe, () => read(key) ?? fallback, () => fallback);
  const set = useCallback((v: string) => {
    volatileValues.set(key, v);
    try { localStorage.setItem(key, v); } catch { /* preferência válida nesta aba, mas não persistida */ }
    window.dispatchEvent(new Event(EVT));
  }, [key]);
  return [value, set];
}
