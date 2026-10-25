import type { CelulaHom, PontoHom } from "./homologacao";
import type { Serie } from "./evolucao";
import type { EstadoSerie } from "./previsoes-contrato";

export type EstadoContrato = [dist: number, ano: number, estado: EstadoSerie, causa: string, naoSomar: boolean];
export interface EstadosContrato {
  commitOrigem: string;
  blobShaOrigem: string;
  celulas: Record<string, EstadoContrato[]>;
}

/** O contrato distingue ausência de publicação de não aplicabilidade por sucessão.
 * Não altera a matriz de homologação nem transforma zero técnico em aprovação humana. */
export function aplicarEstadosContrato(celulas: CelulaHom[], contrato: EstadosContrato, ativo: string): CelulaHom[] {
  const indice = new Map(celulas.map((c) => [`${c[0]}|${c[1]}`, c]));
  return (contrato.celulas[ativo] ?? []).map(([dist, ano, estado, , naoSomar]) => {
    const c = indice.get(`${dist}|${ano}`) ?? [dist, ano, null, "s", 0, "N", -1, 0];
    const valido = (estado === "observado" || estado === "zero_verificado") && c[3] === "v";
    return [dist, ano, valido ? c[2] : null,
      estado === "nao_aplicavel" ? "n" : valido ? "v" : estado === "nao_homologado" ? "x" : c[3] === "v" ? "s" : c[3],
      c[4], c[5], c[6], c[7] | (naoSomar ? 4 : 0)] as CelulaHom;
  });
}

export function pontosContrato(serie: Serie, contrato: EstadosContrato, ativo: string, dist: number): Serie {
  const estados = new Map((contrato.celulas[ativo] ?? []).filter((c) => c[0] === dist).map((c) => [c[1], c]));
  return { ...serie, pontos: serie.pontos.map((p) => {
    const c = estados.get(p.ano);
    if (!c) return { ...p, v: null, estado: "ausente" };
    return { ...p, estado: c[2], motivo: [(p as PontoHom).motivo, c[3]].filter(Boolean).join(" · ") };
  }) };
}

export function lacunasNacionais(contrato: EstadosContrato, ativo: string, ano: number): number {
  return (contrato.celulas[ativo] ?? []).filter((c) => c[1] === ano && !c[4] &&
    !["observado", "zero_verificado", "nao_aplicavel"].includes(c[2])).length;
}
