/** Contrato público do módulo de Confiabilidade (gerado por confiabilidade/publicar.py, contrato "confiabilidade-1"). */

export type EstadoDado = "OBSERVADO_OFICIAL" | "RECONSTRUIDO_VALIDADO" | "DERIVADO_EXPLORATORIO" | "DADO_INDISPONIVEL" | "DEMONSTRATIVO_SINTETICO";
export type Indicador = "dec" | "fec";
export type TipoMetrica = "contagem" | "continua" | "razao" | "pct";

export interface MetricaDef { id: string; nome: string; unidade: string; tipo: TipoMetrica; grupo: string; definicao: string }
/** Métricas de infraestrutura de um conjunto num ano; ausência é null, nunca zero. */
export type Infra = Record<string, number | null>;

export interface AnualDist { dec: number | null; fec: number | null; completo: boolean; completo_dec?: boolean; completo_fec?: boolean; nuc: number; conjuntos: number; acima_dec: number; acima_fec: number; com_infra: number; estado: EstadoDado; regra: string }

export interface DistResumo {
  dist: number; nome: string; sigla: string; agente_aneel: string; grupo: string | null; grupo_nome: string | null; ufs: string[];
  bbox: [number, number, number, number] | null; anual: Record<string, AnualDist>; anos_infra: number[]; geo: boolean; conjuntos: number; conjuntos_com_geo: number;
}

export interface Indice {
  contrato: string; gerado_em: string; anos: number[]; demonstrativo: boolean;
  estados: { continuidade: EstadoDado; infraestrutura: EstadoDado; distribuidora: EstadoDado };
  fontes: {
    continuidade: { nome: string; url: string; licenca: string; gerado_pela_aneel_em: string; recursos: Record<string, { sha256?: string; last_modified?: string }> };
    infraestrutura: { nome: string; nota: string };
    geometria: { nome: string; tipo: string; data_base: string };
  };
  metricas: MetricaDef[]; supressao_k: number; tolerancia_reconstrucao: { relativa: number; absoluta: number };
  totais: Record<string, number>; distribuidoras: DistResumo[];
  auditoria: { conflitos_de_conjunto: unknown[]; aneel_sem_distribuidora: Record<string, number>; bdgd_fora_da_aneel: Record<string, number[]>; codigo_de_outro_agente?: unknown[] };
}

export interface Componentes { ip: number | null; ind: number | null; xp: number | null; xn: number | null; exp: number | null }
export interface Reconstrucao { dec: number | null; fec: number | null; dec_bdgd: number | null; fec_bdgd: number | null; dif_dec: number | null; dif_fec: number | null; cobertura: number | null; estado: EstadoDado; denominador: string; meses_dec?: number; meses_fec?: number }

export interface BlocoAno {
  dec: number | null; fec: number | null; ld: number | null; lf: number | null; nuc: number | null; nuc_dez: number | null; meses_dec: number; meses_fec: number;
  m: { dec: Array<number | null>; fec: Array<number | null>; nuc: Array<number | null> };
  comp: { dec: Componentes; fec: Componentes };
  estado: EstadoDado; infra: Infra | null; infra_estado?: EstadoDado; infra_motivo?: string; rec: Reconstrucao | null; alertas: string[];
}

export interface Alimentador {
  ctmt: string; nome: string | null; sub: string | null; sub_nome: string | null; ten: string | null; km_mt: number | null; km_bt: number | null; km_mt_alimentador: number | null;
  predominante: boolean; uc_bt: number | null; uc_mt: number | null; uc_suprimido: boolean; trafos: number | null; sec: number | null; religadores: number | null; telecomandadas: number | null;
}

export interface Conjunto {
  c: number; n: string; geo: boolean; area_km2: number | null; centro: [number, number] | null;
  a: Record<string, BlocoAno>; al: { ano: number; lista: Alimentador[] } | null;
}

export interface FonteBdgd { item: string; sha256_gdb: string; data_extracao?: string | null; ausencias: string[]; reconciliacao: Record<string, number> }
export interface DistDoc { contrato: string; dist: number; nome: string; agente_aneel: string; anual: Record<string, AnualDist>; fontes_bdgd: Record<string, FonteBdgd>; geo: boolean; conjuntos: Conjunto[] }

/** Tabela nacional de um ano: uma linha por conjunto, em colunas nomeadas por `campos`. */
export interface NacionalAno { ano: number; campos: string[]; linhas: Array<Array<number | string | null>> }

export interface GeoMeta { fonte: string; data_base: string; tipo: string; tolerancia_graus: number }

/** Resultado do estudo estatístico (confiabilidade/estatistica.py). Sem dados suficientes, `resultados` fica vazio com o motivo. */
export interface Associacao {
  variavel: string; n: number; spearman: number | null; ic95: [number, number] | null; p: number | null;
  parcial: number | null; parcial_ic95: [number, number] | null; dentro_dist: number | null; dentro_dist_ic95: [number, number] | null; estavel_por_ano: boolean | null; por_ano: Record<string, number | null>;
}
export interface ModeloResumo { modelo: string; r2_fora: number | null; mae_fora: number | null; n: number; grupos: number; nota: string }
export interface Importancia { variavel: string; importancia: number; desvio: number }
export interface EstudoAlvo {
  alvo: Indicador; n: number; distribuidoras: number; anos: number[]; associacoes: Associacao[]; modelos: ModeloResumo[]; importancias: Importancia[];
  coeficientes: Array<{ variavel: string; beta: number; ic95: [number, number] }>;
  variacao: Array<{ variavel: string; n: number; spearman: number | null; ic95: [number, number] | null }>;
}
export interface Hipotese { id: string; enunciado: string; veredito: "COMPATIVEL" | "NAO_SUSTENTADA" | "INCONCLUSIVA" | "SEM_DADOS"; evidencia: string }
export interface ReferenciaAjustada { ano: number; alvo: Indicador; modelo: string; r2_fora: number | null; campos: string[]; linhas: Array<Array<number | string | null>> }
export interface Fatores {
  contrato: string; gerado_em: string; estado: EstadoDado; demonstrativo: boolean; metodo: string; limitacoes: string[];
  amostra: { conjunto_anos: number; conjuntos: number; distribuidoras: number; anos: number[]; excluidos: Record<string, number> };
  alvos: EstudoAlvo[]; hipoteses: Hipotese[];
  /** referência ajustada por contexto: observado × esperado (fora da amostra) por conjunto, ano mais recente */
  referencia: ReferenciaAjustada | null;
  /** uma referência por indicador (DEC e FEC); `referencia` repete a primeira por compatibilidade */
  referencias?: ReferenciaAjustada[];
}
