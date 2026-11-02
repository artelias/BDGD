/** Contrato do produto pré-calculado do Motor V2 (motor_v2/nacional/exportar_web.py, esquema motor-v2-homologacao/1).
 *
 * Só existe numa build de homologação (scripts/motor-v2-gate.mjs). Nada é treinado no navegador: o índice e um arquivo por
 * distribuidora são carregados sob demanda. Ausência é null e aparece como N/D, nunca como zero. */

export const SCHEMA_MOTOR_V2 = "motor-v2-homologacao/1";
export const CENARIOS_V2 = ["Conservador", "Moderado", "Agressivo"] as const;
export type CenarioV2 = (typeof CENARIOS_V2)[number];
export const ESTADOS_PROJETADOS = ["PROJETADA_EXPERIMENTAL", "PROJETADA_BASELINE", "SEM_ANCORA_2025"] as const;

export type EstadoCenario = "ACEITO" | "CORRIGIDO" | "BLOQUEADO";
export interface PlausibilidadeCenario { estado: EstadoCenario; classe: string | null; severidade: string | null; motivo: string | null; g: number | null; g_pub: number | null; evidencias: Record<string, unknown> | null }
export interface PlausibilidadeV2 {
  severidade: "ALTA" | "MEDIA" | "BAIXA" | null; classe: string | null; motivo: string | null; alerta_intensidade: string | null;
  cenarios: Record<"Conservador" | "Agressivo", PlausibilidadeCenario>;
}
export interface ErrosV2 { mae: number | null; rmse?: number | null; wape: number | null; vies: number | null; origens: number; previsoes?: number; mae_por_origem?: Record<string, number> }
export interface CoeficientesV2 {
  status: "recuperado_e_verificado" | "N/D"; motivo?: string; forma?: string; intercepto?: number;
  termos?: { variavel: string; coeficiente: number; valor_na_ancora: number | null }[];
  padronizados?: { variavel: string; coeficiente: number }[]; parametros?: Record<string, number>; selecao?: string;
  linhas_treino?: number; dist_no_pool?: number; crescimento_log1p_um_passo?: number;
}
export interface ModeloV2 {
  id: string | null; algoritmo: string | null; escopo: string | null; tipo: "baseline" | "ml" | "reconciliacao"; base_da_projecao: string | null;
  mecanismo: string | null; justificativa: string | null; nota: string | null; melhor_baseline: string | null; melhor_ml: string | null;
  homologado: false; motivo_nao_homologado: string; coeficientes: CoeficientesV2 | null;
}
export interface SerieV2 {
  objetivo: string; metrica: string; nome: string; familia: string; unidade: string; natureza: string; variante: string | null;
  estado: string; classe: string | null; motivo: string; fonte: string;
  historico: [number, number | null, string][]; ancora: number | null; horizonte_real: string | null; valor_ancora: number | null; entra_em_totais: boolean;
  modelo: ModeloV2 | null; erros: ErrosV2 | null; baselines: Record<string, ErrosV2> | null; melhor_baseline_medido: string | null; ganho_vs_melhor_baseline: number | null;
  /** Cenário bloqueado pelo portão de plausibilidade = null (sem valor publicável); o original fica só no artefato de auditoria. */
  cenarios: Record<CenarioV2, (number | null)[] | null> | null;
  cenarios_status: Record<CenarioV2, EstadoCenario> | null;
  plausibilidade: PlausibilidadeV2 | null;
  cenarios_meta: { degenerados: boolean; piso_zero: boolean; crescimento_log1p: Record<string, number | null>; transicoes_historicas: number | null; transicoes_atipicas_excluidas: unknown[]; regra: string } | null;
}
export interface DistV2 { schema: string; dist: number; empresa: string; grupo: string | null; series: SerieV2[] }
export interface ObjetivoV2 {
  objetivo: string; metrica: string; nome: string; familia: string; unidade: string; natureza: string; no_catalogo: boolean;
  estados: Record<string, number>; series_com_15_valores: number; cobertura_estoque_2025: number | null; rotulo_total: "PARCIAL" | "COMPLETO" | null;
  observacao: string | null; total_2030: Record<CenarioV2, number | null> | null;
  n_series_total?: Record<CenarioV2, number | null> | null; total_2030_moderado_todas?: number | null; n_series_moderado_todas?: number | null; series_com_cenario_bloqueado?: number; series_com_cenario_corrigido?: number;
}
export interface IndiceV2 {
  schema: string; status_publicacao: string; contrato_sha256: string; anos_historicos: number[]; anos_projecao: number[]; cenarios: CenarioV2[];
  estados: Record<string, { rotulo: string; descricao: string; com_valores: boolean }>; objetivos: ObjetivoV2[]; grupos: Record<string, string>;
  dists: { dist: number; empresa: string; grupo: string | null; projetadas: number; series: number }[];
  resumo: {
    universo: { dist: number; objetivos_metricas_catalogo: number; combinacoes: number; celulas_ano_cenario: number };
    cobertura_processamento: { combinacoes_com_estado: number; fracao: number };
    cobertura_previsao: { com_15_valores: number; com_moderado_e_extremo_bloqueado: number; series_bloqueadas_inteiras: number; cenarios_extremos_bloqueados: number; cenarios_extremos_corrigidos: number; ancora_2025: number; ancora_anterior: number; fracao: number; fracao_aplicavel: number };
    estados: Record<string, number>; combinacoes_objetivo_metrica_com_previsao: number; dist_com_alguma_projecao: number; bloqueio_tecnico: number;
  };
  coeficientes: { recuperados: number; tentados: number }; limitacoes: string[];
}

