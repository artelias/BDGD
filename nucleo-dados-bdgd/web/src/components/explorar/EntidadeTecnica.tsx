"use client";
import { Code2, Download, Info, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useState } from "react";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { Button } from "@/components/ui/Button";
import { Explain } from "@/components/ui/Explain";
import { downloadText, EmptyState, LoadingBlock, Tip, useToast } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { Pill, Value } from "@/components/ui/Value";
import { nomeNegocio } from "@/lib/catalogo";
import type { Dataset } from "@/lib/dataset";
import { useFacets } from "@/lib/data-context";
import { availableCodes, combinableWith, describe, distribution, facetValue, singleAttributes } from "@/lib/facets";
import { fmt, fmtCompact, fmtShare, METRIC_LABEL, METRIC_UNIT, toCSV } from "@/lib/format";
import { participacao } from "@/lib/participacao";
import type { FacetData, Metric, Scope } from "@/lib/types";
import { useQueryPatch, useQueryState } from "@/lib/url-state";
import p from "@/components/pages/pages.module.css";
import s from "@/components/pages/explorar.module.css";

const HOMOL_LABEL: Record<string, { t: string; tone: "ok" | "warn" | "nd" | "default" }> = {
  homologada: { t: "homologada", tone: "ok" }, homologada_com_ressalvas: { t: "homologada com ressalvas", tone: "warn" },
  nao_homologada: { t: "não homologada", tone: "nd" }, informativa: { t: "informativa", tone: "default" },
};
const CLASSE: Record<string, { t: string; tone: "ok" | "warn" | "nd" | "default" }> = {
  filtravel: { t: "Filtrável agora", tone: "ok" }, requer_cubo: { t: "Requer cubo", tone: "default" },
  requer_juncao: { t: "Requer junção", tone: "warn" }, nao_publicavel: { t: "Não publicável", tone: "nd" },
};
const TECNICAS: Metric[] = ["quantidade_registros", "quantidade_cod_id_distinto"];
const pct = (x: number | null) => (x === null ? "N/D" : `${(x * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`);

/** Visão técnica por entidade BDGD (R2): cubos DDA por tabela de origem. Mantida para especialistas e para Perdas e balanço. */
export function EntidadeTecnica({ ds, entidades, dists, scope }: { ds: Dataset; entidades: string[]; dists: Set<number>; scope: Scope }) {
  const patch = useQueryPatch();
  const [entQ] = useQueryState("tec", entidades[0]);
  const [a1] = useQueryState("a1");
  const [c1] = useQueryState("c1");
  const [a2] = useQueryState("a2");
  const [metQ, setMet] = useQueryState("metrica");
  const ent = entidades.includes(entQ) && ds.entidade(entQ) ? entQ : entidades.find((e) => ds.entidade(e)) ?? entidades[0];
  const E = ds.entidade(ent);
  const facets = useFacets(E ? ent : null);
  const brasil = new Set(ds.dists.map((d) => d.dist));
  if (!E) return <EmptyState title="Entidade indisponível">Esta entidade não tem dados no pacote 2025.</EmptyState>;
  const homol = ds.raw.homologacao.filter((h) => h.entidade === ent);
  const facts: Array<{ m: Metric; label: string }> = [
    { m: "quantidade", label: "Quantidade" }, { m: "quantidade_registros", label: "Registros no arquivo" },
    ...(E.metrica !== "quantidade" ? [{ m: E.metrica, label: METRIC_LABEL[E.metrica] }] : []),
  ];
  return (
    <section aria-label="Visão técnica por entidade" data-testid="visao-tecnica">
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", margin: "6px 0 14px" }}>
        {entidades.length > 1 && (
          <Picker label="Entidade BDGD" value={ent} compact width={300} options={entidades.filter((e) => ds.entidade(e)).map((e) => ({ value: e, label: nomeNegocio(e, ds.entidade(e)!.nome), meta: e }))}
            onChange={(v) => patch({ tec: v, a1: null, c1: null, a2: null, metrica: null })} testId="tec-entidade" />
        )}
        <span className="caption"><span className="mono">{ent}</span> · {E.regra}</span>
        {homol.filter((h) => h.status !== "informativa" && !TECNICAS.includes(h.metrica as Metric)).map((h) => <Pill key={h.metrica} tone={HOMOL_LABEL[h.status]?.tone ?? "default"}>{METRIC_LABEL[h.metrica as Metric] ?? h.metrica}: {HOMOL_LABEL[h.status]?.t ?? h.status}</Pill>)}
      </div>
      <div className={s.facts}>
        {facts.map((f) => {
          const a = ds.aggregate([...dists], ent, f.m);
          return (
            <div key={f.m} className={s.fact}>
              <div className={s.factLabel}>{f.label}</div>
              <div className={s.factValue}><Value v={a.v} metric={f.m} /></div>
              <div className="caption">{a.total > 1 ? `${a.n} de ${a.total} distribuidoras com valor` : a.n ? "valor reconciliado" : "sem valor"}</div>
            </div>
          );
        })}
      </div>
      {facets.loading && <LoadingBlock lines={4} label="Carregando recortes" />}
      {facets.error && <EmptyState title="Recortes indisponíveis" tone="warn">{facets.error}</EmptyState>}
      {facets.data && <FacetExplorer key={ent} ds={ds} data={facets.data} dists={dists} brasil={brasil} scope={scope} ent={ent} a1={a1} c1={c1} a2={a2} metQ={metQ} setMet={setMet} patch={patch} defaultMetric={E.metrica} avancado scopeKey={scope.tipo === "brasil" ? "brasil" : `${scope.tipo}-${scope.id}`} />}
      {facets.data && <Inventario data={facets.data} avancado />}
    </section>
  );
}

