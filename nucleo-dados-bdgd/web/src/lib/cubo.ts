import type { ConceitoData, Filtro, MedidaConceito } from "./types";

/** Semântica dos cubos por conceito (R3):
 *  - cada cubo é um GROUP BY exato de todas as suas dimensões; somar linhas responde a qualquer filtro dessas dimensões;
 *  - um recorte só é respondido por um cubo que contenha TODAS as dimensões filtradas (e a de análise); sem cubo -> indisponível;
 *  - valor nulo de uma medida numa DIST (ex.: potência N/D) tira a DIST inteira da soma daquela medida: nunca soma parcial;
 *  - valor -1 = a medida não se aplica àquela entidade (ex.: potência de transformador de medida): a linha não soma nem gera N/D;
 *  - nada é estimado multiplicando percentuais de filtros independentes. */

export interface Recorte { filtro: Filtro; excluir?: Filtro }
export const RECORTE_VAZIO: Recorte = { filtro: {} };

export interface Agregado { v: number | null; n: number; nd: number; dists: Set<number> }
export interface Categoria { code: string; label: string; v: number | null; n: number; nd: number }

export function dimsDoRecorte(r: Recorte): string[] {
  const s = new Set<string>();
  for (const [k, v] of Object.entries(r.filtro)) if (v.length) s.add(k);
  for (const [k, v] of Object.entries(r.excluir ?? {})) if (v.length) s.add(k);
  return [...s];
}

export function juntar(a: Recorte, b: Recorte): Recorte {
  const filtro: Filtro = { ...a.filtro };
  for (const [k, v] of Object.entries(b.filtro)) filtro[k] = filtro[k] ? filtro[k].filter((x) => v.includes(x)) : v;
  const excluir: Filtro = { ...(a.excluir ?? {}) };
  for (const [k, v] of Object.entries(b.excluir ?? {})) excluir[k] = [...new Set([...(excluir[k] ?? []), ...v])];
  return { filtro, excluir };
}

/** Cubo com todas as dimensões pedidas. O principal tem prioridade; depois, cubos com a MESMA cobertura de entidades
 *  (mesmo total); só então cubos de cobertura menor (ex.: município não existe em todas as tabelas), sinalizados por `cobertura`. */
export function escolherCubo(cd: ConceitoData, dims: string[]): string | null {
  const ok = Object.entries(cd.cubos).filter(([, c]) => dims.every((d) => c.dims.includes(d)));
  if (!ok.length) return null;
  if (ok.some(([id]) => id === "principal")) return "principal";
  const plena = cd.cubos.principal?.entidades.length ?? 0;
  ok.sort(([, a], [, b]) => (b.entidades.length >= plena ? 1 : 0) - (a.entidades.length >= plena ? 1 : 0) || b.entidades.length - a.entidades.length || a.rows.length - b.rows.length);
  return ok[0][0];
}

/** Entidades que o cubo deixa de fora em relação ao principal (vazio = cobertura plena). */
export function foraDoCubo(cd: ConceitoData, cubo: string): string[] {
  const c = new Set(cd.cubos[cubo]?.entidades ?? []);
  return (cd.cubos.principal?.entidades ?? []).filter((e) => !c.has(e));
}

/** Dimensões que ainda podem ser combinadas com o recorte atual (existe cubo com todas). */
export function dimsCompativeis(cd: ConceitoData, r: Recorte, extra: string[] = []): Set<string> {
  const base = [...dimsDoRecorte(r), ...extra];
  const out = new Set<string>();
  for (const c of Object.values(cd.cubos)) if (base.every((d) => c.dims.includes(d))) c.dims.forEach((d) => out.add(d));
  return out;
}

function matcher(cd: ConceitoData, cubo: string, r: Recorte) {
  const dims = cd.cubos[cubo].dims;
  const tests: Array<[number, Set<number>, boolean]> = [];
  const idx = (dim: string, codes: string[]) => new Set(codes.map((c) => cd.valores[dim]?.indexOf(c) ?? -1).filter((i) => i >= 0));
  for (const [dim, codes] of Object.entries(r.filtro)) if (codes.length) tests.push([dims.indexOf(dim) + 1, idx(dim, codes), true]);
  for (const [dim, codes] of Object.entries(r.excluir ?? {})) if (codes.length) tests.push([dims.indexOf(dim) + 1, idx(dim, codes), false]);
  if (tests.some(([p]) => p === 0)) return null;
  return (row: Array<number | null>) => tests.every(([p, s, inc]) => s.has(row[p] as number) === inc);
}

function posMedida(cd: ConceitoData, cubo: string, m: MedidaConceito) {
  const i = cd.medidas.indexOf(m);
  return i < 0 ? -1 : 1 + cd.cubos[cubo].dims.length + i;
}

/** Soma de uma medida no recorte, por DIST do escopo (null = todas). */
export function agregar(cd: ConceitoData, r: Recorte, m: MedidaConceito, dists: Set<number> | null, cubo?: string | null): Agregado | null {
  const cid = cubo ?? escolherCubo(cd, dimsDoRecorte(r));
  if (!cid) return null;
  const match = matcher(cd, cid, r), pm = posMedida(cd, cid, m);
  if (!match || pm < 0) return null;
  const porDist = new Map<number, number | null>();
  for (const row of cd.cubos[cid].rows) {
    const d = row[0] as number;
    if (dists && !dists.has(d)) continue;
    const v = row[pm];
    if (!match(row) || v === -1) { if (!porDist.has(d) && v !== -1) porDist.set(d, 0); continue; }
    const cur = porDist.get(d);
    if (v === null || cur === null) porDist.set(d, null);
    else porDist.set(d, (cur ?? 0) + v);
  }
  let v = 0, n = 0, nd = 0;
  for (const x of porDist.values()) { if (x === null) nd++; else { v += x; n++; } }
  return { v: n ? v : null, n, nd, dists: new Set(porDist.keys()) };
}

