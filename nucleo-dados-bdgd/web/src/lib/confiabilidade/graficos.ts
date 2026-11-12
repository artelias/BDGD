import type { EChartsCoreOption } from "echarts/core";
import type { ChartTokens } from "@/components/charts/EChart";

/** Construtores de opções ECharts do módulo. Um eixo por gráfico; cores de série vindas dos tokens; grade e eixos discretos. */
const base = (t: ChartTokens) => ({
  textStyle: { fontFamily: t.font, color: t.text2 },
  grid: { left: 8, right: 16, top: 28, bottom: 6, containLabel: true },
  tooltip: { trigger: "axis" as const, backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontSize: 12 }, axisPointer: { type: "line" as const, lineStyle: { color: t.hairline } }, confine: true },
});
const eixoCat = (t: ChartTokens, data: string[]) => ({ type: "category" as const, data, axisLine: { lineStyle: { color: t.hairline } }, axisTick: { show: false }, axisLabel: { color: t.text3, fontSize: 11 } });
const eixoVal = (t: ChartTokens, nome?: string) => ({ type: "value" as const, name: nome, nameTextStyle: { color: t.text3, fontSize: 11, align: "left" as const }, splitLine: { lineStyle: { color: t.hairline, opacity: 0.6 } }, axisLabel: { color: t.text3, fontSize: 11, formatter: (v: number) => v.toLocaleString("pt-BR") } });
const br = (v: unknown, d = 2) => (typeof v === "number" ? v.toLocaleString("pt-BR", { maximumFractionDigits: d }) : "N/D");
const legendaTopo = (t: ChartTokens) => ({ top: 0, left: 0, itemWidth: 14, itemHeight: 8, textStyle: { color: t.text2, fontSize: 11 } });

/** Acumulado no ano contra o limite anual (mesma unidade, um eixo). */
export function acumuladoNoAno(t: ChartTokens, p: { meses: string[]; atual: Array<number | null>; anterior: Array<number | null> | null; limite: number | null; rotAtual: string; rotAnterior: string; unidade: string }): EChartsCoreOption {
  return {
    ...base(t), legend: legendaTopo(t), xAxis: eixoCat(t, p.meses), yAxis: eixoVal(t, p.unidade),
    tooltip: { ...base(t).tooltip, valueFormatter: (v: unknown) => br(v) },
    series: [
      { name: p.rotAtual, type: "line", data: p.atual, symbolSize: 6, lineStyle: { width: 2, color: t.accent }, itemStyle: { color: t.accent }, connectNulls: false,
        markLine: p.limite === null ? undefined : { silent: true, symbol: "none", lineStyle: { color: t.warn, type: "dashed", width: 1.5 }, label: { formatter: `limite anual ${br(p.limite)}`, color: t.warn, fontSize: 11, position: "insideEndTop" }, data: [{ yAxis: p.limite }] } },
      ...(p.anterior ? [{ name: p.rotAnterior, type: "line" as const, data: p.anterior, symbolSize: 4, lineStyle: { width: 1.5, color: t.text3, type: "dashed" as const }, itemStyle: { color: t.text3 }, connectNulls: false }] : []),
    ],
  };
}

/** Apurado por ano e o limite de cada ano (barras e marcadores na mesma escala). */
export function anualContraLimite(t: ChartTokens, p: { anos: string[]; obs: Array<number | null>; lim: Array<number | null>; unidade: string; nome: string }): EChartsCoreOption {
  return {
    ...base(t), legend: legendaTopo(t), xAxis: eixoCat(t, p.anos), yAxis: eixoVal(t, p.unidade),
    tooltip: { ...base(t).tooltip, valueFormatter: (v: unknown) => br(v) },
    series: [
      { name: `${p.nome} apurado`, type: "bar", data: p.obs, barMaxWidth: 34, itemStyle: { color: t.accent, borderRadius: [4, 4, 0, 0] }, label: { show: true, position: "top", color: t.text2, fontSize: 11, formatter: (x: { value: unknown }) => br(x.value) } },
      { name: "Limite regulatório", type: "line", data: p.lim, symbol: "rect", symbolSize: [30, 3], lineStyle: { width: 0 }, itemStyle: { color: t.warn } },
    ],
  };
}

