import type { Metric } from "./types";

const LOCALE = "pt-BR";
const nf0 = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 2 });
const compact = new Intl.NumberFormat(LOCALE, { notation: "compact", maximumFractionDigits: 1 });

export const ND = "N/D";

export const METRIC_LABEL: Record<Metric, string> = {
  quantidade: "Quantidade",
  quantidade_registros: "Registros",
  quantidade_cod_id_distinto: "COD_ID distintos",
  extensao_km: "Extensão",
  potencia_kva: "Potência",
};

export const METRIC_UNIT: Record<Metric, string> = {
  quantidade: "itens",
  quantidade_registros: "registros",
  quantidade_cod_id_distinto: "códigos",
  extensao_km: "km",
  potencia_kva: "kVA",
};

/** Número completo, com separadores pt-BR. Nulo -> N/D (nunca zero). */
export function fmt(v: number | null | undefined, metric?: Metric): string {
  if (v === null || v === undefined || Number.isNaN(v)) return ND;
  if (metric === "extensao_km") return v < 100 ? nf1.format(v) : nf0.format(v);
  if (metric === "potencia_kva") return nf0.format(v);
  return Number.isInteger(v) ? nf0.format(v) : nf2.format(v);
}

/** Valor + unidade legível. Potência grande é exibida em MVA com a unidade explícita. */
export function fmtUnit(v: number | null | undefined, metric: Metric): { value: string; unit: string } {
  if (v === null || v === undefined) return { value: ND, unit: "" };
  if (metric === "potencia_kva" && Math.abs(v) >= 10_000) return { value: nf0.format(v / 1000), unit: "MVA" };
  return { value: fmt(v, metric), unit: METRIC_UNIT[metric] === "itens" ? "" : METRIC_UNIT[metric] };
}

/** Valor compacto + unidade para números de destaque (≥ 1 milhão vira "mi", ≥ 100 mil vira "mil"). */
export function fmtUnitCompact(v: number | null | undefined, metric: Metric): { value: string; unit: string } {
  if (v === null || v === undefined) return { value: ND, unit: "" };
  let x = v, unit = METRIC_UNIT[metric] === "itens" ? "" : METRIC_UNIT[metric];
  if (metric === "potencia_kva" && Math.abs(v) >= 10_000) { x = v / 1000; unit = "MVA"; }
  if (metric === "quantidade_registros" || metric === "quantidade_cod_id_distinto") unit = "";
  const value = Math.abs(x) >= 100_000 ? compact.format(x) : fmt(x, metric === "potencia_kva" ? "potencia_kva" : metric);
  return { value, unit };
}

export function fmtCompact(v: number | null | undefined, metric?: Metric): string {
  if (v === null || v === undefined) return ND;
  if (metric === "potencia_kva" && Math.abs(v) >= 10_000) return `${compact.format(v / 1000)} MVA`;
  const s = Math.abs(v) < 10_000 ? fmt(v, metric) : compact.format(v);
  if (metric === "extensao_km") return `${s} km`;
  if (metric === "potencia_kva") return `${s} kVA`;
  return s;
}

export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return ND;
  return `${v > 0 ? "+" : ""}${new Intl.NumberFormat(LOCALE, { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(v * 100)}%`;
}

export function fmtShare(v: number): string {
  return `${new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 }).format(v * 100)}%`;
}

export function fmtDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export function fmtArea(km2: number | null | undefined) {
  if (km2 === null || km2 === undefined) return ND;
  return `${nf0.format(km2)} km²`;
}

/** Diferença A − B e variação relativa a B. Sem percentual se B = 0 ou se algum lado é N/D. */
export function diff(a: number | null, b: number | null) {
  if (a === null || b === null) return { abs: null, rel: null };
  return { abs: a - b, rel: b === 0 ? null : (a - b) / b };
}

export function csvEscape(s: string | number | null | undefined) {
  const t = s === null || s === undefined ? "" : String(s);
  return /[",\n;]/.test(t) ? `"${t.replaceAll('"', '""')}"` : t;
}

export function toCSV(header: string[], rows: Array<Array<string | number | null>>) {
  return [header.map(csvEscape).join(","), ...rows.map((r) => r.map(csvEscape).join(","))].join("\n") + "\n";
}
