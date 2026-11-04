import { estadoCompletude, type CompletudeSerie } from "./completude";
import { exigirCoerencia, exigirContagemInteira, ehContagem, naturezaDe, type Natureza } from "./natureza-fisica";

/** Produto estático do Motor de Expansão Elétrica: cenários Conservador | Moderado | Agressivo, pré-calculados fora do navegador. */
export type Cenario = "conservador" | "moderado" | "agressivo";
export const CENARIOS: readonly Cenario[] = ["conservador", "moderado", "agressivo"];
export const ROTULO_CENARIO: Record<Cenario, string> = { conservador: "Conservador", moderado: "Moderado", agressivo: "Agressivo" };
export const ROTULO_ESTADO: Record<string, string> = {
  tres_cenarios: "Três cenários comparados em backtest",
  dois_cenarios: "Dois cenários disponíveis",
  somente_moderado: "Somente cenário moderado",
  somente_baseline: "Somente baseline de persistência",
  bloqueado: "Bloqueado",
};

export interface ModeloDoc { nome: string; familia: string; complexidade: number; formula: string }
export interface ErroModelo {
  wape: number | null; mae: number | null; rmse: number | null; vies: number | null; mdape: number | null; n: number;
  wape_h1: number | null; wape_h2: number | null; estabilidade: number | null; cagr: number | null; elegivel: boolean; motivo: string | null;
  /** Só em métricas de contagem: erro depois de arredondar a previsão para inteiro (patch B do PR #19); ausente em métricas contínuas. */
  mae_fisico?: number | null; wape_fisico?: number | null; vies_fisico?: number | null; fisico_motivo?: string | null;
}
export interface SerieCenario {
  hist: [number, number][];
  conservador: number[] | null; moderado: number[] | null; agressivo: number[] | null;
  erro_moderado: number | null;
  /** Por que a série fica sem um cenário cujo modelo existe na métrica (códigos do gerador). */
  motivos?: Partial<Record<Cenario, string>>;
}
export interface MetricaCenario {
  conceito: string; ativo: string; familia: string; metrica: string; unidade: string; natureza?: Natureza; estado: string; experimental: boolean;
  cenarios: Record<Cenario, string | null>; justificativas: Record<Cenario, string>;
  modelos: Record<string, ErroModelo>; diagnostico_painel: Record<string, Record<string, unknown>>;
  series: Record<string, SerieCenario>;
}
export interface VariavelMotor {
  variavel: string; ativos: string; tipo: string; fonte: string; disponivel_em: string; transformacao: string; associacao: string;
  defasagem: string; disponivel: string; utilizada: string; modelos_que_usaram: string;
}
export interface ProdutoCenarios {
  schema_version: "cenarios-motor-1"; base: number; horizonte: number[]; origens_backtest: number[];
  parametros: Record<string, unknown>; modelos: Record<string, ModeloDoc>; variaveis: VariavelMotor[];
  empresas: Record<string, string>; fontes_sha256: Record<string, string>; metricas: MetricaCenario[];
  intervalos: null; previsao_validada: false;
}

const rec = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);
const fin = (x: unknown): x is number => typeof x === "number" && Number.isFinite(x);
const trajetoria = (x: unknown, n: number) => x === null || Array.isArray(x) && x.length === n && x.every((v) => fin(v) && v >= 0);

