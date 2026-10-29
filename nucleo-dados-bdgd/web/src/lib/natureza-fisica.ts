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

/** USO EXCLUSIVO DE PRODUTORES de dados (geração do produto): contagem publicável a partir de um valor bruto, meio para cima
 *  (Math.round arredonda .5 para +∞), nunca negativo. Nenhuma tela, exportação ou parser deve chamá-la: na borda uma fração é erro. */
export function arredondarContagem(valor: number): number {
  if (!Number.isFinite(valor) || valor < 0) throw Error(`Previsão negativa ou não finita rejeitada: ${valor}`);
  return Math.round(valor);
}

/** Valor que pode aparecer em saída pública. Na borda NÃO arredonda: contagem fracionária ou negativa é recusada (erro de contrato);
 *  nas demais naturezas o valor passa inalterado. */
export const valorPublico = (valor: number, natureza: Natureza, onde = "saída pública") => ehContagem(natureza) ? exigirContagemInteira(valor, onde) : valor;

/** Barreira dos dados: uma contagem fracionária em produto público é um erro de contrato, não algo a arredondar em silêncio. */
export function exigirContagemInteira(valor: number, onde: string): number {
  if (!Number.isInteger(valor) || valor < 0) throw Error(`Contagem fracionária ou negativa em ${onde}: ${valor}`);
  return valor;
}

/** Casas decimais de exibição: 0 para contagens; 1 para extensão/potência/energia; 3 para razões. */
export const casasDe = (n: Natureza) => ehContagem(n) ? 0 : n === "ratio" ? 3 : 1;

/** Exibição. Contagem fracionária lança erro em vez de ser arredondada em silêncio; os parsers já a recusam antes. */
export function formatarFisico(valor: number | null | undefined, natureza: Natureza): string {
  if (valor == null) return "N/D";
  if (ehContagem(natureza)) exigirContagemInteira(valor, "exibição");
  return valor.toLocaleString("pt-BR", { maximumFractionDigits: casasDe(natureza) });
}

/** Natureza e unidade esperadas de cada nome de métrica do contrato nacional. */
const METRICA_NATUREZA: Record<string, Natureza> = { quantidade: "discrete_count", extensao_km: "continuous_length", potencia_kva: "continuous_capacity" };
const METRICA_UNIDADE: Record<string, string> = { extensao_km: "km", potencia_kva: "kva" };
const NATUREZAS: readonly string[] = ["discrete_count", "continuous_length", "continuous_capacity", "continuous_energy", "ratio"];

/** Barreira de coerência entre natureza declarada, unidade e métrica. Nada é corrigido: qualquer divergência é erro. */
export function exigirCoerencia(m: { natureza?: unknown; unidade?: unknown; metrica?: unknown }, onde: string): Natureza {
  const unidade = typeof m.unidade === "string" ? m.unidade.trim() : "";
  const metrica = typeof m.metrica === "string" ? m.metrica : "";
  if (m.natureza !== undefined && (typeof m.natureza !== "string" || !NATUREZAS.includes(m.natureza))) throw Error(`Natureza física inválida em ${onde}: ${String(m.natureza)}`);
  const doMetrica = METRICA_NATUREZA[metrica];
  const daUnidade = unidade ? naturezaDe(unidade) : undefined;
  const declarada = m.natureza as Natureza | undefined;
  const natureza = declarada ?? daUnidade ?? doMetrica;
  if (!natureza) throw Error(`Natureza física não determinável em ${onde}`);
  if (declarada && daUnidade && declarada !== daUnidade) throw Error(`Natureza ${declarada} incompatível com a unidade ${unidade} em ${onde}`);
  if (doMetrica && doMetrica !== natureza) throw Error(`Natureza ${natureza} incompatível com a métrica ${metrica} em ${onde}`);
  if (unidade && METRICA_UNIDADE[metrica] && unidade.toLowerCase() !== METRICA_UNIDADE[metrica]) throw Error(`Unidade ${unidade} incompatível com a métrica ${metrica} em ${onde}`);
  return natureza;
}
