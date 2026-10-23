"use client";
import { ArrowLeftRight, Download, Link2, TriangleAlert } from "lucide-react";
import { motion, useAnimationControls } from "motion/react";
import { useState } from "react";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { Button } from "@/components/ui/Button";
import { DataError, downloadText, LoadingBlock, useToast } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { Value } from "@/components/ui/Value";
import { RadarBenchmark } from "./RadarBenchmark";
import { nomeNegocio } from "@/lib/catalogo";
import { groupColor } from "@/lib/colors";
import { displayName, type Aggregate, type Dataset } from "@/lib/dataset";
import { useData } from "@/lib/data-context";
import { diff, fmt, fmtCompact, fmtPct, METRIC_UNIT, toCSV } from "@/lib/format";
import { useTheme } from "@/lib/theme";
import type { Entidade, Metric, Scope } from "@/lib/types";
import { parseSide, useQueryPatch, useQueryState } from "@/lib/url-state";
import p from "./pages.module.css";
import s from "./comparar.module.css";

type Side = Exclude<Scope, { tipo: "brasil" }>;
const enc = (x: Side) => `${x.tipo}:${x.id}`;

function resolveKey(ds: Dataset, q: string, fallback: number): string {
  const x = parseSide(q);
  const ok = !!x && (x.tipo === "dist" ? !!ds.dist(x.id) : !!ds.grupo(x.id));
  return ok ? q : `grupo:${ds.grupos[fallback].id}`;
}

/** Linhas da comparação (função pura): mesma métrica e cobertura aplicadas a cada lado. */
function compareRows(ds: Dataset, keyA: string, keyB: string, fam: string, modo: string, ordem: "familia" | "diferenca") {
  const da = ds.scopeDists(parseSide(keyA) as Side), db = ds.scopeDists(parseSide(keyB) as Side);
  const rows = ds.entidades.filter((e) => fam === "todas" || e.familia === fam).map((e) => {
    const met: Metric = modo === "quantidade" ? "quantidade" : e.metrica;
    const a = ds.aggregate(da, e.id, met), b = ds.aggregate(db, e.id, met);
    return { e, met, a, b, d: diff(a.v, b.v) };
  });
  return ordem === "diferenca"
    ? [...rows].sort((x, y) => Math.abs(y.d.rel ?? -1) - Math.abs(x.d.rel ?? -1))
    : [...rows].sort((x, y) => ds.familias.indexOf(x.e.familia) - ds.familias.indexOf(y.e.familia));
}

export function Comparar() {
  const data = useData();
  if (data.status === "loading") return <LoadingBlock lines={6} />;
  if (data.status === "error") return <DataError error={data.error} />;
  return <CompararReady ds={data.ds} />;
}