function FacetExplorer({ ds, data, dists, brasil, scope, ent, a1, c1, a2, metQ, setMet, patch, defaultMetric, scopeKey, avancado }: {
  ds: Dataset; data: FacetData; dists: Set<number>; brasil: Set<number>; scope: Scope; ent: string; a1: string; c1: string; a2: string; metQ: string; setMet: (v: string | null) => void;
  patch: (p: Record<string, string | null>, push?: boolean) => void; defaultMetric: Metric; scopeKey: string; avancado: boolean;
}) {
  const toast = useToast();
  const attrs = singleAttributes(data);
  if (!attrs.length) return <EmptyState title="Sem atributos com cubo para este tipo de ativo">Os totais acima continuam válidos. Veja abaixo o inventário de atributos.</EmptyState>;
  const A1 = attrs.includes(a1) ? a1 : attrs.includes("TUC") ? "TUC" : attrs[0];
  const comb = combinableWith(data, A1);
  const C1 = c1 && availableCodes(data, A1, dists).includes(c1) ? c1 : "";
  const A2 = C1 && comb.includes(a2) ? a2 : "";
  const facetForMetrics = data.facets.find((f) => f.dims.length === 1 && f.dims[0] === A1)!;
  const metrics = (Object.keys(facetForMetrics.metricas) as Metric[]).filter((m) => avancado || !TECNICAS.includes(m) || m === defaultMetric);
  const metric: Metric = metrics.includes(metQ as Metric) ? (metQ as Metric) : metrics.includes(defaultMetric) ? defaultMetric : metrics[0];
  const label = (a: string) => data.atributos?.[a]?.rotulo ?? a;
  /** A1 do MCPSE depende do TUC: com TUC fixado, usa a descrição daquele TUC. */
  const desc = (attr: string, code: string) => {
    if (attr === "A1" && A1 === "TUC" && C1 && data.a1PorTuc?.[C1]?.[code]) return data.a1PorTuc[C1][code];
    if (attr === "TUC" && code !== "SEM_CODIGO" && !data.descricoes.TUC?.[code]) return `Código ${code} (sem correspondência no MCPSE)`;
    return describe(data, attr, code);
  };

  const target = A2 || A1;
  const dist = distribution(data, target, metric, dists, A2 ? { [A1]: C1 } : undefined);
  for (const c of dist.categories) if (target === "A1" || target === "TUC") c.label = desc(target, c.code);
  const selectedValue = C1 && !A2 ? facetValue(data, { [A1]: C1 }, metric, dists) : null;
  const total = dist.categories.reduce((x, c) => x + (c.v ?? 0), 0);
  const comEnt = (set: Set<number>) => [...set].filter((d) => ds.hasEntity(d, ent)).length;
  const part = C1 && !A2 && scope.tipo !== "brasil" ? participacao(data, { [A1]: C1 }, A1, metric, dists, brasil, comEnt(dists), comEnt(brasil)) : null;
  const unit = METRIC_UNIT[metric] || "itens";

  const exportCSV = () => {
    const name = `bdgd_2025-12-31_${ent}_${target}${A2 ? `_dado-${A1}-${C1}` : ""}_${metric}_${scopeKey}.csv`.replace(/[^\w.-]+/g, "-");
    downloadText(name, toCSV(["data_base", "versao", "entidade", "escopo", "cubo", "filtro", "atributo", "codigo", "descricao", "metrica", "unidade", "valor", "dists_com_valor", "dists_nd", "cobertura_cubo", "status_soma"],
      dist.categories.map((c) => ["2025-12-31", ds.raw.release.release_id, ent, ds.scopeLabel(scope), dist.facet?.id ?? "", A2 ? `${A1}=${C1}` : "", target, c.code, c.label, metric, unit, c.v, c.n, c.nd,
        `${dist.covered}/${comEnt(dists)}`, dist.additive ? "particao_disjunta" : "categorias_sobrepostas_nao_somar"])));
    toast(`${name} exportado`);
  };

  return (
    <section aria-label="Recortes por atributo">
      <div className={s.step}>
        <div className={s.stepLabel}><span className={s.stepNum}>1</span>Atributo</div>
        <div className={s.attrs} role="group" aria-label="Atributo">
          {attrs.map((a) => (
            <Tip key={a} text={data.atributos?.[a]?.descricao || a}>
              <button className={s.attr} aria-pressed={a === A1} onClick={() => patch({ a1: a, c1: null, a2: null })} data-testid={`attr-${a}`}>{label(a)}{avancado && <span className={s.code}> {a}</span>}</button>
            </Tip>
          ))}
        </div>
      </div>

      {C1 && (
        <div className={s.step}>
          <div className={s.stepLabel}><span className={s.stepNum}>2</span>Cruzar com (cubo conjunto)</div>
          <div className={s.attrs} role="group" aria-label="Segundo atributo">
            {[...new Set([...comb, ...attrs])].filter((a) => a !== A1).sort((x, y) => Number(comb.includes(y)) - Number(comb.includes(x))).map((a) => {
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
              {label(A1)} = {desc(A1, C1)}
              <button aria-label="Remover filtro" onClick={() => patch({ c1: null, a2: null })}><X size={12} /></button>
            </motion.span>
          ) : <motion.span key="none" className="caption" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>sem filtro: clique em uma categoria para filtrar</motion.span>}
        </AnimatePresence>
        <span style={{ flex: 1 }} />
        <Segmented size="sm" label="Medida" value={metric} onChange={(v) => setMet(v)} options={metrics.map((m) => ({ value: m, label: METRIC_LABEL[m] }))} />
      </div>

      {selectedValue && selectedValue.status === "ok" && (
        <p className={p.note}><Info size={14} /><span>{label(A1)} = {desc(A1, C1)}: <b className="num">{fmt(selectedValue.v, metric)} {METRIC_UNIT[metric]}</b> em {selectedValue.n} distribuidora(s){selectedValue.nd ? `, ${selectedValue.nd} sem valor homologado` : ""}.</span></p>
      )}

      {A1 === "TUC" && C1 && !A2 && <Vinculos ds={ds} ent={ent} tuc={C1} dists={dists} nome={desc("TUC", C1)} />}

      {part && (
        <div className={s.part} data-testid="participacao">
          <div className={s.partCell}>
            <div className={s.factLabel}>Participação no {scope.tipo === "grupo" ? "grupo" : "recorte"}</div>
            <div className={s.factValue} data-testid="part-escopo">{pct(part.noEscopo)}</div>
            <div className="caption">{part.noEscopo !== null ? `${desc(A1, C1)} / todas as categorias de ${label(A1).toLowerCase()} em ${ds.scopeLabel(scope)}` : part.motivoEscopo}</div>
          </div>
          <div className={s.partCell}>
            <div className={s.factLabel}>Participação no Brasil</div>
            <div className={s.factValue} data-testid="part-brasil">{pct(part.doBrasil)}</div>
            <div className="caption">{part.doBrasil !== null ? `${ds.scopeLabel(scope)} / total Brasil de ${desc(A1, C1)}` : part.motivoBrasil}</div>
          </div>
          <div className={s.partNote}>
            <Explain title="Participação dupla" align="end" tecnico={`no recorte = v(recorte, ${A1}=${C1}) / Σ_c v(recorte, ${A1}=c); no Brasil = v(recorte, ${A1}=${C1}) / v(Brasil, ${A1}=${C1}); mesmo cubo ${dist.facet?.id ?? ""}, mesma medida (${metric}).`}
              ressalva="Fica N/D se o cubo não cobre todas as distribuidoras que têm este ativo, se as categorias se sobrepõem ou se algum valor não está homologado.">
              Duas leituras do mesmo número: quanto essa categoria representa dentro do recorte escolhido, e quanto o recorte representa do Brasil nessa mesma categoria.
            </Explain>
          </div>
        </div>
      )}

      <div className={s.dist}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <div className="headline" style={{ fontSize: "1rem" }}>{label(target)}{A2 ? <span className="faint"> · dado {label(A1)} = {desc(A1, C1)}</span> : null}</div>
            <div className="caption">{METRIC_LABEL[metric]} ({unit}) por categoria{avancado ? ` · ${dist.facet?.id}` : ""}</div>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {dist.status === "ok" && <Pill tone={dist.covered < comEnt(dists) ? "warn" : "default"} title="Distribuidoras do escopo para as quais este cubo foi calculado">Cubo: {dist.covered} de {comEnt(dists)} distribuidoras</Pill>}
            {dist.status === "ok" && <Button size="sm" onClick={exportCSV} data-testid="explorar-csv"><Download size={13} /> CSV</Button>}
            {!dist.additive && dist.categories.length > 0 && <Pill tone="warn" title="Um mesmo consumidor pode estar em mais de uma categoria (registros históricos com atributos diferentes).">Categorias se sobrepõem · não somar</Pill>}
          </div>
        </div>
        {dist.status === "combinacao_nao_suportada" ? <EmptyState title="Combinação indisponível">Não há cubo conjunto calculado para estes atributos. Nenhuma estimativa é exibida.</EmptyState>
          : dist.status !== "ok" ? <EmptyState title="Sem dados no recorte">Nenhuma distribuidora do escopo possui este ativo com o atributo informado.</EmptyState>
          : (
            <>
              <CategoryChart data={dist.categories.slice(0, 14)} metric={metric} onPick={(code) => !A2 && patch({ c1: code === C1 ? null : code, a2: null })} />
              <table className={s.catTable}>
                <thead><tr><th scope="col">Categoria</th><th scope="col">{METRIC_LABEL[metric]}</th><th scope="col">{dist.additive ? "Participação" : ""}</th><th scope="col">Distribuidoras</th></tr></thead>
                <tbody>
                  {dist.categories.map((c) => (
                    <tr key={c.code} className={s.catRow} aria-selected={!A2 && c.code === C1} onClick={() => !A2 && patch({ c1: c.code === C1 ? null : c.code, a2: null })} tabIndex={A2 ? -1 : 0}
                      onKeyDown={(e) => { if (!A2 && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); patch({ c1: c.code === C1 ? null : c.code, a2: null }); } }}>
                      <td>{c.label} <span className={s.code}>{c.code}</span></td>
                      <td><Value v={c.v} metric={metric} unitOverride="" /></td>
                      <td>{dist.additive && c.v !== null && total > 0 ? <>{fmtShare(c.v / total)}<span className={s.share}><span className={s.shareFill} style={{ transform: `scaleX(${c.v / total})` }} /></span></> : ""}</td>
                      <td className="faint">{c.n}{c.nd ? ` · ${c.nd} sem valor` : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
      </div>
      <p className="caption" style={{ marginTop: 10 }}>Descrições: Dicionário de Dados ANEEL (DDA), MCPSE (TUC e A1, Res. ANEEL 674/2015) e IBGE (municípios). Códigos sem correspondência aparecem como “sem descrição”; “Sem código informado” agrupa registros sem valor no campo.</p>
    </section>
  );
}

/** Equipamentos do TUC e as instalações (UN*) distintas que ocupam: um equipamento não é uma instalação. */
function Vinculos({ ds, ent, tuc, dists, nome }: { ds: Dataset; ent: string; tuc: string; dists: Set<number>; nome: string }) {
  const v = ds.raw.vinculosTuc;
  if (!v) return null;
  let eq = 0, vinc = 0, un = 0, n = 0;
  for (const [d, e, t, equip, , vinculados, unidades] of v.rows) if (e === ent && t === tuc && dists.has(d)) { eq += equip; vinc += vinculados; un += unidades; n++; }
  if (!n) return null;
  const dest = (v.destinos[ent] ?? []).join(", ");
  return (
    <p className={p.note} data-testid="vinculos-tuc"><Info size={14} aria-hidden />
      <span>{nome}: <b className="num">{fmt(eq)}</b> equipamentos, dos quais <b className="num">{fmt(vinc)}</b> apontam para uma instalação existente ({dest}), ocupando <b className="num">{fmt(un)}</b> instalações distintas em {n} distribuidora{n === 1 ? "" : "s"}. Equipamentos e instalações não são somados.</span>
    </p>
  );
}

function Inventario({ data, avancado }: { data: FacetData; avancado: boolean }) {
  const [filtro, setFiltro] = useState("todos");
  const inv = data.inventario ?? [];
  if (!inv.length) return null;
  const cont = (c: string) => inv.filter((x) => x.classe === c).length;
  const shown = inv.filter((x) => filtro === "todos" || x.classe === filtro);
  return (
    <section className={s.inv} aria-labelledby="inv-title" data-testid="inventario-atributos">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div>
          <h3 className="headline" id="inv-title" style={{ fontSize: "1rem" }}>Inventário de atributos</h3>
          <p className="caption" style={{ marginTop: 2 }}>Todos os campos deste tipo de ativo no Manual BDGD e o que é possível fazer com cada um hoje.</p>
        </div>
        <Segmented size="sm" label="Situação do atributo" value={filtro} onChange={setFiltro} options={[{ value: "todos", label: `Todos ${inv.length}` },
          ...Object.entries(CLASSE).filter(([k]) => cont(k)).map(([k, v]) => ({ value: k, label: `${v.t} ${cont(k)}` }))]} />
      </div>
      <ul className={s.invList}>
        {shown.map((x) => (
          <li key={x.campo}>
            <span className={s.invName}>{x.descricao || x.campo}{avancado && <span className={s.code}> {x.campo}</span>}</span>
            <Pill tone={CLASSE[x.classe]?.tone ?? "default"} title={x.motivo}>{CLASSE[x.classe]?.t ?? x.classe}</Pill>
          </li>
        ))}
      </ul>
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
  return <EChart build={build} height={Math.max(140, data.length * 26 + 20)} ariaLabel="Distribuição por categoria do atributo" onClickIndex={(i) => onPick(data[i].code)} testId="chart-categorias" />;
}