/** O portão é decidido na build (next.config.mjs inlines NEXT_PUBLIC_MOTOR_V2). */
export function motorV2Habilitado(env: string | undefined = process.env.NEXT_PUBLIC_MOTOR_V2): boolean {
  return env === "homologacao";
}

export const URL_INDICE = "/data/motor-v2/indice.json";
export const urlDist = (d: number | string) => `/data/motor-v2/distribuidoras/${d}.json`;

export function chaveSerie(s: Pick<SerieV2, "objetivo" | "metrica">) { return `${s.objetivo}|${s.metrica}`; }
export function projetada(s: Pick<SerieV2, "estado">) { return (ESTADOS_PROJETADOS as readonly string[]).includes(s.estado); }
export function ehContagemV2(s: Pick<SerieV2, "natureza" | "unidade">) { return s.natureza === "discrete_count" || s.unidade === "itens"; }

/** Valida o que a interface usa; um arquivo fora do contrato é rejeitado em vez de exibido. */
export function validarDist(j: unknown): DistV2 {
  const d = j as DistV2;
  if (!d || d.schema !== SCHEMA_MOTOR_V2 || !Array.isArray(d.series)) throw new Error("Arquivo do Motor V2 fora do contrato.");
  for (const s of d.series) {
    if (projetada(s)) {
      if (!s.cenarios || !s.cenarios_status) throw new Error(`Série projetada sem cenários: ${chaveSerie(s)}`);
      if (s.cenarios_status.Moderado === "BLOQUEADO") throw new Error(`Moderado bloqueado deve ter estado próprio: ${chaveSerie(s)}`);
      for (const c of CENARIOS_V2) {
        const v = s.cenarios[c];
        if (s.cenarios_status[c] === "BLOQUEADO") {
          if (v !== null) throw new Error(`Cenário bloqueado ${c} publicou valores: ${chaveSerie(s)}`);
          if (!s.plausibilidade?.cenarios?.[c as "Conservador" | "Agressivo"]?.motivo) throw new Error(`Cenário bloqueado ${c} sem motivo: ${chaveSerie(s)}`);
          continue;
        }
        if (!Array.isArray(v) || v.length !== 5 || v.some((x) => typeof x !== "number" || !Number.isFinite(x) || x < 0)) throw new Error(`Cenário ${c} inválido: ${chaveSerie(s)}`);
        if (ehContagemV2(s) && v.some((x) => !Number.isInteger(x))) throw new Error(`Contagem fracionária: ${chaveSerie(s)}`);
      }
    } else if (s.cenarios) throw new Error(`Série sem projeção com valores: ${chaveSerie(s)}`);
  }
  return d;
}

