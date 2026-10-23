import { INDICADORES, type Indicador } from "./catalogo";
import type { Aggregate, Dataset } from "./dataset";
import { kpiValue } from "./kpis";

/** Panorama R3: somente contratos de exibição; não altera a semântica da Matriz/Explorar. */
export type PanoramaKpi = Indicador & { tuc?: string; fontesEq?: string[] };

const original = (id: string): PanoramaKpi => {
  const k = INDICADORES.find((i) => i.id === id);
  if (!k) throw new Error(`Indicador do catálogo ausente: ${id}`);
  return k;
};
const equipamento = (id: string, nome: string, tuc: string, fontesEq: string[], texto: string): PanoramaKpi => ({
  id, nome, tuc, fontesEq, conceito: "transformadores", ent: fontesEq[0], metric: "quantidade",
  resumo: texto,
  explicacao: `${texto} Classificação patrimonial pelo código TUC do equipamento; instalações físicas vinculadas não são somadas novamente.`,
  tecnico: `SUM(equipamentos) para TUC=${tuc} no cubo de vínculos TUC, por DIST e ${fontesEq.join("+")}; validação do total TUC contra COUNT(*) de cada EQ*; sem somar UN*.`,
});

export const PANORAMA_KPIS: PanoramaKpi[] = [
  original("uc"), original("ssdmt"), original("ssdbt"), original("ssdat"),
  equipamento("trdist565", "Transformadores de distribuição", "565", ["EQTRMT", "EQTRAT"], "Quantidade de equipamentos classificados na TUC 565."),
  equipamento("trforca570", "Transformadores de força", "570", ["EQTRMT", "EQTRAT"], "Quantidade de equipamentos classificados na TUC 570."),
  original("sub"),
  { ...original("ctmt"), id: "alimentadores", nome: "Alimentadores", resumo: "Circuitos de média tensão registrados na BDGD.", explicacao: "Contagem dos circuitos CTMT da distribuidora. Não representa circuitos de alta tensão.", tecnico: "COUNT(*) de CTMT, por DIST." },
  original("eqme"), original("pip"),
];
export const PANORAMA_IDS = PANORAMA_KPIS.map((k) => k.id);
export const PANORAMA_PRESETS = [
  { id: "principais", nome: "Dez indicadores", ids: PANORAMA_IDS },
  { id: "redes", nome: "Redes", ids: ["ssdmt", "ssdbt", "ssdat"] },
  { id: "transformadores", nome: "Transformação", ids: ["trdist565", "trforca570", "sub", "alimentadores"] },
  { id: "outros", nome: "Outros ativos", ids: ["uc", "eqme", "pip"] },
];
export const panoramaIndicador = (id: string) => PANORAMA_KPIS.find((k) => k.id === id);

function somaTuc(ds: Dataset, k: PanoramaKpi, dists: number[]): Aggregate {
  const cubo = ds.raw.vinculosTuc;
  let v = 0, n = 0, nd = 0, alerta = 0;
  for (const dist of dists) {
    let total = 0, valido = Boolean(cubo), comAlerta = false;
    for (const fonte of k.fontesEq ?? []) {
      const cell = ds.cell(dist, fonte, "quantidade");
      if (!cell || cell.v === null || !["a", "l"].includes(cell.status)) { valido = false; break; }
      if (cell.status === "l") comAlerta = true;
      const linhas = cubo?.rows.filter((r) => r[0] === dist && r[1] === fonte) ?? [];
      const inventario = linhas.reduce((acc, r) => acc + r[3], 0);
      // Códigos não classificados continuam no denominador, nunca migram para 565/570.
      if (inventario !== cell.v) { valido = false; break; }
      total += linhas.filter((r) => r[2] === k.tuc).reduce((acc, r) => acc + r[3], 0);
    }
    if (!valido) { nd++; continue; }
    v += total; n++;
    if (comAlerta) alerta++;
  }
  return { v: n ? v : null, n, nd, ausentes: 0, total: dists.length, alerta, partial: nd > 0 };
}

/** Falha fechada: um subconjunto de empresas não é rotulado como total do Brasil/grupo. */
export function panoramaValue(ds: Dataset, k: PanoramaKpi, dists: number[]): Aggregate {
  const a = k.tuc ? somaTuc(ds, k, dists) : kpiValue(ds, k, dists);
  if (a.nd > 0 || a.ausentes > 0 || a.total === 0) return { ...a, v: null, partial: true };
  return a;
}
