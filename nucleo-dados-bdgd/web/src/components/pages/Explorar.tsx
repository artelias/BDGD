"use client";
import { Info, Search, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useMemo, useState } from "react";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { DataError, EmptyState, LoadingBlock, Tip } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { Pill, Value } from "@/components/ui/Value";
import { groupColor } from "@/lib/colors";
import { displayName, type Dataset } from "@/lib/dataset";
import { useData, useFacets } from "@/lib/data-context";
import { availableCodes, combinableWith, describe, distribution, facetValue, singleAttributes } from "@/lib/facets";
import { fmt, fmtCompact, fmtShare, METRIC_LABEL, METRIC_UNIT } from "@/lib/format";
import { useTheme } from "@/lib/theme";
import type { FacetData, Metric, Scope } from "@/lib/types";
import { parseSide, useQueryPatch, useQueryState } from "@/lib/url-state";
import p from "./pages.module.css";
import s from "./explorar.module.css";

const HOMOL_LABEL: Record<string, { t: string; tone: "ok" | "warn" | "nd" | "default" }> = {
  homologada: { t: "homologada", tone: "ok" }, homologada_com_ressalvas: { t: "homologada com ressalvas", tone: "warn" },
  nao_homologada: { t: "não homologada", tone: "nd" }, informativa: { t: "informativa", tone: "default" },
};

export function Explorar() {
  const data = useData();
  if (data.status === "loading") return <LoadingBlock lines={6} />;
  if (data.status === "error") return <DataError error={data.error} />;
  return <ExplorarReady ds={data.ds} />;
}

