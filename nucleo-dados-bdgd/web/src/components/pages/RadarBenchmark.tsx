"use client";
import { Download } from "lucide-react";
import { useMemo } from "react";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { Button } from "@/components/ui/Button";
import { Explain } from "@/components/ui/Explain";
import { downloadText, useToast } from "@/components/ui/Feedback";
import { Segmented } from "@/components/ui/Segmented";
import { Value } from "@/components/ui/Value";
import { eixosRadar, REF_LABEL, type RefTipo } from "@/lib/benchmark";
import { indicador, PRESETS_INDICADORES } from "@/lib/catalogo";
import type { Dataset } from "@/lib/dataset";
import { fmtCompact, METRIC_UNIT, toCSV } from "@/lib/format";
import type { Scope } from "@/lib/types";
import { useQueryState } from "@/lib/url-state";
import s from "./comparar.module.css";

type Side = Exclude<Scope, { tipo: "brasil" }>;
const pct = (x: number) => `${(x * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;

/** Radar · Benchmark: volume de A frente a uma referência, com o mesmo denominador (a referência) em cada eixo. */
export function RadarBenchmark({ ds, A, B }: { ds: Dataset; A: Side; B: Side }) {
  const toast = useToast();
  const [refQ, setRef] = useQueryState("ref", "bench_grupos");
  const [presetQ, setPreset] = useQueryState("eixos", "essenciais");
  const ref = (refQ in REF_LABEL ? refQ : "bench_grupos") as RefTipo;
  const preset = PRESETS_INDICADORES.find((x) => x.id === presetQ) ?? PRESETS_INDICADORES[0];
  const inds = useMemo(() => preset.ids.map((id) => indicador(id)).filter((x) => !!x), [preset]);
  const keyA = `${A.tipo}:${A.id}`, keyB = `${B.tipo}:${B.id}`;
  const labelA = ds.scopeLabel(A), labelB = ds.scopeLabel(B);
  const eixos = useMemo(() => eixosRadar(ds, inds, ds.scopeDists(A), ref, ds.scopeDists(B), labelB), [ds, inds, keyA, keyB, ref, labelB]); // eslint-disable-line react-hooks/exhaustive-deps
  const ok = eixos.filter((e) => e.nd === null);
  const refNome = ref === "lado" ? labelB : REF_LABEL[ref];
  const maxPct = Math.max(1, ...ok.map((e) => e.pctA ?? 0));

  const build = (t: ChartTokens) => ({
    legend: { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: t.text2, fontFamily: t.font, fontSize: 11 }, data: [labelA, refNome] },
    tooltip: { trigger: "item", backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
      formatter: (q: { name: string; value: number[] }) => `<b>${q.name}</b><br/>` + ok.map((e, i) => `${e.ind.nome}: ${pct(q.value[i])}`).join("<br/>") },
    radar: {
      radius: "64%", center: ["50%", "47%"], splitNumber: 4, shape: "polygon",
      indicator: ok.map((e) => ({ name: e.ind.nome, max: maxPct * 1.05, min: 0 })),
      axisName: { color: t.text2, fontFamily: t.font, fontSize: 11 },
      splitLine: { lineStyle: { color: t.hairline } }, splitArea: { show: false }, axisLine: { lineStyle: { color: t.hairline } },
    },
    series: [{
      type: "radar", symbolSize: 5,
      data: [
        { name: refNome, value: ok.map(() => 1), lineStyle: { color: t.sideB, width: 1.5, type: "dashed" }, itemStyle: { color: t.sideB }, areaStyle: { color: t.sideB, opacity: 0.06 } },
        { name: labelA, value: ok.map((e) => e.pctA), lineStyle: { color: t.sideA, width: 2 }, itemStyle: { color: t.sideA }, areaStyle: { color: t.sideA, opacity: 0.14 } },
      ],
    }],
  });

  const exportCSV = () => {
    const name = `bdgd_2025-12-31_radar_${keyA.replace(":", "-")}_x_${ref === "lado" ? keyB.replace(":", "-") : ref}.csv`;
    downloadText(name, toCSV(["data_base", "indicador", "entidade", "metrica", "unidade", "A", "A_dists_com_valor", "A_dists_total", "referencia", "referencia_valor", "A_sobre_referencia", "lider", "lider_valor", "lider_cobertura", "situacao"],
      eixos.map((e) => ["2025-12-31", e.ind.nome, e.ind.ent ?? "UCBT+UCMT+UCAT (união de códigos)", e.ind.metric, METRIC_UNIT[e.ind.metric] || "itens", e.a.v, e.a.n, e.a.total, e.refLabel, e.ref, e.pctA,
        e.lider?.nome ?? null, e.lider?.v ?? null, e.lider ? `${e.lider.n}/${e.lider.total}` : null, e.nd ?? "ok"])));
    toast(`${name} exportado`);
  };

  return (
    <section className={s.radar} aria-labelledby="radar-title" data-testid="radar">
      <div className={s.radarHead}>
        <div>
          <div className="eyebrow">Radar · Benchmark</div>
          <h2 className="title" id="radar-title" style={{ fontSize: "1.375rem", marginTop: 4 }}>Quem lidera em volume de ativos</h2>
          <p className="caption" style={{ marginTop: 4, maxWidth: 640, lineHeight: 1.5 }}>
            Maior volume por indicador. Em cada eixo, A e a referência são divididos pelo mesmo valor (o da referência): a referência fica em 100% e A pode passar de 100%. Volume maior não significa desempenho melhor.{" "}
            <Explain title="Como o radar é calculado" testId="radar-explain"
              tecnico="eixo_m = A_m / R_m, com R_m = B_m (lado B), T_m = Σ_d v_d,m (Brasil), MAX_g Σ_{d∈g} v_d,m (grupos verificados) ou MAX_d v_d,m (distribuidoras). Eixo removido se A_m ou R_m for N/D, ou se R_m = 0."
              ressalva="Somas de grupo usam só distribuidoras com valor homologado; a cobertura do líder aparece na tabela. Unidades (UN*) e equipamentos (EQ*) nunca são somados entre si.">
              Para cada indicador, o valor de A é comparado com uma referência: o lado B, o total do Brasil, o maior grupo econômico ou a maior distribuidora naquele indicador.
            </Explain>
          </p>
        </div>
        <div className={s.radarCtl}>
          <Segmented label="Referência" size="sm" value={ref} onChange={(v) => setRef(v)} options={[
            { value: "bench_grupos", label: "Maior grupo" }, { value: "bench_dists", label: "Maior distribuidora" }, { value: "brasil", label: "Brasil" }, { value: "lado", label: "Lado B" }]} />
          <Segmented label="Eixos" size="sm" value={preset.id} onChange={setPreset} options={PRESETS_INDICADORES.map((x) => ({ value: x.id, label: x.nome }))} />
        </div>
      </div>
      <div className={s.radarBody}>
        <div className={s.radarChart}>
          {ok.length >= 3
            ? <EChart build={build} height={380} ariaLabel={`Radar de ${labelA} frente a ${refNome}; os valores estão na tabela ao lado`} testId="chart-radar" />
            : <div className="caption" style={{ padding: 24 }}>Menos de 3 indicadores com valor dos dois lados: radar indisponível. Veja a tabela.</div>}
          <div className="caption" style={{ textAlign: "center" }}>A: <b>{labelA}</b> · Referência: <b>{refNome}</b></div>
        </div>
        <div style={{ minWidth: 0 }}>
          <table className={s.radarTable} data-testid="radar-tabela">
            <caption className="sr-only">Valores por indicador, referência e líder</caption>
            <thead><tr><th scope="col">Indicador</th><th scope="col">A</th><th scope="col">Referência</th><th scope="col">A / ref.</th><th scope="col" className={s.lider}>Líder</th></tr></thead>
            <tbody>
              {eixos.map((e) => (
                <tr key={e.ind.id}>
                  <th scope="row">{e.ind.nome}<span className="faint"> · {METRIC_UNIT[e.ind.metric] || "itens"}</span></th>
                  <td><Value v={e.a.v} metric={e.ind.metric} unitOverride="" /></td>
                  <td><Value v={e.ref} metric={e.ind.metric} unitOverride="" /></td>
                  <td data-testid={`radar-pct-${e.ind.id}`}>{e.pctA === null ? <span className="faint" title={e.nd ?? ""}>N/D</span> : <b className={e.pctA > 1 ? s.over : undefined}>{pct(e.pctA)}</b>}</td>
                  <td className={s.lider}>{e.lider ? <><b>{e.lider.nome}</b><br /><span className="faint">{fmtCompact(e.lider.v, e.ind.metric)}{e.lider.total > 1 ? ` · ${e.lider.n}/${e.lider.total} DIST` : ""}</span></> : <span className="faint">N/D</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {eixos.some((e) => e.nd) && <p className="caption" style={{ marginTop: 8 }}>Fora do radar: {eixos.filter((e) => e.nd).map((e) => `${e.ind.nome} (${e.nd})`).join("; ")}.</p>}
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 10 }}><Button size="sm" onClick={exportCSV} data-testid="radar-csv"><Download size={14} /> CSV do radar</Button></div>
        </div>
      </div>
    </section>
  );
}
