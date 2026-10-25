import { distribution, facetValue, type FacetFilter } from "./facets";
import type { FacetData, Metric } from "./types";

export interface Participacao {
  /** valor da categoria no escopo */
  v: number | null;
  /** soma de todas as categorias do mesmo cubo no escopo (denominador 1) */
  totalEscopo: number | null;
  /** valor da mesma categoria no Brasil (denominador 2) */
  brasil: number | null;
  /** % da categoria dentro do escopo */
  noEscopo: number | null;
  /** % do escopo no total Brasil da mesma categoria */
  doBrasil: number | null;
  motivoEscopo: string | null;
  motivoBrasil: string | null;
}

/** Participação dupla, sempre no mesmo cubo e na mesma medida. Cobertura parcial, categorias sobrepostas
 *  ou valores bloqueados tornam a proporção N/D, com o motivo. `comEntidade*` = DISTs que têm o tipo de ativo. */
export function participacao(data: FacetData, filtro: FacetFilter, alvo: string, metric: Metric, escopo: Set<number>, brasil: Set<number>,
  comEntidadeEscopo: number, comEntidadeBrasil: number, given?: FacetFilter): Participacao {
  const f = { ...(given ?? {}), ...filtro };
  const cat = facetValue(data, f, metric, escopo);
  const catBr = facetValue(data, f, metric, brasil);
  const dEsc = distribution(data, alvo, metric, escopo, given);
  const dBr = distribution(data, alvo, metric, brasil, given);
  const v = cat.status === "ok" ? cat.v : null;
  const br = catBr.status === "ok" ? catBr.v : null;
  let motivoEscopo: string | null = null, motivoBrasil: string | null = null;
  let totalEscopo: number | null = null;
  if (!dEsc.additive) motivoEscopo = "categorias se sobrepõem neste cubo: não há total único";
  else if (dEsc.covered < comEntidadeEscopo) motivoEscopo = `cubo calculado para ${dEsc.covered} de ${comEntidadeEscopo} distribuidoras do recorte`;
  else if (dEsc.categories.some((c) => c.nd > 0)) motivoEscopo = "há categorias sem valor homologado no recorte";
  else totalEscopo = dEsc.categories.reduce((x, c) => x + (c.v ?? 0), 0);
  if (v === null) motivoEscopo = motivoEscopo ?? "categoria sem valor homologado no recorte";
  if (!dBr.additive) motivoBrasil = "categorias se sobrepõem neste cubo";
  else if (dBr.covered < comEntidadeBrasil) motivoBrasil = `cubo calculado para ${dBr.covered} de ${comEntidadeBrasil} distribuidoras do Brasil`;
  else if (catBr.status !== "ok" || catBr.nd > 0 || br === null) motivoBrasil = "categoria sem valor homologado em todas as distribuidoras";
  if (v === null && !motivoBrasil) motivoBrasil = "categoria sem valor homologado no recorte";
  return {
    v, totalEscopo, brasil: motivoBrasil ? null : br,
    noEscopo: motivoEscopo || !totalEscopo ? null : v! / totalEscopo,
    doBrasil: motivoBrasil || !br ? null : v! / br,
    motivoEscopo, motivoBrasil,
  };
}