/** Recusa schema desconhecido, alegação de validação/intervalo, trajetória negativa e cenário apontando para modelo inexistente ou inelegível. */
export function parseCenarios(v: unknown): ProdutoCenarios {
  if (!rec(v) || v.schema_version !== "cenarios-motor-1" || v.previsao_validada !== false || v.intervalos !== null ||
    !fin(v.base) || !Array.isArray(v.horizonte) || !v.horizonte.every(fin) || !rec(v.modelos) || !Array.isArray(v.metricas) ||
    !Array.isArray(v.variaveis) || !rec(v.empresas)) throw Error("Produto de cenários inválido ou não publicável.");
  const n = v.horizonte.length;
  const chaves = new Set<string>();
  for (const m of v.metricas) {
    if (!rec(m) || typeof m.conceito !== "string" || typeof m.metrica !== "string" || !rec(m.cenarios) || !rec(m.modelos) || !rec(m.series))
      throw Error("Métrica inválida no produto de cenários.");
    const k = `${m.conceito}|${m.metrica}`;
    const natureza = exigirCoerencia(m, k);                    // natureza declarada, unidade e métrica precisam concordar
    if (chaves.has(k)) throw Error(`Métrica duplicada: ${k}`);
    chaves.add(k);
    for (const c of CENARIOS) {
      const id = m.cenarios[c];
      if (id === null) continue;
      if (typeof id !== "string" || !(id in v.modelos) || !rec(m.modelos[id]) || (m.modelos[id] as unknown as ErroModelo).elegivel !== true)
        throw Error(`Cenário ${c} de ${k} aponta para modelo inexistente ou inelegível.`);
    }
    if (m.cenarios.moderado === null && (m.cenarios.conservador !== null || m.cenarios.agressivo !== null))
      throw Error(`Cenários alternativos sem moderado em ${k}.`);
    for (const s of Object.values(m.series)) {
      if (!rec(s) || !Array.isArray(s.hist) || !s.hist.every((p) => Array.isArray(p) && fin(p[0]) && fin(p[1]) && p[1] > 0))
        throw Error(`Histórico inválido em ${k}.`);
      for (const c of CENARIOS) {
        if (!trajetoria(s[c], n)) throw Error(`Trajetória inválida em ${k}/${c}.`);
        // Contrato de natureza física: contagem fracionária em produto público é recusada, não arredondada em silêncio.
        if (s[c] !== null && ehContagem(natureza)) (s[c] as number[]).forEach((x, i) => exigirContagemInteira(x, `${k}/${c}[${i}]`));
        if (s[c] !== null && m.cenarios[c] === null) throw Error(`Trajetória sem modelo em ${k}/${c}.`);
      }
      // extremo sem Moderado na própria série é estado inconsistente (os extremos são definidos em relação ao Moderado)
      if (s.moderado === null && (s.conservador !== null || s.agressivo !== null)) throw Error(`Cenário extremo sem Moderado em ${k}.`);
    }
  }
  return v as unknown as ProdutoCenarios;
}

/** Natureza física da métrica: a declarada no produto ou, na falta dela, a derivada da unidade (unidade desconhecida é erro). */
export const naturezaMetrica = (m: Pick<MetricaCenario, "natureza" | "unidade" | "metrica">): Natureza =>
  m.natureza ?? (m.unidade ? naturezaDe(m.unidade) : naturezaDe(m.metrica === "extensao_km" ? "km" : m.metrica === "potencia_kva" ? "kVA" : "itens"));

/** Variação absoluta e percentual da trajetória contra o último ano observado (ano-base). */
export function variacoes(base: number, traj: readonly number[] | null) {
  if (!traj) return null;
  return traj.map((v) => ({ valor: v, abs: v - base, pct: base > 0 ? (v / base - 1) * 100 : null }));
}

/** Soma de grupo só quando todas as distribuidoras têm a trajetória do cenário; caso contrário N/D (sem completar faltantes). */
export function somaGrupo(m: MetricaCenario, dists: readonly string[], c: Cenario, n: number): { hist: Map<number, number> | null; traj: number[] | null; faltantes: string[] } {
  const faltantes = dists.filter((d) => !m.series[d]?.[c]);
  const traj = faltantes.length || !dists.length ? null : Array.from({ length: n }, (_, i) => dists.reduce((s, d) => s + m.series[d][c]![i], 0));
  const anos = new Set<number>();
  for (const d of dists) for (const [a] of m.series[d]?.hist ?? []) anos.add(a);
  let hist: Map<number, number> | null = new Map();
  for (const a of anos) {
    const vals = dists.map((d) => m.series[d]?.hist.find((p) => p[0] === a)?.[1]);
    if (vals.some((x) => x === undefined)) continue;
    hist.set(a, vals.reduce<number>((s, x) => s + (x as number), 0));
  }
  if (!hist.size) hist = null;
  return { hist, traj, faltantes };
}

