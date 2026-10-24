"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Dataset } from "./dataset";
import type { ConceitoData, FacetData, IndexData, InventarioData, Qualidade } from "./types";

export const DATA_BASE = "2025-12-31";
export const DATA_ROOT = `/data/${DATA_BASE}`;

type State = { status: "loading" } | { status: "error"; error: string } | { status: "ready"; ds: Dataset };
const Ctx = createContext<State>({ status: "loading" });

const cache = new Map<string, Promise<unknown>>();
/** fetch com cache de módulo; falha fechada: sem dados reais, nenhum número é exibido. */
export function load<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    cache.set(path, fetch(`${DATA_ROOT}/${path}`, { cache: "force-cache" }).then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status} em ${path}`);
      return r.json();
    }).catch((e) => { cache.delete(path); throw e; }));
  }
  return cache.get(path) as Promise<T>;
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>({ status: "loading" });
  useEffect(() => {
    let alive = true;
    load<IndexData>("index.json")
      .then((raw) => {
        if (raw.release?.data_base !== DATA_BASE) throw new Error("Manifesto com data-base diferente de 2025-12-31");
        if (alive) setState({ status: "ready", ds: new Dataset(raw) });
      })
      .catch((e: Error) => alive && setState({ status: "error", error: e.message }));
    return () => { alive = false; };
  }, []);
  return <Ctx.Provider value={state}>{children}</Ctx.Provider>;
}

export function useData() { return useContext(Ctx); }

export function useAsset<T>(path: string | null) {
  const [s, set] = useState<{ path: string | null; data?: T; error?: string }>({ path: null });
  useEffect(() => {
    if (!path) return;
    let alive = true;
    load<T>(path).then((data) => alive && set({ path, data })).catch((e: Error) => alive && set({ path, error: e.message }));
    return () => { alive = false; };
  }, [path]);
  if (!path || s.path !== path) return { loading: !!path } as { loading: boolean; data?: T; error?: string };
  return { loading: false, data: s.data, error: s.error };
}

export const useFacets = (ent: string | null) => useAsset<FacetData>(ent ? `facetas/${ent}.json` : null);
export const useQualidade = () => useAsset<Qualidade>("qualidade.json");
export const useConceito = (id: string | null) => useAsset<ConceitoData>(id ? `conceitos/${id}.json` : null);
export const useInventario = (dist: number | null) => useAsset<InventarioData>(dist !== null ? `inventario/${dist}.json` : null);

/** Vários conceitos ao mesmo tempo (ex.: colunas filtradas da Matriz); só carrega os ids pedidos. */
export function useConceitos(ids: string[]) {
  const key = [...new Set(ids)].sort().join(",");
  const [st, set] = useState<{ key: string; data: Record<string, ConceitoData>; error?: string }>({ key: "", data: {} });
  useEffect(() => {
    if (!key) return;
    let alive = true;
    Promise.all(key.split(",").map((id) => load<ConceitoData>(`conceitos/${id}.json`).then((d) => [id, d] as const)))
      .then((pairs) => alive && set({ key, data: Object.fromEntries(pairs) }))
      .catch((e: Error) => alive && set({ key, data: {}, error: e.message }));
    return () => { alive = false; };
  }, [key]);
  if (!key) return { loading: false, data: {} as Record<string, ConceitoData> };
  return { loading: st.key !== key, data: st.key === key ? st.data : {}, error: st.key === key ? st.error : undefined };
}
