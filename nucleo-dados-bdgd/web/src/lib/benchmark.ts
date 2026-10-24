import type { Indicador } from "./catalogo";
import type { Aggregate, Dataset } from "./dataset";
import { kpiValue } from "./kpis";

/** Referência do radar. "lado" usa o lado B do comparador (outro grupo ou outra distribuidora). */
export type RefTipo = "lado" | "brasil" | "bench_grupos" | "bench_dists";

export const REF_LABEL: Record<RefTipo, string> = {
  lado: "Lado B",
  brasil: "Brasil — total nacional",
  bench_grupos: "Benchmark Brasil — grupos",
  bench_dists: "Benchmark Brasil — distribuidoras",
};

export interface Lider { nome: string; v: number; n: number; total: number }

export interface Eixo {
  ind: Indicador;
  a: Aggregate;
  /** valor de referência (denominador comum a A e à referência) */
  ref: number | null;
  refLabel: string;
  /** A / ref; pode passar de 1 (não é truncado) */
  pctA: number | null;
  /** referência / ref: 1 quando há valor */
  pctRef: number | null;
  lider: Lider | null;
  /** motivo quando o eixo sai do radar */
  nd: string | null;
}

/** Maior valor entre grupos verificados (MAX_g) ou entre distribuidoras (MAX_d). Grupo com soma parcial entra marcado pela cobertura. */
export function lider(ds: Dataset, ind: Pick<Indicador, "ent" | "metric">, por: "grupos" | "dists"): Lider | null {
  let best: Lider | null = null;
  if (por === "grupos") {
    for (const g of ds.grupos) {
      const a = kpiValue(ds, ind, ds.groupDists(g.id).map((d) => d.dist));
      if (a.v !== null && (!best || a.v > best.v)) best = { nome: g.nome, v: a.v, n: a.n, total: a.total };
    }
  } else {
    for (const d of ds.dists) {
      const a = kpiValue(ds, ind, [d.dist]);
      if (a.v !== null && (!best || a.v > best.v)) best = { nome: d.sigla.replaceAll("_", " "), v: a.v, n: a.n, total: a.total };
    }
  }
  return best;
}

/** Eixos do radar: mesmo denominador (a referência) para A e para a referência; eixo sem valor de algum lado sai do gráfico. */
export function eixosRadar(ds: Dataset, inds: Indicador[], distsA: number[], ref: RefTipo, distsB: number[], labelB: string): Eixo[] {
  return inds.map((ind) => {
    const a = kpiValue(ds, ind, distsA);
    let refV: number | null = null;
    let lid: Lider | null = null;
    let refLabel = labelB;
    if (ref === "lado") refV = kpiValue(ds, ind, distsB).v;
    else if (ref === "brasil") { refV = kpiValue(ds, ind, ds.dists.map((d) => d.dist)).v; refLabel = REF_LABEL.brasil; }
    else {
      lid = lider(ds, ind, ref === "bench_grupos" ? "grupos" : "dists");
      refV = lid?.v ?? null;
      refLabel = lid ? `${REF_LABEL[ref]} (${lid.nome})` : REF_LABEL[ref];
    }
    if (!lid) lid = lider(ds, ind, ref === "bench_grupos" ? "grupos" : "dists");
    let nd: string | null = null;
    if (a.v === null) nd = "A sem valor homologado";
    else if (refV === null) nd = "Referência sem valor homologado";
    else if (refV === 0) nd = "Referência igual a zero: proporção indefinida";
    const ok = nd === null;
    return { ind, a, ref: refV, refLabel, pctA: ok ? a.v! / refV! : null, pctRef: ok ? 1 : null, lider: lid, nd };
  });
}
