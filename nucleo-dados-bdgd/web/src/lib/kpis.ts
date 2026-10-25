import { INDICADOR_PADRAO, INDICADORES, type Indicador } from "./catalogo";
import type { Aggregate, Dataset } from "./dataset";

/** Indicadores do panorama vêm do catálogo semântico (nome de negócio + explicação + cálculo técnico sob demanda). */
export type KpiDef = Indicador;
export const KPIS: KpiDef[] = INDICADOR_PADRAO.map((id) => INDICADORES.find((i) => i.id === id)!);
export const ALL_KPIS: KpiDef[] = INDICADORES;

export function kpiValue(ds: Dataset, k: Pick<Indicador, "ent" | "metric">, dists: number[]): Aggregate {
  return k.ent === null ? ds.consumidores(dists) : ds.aggregate(dists, k.ent, k.metric);
}

export function kpiPerDist(ds: Dataset, k: Pick<Indicador, "ent" | "metric">, dist: number): number | null {
  return kpiValue(ds, k, [dist]).v;
}

/** Texto de cobertura humano: quantas distribuidoras entraram e quantas ficaram sem valor. */
export function coberturaTexto(a: Aggregate) {
  if (a.total <= 1) return a.n ? "Valor reconciliado com o GDB de origem" : "Sem valor homologado nesta distribuidora";
  const partes = [`${a.n} de ${a.total} distribuidoras com valor`];
  if (a.nd) partes.push(`${a.nd} sem valor homologado`);
  if (a.ausentes) partes.push(`${a.ausentes} sem esse tipo de ativo no cadastro`);
  return partes.join(" · ");
}

export interface NdItem { dist: number; sigla: string; motivo: string }

/** Quais distribuidoras do recorte ficaram sem valor homologado e por quê (motivo do pacote, nunca inventado). */
export function ndDetalhe(ds: Dataset, k: Pick<Indicador, "ent" | "metric">, dists: number[]): NdItem[] {
  const out: NdItem[] = [];
  for (const d of dists) {
    const sigla = ds.dist(d)?.sigla.replaceAll("_", " ") ?? `DIST ${d}`;
    if (k.ent === null) {
      const bad = ["UCBT", "UCMT", "UCAT"].map((e) => ds.cell(d, e, "quantidade")).find((c) => c && c.v === null);
      const u = ds.raw.complementares["uc_uniao_distinta"]?.[String(d)]?.["UC*"];
      if (bad) out.push({ dist: d, sigla, motivo: bad.motivo || "Quantidade de consumidores não homologada" });
      else if (!u || u[0] === null) out.push({ dist: d, sigla, motivo: "União de códigos de consumidor indisponível" });
      continue;
    }
    const c = ds.cell(d, k.ent, k.metric);
    if (c && (c.v === null || c.status === "b")) out.push({ dist: d, sigla, motivo: c.motivo || "Valor não homologado" });
  }
  return out;
}

export function ndFrase(n: number) {
  return n === 1 ? "1 distribuidora sem valor homologado" : `${n} distribuidoras sem valor homologado`;
}
