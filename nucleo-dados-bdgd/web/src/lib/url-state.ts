"use client";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

/** Estado compartilhável na URL (somente seleções e filtros agregados; nenhum identificador individual). */
export function useQueryState(key: string, fallback = ""): [string, (v: string | null) => void] {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const value = params.get(key) ?? fallback;
  const set = useCallback((v: string | null) => {
    const next = new URLSearchParams(window.location.search);
    if (v === null || v === "" || v === fallback) next.delete(key); else next.set(key, v);
    const qs = next.toString();
    router.replace(`${pathname}${qs ? `?${qs}` : ""}`, { scroll: false });
  }, [key, fallback, pathname, router]);
  return [value, set];
}

/** Atualiza várias chaves numa só navegação (evita estados intermediários e entradas duplicadas no histórico). */
export function useQueryPatch() {
  const router = useRouter();
  const pathname = usePathname();
  return useCallback((patch: Record<string, string | null>, push = false) => {
    const next = new URLSearchParams(window.location.search);
    for (const [k, v] of Object.entries(patch)) { if (v === null || v === "") next.delete(k); else next.set(k, v); }
    const qs = next.toString();
    const url = `${pathname}${qs ? `?${qs}` : ""}`;
    if (push) router.push(url, { scroll: false }); else router.replace(url, { scroll: false });
  }, [pathname, router]);
}

/** Seleção codificada como "dist:26" ou "grupo:energisa". */
export function parseSide(s: string): { tipo: "dist"; id: number } | { tipo: "grupo"; id: string } | null {
  const [t, id] = s.split(":");
  if (t === "dist" && /^\d+$/.test(id ?? "")) return { tipo: "dist", id: Number(id) };
  if (t === "grupo" && id && /^[a-z0-9_]+$/.test(id)) return { tipo: "grupo", id };
  return null;
}
