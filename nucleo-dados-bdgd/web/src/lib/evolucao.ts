/** Evolução 2022–2025: somente valores observados e validados; nada é preenchido, interpolado ou projetado. */

/** [dist, ano, valor, estado, quebra, ...extensão da homologação] — estado: v validado, a ausente, c campo ausente, b bloqueado,
 * r revisão pendente, p não processado, d competência divergente, s sem publicação, x pendente de decisão humana, g agregado não elegível.
 * A extensão (lib/homologacao: estado de publicação, motivo, flags) é opcional. */
export type CelulaSerie = [number, number, number | null, string, number, ...Array<string | number>];
export interface SerieData {
  anos: number[]; gerado_em: string; versao_regra: string;
  cobertura: Array<{ ano: number; publicadas: number; validadas: number; pendentes: number; competencia_divergente: number; status_ano: string }>;
  nomes: Record<string, string>;
  original: Record<string, CelulaSerie[]>;
  perimetro: Record<string, CelulaSerie[]>;
  eventos: Array<{ evento_id: string; tipo_evento: string; dist_destino_2025: number; dist_origem: number; data_efetivacao: string; fonte_oficial: string }>;
  ponte: Array<{ ano_base: number; dist_origem: number; dist_destino_2025: number; evento_id: string; status_qualidade: string; prova_disjuncao: string }>;
  notas: Record<string, string>;
}

export const ESTADO: Record<string, string> = {
  v: "validado", a: "ativo inexistente nesta competência", c: "campo ausente no layout do ano", b: "valor não homologável",
  r: "mais de uma publicação válida (revisão pendente)", p: "processamento histórico em andamento", d: "arquivo de outra competência", s: "sem publicação da ANEEL neste ano",
  x: "pendente de decisão humana", g: "não é total nacional completo neste ano",
  n: "não aplicável", nao_aplicavel: "não aplicável", ausente: "N/D — dado ausente",
  nao_homologado: "não homologado", observado: "observado", zero_verificado: "zero técnico (verificação independente pendente)",
};

/** Status do ano na cobertura: "homologado" (decisão humana registrada, hoje só 2025), "completo_tecnico" (todas as
 * publicações elegíveis validadas pelas regras automáticas, sem homologação humana) e "parcial". */
export const STATUS_ANO: Record<string, string> = { homologado: "homologado", completo_tecnico: "completo (validação automática)", parcial: "em validação" };

/** Ano com todas as publicações elegíveis validadas: o agregado Brasil pode ser exibido (homologado ou completo técnico). */
export function anoCompleto(statusAno: string | undefined) {
  return statusAno === "homologado" || statusAno === "completo_tecnico";
}

export interface Ponto { ano: number; v: number | null; estado: string; quebra: boolean }
export interface Serie { id: string; nome: string; pontos: Ponto[]; nota?: string }

/** Índice das células por DIST para um ativo e visão (original ou perímetro 2025). */
export function indexar(cel: CelulaSerie[] | undefined) {
  const m = new Map<number, Map<number, CelulaSerie>>();
  for (const c of cel ?? []) { let x = m.get(c[0]); if (!x) { x = new Map(); m.set(c[0], x); } x.set(c[1], c); }
  return m;
}

export function serieDist(idx: ReturnType<typeof indexar>, d: number, anos: number[], nome: string): Serie {
  const x = idx.get(d);
  return { id: String(d), nome, pontos: anos.map((ano) => { const c = x?.get(ano); return { ano, v: c && c[3] === "v" ? c[2] : null, estado: c ? c[3] : "s", quebra: !!c?.[4] }; }) };
}

/** Soma de várias DIST num ano só quando TODAS estão validadas (ou sem o ativo); senão o ano fica sem valor (nunca soma parcial). */
export function serieSoma(idx: ReturnType<typeof indexar>, dists: number[], anos: number[], id: string, nome: string): Serie {
  return { id, nome, pontos: anos.map((ano) => {
    let v = 0, algum = false, falta = false, quebra = false;
    for (const d of dists) {
      const c = idx.get(d)?.get(ano);
      if (typeof c?.[7] === "number" && c[7] & 4) continue; // predecessora já contida na sucessora: nunca somar (evita dupla contagem)
      if (c?.[3] === "n") continue;               // somente não aplicabilidade explícita do contrato não bloqueia
      if (!c) { falta = true; continue; }
      if (c[3] !== "v" || c[2] === null) { falta = true; continue; }
      v += c[2]; algum = true; if (c[4]) quebra = true;
    }
    return { ano, v: !falta && algum ? v : null, estado: falta ? "p" : algum ? "v" : "s", quebra };
  }) };
}

/** Distribuidoras com os quatro anos validados para o ativo (painel balanceado, comparável no tempo). */
export function painelBalanceado(idx: ReturnType<typeof indexar>, dists: number[], anos: number[]): number[] {
  return dists.filter((d) => anos.every((a) => { const c = idx.get(d)?.get(a); return !!c && c[3] === "v" && c[2] !== null; }));
}

export interface Variacao { abs: number | null; pct: number | null; cagr: number | null; motivo: string | null }
/** Variação entre o primeiro e o último ano com valor; CAGR só com base > 0, intervalo ≥ 1 ano e sem quebra no caminho. */
export function variacao(s: Serie): Variacao {
  const com = s.pontos.filter((p) => p.v !== null);
  if (com.length < 2) return { abs: null, pct: null, cagr: null, motivo: "menos de dois anos com valor validado" };
  const ini = com[0], fim = com[com.length - 1];
  const quebra = s.pontos.some((p) => p.quebra && p.ano > ini.ano && p.ano <= fim.ano);
  const abs = fim.v! - ini.v!;
  if (quebra) return { abs: null, pct: null, cagr: null, motivo: "quebra de classificação ou de perímetro no intervalo" };
  if (ini.v! <= 0) return { abs, pct: null, cagr: null, motivo: "base zero: variação percentual indefinida" };
  const n = fim.ano - ini.ano;
  return { abs, pct: abs / ini.v!, cagr: fim.v! > 0 ? Math.pow(fim.v! / ini.v!, 1 / n) - 1 : null, motivo: null };
}

/** Variação ano a ano (só entre anos consecutivos com valor e sem quebra no ano final). */
export function anoAno(s: Serie): Array<{ ano: number; pct: number | null }> {
  return s.pontos.slice(1).map((p, i) => {
    const a = s.pontos[i];
    if (p.v === null || a.v === null || p.quebra || a.v <= 0) return { ano: p.ano, pct: null };
    return { ano: p.ano, pct: (p.v - a.v) / a.v };
  });
}

/** Índice base 100 no primeiro ano com valor (para comparar trajetórias de portes diferentes). */
export function indice100(s: Serie): Serie {
  const b = s.pontos.find((p) => p.v !== null && p.v > 0);
  return { ...s, pontos: s.pontos.map((p) => ({ ...p, v: b && p.v !== null ? (p.v / b.v!) * 100 : null })) };
}
