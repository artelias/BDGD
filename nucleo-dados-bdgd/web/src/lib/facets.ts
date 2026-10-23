import type { FacetData, FacetSpec, Metric, Status } from "./types";

/** Semântica normativa (MODELO-FATOS-FACETAS-2025):
 *  - filtro DDA usa UM cubo cujo conjunto de dimensões é exatamente o conjunto filtrado;
 *  - sem cubo compatível -> "combinacao_nao_suportada" (nunca multiplicar marginais);
 *  - valores bloqueados/nulos ficam N/D, sem zero implícito;
 *  - somar categorias do mesmo cubo só com permite_rollup = sim. */

export type FacetFilter = Record<string, string>;

export interface FacetResult {
  status: "ok" | "combinacao_nao_suportada" | "metrica_indisponivel" | "sem_dados";
  v: number | null;
  n: number;
  nd: number;
  alerta: number;
  facet?: FacetSpec;
  motivos: string[];
}

export interface Category {
  code: string;
  label: string;
  v: number | null;
  n: number;
  nd: number;
  alerta: number;
}

export interface Distribution {
  status: FacetResult["status"];
  facet?: FacetSpec;
  categories: Category[];
  /** soma das categorias só é um total quando a partição é disjunta e completa */
  additive: boolean;
}

export const SEM_CODIGO = "SEM_CODIGO";

export function findFacet(data: FacetData, attrs: string[]): FacetSpec | undefined {
  const want = [...attrs].sort().join("+");
  return data.facets.find((f) => [...f.dims].sort().join("+") === want);
}

/** Atributos que podem ser combinados com `attr` (existe cubo conjunto com as duas dimensões). */
export function combinableWith(data: FacetData, attr: string): string[] {
  return data.facets.filter((f) => f.dims.length === 2 && f.dims.includes(attr)).map((f) => f.dims.find((d) => d !== attr)!).sort();
}

export function singleAttributes(data: FacetData): string[] {
  return data.facets.filter((f) => f.dims.length === 1).map((f) => f.dims[0]).sort();
}

export function describe(data: FacetData, attr: string, code: string): string {
  if (code === SEM_CODIGO) return "Sem código informado";
  const d = data.descricoes[attr]?.[code];
  return d ? d : `Código ${code} (sem descrição no DDA)`;
}

function rowMatches(codes: string[], dims: string[], filter: FacetFilter) {
  return dims.every((dim, i) => filter[dim] === undefined || filter[dim] === codes[i]);
}

/** Valor de um recorte DDA, somado sobre os DISTs do escopo. */
export function facetValue(data: FacetData, filter: FacetFilter, metric: Metric, dists: Set<number>): FacetResult {
  const attrs = Object.keys(filter);
  const facet = findFacet(data, attrs);
  if (!facet) return { status: "combinacao_nao_suportada", v: null, n: 0, nd: 0, alerta: 0, motivos: [] };
  if (!facet.metricas[metric]) return { status: "metrica_indisponivel", v: null, n: 0, nd: 0, alerta: 0, facet, motivos: [] };
  const rows = data.rows[facet.id] ?? [];
  let v = 0;
  const motivos = new Set<string>();
  const ok = new Set<number>(), blocked = new Set<number>(), warned = new Set<number>();
  for (const [dist, codes, vals, sts] of rows) {
    if (!dists.has(dist) || !rowMatches(codes, facet.dims, filter)) continue;
    const st: Status | undefined = sts[metric];
    const val = vals[metric];
    const m = data.motivos[`${dist}|${metric}`];
    if (st === "b" || val === null || val === undefined) { blocked.add(dist); if (m) motivos.add(m); continue; }
    v += val; ok.add(dist);
    if (st === "l") { warned.add(dist); if (m) motivos.add(m); }
  }
  // um DIST com parte das células bloqueadas não entra como valor completo
  for (const d of blocked) ok.delete(d);
  if (!ok.size && !blocked.size) return { status: "sem_dados", v: null, n: 0, nd: 0, alerta: 0, facet, motivos: [] };
  if (blocked.size) {
    // recalcula sem os DISTs bloqueados para não misturar parcial com completo
    v = 0;
    for (const [dist, codes, vals] of rows) if (ok.has(dist) && rowMatches(codes, facet.dims, filter)) v += vals[metric] ?? 0;
  }
  return { status: "ok", v: ok.size ? v : null, n: ok.size, nd: blocked.size, alerta: warned.size, facet, motivos: [...motivos] };
}

/** Distribuição de `attr`, opcionalmente condicionada a outro atributo via cubo conjunto. */
export function distribution(data: FacetData, attr: string, metric: Metric, dists: Set<number>, given?: FacetFilter): Distribution {
  const attrs = [attr, ...Object.keys(given ?? {})];
  const facet = findFacet(data, attrs);
  if (!facet) return { status: "combinacao_nao_suportada", categories: [], additive: false };
  const spec = facet.metricas[metric];
  if (!spec) return { status: "metrica_indisponivel", facet, categories: [], additive: false };
  const i = facet.dims.indexOf(attr);
  const acc = new Map<string, Category>();
  for (const [dist, codes, vals, sts] of data.rows[facet.id] ?? []) {
    if (!dists.has(dist) || !rowMatches(codes, facet.dims, given ?? {})) continue;
    const code = codes[i];
    const c = acc.get(code) ?? { code, label: describe(data, attr, code), v: null, n: 0, nd: 0, alerta: 0 };
    const st = sts[metric]; const val = vals[metric];
    if (st === "b" || val === null || val === undefined) c.nd++;
    else { c.v = (c.v ?? 0) + val; c.n++; if (st === "l") c.alerta++; }
    acc.set(code, c);
  }
  const categories = [...acc.values()].sort((a, b) => (b.v ?? -1) - (a.v ?? -1));
  return { status: categories.length ? "ok" : "sem_dados", facet, categories, additive: spec.rollup && spec.disjunta };
}

/** Códigos existentes de `attr` (para facetas em cascata), restritos ao escopo e a um filtro já aplicado. */
export function availableCodes(data: FacetData, attr: string, dists: Set<number>, given?: FacetFilter): string[] {
  const facet = findFacet(data, [attr, ...Object.keys(given ?? {})]);
  if (!facet) return [];
  const i = facet.dims.indexOf(attr);
  const out = new Set<string>();
  for (const [dist, codes] of data.rows[facet.id] ?? []) if (dists.has(dist) && rowMatches(codes, facet.dims, given ?? {})) out.add(codes[i]);
  return [...out];
}
