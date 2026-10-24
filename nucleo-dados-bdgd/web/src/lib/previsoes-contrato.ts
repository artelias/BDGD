/** Contrato de publicação do Motor de Expansão Elétrica.
 * Nunca inferir zero a partir de ausência ou projetar com séries não homologadas.
 */
export type Perspectiva = "ativos" | "infraestrutura" | "conectividade";
export type ResultadoMotor = "necessidade_tecnica" | "estoque_fisico" | "capex";
export type EstadoSerie = "observado" | "zero_verificado" | "ausente" | "nao_homologado" | "nao_aplicavel" | "ruptura";
export type EstadoModelo = "nao_treinado" | "exploratorio" | "validado" | "reprovado";
export type ModoResultado = "historico" | "simulacao_condicional" | "previsao_validada";

export interface SerieFisica {
  dist: number;
  ano: number;
  perimetroId: string;
  conceitoId: string;
  metrica: string;
  unidade: string;
  regraVersao: string;
  estado: EstadoSerie;
  valor: number | null;
  fonte: string;
  dataBase: string;
  cobertura: number | null;
  perimetroBridgeId: string | null;
}

export interface EvidenciaValidacao {
  protocoloId: string;
  versaoCodigo: string;
  dataCorteTreino: string;
  numeroObservacoes: number;
  numeroOrigensTeste: number;
  baselineId: string;
  metricaErro: "mae" | "rmse" | "wape";
  erroModelo: number;
  erroBaseline: number;
  coberturaHistorica: number;
  fontesHomologadas: boolean;
  perimetroReconciliado: boolean;
}

export interface ResultadoPrevisao {
  modo: ModoResultado;
  perspectiva: Perspectiva;
  resultado: ResultadoMotor;
  dist: number | "brasil";
  conceitoId: string;
  metrica: string;
  unidade: string;
  anoOrigem: number;
  anoAlvo: number;
  perimetroId: string;
  valor: number | null;
  limiteInferior: number | null;
  limiteSuperior: number | null;
  modeloId: string | null;
  modeloEstado: EstadoModelo;
  versaoDados: string;
  hipoteseCenario?: string;
  evidenciaValidacao?: EvidenciaValidacao;
}

/** Falha fechada: sem evidência de validação não há previsão publicável. */
export function previsaoPublicavel(p: ResultadoPrevisao): boolean {
  if (p.modo !== "previsao_validada" || p.modeloEstado !== "validado") return false;
  if (!p.modeloId?.trim() || !p.versaoDados?.trim() || !p.perimetroId?.trim() || !p.conceitoId?.trim() || !p.unidade?.trim() || !p.metrica?.trim()) return false;
  if (typeof p.dist !== "number" && p.dist !== "brasil") return false;
  if (typeof p.dist === "number" && (!Number.isInteger(p.dist) || p.dist <= 0)) return false;
  const ev = p.evidenciaValidacao;
  if (!ev || !ev.protocoloId?.trim() || !ev.versaoCodigo?.trim() || !ev.baselineId?.trim()) return false;
  if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(ev.dataCorteTreino) || !Number.isFinite(Date.parse(ev.dataCorteTreino))) return false;
  if (!Number.isInteger(ev.numeroObservacoes) || ev.numeroObservacoes < 5) return false;
  if (!Number.isInteger(ev.numeroOrigensTeste) || ev.numeroOrigensTeste < 2) return false;
  if (!["mae", "rmse", "wape"].includes(ev.metricaErro)) return false;
  if (!Number.isFinite(ev.erroModelo) || ev.erroModelo < 0 || !Number.isFinite(ev.erroBaseline) || ev.erroBaseline <= 0 || ev.erroModelo >= ev.erroBaseline) return false;
  if (!Number.isFinite(ev.coberturaHistorica) || ev.coberturaHistorica !== 1) return false;
  if (!ev.fontesHomologadas || !ev.perimetroReconciliado) return false;
  if (!Number.isInteger(p.anoOrigem) || !Number.isInteger(p.anoAlvo) || p.anoAlvo <= p.anoOrigem) return false;
  if (p.valor === null || !Number.isFinite(p.valor)) return false;
  if (p.limiteInferior !== null && (!Number.isFinite(p.limiteInferior) || p.limiteInferior > p.valor)) return false;
  if (p.limiteSuperior !== null && (!Number.isFinite(p.limiteSuperior) || p.limiteSuperior < p.valor)) return false;
  if (p.limiteInferior !== null && p.limiteSuperior !== null && p.limiteInferior > p.limiteSuperior) return false;
  if (p.valor < 0 || (p.limiteInferior !== null && p.limiteInferior < 0)) return false;
  return true;
}

/** A ausência de uma célula nunca é convertida em zero verdadeiro. */
export function valorObservado(s: SerieFisica): number | null {
  if (s.estado !== "observado" && s.estado !== "zero_verificado") return null;
  if (s.valor === null || !Number.isFinite(s.valor)) return null;
  if (s.estado === "zero_verificado" && s.valor !== 0) return null;
  return s.valor;
}
