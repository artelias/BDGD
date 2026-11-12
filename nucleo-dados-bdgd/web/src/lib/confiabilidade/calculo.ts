/** Regras de cálculo do módulo de Confiabilidade no navegador. Funções puras (testadas em calculo.test.ts).
 *  - ausência (null) nunca vira zero e nunca entra em soma, média ou ordenação;
 *  - o valor anual do conjunto é a soma dos meses; agregados de conjuntos são ponderados por consumidores;
 *  - nenhuma função daqui afirma causa: as frases comparam valores e posições, só isso. */
import type { BlocoAno, Indicador, Infra, MetricaDef, NacionalAno } from "./tipos";

export const num = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

export function razaoLimite(obs: number | null | undefined, lim: number | null | undefined): number | null {
  return num(obs) && num(lim) && lim > 0 ? obs / lim : null;
}
export type Situacao = "dentro" | "acima" | "nd";
export function situacao(obs: number | null | undefined, lim: number | null | undefined): Situacao {
  const r = razaoLimite(obs, lim);
  return r === null ? "nd" : r > 1 ? "acima" : "dentro";
}
export function variacao(atual: number | null | undefined, anterior: number | null | undefined): { abs: number; rel: number | null } | null {
  if (!num(atual) || !num(anterior)) return null;
  return { abs: atual - anterior, rel: anterior !== 0 ? (atual - anterior) / anterior : null };
}
/** Soma dos meses apurados (valor anual do conjunto). */
export function anualDeMeses(meses: Array<number | null>): { v: number | null; n: number } {
  const v = meses.filter(num);
  return { v: v.length ? v.reduce((a, b) => a + b, 0) : null, n: v.length };
}
/** Acumulado mês a mês; depois do primeiro mês ausente o acumulado fica ausente (não se pula um mês em silêncio). */
export function acumulado(meses: Array<number | null>): Array<number | null> {
  let s = 0, quebrou = false;
  return meses.map((m) => { if (quebrou || !num(m)) { quebrou = true; return null; } s += m; return Math.round(s * 100) / 100; });
}
/** Média ponderada por consumidores (agregado de conjuntos ou de distribuidoras). Nunca média simples. */
export function mediaPonderada(itens: Array<{ v: number | null | undefined; w: number | null | undefined }>): { v: number | null; n: number; fora: number } {
  let s = 0, w = 0, n = 0, fora = 0;
  for (const i of itens) { if (num(i.v) && num(i.w) && i.w > 0) { s += i.v * i.w; w += i.w; n++; } else fora++; }
  return { v: w > 0 ? s / w : null, n, fora };
}
export const valorInd = (b: BlocoAno | undefined | null, ind: Indicador) => (b ? b[ind] : null);
export const limiteInd = (b: BlocoAno | undefined | null, ind: Indicador) => (b ? (ind === "dec" ? b.ld : b.lf) : null);

// ------------------------------------------------------------------ estatística descritiva
export function quantil(ordenado: number[], p: number): number | null {
  if (!ordenado.length) return null;
  const i = (ordenado.length - 1) * p, lo = Math.floor(i), hi = Math.ceil(i);
  return ordenado[lo] + (ordenado[hi] - ordenado[lo]) * (i - lo);
}
export interface Resumo { n: number; min: number; q1: number; mediana: number; q3: number; max: number }
export function resumo(valores: Array<number | null | undefined>): Resumo | null {
  const v = valores.filter(num).sort((a, b) => a - b);
  if (!v.length) return null;
  return { n: v.length, min: v[0], q1: quantil(v, 0.25)!, mediana: quantil(v, 0.5)!, q3: quantil(v, 0.75)!, max: v[v.length - 1] };
}
/** Posição percentil de um valor entre os pares: fração dos pares com valor menor ou igual (0–1). */
export function percentilDe(valor: number | null | undefined, pares: Array<number | null | undefined>): number | null {
  if (!num(valor)) return null;
  const v = pares.filter(num);
  if (!v.length) return null;
  return v.filter((x) => x <= valor).length / v.length;
}
export function histograma(valores: Array<number | null | undefined>, classes = 12): { de: number; ate: number; n: number }[] {
  const v = valores.filter(num);
  if (!v.length) return [];
  const min = Math.min(...v), max = Math.max(...v);
  if (min === max) return [{ de: min, ate: max, n: v.length }];
  const passo = (max - min) / classes;
  const out = Array.from({ length: classes }, (_, i) => ({ de: min + i * passo, ate: min + (i + 1) * passo, n: 0 }));
  for (const x of v) out[Math.min(classes - 1, Math.floor((x - min) / passo))].n++;
  return out;
}

