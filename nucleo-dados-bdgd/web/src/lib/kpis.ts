import type { Aggregate, Dataset } from "./dataset";
import type { Metric } from "./types";

export interface KpiDef {
  key: string;
  label: string;
  ent: string | null; // null = composto (consumidores)
  metric: Metric;
  regra: string;
  nota?: string;
}

/** Indicadores do panorama: cada um reporta entidade, métrica, unidade e regra. Grandezas heterogêneas nunca são somadas. */
export const KPIS: KpiDef[] = [
  { key: "uc", label: "Unidades consumidoras", ent: null, metric: "quantidade",
    regra: "Soma, por DIST, da união de COD_ID distintos de UCBT, UCMT e UCAT (as entidades podem compartilhar códigos). DISTs com UC não validadas pela regra v2 ficam N/D." },
  { key: "ssdmt", label: "Rede de média tensão", ent: "SSDMT", metric: "extensao_km", regra: "SUM(COMP)/1000 dos segmentos SSDMT — comprimento declarado na BDGD." },
  { key: "ssdbt", label: "Rede de baixa tensão", ent: "SSDBT", metric: "extensao_km", regra: "SUM(COMP)/1000 dos segmentos SSDBT — comprimento declarado na BDGD." },
  { key: "untrmt", label: "Transformadores de distribuição", ent: "UNTRMT", metric: "quantidade", regra: "COUNT(*) de unidades transformadoras de média tensão (UNTRMT)." },
  { key: "eqtrmt", label: "Potência de transformação MT", ent: "EQTRMT", metric: "potencia_kva",
    regra: "SUM do código POT_NOM de EQTRMT traduzido pela tabela DDA TPOTAPRT (kVA).", nota: "Não somar com UNTRMT: as duas entidades descrevem a mesma população." },
  { key: "ugbt", label: "Geração conectada em BT", ent: "UGBT", metric: "quantidade", regra: "COUNT(*) de unidades geradoras de baixa tensão.", nota: "Potência instalada N/D: POT_INST não homologado." },
];

export const SECONDARY: KpiDef[] = [
  { key: "ssdat", label: "Rede de alta tensão", ent: "SSDAT", metric: "extensao_km", regra: "SUM(COMP)/1000 de SSDAT." },
  { key: "sub", label: "Subestações", ent: "SUB", metric: "quantidade", regra: "COUNT(*) de SUB." },
  { key: "ponnot", label: "Estruturas (pontos notáveis)", ent: "PONNOT", metric: "quantidade", regra: "COUNT(*) de PONNOT." },
  { key: "pip", label: "Pontos de iluminação pública", ent: "PIP", metric: "quantidade", regra: "COUNT(*) de PIP." },
  { key: "ugmt", label: "Geração conectada em MT", ent: "UGMT", metric: "quantidade", regra: "COUNT(*) de UGMT." },
  { key: "ctmt", label: "Circuitos de média tensão", ent: "CTMT", metric: "quantidade", regra: "COUNT(*) de CTMT." },
];

export const ALL_KPIS = [...KPIS, ...SECONDARY];

export function kpiValue(ds: Dataset, k: KpiDef, dists: number[]): Aggregate {
  return k.ent === null ? ds.consumidores(dists) : ds.aggregate(dists, k.ent, k.metric);
}

export function kpiPerDist(ds: Dataset, k: KpiDef, dist: number): number | null {
  return kpiValue(ds, k, [dist]).v;
}
