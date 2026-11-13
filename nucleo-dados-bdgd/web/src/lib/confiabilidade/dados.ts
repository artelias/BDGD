"use client";
import { useEffect, useState } from "react";
import type { DistDoc, Fatores, Indice, NacionalAno } from "./tipos";

/** Raiz do produto público do módulo. Separada do pacote 2025 do portal: nada aqui altera os dados existentes. */
export const CONF_ROOT = "/data/confiabilidade";

const cache = new Map<string, Promise<unknown>>();
/** fetch com cache de módulo; falha fechada (sem dado real, nenhum número aparece). */
export function carregar<T>(caminho: string): Promise<T> {
  if (!cache.has(caminho)) {
    cache.set(caminho, fetch(`${CONF_ROOT}/${caminho}`, { cache: "force-cache" }).then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status} em ${caminho}`);
      return r.json();
    }).catch((e) => { cache.delete(caminho); throw e; }));
  }
  return cache.get(caminho) as Promise<T>;
}

export interface Recurso<T> { carregando: boolean; dados?: T; erro?: string }
export function useRecurso<T>(caminho: string | null): Recurso<T> {
  const [s, set] = useState<{ caminho: string | null; dados?: T; erro?: string }>({ caminho: null });
  useEffect(() => {
    if (!caminho) return;
    let vivo = true;
    carregar<T>(caminho).then((dados) => vivo && set({ caminho, dados })).catch((e: Error) => vivo && set({ caminho, erro: e.message }));
    return () => { vivo = false; };
  }, [caminho]);
  if (!caminho) return { carregando: false };
  if (s.caminho !== caminho) return { carregando: true };
  return { carregando: false, dados: s.dados, erro: s.erro };
}

export const useIndice = () => useRecurso<Indice>("indice.json");
export const useDist = (dist: number | null) => useRecurso<DistDoc>(dist === null ? null : `distribuidoras/${dist}.json`);
export const useNacional = (ano: number | null) => useRecurso<NacionalAno>(ano === null ? null : `nacional/${ano}.json`);
export const useFatores = () => useRecurso<Fatores>("fatores.json");
export const carregarGeo = (dist: number) => carregar<GeoJSON.FeatureCollection>(`geo/${dist}.json`);
