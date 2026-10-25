import { gerarCenarioExploratorio, type MetodoCenario, type ResultadoCenario } from "./motor-cenarios";
import type { SerieFisica } from "./previsoes-contrato";

/** Adapter para output-historico/contrato-integracao/esquema.json (contrato-nacional-1.0.0). */
export interface LinhaContratoNacional extends Omit<SerieFisica, "valor" | "cobertura" | "perimetroBridgeId"> {
  valor: number | null | "";
  cobertura: number | null | "";
  perimetroBridgeId: string | null | "";
  fonte_homologada: boolean | "true" | "false";
  status_homologacao: string;
  ruptura_desde_ano_anterior: boolean | "true" | "false";
  nao_somar_em_agregados: boolean | "true" | "false";
  tipo_lacuna?: string;
}
const sim = (v: boolean | "true" | "false") => v === true || v === "true";
export interface ResultadoIntegracao extends ResultadoCenario {
  bloqueiosContrato: string[];
  fontesHomologadas: boolean;
  publicavelComoPrevisao: false;
}
export function simularContratoNacional(
  linhas: readonly LinhaContratoNacional[],
  anoFinal = 2030,
  metodo: MetodoCenario = "persistencia",
): ResultadoIntegracao {
  const bloqueios: string[] = [];
  if (linhas.some((p) => sim(p.nao_somar_em_agregados))) bloqueios.push("NAO_SOMAR_EM_AGREGADOS");
  if (linhas.some((p) => sim(p.ruptura_desde_ano_anterior))) bloqueios.push("RUPTURA_TEMPORAL");
  const fontesHomologadas = linhas.length > 0 && linhas.every((p) => sim(p.fonte_homologada) && p.status_homologacao === "HOMOLOGADO");
  const convertidas: SerieFisica[] = linhas.map((p) => ({
    dist: p.dist, ano: p.ano, perimetroId: p.perimetroId, conceitoId: p.conceitoId,
    metrica: p.metrica, unidade: p.unidade, regraVersao: p.regraVersao,
    estado: p.estado, valor: p.valor === "" ? null : p.valor, fonte: p.fonte,
    dataBase: p.dataBase, cobertura: p.cobertura === "" ? null : p.cobertura,
    perimetroBridgeId: p.perimetroBridgeId === "" ? null : p.perimetroBridgeId,
  }));
  // Séries que atravessam ruptura ou incluem predecessora já contida não podem ser projetadas.
  const resultado = bloqueios.length
    ? gerarCenarioExploratorio([], anoFinal, metodo)
    : gerarCenarioExploratorio(convertidas, anoFinal, metodo);
  return {
    ...resultado,
    diagnostico: bloqueios.length
      ? { ...resultado.diagnostico, elegivel: false, motivos: [...resultado.diagnostico.motivos, ...bloqueios], observacoes: linhas.length, anos: linhas.map((p) => p.ano) }
      : resultado.diagnostico,
    bloqueiosContrato: bloqueios,
    fontesHomologadas,
    publicavelComoPrevisao: false,
  };
}