/** Valor por DIST numa única passada (mesma regra de agregar): null = N/D na medida; ausente do mapa = ativo inexistente. */
export function agregarPorDist(cd: ConceitoData, r: Recorte, m: MedidaConceito): Map<number, number | null> | null {
  const cid = escolherCubo(cd, dimsDoRecorte(r));
  if (!cid) return null;
  const match = matcher(cd, cid, r), pm = posMedida(cd, cid, m);
  if (!match || pm < 0) return null;
  const porDist = new Map<number, number | null>();
  for (const row of cd.cubos[cid].rows) {
    const d = row[0] as number, v = row[pm];
    if (!match(row) || v === -1) { if (!porDist.has(d) && v !== -1) porDist.set(d, 0); continue; }
    const cur = porDist.get(d);
    porDist.set(d, v === null || cur === null ? null : (cur ?? 0) + v);
  }
  return porDist;
}

export function rotulo(cd: ConceitoData, dim: string, code: string, r?: Recorte): string {
  if (dim === "a1") {
    const tipos = r?.filtro.tipo;
    if (tipos?.length === 1 && cd.a1PorTuc?.[tipos[0]]?.[code]) return cd.a1PorTuc[tipos[0]][code];
  }
  return cd.rotulos[dim]?.[code] ?? code;
}

/** Distribuição de uma medida pelas categorias de `dim`, dentro do recorte. */
export function distribuicao(cd: ConceitoData, dim: string, r: Recorte, m: MedidaConceito, dists: Set<number> | null): { cubo: string; categorias: Categoria[] } | null {
  const cid = escolherCubo(cd, [...dimsDoRecorte(r), dim]);
  if (!cid) return null;
  const match = matcher(cd, cid, r), pm = posMedida(cd, cid, m), pd = cd.cubos[cid].dims.indexOf(dim) + 1;
  if (!match || pm < 0) return null;
  // por categoria e DIST: soma, ou null se alguma linha da DIST tiver a medida N/D
  const acc = new Map<number, Map<number, number | null>>();
  for (const row of cd.cubos[cid].rows) {
    const d = row[0] as number;
    if ((dists && !dists.has(d)) || !match(row) || row[pm] === -1) continue;
    const c = row[pd] as number, v = row[pm];
    let porD = acc.get(c); if (!porD) { porD = new Map(); acc.set(c, porD); }
    const cur = porD.get(d);
    porD.set(d, v === null || cur === null ? null : (cur ?? 0) + v);
  }
  const categorias: Categoria[] = [];
  for (const [ci, porD] of acc) {
    let v = 0, n = 0, nd = 0;
    for (const x of porD.values()) { if (x === null) nd++; else { v += x; n++; } }
    const code = cd.valores[dim][ci];
    categorias.push({ code, label: rotulo(cd, dim, code, r), v: n ? v : null, n, nd });
  }
  categorias.sort((a, b) => (b.v ?? -1) - (a.v ?? -1));
  // rótulos repetidos (descrições iguais no DDA) recebem o código
  const seen = new Map<string, number>();
  for (const c of categorias) seen.set(c.label, (seen.get(c.label) ?? 0) + 1);
  for (const c of categorias) if ((seen.get(c.label) ?? 0) > 1) c.label = `${c.label} · ${c.code}`;
  return { cubo: cid, categorias };
}

export interface Participacao {
  valor: number | null;
  /** total da mesma população (recorte base do conceito, sem os filtros do usuário) no escopo */
  totalEscopo: number | null;
  /** mesmo recorte no Brasil */
  brasil: number | null;
  noEscopo: number | null;
  doBrasil: number | null;
  motivo: string | null;
}

/** Participação dupla com denominadores homogêneos: mesma medida, mesmo conceito e mesmo cubo-base.
 *  noEscopo = recorte / população do conceito no escopo; doBrasil = recorte no escopo / mesmo recorte no Brasil. */
export function participacao(cd: ConceitoData, base: Recorte, recorte: Recorte, m: MedidaConceito, escopo: Set<number> | null, brasil: Set<number>): Participacao {
  const a = agregar(cd, recorte, m, escopo), b = agregar(cd, base, m, escopo), c = agregar(cd, recorte, m, brasil);
  let motivo: string | null = null;
  if (!a || !b || !c) motivo = "combinação sem cubo calculado";
  else if (a.nd || b.nd || c.nd) motivo = "há distribuidoras sem valor homologado nesta medida";
  const ok = !motivo;
  const valor = a?.v ?? null, totalEscopo = b?.v ?? null, br = c?.v ?? null;
  return {
    valor, totalEscopo, brasil: br, motivo,
    noEscopo: ok && valor !== null && totalEscopo ? valor / totalEscopo : null,
    doBrasil: ok && valor !== null && br ? valor / br : null,
  };
}

/** Recorte da URL: "dim:c1|c2;dim2:c3" (somente códigos de categoria agregada). */
export function lerRecorte(s: string): Filtro {
  const f: Filtro = {};
  for (const part of s.split(";")) {
    const [dim, codes] = part.split(":");
    if (dim && codes && /^[a-z_0-9]+$/.test(dim)) f[dim] = codes.split("|").filter(Boolean);
  }
  return f;
}
export function escreverRecorte(f: Filtro): string {
  return Object.entries(f).filter(([, v]) => v.length).map(([k, v]) => `${k}:${v.join("|")}`).join(";");
}
