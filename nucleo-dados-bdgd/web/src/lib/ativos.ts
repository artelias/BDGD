import type { Recorte } from "./cubo";
import type { Aggregate, Dataset } from "./dataset";
import type { AtivoCfg, ConceitosCatalogo, MedidaConceito, MenuItem, Metric } from "./types";

/** Catálogo semântico R3 (vem do pacote: conceitos/catalogo.json -> index.json). */
export function catalogo(ds: Dataset): ConceitosCatalogo | null { return ds.raw.conceitos ?? null; }
export function ativo(ds: Dataset, id: string): AtivoCfg | undefined { return ds.raw.conceitos?.ativos.find((a) => a.id === id); }
export function ativos(ds: Dataset): AtivoCfg[] { return ds.raw.conceitos?.ativos ?? []; }
export function itensMenu(ds: Dataset): MenuItem[] { return (ds.raw.conceitos?.menu ?? []).flatMap((g) => g.itens); }
export function itemMenu(ds: Dataset, id: string): MenuItem | undefined { return itensMenu(ds).find((i) => i.id === id); }

export const UNIDADE: Record<MedidaConceito, string> = { quantidade: "itens", extensao_km: "km", potencia_kva: "kVA" };
export const ROTULO_MEDIDA: Record<MedidaConceito, string> = { quantidade: "Quantidade", extensao_km: "Extensão", potencia_kva: "Potência" };
/** a camada de formatação existente usa as mesmas chaves de métrica */
export const asMetric = (m: MedidaConceito): Metric => m;

/** Recorte-base de um ativo ou item de menu (o que define a população). */
export function recorteDe(x: { filtro?: AtivoCfg["filtro"]; excluir?: AtivoCfg["filtro"] }): Recorte {
  return { filtro: { ...(x.filtro ?? {}) }, excluir: { ...(x.excluir ?? {}) } };
}

/** Soma do total pré-calculado do ativo entre DISTs (mesma regra do Dataset.aggregate: N/D sai da soma e é contado). */
export function totalAtivo(ds: Dataset, id: string, dists: number[], medida?: MedidaConceito): Aggregate {
  const a = ativo(ds, id);
  const m = medida ?? a?.medida ?? "quantidade";
  const rows = ds.raw.ativosTotais?.[id]?.[m] ?? [];
  const byDist = new Map(rows.map((r) => [r[0], r]));
  let v = 0, n = 0, nd = 0, ausentes = 0, alerta = 0;
  for (const d of dists) {
    const r = byDist.get(d);
    if (!r || r[2] === "n") { ausentes++; continue; }
    if (r[1] === null || r[2] === "b") { nd++; continue; }
    v += r[1]; n++;
    if (r[2] === "l") alerta++;
  }
  return { v: n ? v : null, n, nd, ausentes, total: dists.length, alerta, partial: nd > 0 };
}

export function statusAtivo(ds: Dataset, id: string, dist: number, medida?: MedidaConceito) {
  const a = ativo(ds, id);
  const r = ds.raw.ativosTotais?.[id]?.[medida ?? a?.medida ?? "quantidade"]?.find((x) => x[0] === dist);
  return r ? { v: r[1], status: r[2], motivo: r[3] } : null;
}
