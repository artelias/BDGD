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
}

/** Falha fechada: sem evidência de validação não há previsão publicável. */
export function previsaoPublicavel(p: ResultadoPrevisao): boolean {
  if (p.modo !== "previsao_validada" || p.modeloEstado !== "validado") return false;
  if (!p.modeloId || !p.versaoDados || !p.perimetroId || !p.conceitoId || !p.unidade) return false;
  if (!Number.isInteger(p.anoOrigem) || !Number.isInteger(p.anoAlvo) || p.anoAlvo <= p.anoOrigem) return false;
  if (p.valor === null || !Number.isFinite(p.valor)) return false;
  if (p.limiteInferior !== null && (!Number.isFinite(p.limiteInferior) || p.limiteInferior > p.valor)) return false;
  if (p.limiteSuperior !== null && (!Number.isFinite(p.limiteSuperior) || p.limiteSuperior < p.valor)) return false;
  if (p.limiteInferior !== null && p.limiteSuperior !== null && p.limiteInferior > p.limiteSuperior) return false;
  if (p.resultado !== "capex" && p.valor < 0) return false;
  return true;
}

/** A ausência de uma célula nunca é convertida em zero verdadeiro. */
export function valorObservado(s: SerieFisica): number | null {
  if (s.estado !== "observado" && s.estado !== "zero_verificado") return null;
  if (s.valor === null || !Number.isFinite(s.valor)) return null;
  if (s.estado === "zero_verificado" && s.valor !== 0) return null;
  return s.valor;
}