export function validarIndice(j: unknown): IndiceV2 {
  const x = j as IndiceV2;
  if (!x || x.schema !== SCHEMA_MOTOR_V2 || !Array.isArray(x.objetivos) || !Array.isArray(x.dists)) throw new Error("Índice do Motor V2 fora do contrato.");
  return x;
}

/** Soma de um grupo: só completa quando TODAS as DIST do grupo têm a série com âncora 2025 e a métrica é aditiva.
 * Caso contrário devolve os valores parciais e a lista do que falta, rotulada PARCIAL — nunca completa com zero. */
export function somaGrupo(series: { dist: number; empresa: string; serie: SerieV2 | undefined }[], cenario: CenarioV2) {
  const faltam: string[] = [];
  const naoAditiva = series.some((x) => x.serie && x.serie.objetivo === "reguladores" && x.serie.metrica === "potencia_kva");
  const anos = 5;
  const total: number[] = Array(anos).fill(0);
  const hist = new Map<number, number>();
  const histFaltam = new Set<number>();
  let n = 0;
  for (const { empresa, serie } of series) {
    // os três totais somam o MESMO conjunto: só entra a DIST com os três cenários publicáveis (senão Conservador ≤ Moderado ≤ Agressivo se perderia)
    const vc = serie?.cenarios?.[cenario];
    const tres = serie?.cenarios_status && CENARIOS_V2.every((c) => serie.cenarios_status![c] !== "BLOQUEADO");
    if (!serie || !serie.entra_em_totais || !vc || !tres) { faltam.push(empresa); continue; }
    n += 1;
    vc.forEach((v, i) => { total[i] += v ?? 0; });
    for (const [a, v] of serie.historico) { if (v == null) histFaltam.add(a); else hist.set(a, (hist.get(a) ?? 0) + v); }
  }
  for (const a of histFaltam) hist.delete(a);
  return { total: n ? total : null, hist, faltam, incluidas: n, rotulo: naoAditiva ? "NAO_SOMAVEL" : faltam.length ? "PARCIAL" : "COMPLETO" } as const;
}

export function fmtV2(v: number | null | undefined, s: Pick<SerieV2, "natureza" | "unidade">): string {
  if (v == null || !Number.isFinite(v)) return "N/D";
  return v.toLocaleString("pt-BR", { maximumFractionDigits: ehContagemV2(s) ? 0 : 1 });
}

export const pctV2 = (v: number | null | undefined, d = 2) => v == null || !Number.isFinite(v) ? "N/D" : `${(100 * v).toLocaleString("pt-BR", { maximumFractionDigits: d, minimumFractionDigits: d })}%`;

const esc = (v: unknown) => { const t = v == null ? "" : String(v); return /[";\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t; };

/** CSV coerente com o recorte: uma série de uma DIST, histórico com estado do contrato e os 15 valores; N/D fica vazio. */
export function csvSerieV2(d: Pick<DistV2, "dist" | "empresa">, s: SerieV2): string {
  const linhas = [["DIST", "empresa", "objetivo", "metrica", "unidade", "estado_serie", "ano", "tipo", "cenario", "valor", "estado_celula", "estado_cenario", "modelo", "status_publicacao"].join(";")];
  for (const [a, v, est] of s.historico) linhas.push([d.dist, d.empresa, s.objetivo, s.metrica, s.unidade, s.estado, a, "observado", "", v, est, "", "", "experimental_nao_homologado"].map(esc).join(";"));
  if (s.cenarios) for (const c of CENARIOS_V2) for (let i = 0; i < 5; i += 1) linhas.push(
    [d.dist, d.empresa, s.objetivo, s.metrica, s.unidade, s.estado, 2026 + i, "projecao", c, s.cenarios[c]?.[i] ?? null, "", s.cenarios_status?.[c] ?? "", s.modelo?.id ?? "", "experimental_nao_homologado"].map(esc).join(";"));
  return linhas.join("\n") + "\n";
}
