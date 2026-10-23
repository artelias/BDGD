/** Tipos do pacote publico BDGD 2025 (assets gerados por scripts/85_assets_web.py a partir do contrato 1.1.0). */

export type Status = "a" | "l" | "b" | "e" | "n"; // aprovado, alerta, bloqueado, em_validacao, nao_aplicavel
export type Metric = "quantidade" | "quantidade_registros" | "quantidade_cod_id_distinto" | "extensao_km" | "potencia_kva";

export interface Release {
  schema_version: string;
  release_id: string;
  data_base: string;
  status: string;
  generated_at: string;
  dda_version: string;
  quality: { status: string; source_reconciliation: boolean; facetas_exatas_decimal?: boolean; dists_sem_facetas_exatas?: string[] };
  cobertura: {
    distribuidoras_historicas_consideradas: number;
    com_gdb_2025: number;
    processadas: number;
    quarentena: string[];
    em_processamento: string[];
    sem_publicacao_2025: string[];
  };
  regras: Record<string, string>;
  licenca: string;
  autoria: string;
  privacidade: string;
}

export interface Distribuidora {
  dist: number;
  sigla: string;
  nome: string;
  grupo: string; // grupo_id ou "nao_confirmado"
  grupo_status: "verificado" | "nao_confirmado";
  area_km2: number | null;
  ufs: string[];
  fonte: string;
  sha256: string;
  versao: string;
  alertas: Record<string, number>;
  arat?: { bbox: [number, number, number, number]; centro: [number, number] };
}

export interface Grupo {
  id: string;
  nome: string;
  controlador: string;
  fontes: string[];
  tipo_fonte: string;
  consultado_em: string;
  observacao: string;
}

export interface Entidade {
  id: string;
  nome: string;
  familia: string;
  metrica: Metric;
  unidade: string;
  regra: string;
  ativo: boolean;
  naoSomarCom: string | null;
}

export type FatoRow = [
  dist: number,
  entidade: string,
  quantidade: number | null,
  quantidade_registros: number | null,
  quantidade_cod_id_distinto: number | null,
  extensao_km: number | null,
  potencia_kva: number | null,
  status: Status,
  motivo: string,
];

export interface Cobertura { dist: number; sigla: string; empresa: string; status: string; motivo: string }
export interface Homologacao { entidade: string; metrica: string; status: string; comValor: number; nd: number; alerta: number; recOk: number; criterio: string }
export interface FiltroIndisponivel { dist: number; entidade: string; filtro: string; pct: number | null; motivo: string }

export interface IndexData {
  release: Release;
  distribuidoras: Distribuidora[];
  grupos: Grupo[];
  entidades: Entidade[];
  fatos: { cols: string[]; rows: FatoRow[] };
  /** indicador -> dist -> entidade -> [valor, status, motivo] */
  complementares: Record<string, Record<string, Record<string, [number | null, Status, string]>>>;
  cobertura: Cobertura[];
  filtrosIndisponiveis: FiltroIndisponivel[];
  homologacao: Homologacao[];
}

export interface FacetMetricSpec { unidade: string; rollup: boolean; disjunta: boolean; cobertura: string; status: Status }
export interface FacetSpec { id: string; dims: string[]; metricas: Partial<Record<Metric, FacetMetricSpec>> }
/** [dist, codigos (na ordem de dims), valores por metrica, status por metrica] */
export type FacetRow = [number, string[], Partial<Record<Metric, number | null>>, Partial<Record<Metric, Status>>];
export interface FacetData {
  entidade: string;
  facets: FacetSpec[];
  descricoes: Record<string, Record<string, string>>;
  /** rótulo e descrição do campo segundo o Manual BDGD (Rev. 5) */
  atributos: Record<string, { rotulo: string; descricao: string }>;
  rows: Record<string, FacetRow[]>;
  motivos: Record<string, string>;
}

export interface Qualidade {
  alertasPorTipo: Record<string, number>;
  arat: Array<Record<string, string | number | null> & { dist: number }>;
  ucRegraV2: Array<{ dist: number; entidade: string; registros: number; distintos: number; ativados: number; valida: boolean; motivos: string }>;
  alertas: Array<{ dist: number; entidade: string; tipo: string; detalhe: string }>;
  reconciliacao: Record<string, number>;
}

export type Scope = { tipo: "brasil" } | { tipo: "grupo"; id: string } | { tipo: "dist"; id: number };