function ExplorarReady({ ds }: { ds: Dataset }) {
  const { resolved } = useTheme();
  const patch = useQueryPatch();
  const [entQ] = useQueryState("ent", "UCBT");
  const [escopoQ] = useQueryState("escopo", "brasil");
  const [a1] = useQueryState("a1");
  const [c1] = useQueryState("c1");
  const [a2] = useQueryState("a2");
  const [metQ, setMet] = useQueryState("metrica");
  const [q, setQ] = useState("");
  const ent = ds.entidade(entQ) ? entQ : "UCBT";
  const E = ds.entidade(ent)!;
  const facets = useFacets(ent);

  const scope: Scope = useMemo(() => {
    const x = parseSide(escopoQ);
    if (x?.tipo === "dist" && ds.dist(x.id)) return x;
    if (x?.tipo === "grupo" && ds.grupo(x.id)) return x;
    return { tipo: "brasil" };
  }, [escopoQ, ds]);
  const dists = useMemo(() => new Set(ds.scopeDists(scope)), [ds, scope]);
  const homol = ds.raw.homologacao.filter((h) => h.entidade === ent);

  const railList = useMemo(() => {
    const t = q.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    return ds.familias.map((f) => ({ f, ents: ds.entidadesDaFamilia(f).filter((e) => !t || `${e.id} ${e.nome}`.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().includes(t)) })).filter((x) => x.ents.length);
  }, [ds, q]);

  const scopeOpts = [{ value: "brasil", label: "Brasil", group: "Nacional" },
    ...ds.grupos.map((g) => ({ value: `grupo:${g.id}`, label: g.nome, group: "Grupos verificados", color: groupColor(g.id, resolved), meta: `${ds.groupDists(g.id).length} DIST` })),
    ...ds.dists.map((d) => ({ value: `dist:${d.dist}`, label: displayName(d), group: "Distribuidoras", meta: `DIST ${d.dist}`, keywords: d.nome }))];

  const factsDists = [...dists];
  const facts: Array<{ m: Metric; label: string }> = [
    { m: "quantidade", label: "Quantidade" }, { m: "quantidade_registros", label: "Registros" },
    ...(["UCBT", "UCMT", "UCAT"].includes(ent) ? [{ m: "quantidade_cod_id_distinto" as Metric, label: "COD_ID distintos" }] : []),
    ...(E.metrica !== "quantidade" ? [{ m: E.metrica, label: METRIC_LABEL[E.metrica] }] : []),
  ];

  return (
    <>
      <header className={`${p.head} rise`}>
        <div className="eyebrow">Recortes por atributos do DDA · cubos homologados</div>
        <h1 className="display" style={{ marginTop: 8 }}>Entidades e DDA</h1>
        <p className="lede">Escolha uma entidade e filtre por atributos técnicos com descrições do Dicionário de Dados da ANEEL. Combinações de filtros só aparecem quando existe um cubo conjunto calculado no ETL — nada é estimado a partir de totais marginais.</p>
      </header>

      <div className={s.layout}>
        <nav className={s.rail} aria-label="Entidades BDGD">
          <label className={p.field}><Search size={14} aria-hidden /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar entidade" aria-label="Buscar entidade" /></label>
          <div className={s.railList}>
            {railList.map(({ f, ents }) => (
              <div key={f}>
                <div className={s.fam}>{f}</div>
                {ents.map((e) => (
                  <button key={e.id} className={s.ent} aria-current={e.id === ent} onClick={() => patch({ ent: e.id, a1: null, c1: null, a2: null, metrica: null }, true)}>
                    {e.id === ent && <motion.span layoutId="ent-active" className={s.entActive} transition={{ type: "spring", stiffness: 480, damping: 38 }} />}
                    <span className={s.entCode}>{e.id}</span>{e.nome}
                  </button>
                ))}
              </div>
            ))}
          </div>
          <div className="mobileEnt" style={{ marginTop: 10 }}>
            <Picker label="Entidade" value={ent} options={ds.entidades.map((e) => ({ value: e.id, label: e.nome, meta: e.id, group: e.familia }))} onChange={(v) => patch({ ent: v, a1: null, c1: null, a2: null, metrica: null }, true)} />
          </div>
        </nav>

        <div style={{ minWidth: 0 }}>
          <div className={s.entHead}>
            <div style={{ minWidth: 0 }}>
              <div className="eyebrow"><span className="mono">{E.id}</span> · {E.familia}</div>
              <h2 className="title" style={{ marginTop: 6 }} data-testid="ent-title">{E.nome}</h2>
              <p className="caption" style={{ maxWidth: "70ch", marginTop: 6 }}>{E.regra}</p>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8 }}>
                {homol.filter((h) => h.status !== "informativa").map((h) => <Pill key={h.metrica} tone={HOMOL_LABEL[h.status]?.tone ?? "default"} title={`${h.comValor} DIST com valor, ${h.nd} N/D, ${h.alerta} com alerta · ${h.recOk} reconciliações exatas`}>{METRIC_LABEL[h.metrica as Metric] ?? h.metrica}: {HOMOL_LABEL[h.status]?.t ?? h.status}</Pill>)}
              </div>
            </div>
            <div style={{ width: 280, maxWidth: "100%" }}>
              <Picker label="Escopo" value={scope.tipo === "brasil" ? "brasil" : `${scope.tipo}:${scope.id}`} options={scopeOpts} onChange={(v) => patch({ escopo: v === "brasil" ? null : v })} testId="explorar-escopo" />
            </div>
          </div>

          <div className={s.facts}>
            {facts.map((f) => {
              const a = ds.aggregate(factsDists, ent, f.m);
              return (
                <div key={f.m} className={s.fact}>
                  <div className={s.factLabel}>{f.label} · {ds.scopeLabel(scope)}</div>
                  <div className={s.factValue}><Value v={a.v} metric={f.m} /></div>
                  <div className="caption">{a.n}/{a.total} DIST{a.nd ? ` · ${a.nd} N/D` : ""}{a.ausentes ? ` · ${a.ausentes} sem a entidade` : ""}</div>
                </div>
              );
            })}
          </div>

          {facets.loading && <LoadingBlock lines={4} label="Carregando cubos DDA" />}
          {facets.error && <EmptyState title="Recortes DDA indisponíveis" tone="warn">{facets.error}</EmptyState>}
          {facets.data && <FacetExplorer key={ent} data={facets.data} dists={dists} ent={ent} a1={a1} c1={c1} a2={a2} metQ={metQ} setMet={setMet} patch={patch} defaultMetric={E.metrica} />}
        </div>
      </div>
      <style>{`.mobileEnt{display:none}@media (max-width:1100px){.mobileEnt{display:block}}`}</style>
    </>
  );
}

