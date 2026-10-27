import type { Dataset } from "./dataset";
import type { MedidaConceito } from "./types";
import { coberturaNacionalIncompleta } from "./panorama-r3";

/** Linha comparável: um ativo (ou uma categoria do ativo filtrado) com o valor de cada DIST.
 *  null = sem valor homologado na DIST (fica fora da soma e é contado); DIST ausente do mapa = ativo inexistente. */
export interface Linha { id: string; nome: string; familia: string; medida: MedidaConceito; porDist: Map<number, number | null> }
export interface Soma { v: number | null; n: number; nd: number; total: number }

export function somar(l: Linha, dists: number[]): Soma {
  let v = 0, n = 0, nd = 0;
  for (const d of dists) {
    if (!l.porDist.has(d)) continue;
    const x = l.porDist.get(d)!;
    if (x === null) nd++; else { v += x; n++; }
  }
  return { v: n ? v : null, n, nd, total: dists.length };
}

export type Referencia = "lado" | "brasil" | "bench_grupos" | "bench_dists";
export const REFERENCIA: Record<Referencia, string> = {
  lado: "Lado B", brasil: "Brasil — total nacional", bench_grupos: "Benchmark Brasil — grupos", bench_dists: "Benchmark Brasil — distribuidoras",
};
export interface EixoLinha { linha: Linha; a: Soma; ref: number | null; refNome: string; pctA: number | null; lider: { nome: string; v: number; n: number; total: number } | null; nd: string | null }

/** Maior valor entre grupos verificados (MAX_g) ou entre distribuidoras (MAX_d), na mesma linha (mesmo recorte e medida). */
export function liderLinha(ds: Dataset, l: Linha, por: "grupos" | "dists") {
  let best: EixoLinha["lider"] = null;
  if (por === "grupos") {
    for (const g of ds.grupos) {
      const s = somar(l, ds.groupDists(g.id).map((d) => d.dist));
      if (s.v !== null && !s.nd && (!best || s.v > best.v)) best = { nome: g.nome, v: s.v, n: s.n, total: s.total };
    }
  } else {
    for (const d of ds.dists) {
      const x = l.porDist.get(d.dist);
      if (x !== null && x !== undefined && (!best || x > best.v)) best = { nome: d.sigla.replaceAll("_", " "), v: x, n: 1, total: 1 };
    }
  }
  return best;
}

/** Eixos do radar: A e a referência divididos pelo mesmo valor (a referência), por linha; >100% não é truncado. */
export function benchmarkLinhas(ds: Dataset, linhas: Linha[], distsA: number[], ref: Referencia, distsB: number[], nomeB: string): EixoLinha[] {
  const todas = ds.dists.map((d) => d.dist);
  return linhas.map((l) => {
    const a = somar(l, distsA);
    let refV: number | null, refNome = nomeB;
    let lid = liderLinha(ds, l, ref === "bench_grupos" ? "grupos" : "dists");
    if (ref === "lado") { const b = somar(l, distsB); refV = b.nd ? null : b.v; }
    else if (ref === "brasil") {
      const nacional = somar(l, todas);
      refV = nacional.nd || coberturaNacionalIncompleta(ds, todas) ? null : nacional.v;
      refNome = REFERENCIA.brasil;
    }
    else { refV = lid?.v ?? null; refNome = lid ? `${REFERENCIA[ref]} (${lid.nome})` : REFERENCIA[ref]; }
    if (ref === "lado" || ref === "brasil") lid = liderLinha(ds, l, "dists");
    let nd: string | null = null;
    if (a.nd) nd = "A com cobertura parcial";
    else if (a.v === null) nd = "A sem valor homologado";
    else if (refV === null) nd = "referência sem valor homologado";
    else if (refV === 0) nd = "referência igual a zero: proporção indefinida";
    return { linha: l, a, ref: refV, refNome, pctA: nd ? null : a.v! / refV!, lider: lid, nd };
  });
}
