/** Contrato de natureza física das métricas (espelho de motor_v2/metric_contract.py).
 *  Contagens (clientes, UC, transformadores, postes, dispositivos) são inteiros não negativos em qualquer gráfico, tabela, CSV ou JSON
 *  público. Extensão, potência, energia e razões mantêm decimais. Unidade sem natureza declarada é erro, nunca um padrão. */
export type Natureza = "discrete_count" | "continuous_length" | "continuous_capacity" | "continuous_energy" | "ratio";

const UNIDADES: Record<string, Natureza> = {
  clientes: "discrete_count", customers: "discrete_count", uc: "discrete_count", ucs: "discrete_count", itens: "discrete_count",
  items: "discrete_count", unidades: "discrete_count", quantidade: "discrete_count",
  km: "continuous_length", m: "continuous_length", metros: "continuous_length",
  kva: "continuous_capacity", mva: "continuous_capacity", mw: "continuous_capacity", kw: "continuous_capacity",
  kwh: "continuous_energy", mwh: "continuous_energy", gwh: "continuous_energy",
  "%": "ratio", fraction: "ratio", ratio: "ratio",
};

export function naturezaDe(unidade: string): Natureza {
  const n = UNIDADES[unidade.trim().toLowerCase()];
  if (!n) throw Error(`Unidade sem natureza física declarada: ${unidade}`);
  return n;
}
export const ehContagem = (n: Natureza) => n === "discrete_count";

/** Contagem publicável a partir de um valor bruto: meio para cima (Math.round arredonda .5 para +∞), nunca negativo. */
export function arredondarContagem(valor: number): number {
  if (!Number.isFinite(valor) || valor < 0) throw Error(`Previsão negativa ou não finita rejeitada: ${valor}`);
  return Math.round(valor);
}

/** Valor que pode aparecer em saída pública: inteiro para contagens, inalterado para as demais naturezas. */
export const valorPublico = (valor: number, natureza: Natureza) => ehContagem(natureza) ? arredondarContagem(valor) : valor;

/** Barreira dos dados: uma contagem fracionária em produto público é um erro de contrato, não algo a arredondar em silêncio. */
export function exigirContagemInteira(valor: number, onde: string): number {
  if (!Number.isInteger(valor) || valor < 0) throw Error(`Contagem fracionária ou negativa em ${onde}: ${valor}`);
  return valor;
}

/** Casas decimais de exibição: 0 para contagens; 1 para extensão/potência/energia; 3 para razões. */
export const casasDe = (n: Natureza) => ehContagem(n) ? 0 : n === "ratio" ? 3 : 1;

export function formatarFisico(valor: number | null | undefined, natureza: Natureza): string {
  if (valor == null) return "N/D";
  const v = ehContagem(natureza) ? Math.round(valor) : valor;
  return v.toLocaleString("pt-BR", { maximumFractionDigits: casasDe(natureza) });
}