// ------------------------------------------------------------------ tabela nacional
export interface Linha { dist: number; c: number; n: string; dec: number | null; fec: number | null; ld: number | null; lf: number | null; nuc: number | null; infra: Infra }
const FIXOS = ["dist", "c", "n", "dec", "fec", "ld", "lf", "nuc"];
export function linhasNacionais(t: NacionalAno): Linha[] {
  const ix = new Map(t.campos.map((c, i) => [c, i]));
  const extras = t.campos.filter((c) => !FIXOS.includes(c));
  return t.linhas.map((r) => {
    const infra: Infra = {};
    for (const c of extras) infra[c] = r[ix.get(c)!] as number | null;
    return { dist: r[ix.get("dist")!] as number, c: r[ix.get("c")!] as number, n: String(r[ix.get("n")!] ?? ""), dec: r[ix.get("dec")!] as number | null, fec: r[ix.get("fec")!] as number | null,
      ld: r[ix.get("ld")!] as number | null, lf: r[ix.get("lf")!] as number | null, nuc: r[ix.get("nuc")!] as number | null, infra };
  });
}
export const chave = (l: { dist: number; c: number }) => `${l.dist}:${l.c}`;
export const temInfra = (l: Linha) => num(l.infra.uc) && num(l.infra.km_mt);

// ------------------------------------------------------------------ pares semelhantes
/** Critérios de semelhança: contexto que a distribuidora não escolhe no curto prazo (porte, densidade, ruralidade, dispersão da rede, carga). */
export const CRITERIOS_PADRAO: Array<{ id: string; log: boolean; rotulo: string }> = [
  { id: "uc", log: true, rotulo: "porte (consumidores)" },
  { id: "uc_por_km2", log: true, rotulo: "densidade de consumidores" },
  { id: "pct_uc_rural", log: false, rotulo: "consumidores em área não urbana" },
  { id: "km_mt_por_mil_uc", log: true, rotulo: "rede MT por mil consumidores" },
  { id: "mwh_por_uc", log: true, rotulo: "consumo por consumidor" },
];
export interface Par { linha: Linha; distancia: number; contrib: Record<string, number> }
const tr = (v: number, log: boolean) => (log ? Math.log(Math.max(v, 1e-9)) : v);

/** Escala robusta de cada critério no universo: mediana e intervalo interquartil do valor transformado. */
export function escalas(universo: Linha[], criterios = CRITERIOS_PADRAO): Record<string, { med: number; iqr: number }> {
  const out: Record<string, { med: number; iqr: number }> = {};
  for (const c of criterios) {
    const v = universo.map((l) => l.infra[c.id]).filter((x): x is number => num(x) && (!c.log || x > 0)).map((x) => tr(x, c.log)).sort((a, b) => a - b);
    const q1 = quantil(v, 0.25), q3 = quantil(v, 0.75), med = quantil(v, 0.5);
    if (med !== null && q1 !== null && q3 !== null && q3 > q1) out[c.id] = { med, iqr: q3 - q1 };
  }
  return out;
}
/** k conjuntos mais próximos do alvo nos critérios (distância euclidiana em unidades de IQR). Só entra quem tem TODOS os critérios;
 *  o resultado traz a contribuição de cada critério para a distância, para mostrar por que são comparáveis. */
export function paresSemelhantes(alvo: Linha, universo: Linha[], k = 20, criterios = CRITERIOS_PADRAO, esc = escalas(universo, criterios)): { pares: Par[]; usados: string[]; motivo?: string } {
  const usados = criterios.filter((c) => esc[c.id] && num(alvo.infra[c.id]) && (!c.log || (alvo.infra[c.id] as number) > 0));
  if (usados.length < 3) return { pares: [], usados: usados.map((c) => c.id), motivo: "O conjunto não tem pelo menos três dos critérios de semelhança; sem pares definidos." };
  const z = (l: Linha, c: (typeof criterios)[number]) => (tr(l.infra[c.id] as number, c.log) - esc[c.id].med) / esc[c.id].iqr;
  const za = usados.map((c) => z(alvo, c));
  const pares: Par[] = [];
  for (const l of universo) {
    if (chave(l) === chave(alvo)) continue;
    if (!usados.every((c) => num(l.infra[c.id]) && (!c.log || (l.infra[c.id] as number) > 0))) continue;
    let d2 = 0; const contrib: Record<string, number> = {};
    usados.forEach((c, i) => { const d = z(l, c) - za[i]; contrib[c.id] = d * d; d2 += d * d; });
    pares.push({ linha: l, distancia: Math.sqrt(d2), contrib });
  }
  pares.sort((a, b) => a.distancia - b.distancia || a.linha.c - b.linha.c);
  return { pares: pares.slice(0, k), usados: usados.map((c) => c.id) };
}