/** Motivos por série, do gerador (motor_cenarios/cenarios.py), em linguagem do usuário. */
export const MOTIVO_SERIE: Record<string, string> = {
  TRAJETORIA_IMPLAUSIVEL_NA_SERIE: "a trajetória do modelo nesta distribuidora sai da faixa física plausível (2030/2025 entre 0,5 e 3)",
  HISTORICO_CONTIGUO_INSUFICIENTE: "a série não tem três anos contíguos comparáveis terminando em 2025",
  MODELO_SEM_PROJECAO_NA_SERIE: "o modelo deste cenário não projeta esta distribuidora (variáveis do modelo ausentes)",
  SEM_MODERADO_NA_SERIE: "sem cenário Moderado publicável nesta distribuidora; um extremo nunca é publicado sozinho",
};
const semPrefixo = (t: string) => t.replace(/^Indisponível:\s*/, "");

/** Completude dos cenários de uma distribuidora: o que foi publicado e, para o que falta, o motivo (da métrica ou da série). */
export function completudeSerie(m: MetricaCenario, s: SerieCenario | undefined): CompletudeSerie<Cenario> {
  const publicados = CENARIOS.filter((c) => !!s?.[c]);
  const naoPublicados = CENARIOS.filter((c) => !publicados.includes(c)).map((c): [Cenario, string] => [c,
    !m.cenarios[c] ? semPrefixo(m.justificativas[c] ?? "sem modelo para o cenário")
      : MOTIVO_SERIE[s?.motivos?.[c] ?? ""] ?? s?.motivos?.[c] ?? "sem trajetória publicável nesta distribuidora"]);
  return { estado: estadoCompletude(CENARIOS, "moderado", publicados, `${m.conceito}|${m.metrica}`), publicados, naoPublicados };
}

/** Completude de um grupo: um cenário só é publicado para o grupo quando todas as distribuidoras o têm (soma sem completar faltantes). */
export function completudeGrupo(m: MetricaCenario, dists: readonly string[]): CompletudeSerie<Cenario> {
  const publicados = dists.length ? CENARIOS.filter((c) => dists.every((d) => !!m.series[d]?.[c])) : [];
  const naoPublicados = CENARIOS.filter((c) => !publicados.includes(c)).map((c): [Cenario, string] => {
    const sem = dists.filter((d) => !m.series[d]?.[c]);
    return [c, !m.cenarios[c] ? semPrefixo(m.justificativas[c] ?? "sem modelo para o cenário")
      : `${sem.length} de ${dists.length} distribuidoras do grupo sem este cenário; a soma não é completada`];
  });
  return { estado: estadoCompletude(CENARIOS, "moderado", publicados, `${m.conceito}|${m.metrica} (grupo)`), publicados, naoPublicados };
}

export function exportarCsv(p: ProdutoCenarios, m: MetricaCenario, dist: string): string {
  const s = m.series[dist];
  const comp = completudeSerie(m, s);
  // Coluna de cada cenário: modelo publicado ou "nao_publicado"; a completude e os cenários publicados aparecem em toda linha.
  const linhas = [["ano", "natureza", "observado", ...CENARIOS.map((c) => `${c}_${s[c] ? m.cenarios[c] : "nao_publicado"}`), "completude_cenarios", "cenarios_publicados"].join(",")];
  const nat = naturezaMetrica(m);
  const conta = (v: number, onde: string) => ehContagem(nat) ? exigirContagemInteira(v, onde) : v;
  const fim = [comp.estado, comp.publicados.join("|")];
  for (const [a, v] of s.hist) linhas.push([a, "observado", conta(v, `exportação ${m.conceito}/histórico`), "", "", "", ...fim].join(","));
  p.horizonte.forEach((a, i) => linhas.push([a, "simulacao_condicional", "", ...CENARIOS.map((c) => { const v = s[c]?.[i]; return v == null ? "" : conta(v, `exportação ${m.conceito}/${c}`); }), ...fim].join(",")));
  return linhas.join("\n") + "\n";
}
