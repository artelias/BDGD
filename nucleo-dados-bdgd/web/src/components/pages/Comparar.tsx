"use client";
import { ObservacoesDados } from "@/components/ui/ObservacoesDados";
import { camposObservacoes, COLUNAS_OBSERVACOES } from "@/lib/observacoes";
import { ArrowLeftRight, Download, Link2, SlidersHorizontal, TriangleAlert, X } from "lucide-react";
import { AnimatePresence, motion, useAnimationControls } from "motion/react";
import { useMemo } from "react";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { Button } from "@/components/ui/Button";
import { Explain } from "@/components/ui/Explain";
import { DataError, downloadText, EmptyState, LoadingBlock, useToast } from "@/components/ui/Feedback";
import { MultiPick } from "@/components/ui/MultiPick";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { ativos as listaAtivos, ESSENCIAIS, itensMenu, recorteDe, UNIDADE } from "@/lib/ativos";
import { groupColor } from "@/lib/colors";
import { benchmarkLinhas, REFERENCIA, somar, type Linha, type Referencia } from "@/lib/comparador";
import { agregarPorDist, dimsCompativeis, escreverRecorte, juntar, lerRecorte, porDistPorCategoria, rotulo } from "@/lib/cubo";
import { displayName, type Dataset } from "@/lib/dataset";
import { useConceito, useData } from "@/lib/data-context";
import { diff, fmt, fmtCompact, fmtPct, toCSV } from "@/lib/format";
import { useTheme } from "@/lib/theme";
import type { ConceitoData, MenuItem, Scope } from "@/lib/types";
import { parseSide, useQueryPatch, useQueryState } from "@/lib/url-state";
import p from "./pages.module.css";
import s from "./comparar.module.css";

