import { exigirContagemInteira, ehContagem, naturezaDe, type Natureza } from "./natureza-fisica";

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
  mae_fisico?: number | null; wape_fisico?: number | null; vies_fisico?: number | null; fisico_motivo?: string;
}
export interface SerieCenario {
  hist: [number, number][];
  conservador: number[] | null; moderado: number[] | null; agressivo: number[] | null;
  erro_moderado: number | null;
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
        if (s[c] !== null && ehContagem(naturezaMetrica(m as unknown as MetricaCenario))) (s[c] as number[]).forEach((x, i) => exigirContagemInteira(x, `${k}/${c}[${i}]`));
        if (s[c] !== null && m.cenarios[c] === null) throw Error(`Trajetória sem modelo em ${k}/${c}.`);
      }
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

export function exportarCsv(p: ProdutoCenarios, m: MetricaCenario, dist: string): string {
  const s = m.series[dist];
  const linhas = [["ano", "natureza", ...CENARIOS.map((c) => `${c}${m.cenarios[c] ? `_${m.cenarios[c]}` : "_indisponivel"}`)].join(",")];
  const nat = naturezaMetrica(m);
  for (const [a, v] of s.hist) linhas.push([a, "observado", v, v, v].join(","));
  p.horizonte.forEach((a, i) => linhas.push([a, "simulacao_condicional", ...CENARIOS.map((c) => { const v = s[c]?.[i]; return v == null ? "" : ehContagem(nat) ? exigirContagemInteira(v, `exportação ${m.conceito}/${c}`) : v; })].join(",")));
  return linhas.join("\n") + "\n";
}