// ------------------------------------------------------------------ comparação A × B
export interface LinhaComparacao { id: string; nome: string; unidade: string; tipo: MetricaDef["tipo"]; grupo: string; a: number | null; b: number | null; dif: number | null; rel: number | null }
export function comparar(a: Infra | null, b: Infra | null, metricas: MetricaDef[], ids?: string[]): LinhaComparacao[] {
  return metricas.filter((m) => !ids || ids.includes(m.id)).map((m) => {
    const va = a?.[m.id] ?? null, vb = b?.[m.id] ?? null;
    const ok = num(va) && num(vb);
    return { id: m.id, nome: m.nome, unidade: m.unidade, tipo: m.tipo, grupo: m.grupo, a: va, b: vb, dif: ok ? va - vb : null, rel: ok && vb !== 0 && m.tipo !== "pct" ? (va - vb) / Math.abs(vb) : null };
  });
}

/** Frases de leitura da comparação, geradas por regra explícita. Descrevem diferenças e posições; nunca explicam uma pela outra. */
export function frasesComparacao(p: {
  nomeA: string; nomeB: string; ind: Indicador; a: BlocoAno | null; b: BlocoAno | null; metricas: MetricaDef[];
  medianaParesA?: number | null; medianaParesB?: number | null; distancia?: number | null;
}): string[] {
  const out: string[] = [];
  const I = p.ind.toUpperCase(), va = valorInd(p.a, p.ind), vb = valorInd(p.b, p.ind);
  const dec = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  if (num(va) && num(vb)) {
    if (Math.abs(va - vb) < 0.005) out.push(`${p.nomeA} e ${p.nomeB} têm o mesmo ${I} apurado no ano.`);
    else out.push(`O ${I} de ${va > vb ? p.nomeA : p.nomeB} (${dec(Math.max(va, vb))}) é maior que o de ${va > vb ? p.nomeB : p.nomeA} (${dec(Math.min(va, vb))}).`);
  } else out.push(`Sem ${I} apurado nos dois conjuntos para o ano escolhido: a comparação de continuidade não é possível.`);
  for (const [nome, bloco] of [[p.nomeA, p.a], [p.nomeB, p.b]] as const) {
    const r = razaoLimite(valorInd(bloco, p.ind), limiteInd(bloco, p.ind));
    if (r !== null) out.push(`${nome} está ${r > 1 ? `${Math.round((r - 1) * 100)}% acima` : r === 1 ? "exatamente no" : `${Math.round((1 - r) * 100)}% abaixo`}${r === 1 ? "" : " do"} limite regulatório de ${I}.`);
  }
  for (const [nome, v, med] of [[p.nomeA, va, p.medianaParesA], [p.nomeB, vb, p.medianaParesB]] as const) {
    if (num(v) && num(med)) out.push(`O ${I} de ${nome} está ${v > med ? "acima" : v < med ? "abaixo" : "na"}${v === med ? "" : " da"} mediana dos seus pares comparáveis (${dec(med)}).`);
  }
  const ia = p.a?.infra, ib = p.b?.infra;
  if (ia && ib) {
    for (const id of ["km_mt_por_mil_uc", "uc_por_alim", "relig_por_100km", "tlcd_por_100km", "pct_uc_rural", "uc_por_km2"]) {
      const m = p.metricas.find((x) => x.id === id), x = ia[id], y = ib[id];
      if (!m || !num(x) || !num(y)) continue;
      const maior = Math.max(x, y), menor = Math.min(x, y);
      if (maior === 0 || (maior - menor) / maior < 0.2) continue;   // só diferenças de pelo menos 20%
      out.push(`${x > y ? p.nomeA : p.nomeB} tem ${m.nome.charAt(0).toLowerCase()}${m.nome.slice(1)} maior que ${x > y ? p.nomeB : p.nomeA}.`);
    }
    if (num(p.distancia) && p.distancia > 2) out.push("Os conjuntos têm perfis de porte, densidade e ruralidade diferentes; a comparação direta requer cautela.");
  } else out.push("Pelo menos um dos conjuntos está sem infraestrutura da BDGD no ano escolhido; só a continuidade pode ser comparada.");
  return out;
}

// ------------------------------------------------------------------ perfil dos melhores e dos piores
export interface PerfilLinha { id: string; melhores: number | null; demais: number | null; piores: number | null; contraste: number | null; nMelhores: number; nPiores: number }
/** Mediana de cada métrica no quartil de menor indicador ("melhores"), no de maior ("piores") e no meio.
 *  contraste = (mediana dos piores − mediana dos melhores) ÷ IQR do universo: tamanho da diferença, não causa. */
