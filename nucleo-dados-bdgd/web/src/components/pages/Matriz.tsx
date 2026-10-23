"use client";
import { ArrowDown, Download, Info, Rows3, Search, SlidersHorizontal, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { DataError, downloadText, EmptyState, LoadingBlock, useToast } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { groupColor } from "@/lib/colors";
import { displayName, type Dataset } from "@/lib/dataset";
import { useData } from "@/lib/data-context";
import { fmt, METRIC_LABEL, METRIC_UNIT, ND, toCSV } from "@/lib/format";
import { useTheme } from "@/lib/theme";
import type { Entidade, Metric } from "@/lib/types";
import { useQueryPatch, useQueryState } from "@/lib/url-state";
import s from "./pages.module.css";

type Mode = "principal" | "quantidade" | "quantidade_registros" | "quantidade_cod_id_distinto";
const MODES: Array<{ value: Mode; label: string; title: string }> = [
  { value: "principal", label: "Métrica principal", title: "km para rede, kVA para transformação/regulação e quantidade para as demais" },
  { value: "quantidade", label: "Quantidade", title: "Quantidade homologada (COD_ID distintos validados para consumidores)" },
  { value: "quantidade_registros", label: "Registros", title: "Linhas da camada no GDB" },
  { value: "quantidade_cod_id_distinto", label: "COD_ID distintos", title: "COUNT(DISTINCT COD_ID) na entidade" },
];
const metricFor = (e: Entidade, m: Mode): Metric => (m === "principal" ? e.metrica : m);

export function Matriz() {
  const data = useData();
  if (data.status === "loading") return <LoadingBlock lines={6} />;
  if (data.status === "error") return <DataError error={data.error} />;
  return <MatrizReady ds={data.ds} />;
}

function MatrizReady({ ds }: { ds: Dataset }) {
  const { resolved } = useTheme();
  const toast = useToast();
  const patch = useQueryPatch();
  const [mode, setMode] = useQueryState("metrica", "principal");
  const [grupo, setGrupo] = useQueryState("grupo", "todos");
  const [famQ, setFamQ] = useQueryState("familias", "");
  const [sortQ, setSort] = useQueryState("ordem", "");
  const [distQ] = useQueryState("dist");
  const [q, setQ] = useState("");
  const [famOpen, setFamOpen] = useState(false);
  const [transposed, setTransposed] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const famRef = useRef<HTMLDivElement>(null);
  const m = (MODES.some((x) => x.value === mode) ? mode : "principal") as Mode;

  const famSel = useMemo(() => new Set(famQ ? famQ.split(",") : ds.familias), [famQ, ds]);
  const ents = useMemo(() => ds.entidades.filter((e) => famSel.has(e.familia)).sort((a, b) => ds.familias.indexOf(a.familia) - ds.familias.indexOf(b.familia)), [ds, famSel]);
  const fams = useMemo(() => ds.familias.filter((f) => famSel.has(f)).map((f) => ({ f, n: ents.filter((e) => e.familia === f).length })).filter((x) => x.n), [ds, famSel, ents]);

  const rows = useMemo(() => {
    const t = q.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
    let r = ds.dists.filter((d) => grupo === "todos" || (grupo === "nao_confirmado" ? d.grupo_status !== "verificado" : d.grupo === grupo && d.grupo_status === "verificado"));
    if (t) r = r.filter((d) => `${d.sigla} ${d.nome} ${d.dist} ${d.ufs.join(" ")}`.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().includes(t));
    const [se, dir] = sortQ.split(":");
    const e = se ? ds.entidade(se) : null;
    if (e) {
      const met = metricFor(e, m);
      r = [...r].sort((a, b) => {
        const va = ds.cell(a.dist, e.id, met)?.v ?? null, vb = ds.cell(b.dist, e.id, met)?.v ?? null;
        if (va === null && vb === null) return 0; if (va === null) return 1; if (vb === null) return -1; // N/D sempre ao final
        return dir === "asc" ? va - vb : vb - va;
      });
    }
    return r;
  }, [ds, grupo, q, sortQ, m]);

  const selected = distQ ? Number(distQ) : null;
  useEffect(() => {
    if (selected === null) return;
    const el = wrap.current?.querySelector(`[data-dist="${selected}"]`);
    el?.scrollIntoView({ block: "center" });
  }, [selected]);
  useEffect(() => {
    if (!famOpen) return;
    const close = (e: MouseEvent) => { if (!famRef.current?.contains(e.target as Node)) setFamOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setFamOpen(false); };
    document.addEventListener("mousedown", close); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", esc); };
  }, [famOpen]);

  const sortBy = (id: string) => {
    const [se, dir] = sortQ.split(":");
    setSort(se !== id ? `${id}:desc` : dir === "desc" ? `${id}:asc` : "");
  };
  const toggleFam = (f: string) => {
    const n = new Set(famSel); if (n.has(f)) n.delete(f); else n.add(f);
    setFamQ(n.size === ds.familias.length ? "" : [...n].join(","));
  };

  const exportCSV = () => {
    const header = ["dist", "sigla", "grupo_economico", "data_base", ...ents.map((e) => `${e.id}__${metricFor(e, m)}`)];
    const body = rows.map((d) => [d.dist, d.sigla, d.grupo, "2025-12-31", ...ents.map((e) => ds.cell(d.dist, e.id, metricFor(e, m))?.v ?? null)]);
    const name = `bdgd_2025-12-31_matriz_${m}${grupo !== "todos" ? `_grupo-${grupo}` : ""}.csv`;
    downloadText(name, toCSV(header, body));
    toast(`${name} exportado · ${rows.length} distribuidoras, vazio = N/D`);
  };

  const groupOpts = [{ value: "todos", label: "Todos os grupos" }, ...ds.grupos.map((g) => ({ value: g.id, label: g.nome, color: groupColor(g.id, resolved), meta: `${ds.groupDists(g.id).length}` })), { value: "nao_confirmado", label: "Não confirmado", meta: `${ds.dists.filter((d) => d.grupo_status !== "verificado").length}` }];

  return (
    <>
      <header className={`${s.head} rise`}>
        <div className="eyebrow">Fato-base · uma linha por distribuidora e entidade</div>
        <h1 className="display" style={{ marginTop: 8 }}>Matriz nacional de ativos</h1>
        <p className="lede">Todas as entidades BDGD de cada distribuidora, com unidade explícita. Valores vêm do total-base reconciliado com o GDB de 31/12/2025; células vazias são N/D (entidade inexistente ou indicador não homologado), nunca zero.</p>
      </header>

      <div className={s.toolbar} role="toolbar" aria-label="Opções da matriz">
        <Segmented label="Métrica" options={MODES} value={m} onChange={(v) => setMode(v)} />
        <Picker label="Grupo" value={grupo} options={groupOpts} onChange={(v) => setGrupo(v)} width={230} testId="matriz-grupo" compact />
        <div className={s.popWrap} ref={famRef}>
          <Button onClick={() => setFamOpen((o) => !o)} aria-expanded={famOpen} aria-haspopup="dialog"><SlidersHorizontal size={15} /> Famílias <span className="faint num">{fams.length}/{ds.familias.length}</span></Button>
          <AnimatePresence>
            {famOpen && (
              <motion.div className={s.pop} role="dialog" aria-label="Famílias de entidades" initial={{ opacity: 0, y: -4, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -2 }} transition={{ duration: 0.16 }}>
                {ds.familias.map((f) => (
                  <label key={f} className={s.check}><input type="checkbox" checked={famSel.has(f)} onChange={() => toggleFam(f)} /> {f} <span>{ds.entidadesDaFamilia(f).length}</span></label>
                ))}
                <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                  <Button size="sm" onClick={() => setFamQ("")}>Todas</Button>
                  <Button size="sm" variant="ghost" onClick={() => setFamQ("Consumidores,Rede,Transformação")}>Essenciais</Button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <label className={s.field}><Search size={14} aria-hidden /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Distribuidora, DIST ou UF" aria-label="Filtrar distribuidoras" data-testid="matriz-busca" />{q && <button onClick={() => setQ("")} aria-label="Limpar" style={{ border: 0, background: "transparent", color: "inherit", display: "flex" }}><X size={14} /></button>}</label>
        <span className={s.spacer} />
        <Button variant="ghost" onClick={() => setTransposed((t) => !t)} aria-pressed={transposed} title="Alternar linhas e colunas"><Rows3 size={15} /> {transposed ? "Distribuidoras nas colunas" : "Transpor"}</Button>
        <Button variant="primary" onClick={exportCSV} data-testid="matriz-csv"><Download size={15} /> CSV</Button>
      </div>

      <p className={s.note}><Info size={14} aria-hidden />{rows.length} distribuidoras × {ents.length} entidades · {METRIC_LABEL[m === "principal" ? "quantidade" : m]}{m === "principal" ? " ou métrica física de cada entidade" : ""}. UNTRMT/EQTRMT e UNTRAT/EQTRAT descrevem a mesma população e não devem ser somadas. Ponto âmbar = alerta de qualidade documentado.</p>

      {rows.length === 0 ? <EmptyState title="Nenhuma distribuidora no filtro">Ajuste a busca ou o grupo selecionado.</EmptyState> : transposed ? (
        <Transposed ds={ds} ents={ents} rows={rows} m={m} theme={resolved} />
      ) : (
        <div className={s.tableWrap} ref={wrap} data-testid="matriz-tabela">
          <table className={s.table}>
            <thead>
              <tr>
                <th className={`${s.corner} ${s.sticky}`} rowSpan={1}>Família</th>
                {fams.map(({ f, n }) => <th key={f} colSpan={n} scope="colgroup">{f}</th>)}
              </tr>
              <tr>
                <th className={`${s.corner} ${s.sticky}`} scope="col" style={{ top: 30 }}>Distribuidora</th>
                {ents.map((e) => {
                  const met = metricFor(e, m); const [se, dir] = sortQ.split(":"); const on = se === e.id;
                  return (
                    <th key={e.id} scope="col" aria-sort={on ? (dir === "asc" ? "ascending" : "descending") : "none"}>
                      <button className={s.colHead} onClick={() => sortBy(e.id)} title={`${e.nome} — ${e.regra}`}>
                        <span className={s.colCode}>{on && <ArrowDown size={11} className={s.sortIcon} style={{ transform: dir === "asc" ? "rotate(180deg)" : undefined }} />}{e.id}</span>
                        <span className={s.colName}>{e.nome}</span>
                        <span className={s.colUnit}>{METRIC_UNIT[met]}</span>
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              <tr className={s.totalRow}>
                <td className={s.sticky}><div className={s.distCell}><span><div className={s.distName}>Total do recorte</div><div className={s.distMeta}>soma entre DISTs · cobertura</div></span></div></td>
                {ents.map((e) => {
                  const a = ds.aggregate(rows.map((d) => d.dist), e.id, metricFor(e, m));
                  return <td key={e.id} className={`${s.cell} ${a.v === null ? s.cellNd : ""}`} title={`${a.n} de ${a.total} distribuidoras com valor${a.nd ? `; ${a.nd} N/D` : ""}${a.ausentes ? `; ${a.ausentes} sem a entidade` : ""}`}>{fmt(a.v, metricFor(e, m))}{a.nd > 0 && <span className="faint" style={{ fontSize: 10, marginLeft: 4 }}>*</span>}</td>;
                })}
              </tr>
              {rows.map((d) => (
                <tr key={d.dist} data-dist={d.dist} data-selected={selected === d.dist} onClick={() => patch({ dist: String(d.dist) })}>
                  <td className={s.sticky}>
                    <div className={s.distCell}>
                      <span className={`${s.sw} ${d.grupo_status !== "verificado" ? s.swHatch : ""}`} style={d.grupo_status === "verificado" ? { background: groupColor(d.grupo, resolved) } : undefined} />
                      <span style={{ minWidth: 0 }}><div className={s.distName}>{displayName(d)}</div><div className={s.distMeta}>DIST {d.dist}{d.ufs.length ? ` · ${d.ufs.join(", ")}` : ""}</div></span>
                    </div>
                  </td>
                  {ents.map((e) => {
                    const c = ds.cell(d.dist, e.id, metricFor(e, m));
                    const nd = !c || c.v === null;
                    return (
                      <td key={e.id} className={`${s.cell} ${nd ? s.cellNd : ""} ${c && c.status === "l" ? s.cellAlert : ""}`}
                        title={!c ? "Entidade inexistente no GDB desta distribuidora" : c.v === null ? `N/D — ${c.motivo || "indicador não homologado"}` : c.status === "l" ? `Alerta: ${c.motivo}` : undefined}>
                        {nd ? ND : fmt(c!.v, metricFor(e, m))}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="caption" style={{ marginTop: 10 }}>* total parcial: ao menos uma distribuidora do recorte tem o indicador N/D e não entra na soma.</p>
    </>
  );
}

function Transposed({ ds, ents, rows, m, theme }: { ds: Dataset; ents: Entidade[]; rows: Dataset["dists"]; m: Mode; theme: "light" | "dark" }) {
  return (
    <div className={s.tableWrap} data-testid="matriz-transposta">
      <table className={s.table}>
        <thead>
          <tr>
            <th className={`${s.corner} ${s.sticky}`} style={{ top: 0 }}>Entidade</th>
            {rows.map((d) => (
              <th key={d.dist} scope="col" style={{ top: 0, height: "auto", padding: "8px 12px", textAlign: "right", textTransform: "none", letterSpacing: 0, fontSize: 12 }}>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}><span className={`${s.sw} ${d.grupo_status !== "verificado" ? s.swHatch : ""}`} style={d.grupo_status === "verificado" ? { background: groupColor(d.grupo, theme) } : undefined} />{displayName(d)}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ents.map((e) => (
            <tr key={e.id}>
              <td className={s.sticky}><div className={s.distCell}><span><div className={s.distName}>{e.nome}</div><div className={s.distMeta}><span className="mono">{e.id}</span> · {METRIC_UNIT[metricFor(e, m)]} · {e.familia}</div></span></div></td>
              {rows.map((d) => { const c = ds.cell(d.dist, e.id, metricFor(e, m)); const nd = !c || c.v === null; return <td key={d.dist} className={`${s.cell} ${nd ? s.cellNd : ""} ${c?.status === "l" ? s.cellAlert : ""}`}>{nd ? ND : fmt(c!.v, metricFor(e, m))}</td>; })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
