import type { Dataset } from "./dataset";

/** Escopo de análise compartilhado por Explorar e Evolução.
 *  brasil: todas as DIST; grupo: DIST com vínculo verificado (todas ou um subconjunto); dists: seleção livre de uma ou várias. */
export type Escopo = { modo: "brasil" } | { modo: "grupo"; grupo: string; dists: number[] } | { modo: "dists"; dists: number[] };

const lista = (s: string) => s.split(",").map(Number).filter((n) => Number.isInteger(n) && n > 0);

/** URL: escopo=brasil | grupo:<id> | dists (+ dists=1,2). Aceita o formato antigo escopo=dist:N. */
export function lerEscopo(ds: Dataset, escopo: string, dists: string): Escopo {
  const [t, id] = escopo.split(":");
  if (t === "grupo" && id && ds.grupo(id)) {
    const membros = new Set(ds.groupDists(id).map((d) => d.dist));
    return { modo: "grupo", grupo: id, dists: lista(dists).filter((d) => membros.has(d)) };
  }
  if (t === "dist" && /^\d+$/.test(id ?? "") && ds.dist(Number(id))) return { modo: "dists", dists: [Number(id)] };
  if (t === "dists") {
    const ds2 = lista(dists).filter((d) => ds.dist(d));
    if (ds2.length) return { modo: "dists", dists: ds2 };
  }
  return { modo: "brasil" };
}

export function escreverEscopo(e: Escopo): { escopo: string | null; dists: string | null } {
  if (e.modo === "brasil") return { escopo: null, dists: null };
  if (e.modo === "grupo") return { escopo: `grupo:${e.grupo}`, dists: e.dists.length ? e.dists.join(",") : null };
  return { escopo: "dists", dists: e.dists.join(",") };
}

export function distsDoEscopo(ds: Dataset, e: Escopo): number[] {
  if (e.modo === "brasil") return ds.dists.map((d) => d.dist);
  if (e.modo === "grupo") return e.dists.length ? e.dists : ds.groupDists(e.grupo).map((d) => d.dist);
  return e.dists;
}

export function rotuloEscopo(ds: Dataset, e: Escopo): string {
  if (e.modo === "brasil") return "Brasil";
  if (e.modo === "grupo") {
    const g = ds.grupo(e.grupo)?.nome ?? e.grupo;
    if (!e.dists.length) return g;
    return e.dists.length === 1 ? ds.dist(e.dists[0])!.sigla.replaceAll("_", " ") : `${e.dists.length} distribuidoras de ${g}`;
  }
  return e.dists.length === 1 ? (ds.dist(e.dists[0])?.sigla.replaceAll("_", " ") ?? `DIST ${e.dists[0]}`) : `${e.dists.length} distribuidoras selecionadas`;
}

/** Palavra para a participação interna: "no grupo", "na distribuidora", "na seleção". */
export function noEscopo(e: Escopo): string {
  if (e.modo === "brasil") return "no Brasil";
  if (e.modo === "grupo" && !e.dists.length) return "no grupo";
  return e.dists.length === 1 ? "na distribuidora" : "na seleção";
}