function FacetExplorer({ data, dists, ent, a1, c1, a2, metQ, setMet, patch, defaultMetric }: {
  data: FacetData; dists: Set<number>; ent: string; a1: string; c1: string; a2: string; metQ: string; setMet: (v: string | null) => void;
  patch: (p: Record<string, string | null>, push?: boolean) => void; defaultMetric: Metric;
}) {
  const attrs = singleAttributes(data);
  if (!attrs.length) return <EmptyState title="Sem atributos DDA para esta entidade">A entidade não possui campos com domínio DDA mapeado no catálogo M10; os totais acima continuam válidos.</EmptyState>;
  const A1 = attrs.includes(a1) ? a1 : attrs[0];
  const comb = combinableWith(data, A1);
  const C1 = c1 && availableCodes(data, A1, dists).includes(c1) ? c1 : "";
  const A2 = C1 && comb.includes(a2) ? a2 : "";
  const facetForMetrics = data.facets.find((f) => f.dims.length === 1 && f.dims[0] === A1)!;
  const metrics = (Object.keys(facetForMetrics.metricas) as Metric[]);
  const metric: Metric = metrics.includes(metQ as Metric) ? (metQ as Metric) : metrics.includes(defaultMetric) ? defaultMetric : metrics[0];
  const label = (a: string) => data.atributos?.[a]?.rotulo ?? a;

  const target = A2 || A1;
  const dist = distribution(data, target, metric, dists, A2 ? { [A1]: C1 } : undefined);
  const selectedValue = C1 && !A2 ? facetValue(data, { [A1]: C1 }, metric, dists) : null;
  const total = dist.categories.reduce((x, c) => x + (c.v ?? 0), 0);

  return (
    <section aria-label="Recortes DDA">
      <div className={s.step}>
        <div className={s.stepLabel}><span className={s.stepNum}>1</span>Atributo</div>
        <div className={s.attrs} role="group" aria-label="Atributo DDA">
          {attrs.map((a) => (
            <Tip key={a} text={data.atributos?.[a]?.descricao || a}>
              <button className={s.attr} aria-pressed={a === A1} onClick={() => patch({ a1: a, c1: null, a2: null })} data-testid={`attr-${a}`}>{label(a)}</button>
            </Tip>
          ))}
        </div>
      </div>

      {C1 && (
        <div className={s.step}>
          <div className={s.stepLabel}><span className={s.stepNum}>2</span>Cruzar com (cubo conjunto)</div>
          <div className={s.attrs} role="group" aria-label="Segundo atributo">
            {attrs.filter((a) => a !== A1).map((a) => {
              const ok = comb.includes(a);
              return (
                <Tip key={a} text={ok ? data.atributos?.[a]?.descricao || a : "Combinação indisponível: não há cubo conjunto calculado para estes dois atributos."}>
                  <button className={s.attr} aria-pressed={a === A2} aria-disabled={!ok} onClick={() => ok && patch({ a2: a === A2 ? null : a })} data-testid={`attr2-${a}`}>{label(a)}</button>
                </Tip>
              );
            })}
          </div>
        </div>
      )}

      <div className={s.chipsActive} aria-live="polite">
        <span className="label">Recorte:</span>
        <AnimatePresence initial={false}>
          {C1 ? (
            <motion.span key="c1" className={s.chip} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
              {label(A1)} = {describe(data, A1, C1)}
              <button aria-label="Remover filtro" onClick={() => patch({ c1: null, a2: null })}><X size={12} /></button>
            </motion.span>
          ) : <motion.span key="none" className="caption" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>sem filtro — clique em uma categoria para filtrar</motion.span>}
        </AnimatePresence>
        <span style={{ flex: 1 }} />
        <Segmented size="sm" label="Métrica" value={metric} onChange={(v) => setMet(v)} options={metrics.map((m) => ({ value: m, label: METRIC_LABEL[m] }))} />
      </div>

      {selectedValue && selectedValue.status === "ok" && (
        <p className={p.note}><Info size={14} />{label(A1)} = {describe(data, A1, C1)}: <b className="num">{fmt(selectedValue.v, metric)} {METRIC_UNIT[metric]}</b> em {selectedValue.n} distribuidora(s){selectedValue.nd ? `, ${selectedValue.nd} N/D` : ""}.</p>
      )}

      <div className={s.dist}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <div className="headline" style={{ fontSize: "1rem" }}>{label(target)}{A2 ? <span className="faint"> · dado {label(A1)} = {describe(data, A1, C1)}</span> : null}</div>
            <div className="caption">{METRIC_LABEL[metric]} ({METRIC_UNIT[metric]}) por categoria · {dist.facet?.id}</div>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {dist.status === "ok" && <Pill tone={dist.covered < dists.size ? "warn" : "default"} title="Distribuidoras do escopo para as quais este cubo foi calculado">Cubo: {dist.covered} de {dists.size} DIST</Pill>}
            {!dist.additive && dist.categories.length > 0 && <Pill tone="warn" title="Um mesmo COD_ID pode estar em mais de uma categoria (registros históricos AT/DS com atributos diferentes).">Categorias se sobrepõem · não somar</Pill>}
          </div>
        </div>
        {dist.status === "combinacao_nao_suportada" ? <EmptyState title="Combinação indisponível">Não há cubo conjunto calculado para estes atributos. Nenhuma estimativa é exibida.</EmptyState>
          : dist.status !== "ok" ? <EmptyState title="Sem dados no recorte">Nenhuma distribuidora do escopo possui esta entidade com o atributo informado.</EmptyState>
          : (
            <>
              <CategoryChart data={dist.categories.slice(0, 14)} metric={metric} onPick={(code) => !A2 && patch({ c1: code === C1 ? null : code, a2: null })} />
              <table className={s.catTable}>
                <thead><tr><th scope="col">Categoria (DDA)</th><th scope="col">{METRIC_LABEL[metric]}</th><th scope="col">{dist.additive ? "Participação" : ""}</th><th scope="col">DIST</th></tr></thead>
                <tbody>
                  {dist.categories.map((c) => (
                    <tr key={c.code} className={s.catRow} aria-selected={!A2 && c.code === C1} onClick={() => !A2 && patch({ c1: c.code === C1 ? null : c.code, a2: null })} tabIndex={A2 ? -1 : 0}
                      onKeyDown={(e) => { if (!A2 && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); patch({ c1: c.code === C1 ? null : c.code, a2: null }); } }}>
                      <td>{c.label} <span className={s.code}>{c.code}</span></td>
                      <td><Value v={c.v} metric={metric} unitOverride="" /></td>
                      <td>{dist.additive && c.v !== null && total > 0 ? <>{fmtShare(c.v / total)}<span className={s.share}><span className={s.shareFill} style={{ transform: `scaleX(${c.v / total})` }} /></span></> : ""}</td>
                      <td className="faint">{c.n}{c.nd ? ` · ${c.nd} N/D` : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
      </div>
      <p className="caption" style={{ marginTop: 10 }}>Descrições: {`Dicionário de Dados ANEEL (DDA M10)`}; códigos sem correspondência no DDA aparecem como “sem descrição”. “Sem código informado” agrupa registros sem valor no campo. Entidade: {ent}.</p>
    </section>
  );
}

function CategoryChart({ data, metric, onPick }: { data: Array<{ code: string; label: string; v: number | null }>; metric: Metric; onPick: (code: string) => void }) {
  const build = useCallback((t: ChartTokens) => ({
    grid: { left: 8, right: 64, top: 10, bottom: 4, containLabel: true },
    tooltip: { trigger: "item", backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
      formatter: (q: { dataIndex: number }) => `<b>${data[q.dataIndex].label}</b><br/>${fmt(data[q.dataIndex].v, metric)} ${METRIC_UNIT[metric]}` },
    xAxis: { type: "value", show: false },
    yAxis: { type: "category", inverse: true, data: data.map((c) => (c.label.length > 34 ? c.label.slice(0, 33) + "…" : c.label)), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 11 } },
    series: [{ type: "bar", barWidth: 11, data: data.map((c) => ({ value: c.v ?? 0, itemStyle: { color: c.v === null ? t.nd : t.accent, borderRadius: 3 } })),
      label: { show: true, position: "right", color: t.text2, fontFamily: t.font, fontSize: 11, formatter: (q: { dataIndex: number }) => fmtCompact(data[q.dataIndex].v, metric) } }],
  }), [data, metric]);
  return <EChart build={build} height={Math.max(140, data.length * 26 + 20)} ariaLabel="Distribuição por categoria do atributo DDA" onClickIndex={(i) => onPick(data[i].code)} testId="chart-categorias" />;
}