export function barrasSimples(t: ChartTokens, p: { rotulos: string[]; valores: number[]; unidade?: string; destaque?: number | null }): EChartsCoreOption {
  return {
    ...base(t), xAxis: { ...eixoCat(t, p.rotulos), axisLabel: { color: t.text3, fontSize: 10, hideOverlap: true } }, yAxis: eixoVal(t, p.unidade),
    tooltip: { ...base(t).tooltip, valueFormatter: (v: unknown) => br(v, 0) },
    series: [{ type: "bar", data: p.valores.map((v, i) => ({ value: v, itemStyle: { color: i === p.destaque ? t.text : t.accent, borderRadius: [3, 3, 0, 0] } })), barCategoryGap: "12%" }],
  };
}

/** Séries anuais sobrepostas (A × B ou conjunto × referência), mesma unidade. */
export function linhasAnuais(t: ChartTokens, p: { anos: string[]; series: Array<{ nome: string; dados: Array<number | null>; cor: string; tracejada?: boolean }>; unidade: string }): EChartsCoreOption {
  return {
    ...base(t), legend: legendaTopo(t), xAxis: eixoCat(t, p.anos), yAxis: eixoVal(t, p.unidade), tooltip: { ...base(t).tooltip, valueFormatter: (v: unknown) => br(v) },
    series: p.series.map((s) => ({ name: s.nome, type: "line", data: s.dados, symbolSize: 7, connectNulls: false, lineStyle: { width: 2, color: s.cor, type: s.tracejada ? "dashed" : "solid" }, itemStyle: { color: s.cor } })),
  };
}

export type Ponto = [number, number, string];
/** Dispersão: cada ponto é um conjunto. Fundo = universo; destaque = seleção. Eixos nomeados com unidade. */
export function dispersao(t: ChartTokens, p: { fundo: Ponto[]; destaque: Ponto[]; marcados: Array<{ ponto: Ponto; cor: string }>; nomeX: string; nomeY: string; logX: boolean; rotFundo: string; rotDestaque: string }): EChartsCoreOption {
  const comum = { name: p.nomeX, nameLocation: "middle" as const, nameGap: 26, nameTextStyle: { color: t.text3, fontSize: 11 }, splitLine: { lineStyle: { color: t.hairline, opacity: 0.5 } }, axisLabel: { color: t.text3, fontSize: 11, formatter: (v: number) => v.toLocaleString("pt-BR") } };
  return {
    textStyle: { fontFamily: t.font, color: t.text2 }, grid: { left: 8, right: 18, top: 30, bottom: 30, containLabel: true }, legend: { ...legendaTopo(t), itemWidth: 10, itemHeight: 10 },
    tooltip: { trigger: "item", backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontSize: 12 }, confine: true,
      formatter: (x: { value: Ponto }) => `<b>${x.value[2]}</b><br/>${p.nomeX}: ${br(x.value[0])}<br/>${p.nomeY}: ${br(x.value[1])}` },
    xAxis: p.logX ? { type: "log", ...comum } : { type: "value", ...comum }, yAxis: eixoVal(t, p.nomeY),
    series: [
      { name: p.rotFundo, type: "scatter", data: p.fundo, symbolSize: 5, itemStyle: { color: t.text3, opacity: 0.28 } },
      { name: p.rotDestaque, type: "scatter", data: p.destaque, symbolSize: 8, itemStyle: { color: t.accent, opacity: 0.85, borderColor: t.surface, borderWidth: 1 } },
      ...p.marcados.map((mk) => ({ name: mk.ponto[2], type: "scatter" as const, data: [mk.ponto], symbolSize: 14, itemStyle: { color: mk.cor, borderColor: t.surface, borderWidth: 2 }, label: { show: true, formatter: mk.ponto[2], position: "top" as const, color: t.text, fontSize: 11 }, z: 5 })),
    ],
  };
}
