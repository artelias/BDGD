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
  /** R2: equipamentos (EQ*) por TUC e unidades físicas distintas vinculadas (EQ -> UN), por DIST */
  vinculosTuc?: { cols: string[]; destinos: Record<string, string[]>; rows: Array<[number, string, string, number, number, number, number]> };
  /** nomes MCPSE (Res. ANEEL 674/2015) dos TUC presentes */
  tucNomes?: Record<string, string>;
  /** R3: catálogo semântico compartilhado (conceitos, ativos, menu) */
  conceitos?: ConceitosCatalogo;
  /** R3: total por ativo e medida, por DIST, calculado do cubo principal do conceito */
  ativosTotais?: Record<string, Partial<Record<MedidaConceito, TotalAtivoRow[]>>>;
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
  /** descrição MCPSE do A1 por TUC (o mesmo código A1 tem significado diferente em cada TUC) */
  a1PorTuc?: Record<string, Record<string, string>>;
  /** todos os campos do Manual BDGD para a entidade e o que é possível fazer com cada um hoje */
  inventario?: Array<{ campo: string; descricao: string; classe: "filtravel" | "requer_cubo" | "requer_juncao" | "nao_publicavel"; motivo: string }>;
}

export interface Qualidade {
  alertasPorTipo: Record<string, number>;
  arat: Array<Record<string, string | number | null> & { dist: number }>;
  ucRegraV2: Array<{ dist: number; entidade: string; registros: number; distintos: number; ativados: number; valida: boolean; motivos: string }>;
  alertas: Array<{ dist: number; entidade: string; tipo: string; detalhe: string }>;
  reconciliacao: Record<string, number>;
  municipios?: Array<{ dist: number; entidade: string; municipios: number; codigosForaIbge: number; registrosForaIbge: number; registrosSemCodigo: number; registros: number }>;
}

export type Scope = { tipo: "brasil" } | { tipo: "grupo"; id: string } | { tipo: "dist"; id: number };

/* ---------- R3: catálogo semântico de ativos e cubos por conceito ---------- */
export type MedidaConceito = "quantidade" | "extensao_km" | "potencia_kva";
export type Filtro = Record<string, string[]>;
export interface ConceitoCfg {
  nome: string; descricao: string; entidades: string[]; vinculos?: string[]; medidas: MedidaConceito[];
  categoria: string | null; cubos: Record<string, string[]>; inventario?: "sub" | "ctmt" | "ctat" | "conj";
}
export interface AtivoCfg {
  id: string; nome: string; conceito: string; filtro: Filtro; medida: MedidaConceito; medidas_extra?: MedidaConceito[]; familia: string;
  resumo: string; explicacao: string; tecnico: string; ressalva?: string;
}
export interface MenuItem { id: string; nome: string; conceito?: string; filtro?: Filtro; excluir?: Filtro; descricao?: string; tecnico?: string[] }
export interface ConceitosCatalogo {
  versao: string;
  dimensoes: Record<string, { rotulo: string; dda?: string; fonte?: string }>;
  medidas: Record<MedidaConceito, { rotulo: string; unidade: string; ressalva?: string }>;
  conceitos: Record<string, ConceitoCfg>;
  ativos: AtivoCfg[];
  kpis_padrao: string[];
  menu: Array<{ grupo: string; itens: MenuItem[] }>;
}
/** [dist, valor, status, motivo] */
export type TotalAtivoRow = [number, number | null, Status, string];
/** linha compacta: [dist, ...índices das dimensões, ...valores das medidas do conceito] */
export type CuboRow = number[];
export interface ConceitoData {
  cobertura_incompleta?: Array<{ dist: number; dimensao: string; codigo: string; metrica: MedidaConceito }>;
  id: string; medidas: MedidaConceito[];
  valores: Record<string, string[]>;
  rotulos: Record<string, Record<string, string>>;
  cubos: Record<string, { dims: string[]; entidades: string[]; rows: Array<Array<number | null>> }>;
  a1PorTuc?: Record<string, Record<string, string>>;
}
export interface InventarioTabela { cols: string[]; rows: Array<Array<string | number | null>> }
export type InventarioData = Partial<Record<"sub" | "ctmt" | "ctat" | "conj", InventarioTabela>>;
