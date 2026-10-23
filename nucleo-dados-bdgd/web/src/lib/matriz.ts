import type { Dataset } from "./dataset";
import { toCSV } from "./format";
import type { Distribuidora, Entidade, Metric } from "./types";

/** Medidas de negócio da matriz. Registros e COD_ID distintos ficam só no CSV técnico e na metodologia. */
export type Modo = "principal" | "quantidade" | "extensao_km" | "potencia_kva";
export const MODOS: Array<{ value: Modo; label: string; title: string }> = [
  { value: "principal", label: "Medida principal", title: "km para redes, kVA para transformação e quantidade para os demais" },
  { value: "quantidade", label: "Quantidade", title: "Quantidade homologada (consumidores: códigos distintos validados)" },
  { value: "extensao_km", label: "Extensão", title: "Comprimento de rede em km (somente tipos com extensão)" },
  { value: "potencia_kva", label: "Potência", title: "Potência nominal em kVA (somente tipos com potência homologada)" },
];
export const metricaDe = (e: Entidade, m: Modo): Metric => (m === "principal" ? e.metrica : m);

/** A medida existe para o tipo de ativo em ao menos uma distribuidora (nunca inventa uma coluna vazia). */
export function aplicavel(ds: Dataset, e: Entidade, m: Modo): boolean {
  if (m === "principal" || m === "quantidade") return true;
  if (e.metrica === m) return true;
  return ds.dists.some((d) => { const c = ds.cell(d.dist, e.id, m); return !!c && c.v !== null; });
}

export interface FiltroMatriz { grupo: string; dists: number[]; ufs: string[] }

export function filtraDists(ds: Dataset, f: FiltroMatriz): Distribuidora[] {
  return ds.dists.filter((d) =>
    (f.grupo === "todos" || (f.grupo === "nao_confirmado" ? d.grupo_status !== "verificado" : d.grupo === f.grupo && d.grupo_status === "verificado")) &&
    (f.dists.length === 0 || f.dists.includes(d.dist)) &&
    (f.ufs.length === 0 || d.ufs.some((u) => f.ufs.includes(u))));
}

/** CSV longo do recorte exato: uma linha por distribuidora × tipo de ativo, com regra, versão, cobertura e status. */
export function csvRecorte(ds: Dataset, rows: Distribuidora[], ents: Entidade[], m: Modo): string {
  const ST: Record<string, string> = { a: "aprovado", l: "alerta", b: "bloqueado", e: "em_validacao", n: "nao_aplicavel" };
  const header = ["data_base", "versao", "dist", "sigla", "grupo_economico", "grupo_status", "entidade", "tipo_de_ativo", "metrica", "unidade", "valor", "status", "motivo", "regra", "cobertura_recorte"];
  const dists = rows.map((d) => d.dist);
  const body: Array<Array<string | number | null>> = [];
  for (const e of ents) {
    const met = metricaDe(e, m);
    const a = ds.aggregate(dists, e.id, met);
    const cob = `${a.n}/${a.total} distribuidoras com valor`;
    const un = met === "extensao_km" ? "km" : met === "potencia_kva" ? "kVA" : "itens";
    for (const d of rows) {
      const c = ds.cell(d.dist, e.id, met);
      body.push(["2025-12-31", ds.raw.release.release_id, d.dist, d.sigla, d.grupo, d.grupo_status, e.id, e.nome, met, un, c ? c.v : null,
        c ? (c.v === null ? "nd" : ST[c.status] ?? c.status) : "entidade_ausente", c ? c.motivo : "Tipo de ativo inexistente no GDB desta distribuidora", e.regra, cob]);
    }
  }
  return toCSV(header, body);
}
