"use client";
import { useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { useQueryPatch } from "@/lib/url-state";
import type { ModoCor } from "./escala";
import type { Indicador } from "./tipos";

export type Aba = "mapa" | "comparar" | "benchmarking" | "fatores" | "metodologia";
export type FiltroSituacao = "todos" | "acima" | "dentro";
export type Referencia = "brasil" | "dist";
export interface Lado { dist: number; conj: number }

const ABAS: Aba[] = ["mapa", "comparar", "benchmarking", "fatores", "metodologia"];
const inteiro = (s: string | null) => (s && /^\d+$/.test(s) ? Number(s) : null);
export function lerLado(s: string | null): Lado | null {
  const m = s?.match(/^(\d+)-(\d+)$/);
  return m ? { dist: Number(m[1]), conj: Number(m[2]) } : null;
}
export const escreverLado = (l: Lado | null) => (l ? `${l.dist}-${l.conj}` : null);

/** Estado do módulo na URL (compartilhável): só seleções e filtros de agregados. */
export function useEstadoConf(anos: number[]) {
  const q = useSearchParams();
  const patch = useQueryPatch();
  return useMemo(() => {
    const ultimo = anos.length ? Math.max(...anos) : 2025;
    const ano = inteiro(q.get("ano"));
    const mes = inteiro(q.get("mes"));
    const aba = q.get("aba") as Aba | null;
    const sit = q.get("sit");
    const grupo = q.get("grupo");
    return {
      aba: aba && ABAS.includes(aba) ? aba : ("mapa" as Aba),
      ind: (q.get("ind") === "fec" ? "fec" : "dec") as Indicador,
      ano: ano !== null && anos.includes(ano) ? ano : ultimo,
      mes: mes !== null && mes >= 1 && mes <= 12 ? mes : null,
      modo: (q.get("cor") === "limite" ? "regulatorio" : "absoluto") as ModoCor,
      sit: (sit === "acima" || sit === "dentro" ? sit : "todos") as FiltroSituacao,
      ref: (q.get("ref") === "dist" ? "dist" : "brasil") as Referencia,
      grupo: grupo && /^[a-z0-9_]+$/.test(grupo) ? grupo : null,
      dist: inteiro(q.get("dist")), conj: inteiro(q.get("conj")),
      a: lerLado(q.get("a")), b: lerLado(q.get("b")),
      set: (p: Record<string, string | number | null>, push = false) => patch(Object.fromEntries(Object.entries(p).map(([k, v]) => [k, v === null ? null : String(v)])), push),
    };
  }, [q, patch, anos]);
}
export type EstadoConf = ReturnType<typeof useEstadoConf>;