export function perfilPorQuartil(universo: Linha[], ind: Indicador, ids: string[]): { linhas: PerfilLinha[]; cortes: { q1: number; q3: number } | null; n: number } {
  const com = universo.filter((l) => num(l[ind]));
  const r = resumo(com.map((l) => l[ind]));
  if (!r || com.length < 12) return { linhas: [], cortes: null, n: com.length };
  const melhores = com.filter((l) => (l[ind] as number) <= r.q1), piores = com.filter((l) => (l[ind] as number) >= r.q3);
  const demais = com.filter((l) => (l[ind] as number) > r.q1 && (l[ind] as number) < r.q3);
  const linhas = ids.map((id) => {
    const m = resumo(melhores.map((l) => l.infra[id])), p = resumo(piores.map((l) => l.infra[id])), d = resumo(demais.map((l) => l.infra[id])), u = resumo(com.map((l) => l.infra[id]));
    const iqr = u ? u.q3 - u.q1 : 0;
    return { id, melhores: m?.mediana ?? null, demais: d?.mediana ?? null, piores: p?.mediana ?? null, contraste: m && p && iqr > 0 ? (p.mediana - m.mediana) / iqr : null, nMelhores: m?.n ?? 0, nPiores: p?.n ?? 0 };
  });
  return { linhas, cortes: { q1: r.q1, q3: r.q3 }, n: com.length };
}

// ------------------------------------------------------------------ alimentadores
export interface Faixa { rotulo: string; n: number; km: number }
/** Faixas de extensão dos alimentadores dentro do conjunto. Os limiares são parâmetros de leitura, não padrão regulatório. */
export function faixasDeExtensao(kms: Array<number | null>, limiares: [number, number] = [10, 40]): Faixa[] {
  const [a, b] = limiares;
  const f: Faixa[] = [{ rotulo: `curtos (até ${a} km)`, n: 0, km: 0 }, { rotulo: `médios (${a} a ${b} km)`, n: 0, km: 0 }, { rotulo: `longos (mais de ${b} km)`, n: 0, km: 0 }];
  for (const k of kms) { if (!num(k) || k <= 0) continue; const i = k <= a ? 0 : k <= b ? 1 : 2; f[i].n++; f[i].km += k; }
  return f;
}

// ------------------------------------------------------------------ ranking
export type TipoRanking = "melhores" | "piores" | "melhorias" | "pioras" | "acima_limite";
export interface ItemRanking { linha: Linha; valor: number; anterior?: number | null }
export function ranking(atual: Linha[], anterior: Linha[] | null, ind: Indicador, tipo: TipoRanking, k = 15): ItemRanking[] {
  const ant = new Map((anterior ?? []).map((l) => [chave(l), l]));
  const itens: ItemRanking[] = [];
  for (const l of atual) {
    const v = l[ind];
    if (!num(v)) continue;
    if (tipo === "melhores" || tipo === "piores") itens.push({ linha: l, valor: v });
    else if (tipo === "acima_limite") { const r = razaoLimite(v, ind === "dec" ? l.ld : l.lf); if (r !== null) itens.push({ linha: l, valor: r }); }
    else { const p = ant.get(chave(l))?.[ind]; if (num(p)) itens.push({ linha: l, valor: v - p, anterior: p }); }
  }
  const crescente = tipo === "melhores" || tipo === "melhorias";
  itens.sort((a, b) => (crescente ? a.valor - b.valor : b.valor - a.valor) || a.linha.c - b.linha.c);
  return itens.slice(0, k);
}

// ------------------------------------------------------------------ formatação
export function fmtMetrica(v: number | null | undefined, m: Pick<MetricaDef, "tipo">): string {
  if (!num(v)) return "N/D";
  if (m.tipo === "contagem") return Number.isInteger(v) ? v.toLocaleString("pt-BR") : "valor inválido";
  if (m.tipo === "pct") return `${(v * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
  const abs = Math.abs(v);
  return v.toLocaleString("pt-BR", { maximumFractionDigits: abs >= 1000 ? 0 : abs >= 100 ? 1 : abs >= 1 ? 2 : 3 });
}
export const fmtInd = (v: number | null | undefined) => (num(v) ? v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "N/D");
export const UNIDADE_IND: Record<Indicador, string> = { dec: "h por consumidor", fec: "interrupções por consumidor" };
export const NOME_IND: Record<Indicador, string> = { dec: "DEC", fec: "FEC" };
export const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
export const ROTULO_ALERTA: Record<string, string> = {
  apuracao_parcial: "Apuração com menos de 12 meses no ano; o valor anual é parcial.",
  sem_limite: "Sem limite regulatório publicado para o ano.",
  consumidores_divergentes: "O número de consumidores da BDGD (31/12) difere em mais de 15% do NumCon de dezembro da ANEEL; as métricas por consumidor pedem cautela.",
  variacao_cadastral_uc: "Os consumidores cadastrados mudaram mais de 30% em relação ao ano anterior: possível reconfiguração do conjunto, não crescimento físico.",
  variacao_cadastral_km_mt: "A rede MT cadastrada mudou mais de 30% em relação ao ano anterior: possível reconfiguração do conjunto, não expansão física.",
};