type Side = Exclude<Scope, { tipo: "brasil" }>;
const enc = (x: Side) => `${x.tipo}:${x.id}`;
const pct = (x: number) => `${(x * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;

function resolveKey(ds: Dataset, q: string, fallback: number): string {
  const x = parseSide(q);
  const ok = !!x && (x.tipo === "dist" ? !!ds.dist(x.id) : !!ds.grupo(x.id));
  return ok ? q : `grupo:${ds.grupos[fallback].id}`;
}

export function Comparar() {
  const data = useData();
  if (data.status === "loading") return <LoadingBlock lines={6} />;
  if (data.status === "error") return <DataError error={data.error} />;
  if (!data.ds.raw.conceitos) return <EmptyState title="Catálogo de ativos indisponível" tone="warn">O pacote publicado não contém o catálogo de ativos.</EmptyState>;
  return <CompararReady ds={data.ds} />;
}

function CompararReady({ ds }: { ds: Dataset }) {
  const [itemQ] = useQueryState("ativo", "todos");
  const item = itensMenu(ds).find((i) => i.id === itemQ && i.conceito) ?? null;
  const conceito = useConceito(item?.conceito ?? null);
  if (item && (conceito.loading || !conceito.data)) return <LoadingBlock lines={6} label="Carregando o ativo" />;
  return <Corpo ds={ds} item={item} cd={item ? conceito.data! : null} />;
}

function Corpo({ ds, item, cd }: { ds: Dataset; item: MenuItem | null; cd: ConceitoData | null }) {
  const { resolved } = useTheme();
  const toast = useToast();
  const patch = useQueryPatch();
  const cat = ds.raw.conceitos!;
  const [aQ] = useQueryState("a", "grupo:energisa");
  const [bQ] = useQueryState("b", "grupo:equatorial");
  const [fam, setFam] = useQueryState("familia", "todas");
  const [abaQ, setAba] = useQueryState("aba", "tabela");
  const [vista, setVista] = useQueryState("grafico", "pct");
  const [ordem, setOrdem] = useQueryState("ordem", "familia");
  const [fQ] = useQueryState("f");
  const [porQ, setPor] = useQueryState("por");
  const [refQ, setRef] = useQueryState("ref", "bench_grupos");
  const swapCtl = useAnimationControls();
  const aba = ["tabela", "graficos", "radar"].includes(abaQ) ? abaQ : "tabela";
  const ref = (refQ in REFERENCIA ? refQ : "bench_grupos") as Referencia;

  const keyA = resolveKey(ds, aQ, 0), keyB = resolveKey(ds, bQ, 1);
  const A = parseSide(keyA) as Side, B = parseSide(keyB) as Side;
  const dA = ds.scopeDists(A), dB = ds.scopeDists(B);
  const nested = A.tipo !== B.tipo && (A.tipo === "dist" ? dB.includes(A.id as number) : dA.includes(B.id as number));
  const nomeA = ds.scopeLabel(A), nomeB = ds.scopeLabel(B);

  // ---- linhas: todos os ativos (totais) ou as categorias do ativo escolhido, no MESMO recorte para A, B e benchmarks
  const filtro = useMemo(() => lerRecorte(fQ), [fQ]);
  const todasDims = useMemo(() => (cd ? [...new Set(Object.values(cd.cubos).flatMap((c) => c.dims))] : []), [cd]);
  const base = useMemo(() => (item ? recorteDe(item) : { filtro: {} }), [item]);
  const recorte = useMemo(() => juntar(base, { filtro }), [base, filtro]);
  const cfg = item ? cat.conceitos[item.conceito!] : null;
  const fixadas = new Set(Object.keys(base.filtro));
  const essenciais = item && cfg ? [...new Set([...(cfg.categoria && !fixadas.has(cfg.categoria) ? [cfg.categoria] : []), ...(ESSENCIAIS[item.conceito!] ?? [])])].filter((d) => todasDims.includes(d) && !fixadas.has(d)) : [];
  const compat = useMemo(() => (cd ? dimsCompativeis(cd, recorte) : new Set<string>()), [cd, recorte]);
  const porOpts = todasDims.filter((d) => compat.has(d) && !fixadas.has(d) && d !== "municipio");
  const por = porOpts.includes(porQ) ? porQ : (essenciais.find((d) => porOpts.includes(d)) ?? porOpts[0]);
  const medida = cd ? cd.medidas[0] : "quantidade";

  const linhas: Linha[] = (() => {
    if (!item || !cd) {
      return listaAtivos(ds).filter((a) => fam === "todas" || a.familia === fam).map((a) => ({
        id: a.id, nome: a.nome, familia: a.familia, medida: a.medida,
        porDist: new Map((ds.raw.ativosTotais?.[a.id]?.[a.medida] ?? []).filter((r) => r[2] !== "n").map((r) => [r[0], r[2] === "b" ? null : r[1]] as [number, number | null])),
      }));
    }
    const out: Linha[] = [];
    const tot = agregarPorDist(cd, recorte, medida);
    if (tot) out.push({ id: "__total", nome: `${item.nome} (todo o recorte)`, familia: "Total", medida, porDist: tot });
    const cats = por ? porDistPorCategoria(cd, por, recorte, medida) : null;
    for (const [code, mm] of cats ?? []) out.push({ id: code, nome: rotulo(cd, por!, code, recorte), familia: cat.dimensoes[por!]?.rotulo ?? por!, medida, porDist: mm });
    return out;
  })();

  const tabela = (() => {
    const r = linhas.map((l) => { const a = somar(l, dA), b = somar(l, dB); return { l, a, b, d: diff(a.nd ? null : a.v, b.nd ? null : b.v) }; });
    const [tot, resto] = [r.filter((x) => x.l.id === "__total"), r.filter((x) => x.l.id !== "__total")];
    const ord = ordem === "diferenca" ? [...resto].sort((x, y) => Math.abs(y.d.rel ?? -1) - Math.abs(x.d.rel ?? -1))
      : item ? [...resto].sort((x, y) => Math.max(y.a.v ?? 0, y.b.v ?? 0) - Math.max(x.a.v ?? 0, x.b.v ?? 0)) : resto;
    return [...tot, ...ord];
  })();
  const semTotal = tabela.filter((r) => r.l.id !== "__total");

  const swap = () => { patch({ a: enc(B), b: enc(A) }); swapCtl.start({ rotate: [0, 180], transition: { duration: 0.32, ease: [0.22, 1, 0.36, 1] } }); };
  const setSide = (k: "a" | "b", v: Side) => patch({ [k]: enc(v) });
  const setFiltro = (dim: string, v: string[]) => patch({ f: escreverRecorte({ ...filtro, [dim]: v }) || null });
  const recorteTxt = escreverRecorte(recorte.filtro) || "(população do ativo)";
  const recorteLegivel = cd && Object.values(filtro).some((v) => v.length)
    ? Object.entries(filtro).filter(([, v]) => v.length).map(([d, v]) => `${cat.dimensoes[d]?.rotulo ?? d}: ${v.map((c) => rotulo(cd, d, c, recorte)).join(", ")}`).join(" · ")
    : "sem filtros";

  const camposDaLinha = (linha: Linha) => camposObservacoes({ dists: [...dA, ...dB], ativos: [item?.id ?? linha.id], anos: [2025], metricas: [linha.medida],
    filtro: item && por && linha.id !== "__total" ? { ...recorte.filtro, [por]: [linha.id] } : recorte.filtro });
  const exportCSV = () => {
    const name = `bdgd_2025-12-31_comparacao_${enc(A).replace(":", "-")}_x_${enc(B).replace(":", "-")}${item ? `_${item.id}` : ""}.csv`;
    downloadText(name, toCSV(["data_base", "versao", "ativo", "recorte", "linha", "medida", "unidade", "A", "B", "A_menos_B", "variacao_rel_B", "A_dists_com_valor", "A_dists_total", "B_dists_com_valor", "B_dists_total", ...COLUNAS_OBSERVACOES],
      tabela.map((r) => ["2025-12-31", ds.raw.release.release_id, item?.nome ?? "todos", recorteTxt, r.l.nome, r.l.medida, UNIDADE[r.l.medida], r.a.v, r.b.v, r.d.abs, r.d.rel, r.a.n, r.a.total, r.b.n, r.b.total, ...camposDaLinha(r.l)])));
    toast(`${name} exportado`);
  };
  const share = async () => { try { await navigator.clipboard.writeText(window.location.href); toast("Link da comparação copiado"); } catch { toast("Não foi possível copiar o link"); } };

  const sideCard = (k: "a" | "b", x: Side, color: string) => {
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
          onChange={(v) => setSide(k, x.tipo === "dist" ? { tipo: "dist", id: Number(v) } : { tipo: "grupo", id: v })} testId={`picker-${k}`} inlineMenu />
        <div className={s.sideName}>{ds.scopeLabel(x)}</div>
        <div className={s.sideMeta}>{x.tipo === "grupo" ? `${dists.length} distribuidoras · controlador ${g?.controlador ?? ""}` : `DIST ${x.id} · ${g ? `grupo ${g.nome}` : "grupo não confirmado"}`}</div>
      </motion.div>
    );
  };

  // ---- gráficos (preservados do R2): diferença % e barras espelhadas, sobre as mesmas linhas
  const buildPct = (t: ChartTokens) => {
    const rr = semTotal.filter((r) => r.d.rel !== null).slice(0, 18);
    return {
      grid: { left: 8, right: 28, top: 8, bottom: 8, containLabel: true },
      tooltip: { trigger: "item", backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
        formatter: (q: { dataIndex: number }) => { const r = rr[q.dataIndex]; return `<b>${r.l.nome}</b><br/>A: ${fmt(r.a.v, r.l.medida)} · B: ${fmt(r.b.v, r.l.medida)} ${UNIDADE[r.l.medida]}<br/>A em relação a B: ${fmtPct(r.d.rel)}`; } },
      xAxis: { type: "value", axisLabel: { color: t.text3, fontFamily: t.font, fontSize: 10, formatter: (v: number) => `${Math.round(v * 100)}%` }, splitLine: { lineStyle: { color: t.hairline } } },
      yAxis: { type: "category", inverse: true, data: rr.map((r) => (r.l.nome.length > 34 ? r.l.nome.slice(0, 33) + "…" : r.l.nome)), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 11 } },
      series: [{ type: "bar", barWidth: 10, data: rr.map((r) => ({ value: Math.max(-1.5, Math.min(r.d.rel!, 3)), itemStyle: { color: r.d.rel! >= 0 ? t.sideA : t.sideB, borderRadius: 3 } })),
        markLine: { silent: true, symbol: "none", lineStyle: { color: t.text3, type: "solid" }, data: [{ xAxis: 0 }], label: { show: false } } }],
    };
  };
  const buildMirror = (t: ChartTokens) => {
    const rr = semTotal.filter((r) => r.a.v !== null && r.b.v !== null && Math.max(r.a.v, r.b.v) > 0).slice(0, 18);
    const m = (r: (typeof rr)[number]) => Math.max(r.a.v!, r.b.v!);
    return {
      grid: { left: 8, right: 8, top: 26, bottom: 8, containLabel: true },
      legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: t.text2, fontFamily: t.font, fontSize: 11 }, data: [`A · ${nomeA}`, `B · ${nomeB}`] },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
        formatter: (q: Array<{ dataIndex: number }>) => { const r = rr[q[0].dataIndex]; return `<b>${r.l.nome}</b><br/>A: ${fmt(r.a.v, r.l.medida)} ${UNIDADE[r.l.medida]}<br/>B: ${fmt(r.b.v, r.l.medida)} ${UNIDADE[r.l.medida]}`; } },
      xAxis: { type: "value", min: -1.35, max: 1.35, axisLabel: { show: false }, splitLine: { show: false } },
      yAxis: { type: "category", inverse: true, data: rr.map((r) => (r.l.nome.length > 34 ? r.l.nome.slice(0, 33) + "…" : r.l.nome)), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 11 } },
      series: [
        { name: `A · ${nomeA}`, type: "bar", stack: "x", barWidth: 10, data: rr.map((r) => ({ value: -r.a.v! / m(r), itemStyle: { color: t.sideA, borderRadius: [3, 0, 0, 3] } })),
          label: { show: true, position: "left", color: t.text2, fontFamily: t.font, fontSize: 10, formatter: (q: { dataIndex: number }) => fmtCompact(rr[q.dataIndex].a.v, rr[q.dataIndex].l.medida) } },
        { name: `B · ${nomeB}`, type: "bar", stack: "x", barWidth: 10, data: rr.map((r) => ({ value: r.b.v! / m(r), itemStyle: { color: t.sideB, borderRadius: [0, 3, 3, 0] } })),
          label: { show: true, position: "right", color: t.text2, fontFamily: t.font, fontSize: 10, formatter: (q: { dataIndex: number }) => fmtCompact(rr[q.dataIndex].b.v, rr[q.dataIndex].l.medida) },
          markLine: { silent: true, symbol: "none", lineStyle: { color: t.text3, type: "solid" }, data: [{ xAxis: 0 }], label: { show: false } } },
      ],
    };
  };
  const nGraf = (vista === "valores" ? semTotal.filter((r) => r.a.v !== null && r.b.v !== null).length : semTotal.filter((r) => r.d.rel !== null).length);

  return (
    <>
      <header className={`${p.head} rise`}>
        <div className="eyebrow">Mesma data-base · mesmo recorte · mesma medida</div>
        <h1 className="display" style={{ marginTop: 8 }}>Comparador</h1>
        <p className="lede">Distribuidora × distribuidora, grupo × grupo ou distribuidora × grupo. O ativo e as características escolhidas valem igualmente para A, B e os benchmarks. Diferença positiva significa apenas que A é maior que B.</p>
      </header>

      <div className={s.sides}>
        {sideCard("a", A, "var(--side-a)")}
        <motion.button className={s.swap} onClick={swap} animate={swapCtl} aria-label="Trocar A e B" title="Trocar A e B" data-testid="trocar"><ArrowLeftRight size={18} /></motion.button>
        {sideCard("b", B, "var(--side-b)")}
      </div>
      {keyA === keyB && <div className={s.warnLine}><TriangleAlert size={14} /> A e B são o mesmo recorte.</div>}
      {nested && <div className={s.warnLine}><TriangleAlert size={14} /> {A.tipo === "dist" ? "A distribuidora A pertence ao grupo B" : "A distribuidora B pertence ao grupo A"}: os valores do grupo já incluem a distribuidora. A comparação é válida como participação, mas A e B não são somáveis.</div>}

      <div className={p.toolbar} role="toolbar" aria-label="Ativo e recorte">
        <Picker label="Ativo" value={item?.id ?? "todos"} width={260} testId="comparar-ativo"
          options={[{ value: "todos", label: "Todos os ativos", group: "Visão geral" }, ...cat.menu.flatMap((g) => g.itens.filter((i) => i.conceito).map((i) => ({ value: i.id, label: i.nome, group: g.grupo })))]}
          onChange={(v) => patch({ ativo: v === "todos" ? null : v, f: null, por: null })} />
        {!item && <Picker label="Família" value={fam} compact width={230} options={[{ value: "todas", label: "Todas" }, ...[...new Set(listaAtivos(ds).map((a) => a.familia))].map((f) => ({ value: f, label: f }))]} onChange={setFam} testId="comparar-familia" />}
        {item && cd && (
          <>
            <span className="caption" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><SlidersHorizontal size={13} aria-hidden /> Características</span>
            {essenciais.map((d) => {
              const ok = compat.has(d) || (filtro[d]?.length ?? 0) > 0;
              return (
                <span key={d} style={ok ? undefined : { opacity: 0.45, pointerEvents: "none" }} title={ok ? undefined : "Sem cubo exato para combinar com o filtro atual"}>
                  <MultiPick label={cat.dimensoes[d]?.rotulo ?? d} value={filtro[d] ?? []} allLabel="Todos" testId={`cmp-filtro-${d}`} width={320}
                    options={(cd.valores[d] ?? []).map((code) => ({ value: code, label: rotulo(cd, d, code, recorte), keywords: code }))} onChange={(v) => setFiltro(d, v)} />
                </span>
              );
            })}
            <Picker label="Comparar por" value={por ?? null} compact width={240} options={porOpts.map((d) => ({ value: d, label: cat.dimensoes[d]?.rotulo ?? d }))} onChange={(v) => setPor(v)} testId="comparar-por" />
          </>
        )}
      </div>
      {item && Object.values(filtro).some((v) => v.length) && (
        <div className={s.chipsLine} data-testid="comparar-chips">
          {Object.entries(filtro).filter(([, v]) => v.length).map(([d, v]) => <button key={d} type="button" className={s.chip} onClick={() => setFiltro(d, [])}>{cat.dimensoes[d]?.rotulo ?? d}: {v.length === 1 ? rotulo(cd!, d, v[0], recorte) : `${v.length} valores`} <X size={12} aria-hidden /></button>)}
        </div>
      )}

      <section className={s.stage} aria-label="Resultado da comparação">
        <div className={s.stageHead}>
          <Segmented label="Visualização" value={aba} onChange={(v) => setAba(v)} options={[{ value: "tabela", label: "Tabela" }, { value: "graficos", label: "Gráficos" }, { value: "radar", label: "Radar" }]} />
          <span className={p.spacer} />
          {aba !== "radar" && <Segmented label="Ordenar" size="sm" value={ordem === "diferenca" ? "diferenca" : "familia"} onChange={setOrdem} options={[{ value: "familia", label: item ? "Maiores valores" : "Por família funcional" }, { value: "diferenca", label: "Maiores diferenças" }]} />}
          {aba === "graficos" && <Segmented label="Tipo de gráfico" size="sm" value={vista} onChange={setVista} options={[{ value: "pct", label: "Diferença (%)" }, { value: "valores", label: "Valores A × B" }]} />}
          <Button variant="ghost" size="sm" onClick={share}><Link2 size={14} /> Link</Button>
          <Button size="sm" variant="primary" onClick={exportCSV} data-testid="comparar-csv"><Download size={14} /> CSV</Button>
        </div>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={aba} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}>
            {aba === "tabela" && (
              <table className={s.table} data-testid="comparar-tabela">
                <caption className="sr-only">Comparação entre {nomeA} e {nomeB}</caption>
                <thead><tr><th scope="col">{item ? (cat.dimensoes[por ?? ""]?.rotulo ?? "Categoria") : "Ativo"}</th><th scope="col">Unidade</th><th scope="col"><span className={s.vA}>A</span></th><th scope="col"><span className={s.vB}>B</span></th><th scope="col">A − B</th><th scope="col">Δ% vs B</th><th scope="col" className={s.hideSm}>Cobertura A · B</th></tr></thead>
                <tbody>
                  {tabela.map((r, i) => {
                    const head = !item && ordem !== "diferenca" && (i === 0 || tabela[i - 1].l.familia !== r.l.familia);
                    return [
                      head ? <tr key={`f-${r.l.familia}`} className={s.famRow}><td colSpan={7}>{r.l.familia}</td></tr> : null,
                      <tr key={r.l.id} className={r.l.id === "__total" ? s.totalLine : undefined}>
                        <td><span className={s.entName}>{r.l.nome}</span></td>
                        <td className="faint">{UNIDADE[r.l.medida]}</td>
                        <td className={s.vA}>{r.a.v === null ? <span className="faint">N/D</span> : fmt(r.a.v, r.l.medida)}</td>
                        <td className={s.vB}>{r.b.v === null ? <span className="faint">N/D</span> : fmt(r.b.v, r.l.medida)}</td>
                        <td>{r.d.abs === null ? <span className="faint">N/D</span> : fmt(r.d.abs, r.l.medida)}</td>
                        <td>{r.d.rel === null ? <span className="faint" title={r.b.v === 0 ? "B = 0: variação percentual indefinida" : "Algum lado N/D"}>N/D</span> : fmtPct(r.d.rel)}</td>
                        <td className={`${s.cov} ${s.hideSm}`}>{r.a.n}/{r.a.total} · {r.b.n}/{r.b.total}</td>
                      </tr>,
                    ];
                  })}
                </tbody>
              </table>
            )}
            {aba === "graficos" && (
              <div>
                <div className="label" style={{ marginBottom: 6 }}>{vista === "valores" ? "Valores de A e B lado a lado (cada linha na escala do maior valor; omitidas quando algum lado é N/D)" : "A em relação a B (Δ% = (A − B) / B; omitidas quando B = 0 ou N/D)"}</div>
                {nGraf === 0 ? <EmptyState title="Sem linhas comparáveis">Nenhuma linha tem valor dos dois lados.</EmptyState>
                  : vista === "valores"
                    ? <EChart key="mirror" build={buildMirror} height={Math.max(200, Math.min(18, nGraf) * 24 + 44)} ariaLabel="Valores de A e B em barras espelhadas; os números estão na aba Tabela" testId="chart-espelhado" />
                    : <EChart key="pct" build={buildPct} height={Math.max(180, Math.min(18, nGraf) * 22 + 30)} ariaLabel="Diferença relativa entre A e B; os números estão na aba Tabela" testId="chart-comparacao" />}
              </div>
            )}
            {aba === "radar" && <Radar observacoesDeLinha={camposDaLinha} ds={ds} linhas={semTotal.map((r) => r.l)} dA={dA} dB={dB} nomeA={nomeA} nomeB={nomeB} refQ={ref} setRef={(v) => setRef(v)} recorteTxt={item ? `${item.nome} · ${recorteLegivel}` : "todos os ativos"} />}
          </motion.div>
        </AnimatePresence>
      </section>
      <p className="caption" style={{ marginTop: 10 }}>Grupos somam apenas distribuidoras com vínculo verificado e valor homologado; a cobertura mostra quantas entraram em cada soma. Potência de geração não é publicada.</p>
      <ObservacoesDados dists={[...dA, ...dB]} ativos={item ? [item.id] : linhas.map((l) => l.id)} anos={[2025]} filtro={recorte.filtro} />
    </>
  );
}

/** Radar · Benchmark: eixos = as mesmas linhas da tabela (já filtradas). Referência e líderes recalculados no recorte. */
function Radar({ ds, linhas, dA, dB, nomeA, nomeB, refQ, setRef, recorteTxt, observacoesDeLinha }: { observacoesDeLinha: (linha: Linha) => string[]; ds: Dataset; linhas: Linha[]; dA: number[]; dB: number[]; nomeA: string; nomeB: string; refQ: Referencia; setRef: (v: string) => void; recorteTxt: string }) {
  const toast = useToast();
  const top = [...linhas].sort((x, y) => Math.max(somar(y, dA).v ?? 0, somar(y, dB).v ?? 0) - Math.max(somar(x, dA).v ?? 0, somar(x, dB).v ?? 0)).slice(0, 8);
  const eixos = benchmarkLinhas(ds, top, dA, refQ, dB, nomeB);
  const ok = eixos.filter((e) => e.nd === null);
  const refNome = refQ === "lado" ? nomeB : REFERENCIA[refQ];
  const maxPct = Math.max(1, ...ok.map((e) => e.pctA ?? 0));
  const build = (t: ChartTokens) => ({
    legend: { bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: t.text2, fontFamily: t.font, fontSize: 11 }, data: [nomeA, refNome] },
    tooltip: { trigger: "item", backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
      formatter: (q: { name: string; value: number[] }) => `<b>${q.name}</b><br/>` + ok.map((e, i) => `${e.linha.nome}: ${pct(q.value[i])}`).join("<br/>") },
    radar: { radius: "62%", center: ["50%", "47%"], splitNumber: 4, shape: "polygon", indicator: ok.map((e) => ({ name: e.linha.nome.length > 26 ? e.linha.nome.slice(0, 25) + "…" : e.linha.nome, max: maxPct * 1.05, min: 0 })),
      axisName: { color: t.text2, fontFamily: t.font, fontSize: 11 }, splitLine: { lineStyle: { color: t.hairline } }, splitArea: { show: false }, axisLine: { lineStyle: { color: t.hairline } } },
    series: [{ type: "radar", symbolSize: 5, data: [
      { name: refNome, value: ok.map(() => 1), lineStyle: { color: t.sideB, width: 1.5, type: "dashed" }, itemStyle: { color: t.sideB }, areaStyle: { color: t.sideB, opacity: 0.06 } },
      { name: nomeA, value: ok.map((e) => e.pctA), lineStyle: { color: t.sideA, width: 2 }, itemStyle: { color: t.sideA }, areaStyle: { color: t.sideA, opacity: 0.14 } },
    ] }],
  });
  const exportCSV = () => {
    const name = `bdgd_2025-12-31_radar_${refQ}.csv`;
    downloadText(name, toCSV(["data_base", "recorte", "linha", "medida", "unidade", "A", "A_dists_com_valor", "A_dists_total", "referencia", "referencia_valor", "A_sobre_referencia", "lider", "lider_valor", "situacao", ...COLUNAS_OBSERVACOES],
      eixos.map((e) => ["2025-12-31", recorteTxt, e.linha.nome, e.linha.medida, UNIDADE[e.linha.medida], e.a.v, e.a.n, e.a.total, e.refNome, e.ref, e.pctA, e.lider?.nome ?? null, e.lider?.v ?? null, e.nd ?? "ok", ...observacoesDeLinha(e.linha)])));
    toast(`${name} exportado`);
  };
  return (
    <div data-testid="radar">
      <div className={s.radarHead}>
        <div>
          <h2 className="title" style={{ fontSize: "1.25rem" }}>Quem lidera em volume de ativos</h2>
          <p className="caption" style={{ marginTop: 4, maxWidth: 640, lineHeight: 1.5 }}>
            Maior volume por indicador, no recorte atual ({recorteTxt}). Em cada eixo, A e a referência são divididos pelo valor da referência: ela fica em 100% e A pode passar de 100%. Volume maior não significa desempenho melhor.{" "}
            <Explain title="Como o radar é calculado" testId="radar-explain" tecnico="eixo_m = A_m / R_m, com R_m = B_m (lado B), T_m = Σ_d v_d,m (Brasil), MAX_g Σ_{d∈g} v_d,m (grupos verificados) ou MAX_d v_d,m (distribuidoras), todos no mesmo recorte e medida. Eixo removido se A_m ou R_m for N/D ou R_m = 0.">
              Para cada linha da comparação, o valor de A é comparado com uma referência: o lado B, o total do Brasil, o maior grupo econômico ou a maior distribuidora, sempre com os mesmos filtros.
            </Explain>
          </p>
        </div>
        <div className={s.radarCtl}>
          <Segmented label="Referência" size="sm" value={refQ} onChange={setRef} options={[
            { value: "bench_grupos", label: "Maior grupo" }, { value: "bench_dists", label: "Maior distribuidora" }, { value: "brasil", label: "Brasil" }, { value: "lado", label: "Lado B" }]} />
        </div>
      </div>
      <div className={s.radarBody}>
        <div className={s.radarChart}>
          {ok.length >= 3 ? <EChart build={build} height={380} ariaLabel={`Radar de ${nomeA} frente a ${refNome}; os valores estão na tabela ao lado`} testId="chart-radar" />
            : <div className="caption" style={{ padding: 24 }}>Menos de 3 linhas com valor dos dois lados: radar indisponível. Veja a tabela ao lado.</div>}
        </div>
        <div style={{ minWidth: 0 }}>
          <table className={s.radarTable} data-testid="radar-tabela">
            <caption className="sr-only">Valores por linha, referência e líder</caption>
            <thead><tr><th scope="col">Linha</th><th scope="col">A</th><th scope="col">Referência</th><th scope="col">A / ref.</th><th scope="col" className={s.lider}>Líder</th></tr></thead>
            <tbody>
              {eixos.map((e) => (
                <tr key={e.linha.id}>
                  <th scope="row">{e.linha.nome}<span className="faint"> · {UNIDADE[e.linha.medida]}</span></th>
                  <td>{e.a.v === null ? "N/D" : fmt(e.a.v, e.linha.medida)}</td>
                  <td>{e.ref === null ? "N/D" : fmt(e.ref, e.linha.medida)}</td>
                  <td data-testid={`radar-pct-${e.linha.id}`}>{e.pctA === null ? <span className="faint" title={e.nd ?? ""}>N/D</span> : <b className={e.pctA > 1 ? s.over : undefined}>{pct(e.pctA)}</b>}</td>
                  <td className={s.lider}>{e.lider ? <><b>{e.lider.nome}</b><br /><span className="faint">{fmtCompact(e.lider.v, e.linha.medida)}</span></> : <span className="faint">N/D</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 10 }}><Button size="sm" onClick={exportCSV} data-testid="radar-csv"><Download size={14} /> CSV do radar</Button></div>
        </div>
      </div>
    </div>
  );
}
