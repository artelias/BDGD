"use client";
import type { EChartsCoreOption, ECharts } from "echarts/core";
import { useEffect, useRef, useState } from "react";
import { useTheme } from "@/lib/theme";

type EchartsModule = typeof import("echarts/core");
let mod: Promise<EchartsModule> | null = null;
/** Carrega só os módulos usados (barras, radar, grade, tooltip, aria) — sem o pacote completo. */
function loadEcharts() {
  if (!mod) {
    mod = (async () => {
      const [core, charts, comps, renderers] = await Promise.all([import("echarts/core"), import("echarts/charts"), import("echarts/components"), import("echarts/renderers")]);
      core.use([charts.BarChart, charts.RadarChart, charts.LineChart, charts.HeatmapChart, comps.RadarComponent, comps.LegendComponent, comps.VisualMapComponent, comps.GridComponent, comps.TooltipComponent, comps.AriaComponent, comps.MarkLineComponent, renderers.SVGRenderer]);
      return core;
    })();
  }
  return mod;
}

export interface ChartTokens { text: string; text2: string; text3: string; hairline: string; accent: string; surface: string; sideA: string; sideB: string; font: string; warn: string; nd: string }
export function chartTokens(): ChartTokens {
  const c = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  return { text: c("--text"), text2: c("--text-2"), text3: c("--text-3"), hairline: c("--hairline-strong"), accent: c("--accent"), surface: c("--surface"), sideA: c("--side-a"), sideB: c("--side-b"), font: c("--font-ui"), warn: c("--warn"), nd: c("--nd") };
}

export function EChart({ build, height, ariaLabel, onClickIndex, testId }: {
  build: (t: ChartTokens, reduce: boolean) => EChartsCoreOption; height: number | string; ariaLabel: string; onClickIndex?: (i: number) => void; testId?: string;
}) {
  const el = useRef<HTMLDivElement>(null);
  const inst = useRef<ECharts | null>(null);
  const { resolved } = useTheme();
  const [ready, setReady] = useState(false);
  const click = useRef(onClickIndex);
  useEffect(() => { click.current = onClickIndex; });

  useEffect(() => {
    let alive = true; let ro: ResizeObserver | null = null;
    loadEcharts().then((ec) => {
      if (!alive || !el.current) return;
      inst.current = ec.init(el.current, undefined, { renderer: "svg" });
      inst.current.on("click", (p) => { if (typeof p.dataIndex === "number") click.current?.(p.dataIndex); });
      ro = new ResizeObserver(() => inst.current?.resize());
      ro.observe(el.current);
      setReady(true);
    });
    return () => { alive = false; ro?.disconnect(); inst.current?.dispose(); inst.current = null; };
  }, []);

  useEffect(() => {
    if (!ready || !inst.current) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const opt = build(chartTokens(), reduce);
    inst.current.setOption({ animation: !reduce, animationDuration: 420, animationDurationUpdate: 360, animationEasingUpdate: "cubicOut", aria: { enabled: true, label: { description: ariaLabel } }, ...opt }, { notMerge: false, replaceMerge: ["series", "xAxis", "yAxis"] });
  }, [build, ready, resolved, ariaLabel]);

  return <div ref={el} style={{ width: "100%", minWidth: 0, overflow: "hidden", height }} role="img" aria-label={ariaLabel} data-testid={testId} />;
}
