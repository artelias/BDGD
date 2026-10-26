export interface MetricasMotor { n: number; mae: number | null; rmse: number | null; wape: number | null; vies: number | null }
export interface ObjetivoMotor { objetivo_id: string; nome: string; familia: string; metrica: string; unidade: string; padrao: boolean; series: number; series_elegiveis: number; motivo: string | null }
export interface ModeloMotor { modelo: string; metricas: MetricasMotor; auditoria: MetricasMotor; motivo: string | null; futuro: number[] }
export interface SerieMotor {
  DIST: string; empresa: string; objetivo_id: string; metrica: string; unidade: string;
  territorio: { nivel: string; id: string }; status: string; motivos: string[]; observacoes_treino: number;
  modelo_selecionado: string | null; validacao: string | null;
  historico: { ano: number; valor: number | null; estado: string; variacao_liquida: number | null }[]; modelos: ModeloMotor[];
}
export interface ResumoMotor {
  schema_version: string; experiment_id: string; dataset_version: string; dataset_sha256: string;
  source_sha256: string; code_version: string; as_of: string; base_year: number; horizontes: number[];
  sintetico: boolean; previsao_validada: false; objetivos_catalogados: number; series_elegiveis: number;
  objetivos: ObjetivoMotor[]; series: SerieMotor[]; limites: string[];
}
const record = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null;
const num = (x: unknown): x is number => typeof x === "number" && Number.isFinite(x);

/** Recusa schemas desconhecidos, dados sintéticos e alegações de homologação automática. */
export function parseResumoMotor(value: unknown): ResumoMotor {
  if (!record(value) || value.schema_version !== "experimento-bdgd-1" || value.sintetico !== false || value.previsao_validada !== false ||
    typeof value.experiment_id !== "string" || typeof value.dataset_sha256 !== "string" || typeof value.code_version !== "string" ||
    typeof value.source_sha256 !== "string" || typeof value.dataset_version !== "string" || typeof value.as_of !== "string" ||
    !num(value.objetivos_catalogados) || !num(value.series_elegiveis) ||
    !Array.isArray(value.objetivos) || !Array.isArray(value.series) || !Array.isArray(value.horizontes) ||
    !value.horizontes.every((y) => num(y) && Number.isInteger(y)) || !num(value.base_year) ||
    !Array.isArray(value.limites) || !value.limites.every((s) => typeof s === "string")) throw Error("Contrato do motor universal inválido ou não publicável.");
  const keys = new Map<string, string>();
  for (const t of value.objetivos) {
    if (!record(t) || [t.objetivo_id, t.nome, t.familia, t.metrica, t.unidade].some((x) => typeof x !== "string")) throw Error("Objetivo inválido.");
    const key = `${t.objetivo_id}|${t.metrica}`;
    if (keys.has(key)) throw Error("Objetivo duplicado.");
    keys.set(key, String(t.unidade));
  }
  const seriesKeys = new Set<string>();
  for (const s of value.series) {
    if (!record(s) || typeof s.DIST !== "string" || !keys.has(`${s.objetivo_id}|${s.metrica}`) || keys.get(`${s.objetivo_id}|${s.metrica}`) !== s.unidade ||
      !record(s.territorio) || !Array.isArray(s.historico) || !Array.isArray(s.modelos) || !Array.isArray(s.motivos)) throw Error("Série inválida.");
    const key = `${s.DIST}|${s.objetivo_id}|${s.metrica}|${s.territorio.nivel}|${s.territorio.id}`;
    if (seriesKeys.has(key)) throw Error("Séries ambíguas; selecione um contrato de perímetro e regra único.");
    seriesKeys.add(key);
    for (const h of s.historico) if (!record(h) || !num(h.ano) || !(h.valor === null || num(h.valor) && h.valor >= 0) || typeof h.estado !== "string") throw Error("Histórico inválido.");
    for (const m of s.modelos) if (!record(m) || typeof m.modelo !== "string" || !record(m.metricas) || !record(m.auditoria) ||
      !Array.isArray(m.futuro) || m.futuro.some((n) => !num(n) || n < 0) || m.futuro.length !== 0 && m.futuro.length !== value.horizontes.length) throw Error("Modelo ou projeção inválida.");
  }
  return value as unknown as ResumoMotor;
}

export function exportarExperimentoMotor(data: ResumoMotor, serie: SerieMotor, modelo: ModeloMotor | undefined) {
  return JSON.stringify({ schema_version: data.schema_version, experiment_id: data.experiment_id,
    dataset_version: data.dataset_version, dataset_sha256: data.dataset_sha256, source_sha256: data.source_sha256,
    code_version: data.code_version, corte: data.as_of, previsao_validada: false,
    natureza: "simulacao_condicional", intervalos: null, serie, modelo,
    natureza_alvo: "estoque_fisico", necessidade_expansao: null,
    interpretacao_variacao: "Diferença líquida de estoques não identifica entradas, baixas, substituições ou necessidade de expansão",
    horizontes: data.horizontes, limites: data.limites }, null, 2);
}