function CompararReady({ ds }: { ds: Dataset }) {
  const { resolved } = useTheme();
  const toast = useToast();
  const patch = useQueryPatch();
  const [aQ] = useQueryState("a", "grupo:energisa");
  const [bQ] = useQueryState("b", "grupo:equatorial");
  const [fam, setFam] = useQueryState("familia", "todas");
  const [modo, setModo] = useQueryState("metrica", "principal");
  const [ordem, setOrdem] = useState<"familia" | "diferenca">("familia");
  const [vista, setVista] = useQueryState("grafico", "pct");
  const swapCtl = useAnimationControls();

  // chaves canônicas em texto (imutáveis): seleção inválida na URL cai para os dois maiores grupos
  const keyA = resolveKey(ds, aQ, 0), keyB = resolveKey(ds, bQ, 1);
  const A = parseSide(keyA) as Side, B = parseSide(keyB) as Side;
  const dA = ds.scopeDists(A), dB = ds.scopeDists(B);
  const nested = A.tipo !== B.tipo && (A.tipo === "dist" ? dB.includes(A.id as number) : dA.includes(B.id as number));
  const same = keyA === keyB;

  const rows = compareRows(ds, keyA, keyB, fam, modo, ordem);

  const swap = async () => {
    patch({ a: enc(B), b: enc(A) });
    swapCtl.start({ rotate: [0, 180], transition: { duration: 0.32, ease: [0.22, 1, 0.36, 1] } });
  };
  const setSide = (k: "a" | "b", v: Side) => patch({ [k]: enc(v) });

  const exportCSV = () => {
    const name = `bdgd_2025-12-31_comparacao_${enc(A).replace(":", "-")}_x_${enc(B).replace(":", "-")}.csv`;
    downloadText(name, toCSV(["data_base", "entidade", "metrica", "unidade", "A", "B", "A_menos_B", "variacao_rel_B", "A_dists_com_valor", "A_dists_total", "B_dists_com_valor", "B_dists_total"],
      rows.map((r) => ["2025-12-31", r.e.id, r.met, METRIC_UNIT[r.met], r.a.v, r.b.v, r.d.abs, r.d.rel, r.a.n, r.a.total, r.b.n, r.b.total])));
    toast(`${name} exportado`);
  };
  const share = async () => {
    try { await navigator.clipboard.writeText(window.location.href); toast("Link da comparação copiado"); } catch { toast("Não foi possível copiar o link"); }
  };

  const label = (x: Side) => ds.scopeLabel(x);
  const build = (t: ChartTokens) => {
    const rr = rows.filter((r) => r.d.rel !== null).slice(0, 18);
    return {
      grid: { left: 8, right: 28, top: 8, bottom: 8, containLabel: true },
      tooltip: { trigger: "item", backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
        formatter: (q: { dataIndex: number }) => { const r = rr[q.dataIndex]; return `<b>${r.e.nome}</b> (${r.e.id})<br/>A: ${fmt(r.a.v, r.met)} · B: ${fmt(r.b.v, r.met)} ${METRIC_UNIT[r.met]}<br/>A em relação a B: ${fmtPct(r.d.rel)}`; } },
      xAxis: { type: "value", axisLabel: { color: t.text3, fontFamily: t.font, fontSize: 10, formatter: (v: number) => `${Math.round(v * 100)}%` }, splitLine: { lineStyle: { color: t.hairline } } },
      yAxis: { type: "category", inverse: true, data: rr.map((r) => r.e.id), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 11 } },
      series: [{ type: "bar", barWidth: 10, data: rr.map((r) => ({ value: Math.max(-1.5, Math.min(r.d.rel!, 3)), itemStyle: { color: r.d.rel! >= 0 ? t.sideA : t.sideB, borderRadius: 3 } })),
        markLine: { silent: true, symbol: "none", lineStyle: { color: t.text3, type: "solid" }, data: [{ xAxis: 0 }], label: { show: false } } }],
    };
  };
  /** Barras espelhadas: A à esquerda, B à direita, cada linha na escala do maior dos dois (unidades diferentes entre linhas). */
  const buildMirror = (t: ChartTokens) => {
    const rr = rows.filter((r) => r.a.v !== null && r.b.v !== null && Math.max(r.a.v, r.b.v) > 0).slice(0, 18);
    const m = (r: (typeof rr)[number]) => Math.max(r.a.v!, r.b.v!);
    const lab = (v: number | null, met: Metric) => fmtCompact(v, met);
    return {
      grid: { left: 8, right: 8, top: 26, bottom: 8, containLabel: true },
      legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: t.text2, fontFamily: t.font, fontSize: 11 }, data: [`A · ${label(A)}`, `B · ${label(B)}`] },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
        formatter: (q: Array<{ dataIndex: number }>) => { const r = rr[q[0].dataIndex]; return `<b>${r.e.nome}</b> (${r.e.id})<br/>A: ${fmt(r.a.v, r.met)} ${METRIC_UNIT[r.met]}<br/>B: ${fmt(r.b.v, r.met)} ${METRIC_UNIT[r.met]}`; } },
      xAxis: { type: "value", min: -1.35, max: 1.35, axisLabel: { show: false }, splitLine: { show: false } },
      yAxis: { type: "category", inverse: true, data: rr.map((r) => r.e.id), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 11 } },
      series: [
        { name: `A · ${label(A)}`, type: "bar", stack: "x", barWidth: 10, data: rr.map((r) => ({ value: -r.a.v! / m(r), itemStyle: { color: t.sideA, borderRadius: [3, 0, 0, 3] } })),
          label: { show: true, position: "left", color: t.text2, fontFamily: t.font, fontSize: 10, formatter: (q: { dataIndex: number }) => lab(rr[q.dataIndex].a.v, rr[q.dataIndex].met) } },
        { name: `B · ${label(B)}`, type: "bar", stack: "x", barWidth: 10, data: rr.map((r) => ({ value: r.b.v! / m(r), itemStyle: { color: t.sideB, borderRadius: [0, 3, 3, 0] } })),
          label: { show: true, position: "right", color: t.text2, fontFamily: t.font, fontSize: 10, formatter: (q: { dataIndex: number }) => lab(rr[q.dataIndex].b.v, rr[q.dataIndex].met) },
          markLine: { silent: true, symbol: "none", lineStyle: { color: t.text3, type: "solid" }, data: [{ xAxis: 0 }], label: { show: false } } },
      ],
    };
  };

  const sideCard = (k: "a" | "b", x: Side, color: string, n: Aggregate | null) => {
    const opts = x.tipo === "dist"
      ? ds.dists.map((d) => ({ value: String(d.dist), label: displayName(d), meta: `DIST ${d.dist}`, group: ds.grupo(d.grupo)?.nome ?? "Grupo não confirmado", keywords: `${d.nome} ${d.ufs.join(" ")}`, color: d.grupo_status === "verificado" ? groupColor(d.grupo, resolved) : undefined }))
        .sort((a, b) => (a.group ?? "").localeCompare(b.group ?? "") || a.label.localeCompare(b.label))
      : ds.grupos.map((g) => ({ value: g.id, label: g.nome, meta: `${ds.groupDists(g.id).length} DIST`, color: groupColor(g.id, resolved) }));
    const dists = ds.scopeDists(x);
    const g = x.tipo === "grupo" ? ds.grupo(x.id) : ds.grupo(ds.dist(x.id)!.grupo);
    return (
      <motion.div layout className={s.side} style={{ ["--c" as string]: color }} transition={{ type: "spring", stiffness: 420, damping: 38 }} data-testid={`lado-${k}`}>
        <div className={s.sideTop}>
          <span className={s.sideTag} aria-hidden>{k.toUpperCase()}</span>
          <Segmented size="sm" label={`Tipo do lado ${k.toUpperCase()}`} value={x.tipo} onChange={(t) => setSide(k, t === "dist" ? { tipo: "dist", id: (x.tipo === "grupo" ? ds.groupDists(x.id)[0]?.dist : x.id) ?? ds.dists[0].dist } : { tipo: "grupo", id: x.tipo === "dist" ? (ds.dist(x.id)!.grupo_status === "verificado" ? ds.dist(x.id)!.grupo : ds.grupos[0].id) : x.id })}
            options={[{ value: "dist", label: "Distribuidora" }, { value: "grupo", label: "Grupo" }]} />
        </div>
        <Picker label={x.tipo === "dist" ? "Distribuidora" : "Grupo econômico verificado"} value={String(x.id)} options={opts}
          onChange={(v) => setSide(k, x.tipo === "dist" ? { tipo: "dist", id: Number(v) } : { tipo: "grupo", id: v })} testId={`picker-${k}`} />
        <div className={s.sideName}>{label(x)}</div>
        <div className={s.sideMeta}>
          {x.tipo === "grupo" ? `${dists.length} distribuidoras · controlador ${g?.controlador ?? ""}` : `DIST ${x.id} · ${g ? `grupo ${g.nome}` : "grupo não confirmado"}`}
          {n && n.nd > 0 ? ` · consumidores N/D em ${n.nd}` : ""}
        </div>
      </motion.div>
    );
  };

  return (
    <>
      <header className={`${p.head} rise`}>
        <div className="eyebrow">Mesma data-base · mesma métrica · cobertura de cada lado</div>
        <h1 className="display" style={{ marginTop: 8 }}>Comparador</h1>
        <p className="lede">Distribuidora × distribuidora, grupo × grupo ou distribuidora × grupo, entidade por entidade. Diferença positiva significa apenas que A é maior que B — não que seja melhor.</p>
      </header>

      <div className={s.sides}>
        {sideCard("a", A, "var(--side-a)", ds.consumidores(dA))}
        <motion.button className={s.swap} onClick={swap} animate={swapCtl} aria-label="Trocar A e B" title="Trocar A e B" data-testid="trocar"><ArrowLeftRight size={18} /></motion.button>
        {sideCard("b", B, "var(--side-b)", ds.consumidores(dB))}
      </div>

      {same && <div className={s.warnLine}><TriangleAlert size={14} /> A e B são o mesmo recorte.</div>}
      {nested && <div className={s.warnLine}><TriangleAlert size={14} /> {A.tipo === "dist" ? "A distribuidora A pertence ao grupo B" : "A distribuidora B pertence ao grupo A"}: os valores do grupo já incluem a distribuidora. A comparação é válida como participação, mas A e B não são somáveis.</div>}

      <div className={p.toolbar} role="toolbar" aria-label="Opções da comparação">
        <Segmented label="Família" value={fam} onChange={setFam} options={[{ value: "todas", label: "Todas" }, ...ds.familias.filter((f) => f !== "Área de atuação").map((f) => ({ value: f, label: f }))]} />
        <span className={p.spacer} />
        <Segmented label="Métrica" size="sm" value={modo} onChange={setModo} options={[{ value: "principal", label: "Principal" }, { value: "quantidade", label: "Quantidade" }]} />
        <Segmented label="Ordenar" size="sm" value={ordem} onChange={setOrdem} options={[{ value: "familia", label: "Por família funcional" }, { value: "diferenca", label: "Maiores diferenças" }]} />
        <Button variant="ghost" onClick={share}><Link2 size={15} /> Link</Button>
        <Button variant="primary" onClick={exportCSV} data-testid="comparar-csv"><Download size={15} /> CSV</Button>
      </div>

      <section className={p.note} style={{ display: "block" }} aria-label="Diferença entre A e B por entidade">
        <div className={s.chartHead}>
          <div className="label">{vista === "valores" ? "Valores de A e B lado a lado (cada linha na escala do maior valor; omitidas quando algum lado é N/D)" : "A em relação a B, por entidade (Δ% = (A − B) / B; omitidas quando B = 0 ou N/D)"}</div>
          <Segmented label="Tipo de gráfico" size="sm" value={vista} onChange={setVista} options={[{ value: "pct", label: "Diferença (%)" }, { value: "valores", label: "Valores A × B" }]} />
        </div>
        {vista === "valores"
          ? <EChart key="mirror" build={buildMirror} height={Math.max(200, Math.min(18, rows.filter((r) => r.a.v !== null && r.b.v !== null).length) * 24 + 44)} ariaLabel="Valores de A e B em barras espelhadas" testId="chart-espelhado" />
          : <EChart key="pct" build={build} height={Math.max(180, Math.min(18, rows.filter((r) => r.d.rel !== null).length) * 22 + 30)} ariaLabel="Diferença relativa entre A e B por entidade" testId="chart-comparacao" />}
      </section>

      <RadarBenchmark ds={ds} A={A} B={B} />

      <table className={s.table} data-testid="comparar-tabela">
        <thead>
          <tr>
            <th scope="col">Entidade</th>
            <th scope="col">Unidade</th>
            <th scope="col"><span className={s.vA}>A</span></th>
            <th scope="col"><span className={s.vB}>B</span></th>
            <th scope="col">A − B</th>
            <th scope="col">Δ% vs B</th>
            <th scope="col" className={s.hideSm}>Participação</th>
            <th scope="col" className={s.hideSm}>Cobertura A · B</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const head = ordem === "familia" && (i === 0 || rows[i - 1].e.familia !== r.e.familia);
            const tot = (r.a.v ?? 0) + (r.b.v ?? 0);
            return [
              head ? <tr key={`f-${r.e.familia}`} className={s.famRow}><td colSpan={8}>{r.e.familia}</td></tr> : null,
              <tr key={r.e.id}>
                <td><span className={s.entCode}>{r.e.id}</span><span className={s.entName}>{nomeNegocio(r.e.id, r.e.nome)}</span>{r.e.naoSomarCom && <span className="caption"> · não somar com {r.e.naoSomarCom}</span>}</td>
                <td className="faint">{METRIC_UNIT[r.met]}</td>
                <td className={s.vA}><Value v={r.a.v} metric={r.met} unitOverride="" /></td>
                <td className={s.vB}><Value v={r.b.v} metric={r.met} unitOverride="" /></td>
                <td>{r.d.abs === null ? <span className="faint">N/D</span> : fmt(r.d.abs, r.met)}</td>
                <td>{r.d.rel === null ? <span className="faint" title={r.b.v === 0 ? "B = 0: variação percentual indefinida" : "Algum lado N/D"}>N/D</span> : fmtPct(r.d.rel)}</td>
                <td className={s.hideSm}>
                  {tot > 0 && r.a.v !== null && r.b.v !== null ? (
                    <span className={s.split} role="img" aria-label={`A ${Math.round((r.a.v / tot) * 100)}%, B ${Math.round((r.b.v / tot) * 100)}%`}>
                      <span className={s.splitA} style={{ flexGrow: r.a.v / tot }} /><span className={s.splitB} style={{ flexGrow: r.b.v / tot }} />
                    </span>
                  ) : <span className="faint">—</span>}
                </td>
                <td className={`${s.cov} ${s.hideSm}`}>{r.a.n}/{r.a.total} · {r.b.n}/{r.b.total}</td>
              </tr>,
            ];
          })}
        </tbody>
      </table>
      <p className="caption" style={{ marginTop: 10 }}>Valores de grupo somam apenas distribuidoras com vínculo verificado e indicador disponível; a coluna Cobertura mostra quantas entraram em cada soma. Potência de geração (UG*) é N/D por não estar homologada.</p>
    </>
  );
}
