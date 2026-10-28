/** Homologação assistida (Fase 4) aplicada à Evolução: estado de publicação por ano × DIST × ativo, agregados elegíveis,
 * proveniência e sinais. Regras: nada é preenchido; célula não publicável vira N/D com motivo; soma nunca inclui célula
 * pendente/bloqueada nem predecessora já contida na sucessora ("não somar"). */
import type { CelulaSerie, Ponto, Serie } from "@/lib/evolucao";
import { lacunasNacionais, type EstadosContrato } from "./historico-contrato";

export type EstadoPub = "H" | "T" | "R" | "P" | "B" | "N";
export const PUBLICAVEL: ReadonlySet<string> = new Set(["H", "T", "R"]);
export const FLAG = { quebra: 1, sinal: 2, naoSomar: 4 } as const;
export const ROTULO_PUB: Record<EstadoPub, string> = {
  H: "pacote auditado", T: "validado automaticamente", R: "apto com ressalvas", P: "pendente de decisão", B: "bloqueado", N: "não disponível",
};
export const DESCRICAO_PUB: Record<EstadoPub, string> = {
  H: "Pacote 2025 com verificações técnicas concluídas; intervalo da base anual compatível. Não representa homologação regulatória.",
  T: "Validado pelas regras automáticas, sem sinal temporal ou ressalva. Não representa certificação patrimonial.",
  R: "Valor validado e exibido com ressalva (quebra, sinal temporal, intervalo da base ou anomalia).",
  P: "Sem valor publicado: aguarda decisão humana (publicações divergentes, base inconsistente ou anomalia comprovada).",
  B: "Sem valor publicado: arquivo de outra competência ou valor não homologável.",
  N: "Sem dado: distribuidora sem publicação no ano, ativo inexistente na base ou campo ausente. Nunca é zero.",
};
export const NATUREZA: Record<string, string> = {
  expansao_fisica: "expansão física (plausível)", mudanca_cadastral: "mudança cadastral", mudanca_classificacao: "mudança de classificação (TUC)",
  anomalia_publicacao: "anomalia na publicação", sucessao: "sucessão societária", base_pequena: "base pequena", sem_explicacao: "sem explicação",
};

export interface Publicacao { item: string; titulo: string; versao: string; data_base: string; inc: string; fnl: string; ext: string; intervalo: string; extra: string; sha: string; uso: string; decisao: string }
export interface Par { grupo: string; risco: string; ordem: number; ativos_dif: number; recomendacao: string; A: { item: string; versao: string }; B: { item: string; versao: string }; decisao: string; dif: Record<string, [number | null, number | null]> }
export interface Homologacao {
  versao: string; fonte: string; fontes: Record<string, string>; estados: Record<EstadoPub, string>; motivos: string[];
  celulas: Record<string, Array<[number, number, EstadoPub, number, number]>>;
  brasil: Record<string, Array<[number, number | null, EstadoPub, number, number, number[], number]>>;
  painel: Record<string, { universo: number[]; valores: Array<[number, number | null]> }>;
  proveniencia: Record<string, Publicacao[]>;
  sinais: Record<string, [string, string, string, number]>;
  pares: Record<string, Par>;
  pontes: Array<{ evento: string; tipo: string; destino: string; origem: string; status: string; regra: string; prova: string; efetivacao: string; fonte: string }>;
  absorcao_epb: Record<string, [number | null, number | null]>;
  sem_tuc: Record<string, number>;
}

/** Célula da série com o estado de publicação: [dist, ano, valor, estado_serie, quebra, estado_pub, motivo, flags]. */
export type CelulaHom = [number, number, number | null, string, number, EstadoPub, number, number];
export interface PontoHom extends Ponto { pub?: EstadoPub; motivo?: string; flags?: number }

export function indiceHom(h: Homologacao, ativo: string) {
  const m = new Map<string, [EstadoPub, number, number]>();
  for (const [d, ano, e, mi, fl] of h.celulas[ativo] ?? []) m.set(`${d}|${ano}`, [e, mi, fl]);
  return m;
}

/** Aplica a matriz: célula não publicável perde o valor (N/D) e recebe o estado; sem entrada na matriz = não disponível. */
export function aplicarMatriz(cel: CelulaSerie[] | undefined, ih: ReturnType<typeof indiceHom>): CelulaHom[] {
  return (cel ?? []).map(([d, ano, v, st, q]) => {
    const [e, mi, fl] = ih.get(`${d}|${ano}`) ?? (["N", -1, 0] as [EstadoPub, number, number]);
    const pub = PUBLICAVEL.has(e) && st === "v";
    const est = pub ? "v" : e === "P" ? (st === "r" ? "r" : "x") : e === "B" ? (st === "d" ? "d" : "b") : st === "v" ? "s" : st;
    return [d, ano, pub ? v : null, est, q || (fl & FLAG.quebra ? 1 : 0), e, mi, fl];
  });
}

/** Índice no formato de evolucao.indexar, preservando a célula estendida. */
export function indexarHom(cel: CelulaHom[]) {
  const m = new Map<number, Map<number, CelulaSerie>>();
  for (const c of cel) { let x = m.get(c[0]); if (!x) { x = new Map(); m.set(c[0], x); } x.set(c[1], c as unknown as CelulaSerie); }
  return m;
}

