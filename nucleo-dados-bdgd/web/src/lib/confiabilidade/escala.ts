/** Classes e cores do mapa e dos gráficos de continuidade. Valores maiores = pior continuidade (nunca invertido).
 *  Valor absoluto: sequencial de um matiz (azul), claro → escuro no tema claro e escuro → claro no tema escuro.
 *  Desempenho regulatório (observado ÷ limite): divergente azul ↔ vermelho com cinza neutro em torno de 1,0. */

export type Tema = "light" | "dark";
export type ModoCor = "absoluto" | "regulatorio";

export const SEQ: Record<Tema, string[]> = {
  light: ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"],
  dark: ["#16345c", "#1c5cab", "#3987e5", "#86b6ef", "#d6e8fd"],
};
/** Limites superiores das classes de observado ÷ limite; a classe central (0,95–1,05) é "no limite". */
export const QUEBRAS_REG = [0.5, 0.75, 0.95, 1.05, 1.25, 1.5];
export const DIV: Record<Tema, string[]> = {
  light: ["#1c5cab", "#5598e7", "#b7d3f6", "#d7d6d0", "#f3b9ae", "#de6f60", "#ab2d22"],
  dark: ["#3987e5", "#2a66b0", "#1f4573", "#55554f", "#7a3a33", "#c65a4c", "#f08a7a"],
};
export const COR_ND: Record<Tema, string> = { light: "#e4e3de", dark: "#2a2c30" };

/** Quebras por quantis (n classes → n−1 quebras), sobre os valores presentes. Menos de n valores distintos reduz as classes. */
export function quebrasQuantis(valores: Array<number | null | undefined>, n = 5): number[] {
  const v = valores.filter((x): x is number => typeof x === "number" && Number.isFinite(x)).sort((a, b) => a - b);
  if (v.length < 2) return [];
  const out: number[] = [];
  for (let i = 1; i < n; i++) {
    const q = v[Math.min(v.length - 1, Math.floor((i * v.length) / n))];
    if (!out.length || q > out[out.length - 1]) out.push(q);
  }
  return out.filter((q) => q > v[0]);
}

/** Índice da classe: v < quebras[0] → 0; … ; v ≥ última quebra → quebras.length. */
export function classeDe(v: number | null | undefined, quebras: number[]): number | null {
  if (typeof v !== "number" || !Number.isFinite(v)) return null;
  let i = 0;
  while (i < quebras.length && v >= quebras[i]) i++;
  return i;
}

export function corDe(v: number | null | undefined, quebras: number[], modo: ModoCor, tema: Tema): string {
  const k = classeDe(v, modo === "regulatorio" ? QUEBRAS_REG : quebras);
  if (k === null) return COR_ND[tema];
  if (modo === "regulatorio") return DIV[tema][k];
  const rampa = SEQ[tema];
  // com menos quebras que cores, espalha as classes pela rampa inteira
  const n = quebras.length + 1;
  return rampa[n <= 1 ? 2 : Math.round((k * (rampa.length - 1)) / (n - 1))];
}

export interface ItemLegenda { cor: string; rotulo: string }
export function legenda(quebras: number[], modo: ModoCor, tema: Tema, fmt: (v: number) => string): ItemLegenda[] {
  if (modo === "regulatorio") {
    const q = QUEBRAS_REG, p = (x: number) => `${Math.round(x * 100)}%`;
    return DIV[tema].map((cor, i) => ({ cor, rotulo: i === 0 ? `até ${p(q[0])}` : i === q.length ? `acima de ${p(q[q.length - 1])}` : i === 3 ? `no limite (${p(q[2])}–${p(q[3])})` : `${p(q[i - 1])}–${p(q[i])}` }));
  }
  const n = quebras.length + 1;
  return Array.from({ length: n }, (_, i) => ({
    cor: corDe(i === 0 ? (quebras[0] ?? 0) - 1 : quebras[i - 1], quebras, "absoluto", tema),
    rotulo: n === 1 ? "todos os valores" : i === 0 ? `menos de ${fmt(quebras[0])}` : i === n - 1 ? `${fmt(quebras[i - 1])} ou mais` : `${fmt(quebras[i - 1])} a ${fmt(quebras[i])}`,
  }));
}