/** Enriquecimento dos pontos de uma série de DIST com estado, motivo e flags. */
export function pontosHom(s: Serie, h: Homologacao, ih: ReturnType<typeof indiceHom>, d: number): Serie {
  return { ...s, pontos: s.pontos.map((p) => { const x = ih.get(`${d}|${p.ano}`); return x ? { ...p, pub: x[0], motivo: h.motivos[x[1]], flags: x[2] } as PontoHom : { ...p, pub: "N" } as PontoHom; }) };
}

/** Brasil pelo agregado da matriz: só anos elegíveis; 2022–2023 nunca como total nacional. */
export function serieBrasil(h: Homologacao, ativo: string, anos: number[], contrato?: EstadosContrato): Serie {
  const linhas = new Map((h.brasil[ativo] ?? []).map((r) => [r[0], r]));
  return { id: "brasil", nome: "Brasil (cobertura completa)", nota: "N/D quando há lacunas; o painel balanceado não representa o total nacional", pontos: anos.map((ano) => {
    const r = linhas.get(ano);
    const lacunas = contrato ? lacunasNacionais(contrato, ativo, ano) : null;
    const pub = ano >= 2024 && !!r && PUBLICAVEL.has(r[2]) && r[1] !== null && r[4] === 0 &&
      lacunas === 0 && (contrato?.celulas[ativo]?.some((c) => c[1] === ano) ?? false);
    return { ano, v: pub ? r![1] : null, estado: pub ? "v" : "g", quebra: false, pub: pub ? r![2] : "N",
      motivo: !pub ? `Total nacional indisponível: ${lacunas ?? "cobertura não comprovada"}${lacunas === null ? "" : " DIST com lacunas"}. Use o painel balanceado identificado.` : h.motivos[r![6]] } as PontoHom;
  }) };
}

export function seriePainel(h: Homologacao, ativo: string, anos: number[]): Serie | null {
  const p = h.painel[ativo];
  if (!p || !p.universo.length) return null;
  const v = new Map(p.valores);
  return { id: "painel", nome: `Painel balanceado (${p.universo.length} distribuidoras)`, nota: "mesmas distribuidoras nos quatro anos; não representa o total nacional",
    pontos: anos.map((ano) => ({ ano, v: v.get(ano) ?? null, estado: v.get(ano) === undefined ? "s" : "v", quebra: false, pub: "R" }) as PontoHom) };
}

/** Subtotal das DIST com valores elegiveis em cada ano, sem exigir cobertura nacional completa.
 * Nao equivale ao total Brasil; comparacoes temporais sao bloqueadas se o conjunto de DIST mudar.
 * Flag 4 preserva a regra de nao duplicar predecessor ja contido na sucessora. */
export function serieSubtotalObservado(idx: ReturnType<typeof indexarHom>, anos: number[]): Serie {
  let anterior: string | null = null;
  const pontos: PontoHom[] = anos.map((ano) => {
    let soma = 0;
    const membros: number[] = [];
    for (const [dist, serie] of idx) {
      const c = serie.get(ano);
      if (typeof c?.[7] === "number" && (c[7] & 4)) continue;
      if (c?.[3] !== "v" || typeof c[2] !== "number") continue;
      soma += c[2];
      membros.push(dist);
    }
    membros.sort((a, b) => a - b);
    const chave = membros.join(",");
    const ruptura = anterior !== null && anterior !== chave;
    anterior = chave;
    return {
      ano, v: membros.length ? soma : null, estado: membros.length ? "v" : "s",
      quebra: ruptura, motivo: `Subtotal de ${membros.length} distribuidoras com valores validos no ano; universo variavel; nao e total nacional.`,
    };
  });
  return { id: "subtotal", nome: "Subtotal observado (cobertura variável)",
    nota: "DIST disponíveis em cada ano; não representa o total nacional. Quebras de composição impedem variações comparáveis.", pontos };
}

/** Contagem de estados de publicação por ano para um ativo (cobertura e qualidade). */
export function coberturaAtivo(h: Homologacao, ativo: string, anos: number[], dists?: number[]) {
  const alvo = dists ? new Set(dists) : null;
  return anos.map((ano) => {
    const c: Record<EstadoPub, number> = { H: 0, T: 0, R: 0, P: 0, B: 0, N: 0 };
    for (const [d, a, e] of h.celulas[ativo] ?? []) if (a === ano && (!alvo || alvo.has(d))) c[e]++;
    return { ano, ...c, publicaveis: c.H + c.T + c.R };
  });
}

/** Natureza de cada variação anual de uma DIST, a partir do ranking de sinais da Fase 4. */
export function naturezaVariacoes(h: Homologacao, dist: number, ativo: string, anos: number[]) {
  return anos.slice(1).map((ano) => {
    const s = h.sinais[`${dist}|${ativo}|${ano - 1}|${ano}`];
    return { ano, natureza: s?.[0] ?? null, confianca: s?.[1] ?? null, causa: s?.[2] ?? null, prioridade: s?.[3] ?? null };
  });
}

/** Sinais de um conjunto de DIST numa transição anual (para agregados). */
export function sinaisNoEscopo(h: Homologacao, dists: number[], ativo: string, anos: number[]) {
  return anos.slice(1).map((ano) => {
    const c: Record<string, number> = {};
    for (const d of dists) { const s = h.sinais[`${d}|${ativo}|${ano - 1}|${ano}`]; if (s) c[s[0]] = (c[s[0]] ?? 0) + 1; }
    return { ano, contagem: c, total: Object.values(c).reduce((a, b) => a + b, 0) };
  });
}

export const urlItem = (item: string) => `https://www.arcgis.com/home/item.html?id=${encodeURIComponent(item)}`;
