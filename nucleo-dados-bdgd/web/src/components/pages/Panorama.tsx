"use client";
import { ArrowLeft, ChevronRight, ExternalLink, GitCompareArrows, Info, Layers3, Maximize2, Search, Table2, TriangleAlert, X } from "lucide-react";
import { AnimatePresence, motion, useAnimationControls, type PanInfo } from "motion/react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { EChart } from "@/components/charts/EChart";
import { AratMap, type AratMapHandle, type HoverInfo } from "@/components/map/AratMap";
import mapStyles from "@/components/map/map.module.css";
import { Button } from "@/components/ui/Button";
import { DataError, LoadingBlock, Tip } from "@/components/ui/Feedback";
import { Pill, StatusDot, Ticker, Value } from "@/components/ui/Value";
import { groupColor } from "@/lib/colors";
import { displayName, type Dataset } from "@/lib/dataset";
import { useData } from "@/lib/data-context";
import { fmt, fmtArea, fmtCompact } from "@/lib/format";
import { ALL_KPIS, KPIS, kpiValue, type KpiDef } from "@/lib/kpis";
import { useMediaQuery } from "@/lib/hooks";
import { useTheme, useReducedMotion } from "@/lib/theme";
import type { Scope } from "@/lib/types";
import { useQueryPatch, useQueryState } from "@/lib/url-state";
import s from "@/app/panorama.module.css";

const ALERT_LABEL: Record<string, string> = {
  potencia_UG_acima_75kW: "Potência de geração acima de 75 kW em registros de BT (preservada, não somada)",
  uc_cod_id_inconsistente: "Consumidores com COD_ID repetido",
  uc_sobreposicao_entre_entidades: "COD_ID presente em mais de uma entidade UC",
  filtro_indisponivel: "Filtro por circuito/subestação indisponível por chaves órfãs",
  divergencia_potencia: "Potência divergente entre unidade e equipamento transformador",
  POT_NOM_provavel_MVA: "Potência de unidade transformadora aparentemente em MVA",
};

function useIsMobile() { return useMediaQuery("(max-width: 900px)"); }

export function Panorama() {
  const data = useData();
  if (data.status === "loading") return <PanoramaSkeleton />;
  if (data.status === "error") return <DataError error={data.error} />;
  return <PanoramaReady ds={data.ds} />;
}

function PanoramaSkeleton() {
  return (
    <div>
      <div style={{ maxWidth: 520, marginBottom: 24 }}><LoadingBlock lines={3} /></div>
      <div className="skeleton" style={{ height: "62vh", borderRadius: 22 }} />
    </div>
  );
}

function PanoramaReady({ ds }: { ds: Dataset }) {
  const { resolved } = useTheme();
  const reduce = useReducedMotion();
  const mobile = useIsMobile();
  const [distQ] = useQueryState("dist");
  const [grupoQ] = useQueryState("grupo");
  const [kpiQ, setKpi] = useQueryState("indicador", "ssdmt");
  const patch = useQueryPatch();
  const mapRef = useRef<AratMapHandle>(null);
  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [q, setQ] = useState("");

  const selected = distQ && ds.dist(Number(distQ)) ? Number(distQ) : null;
  const grupo = grupoQ && ds.grupo(grupoQ) ? grupoQ : null;
  const scope: Scope = selected !== null ? { tipo: "dist", id: selected } : grupo ? { tipo: "grupo", id: grupo } : { tipo: "brasil" };
  const scopeDists = useMemo(() => ds.scopeDists(scope), [ds, scope.tipo, selected, grupo]); // eslint-disable-line react-hooks/exhaustive-deps
  const highlight = useMemo(() => (grupo ? new Set(ds.groupDists(grupo).map((d) => d.dist)) : null), [ds, grupo]);
  const kpi = ALL_KPIS.find((k) => k.key === kpiQ) ?? KPIS[1];
  const rel = ds.raw.release;

  const select = useCallback((d: number | null) => patch({ dist: d === null ? null : String(d) }, true), [patch]);
  const setGrupo = (g: string | null) => patch({ grupo: g, dist: null }, true);

  const padding = mobile ? { left: 0, right: 0, top: 0, bottom: 260 } : { left: 382, right: 0, top: 0, bottom: 0 };

  const listed = useMemo(() => {
    const t = q.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
    return ds.dists.filter((d) => (!grupo || (d.grupo === grupo && d.grupo_status === "verificado")) &&
      (!t || `${d.sigla} ${d.nome} ${d.dist} ${d.ufs.join(" ")}`.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().includes(t)));
  }, [ds, q, grupo]);

  return (
    <>
      <header className={`${s.head} rise`}>
        <div>
          <div className="eyebrow">BDGD · ANEEL · data-base 31/12/2025</div>
          <h1 className="display" style={{ marginTop: 8 }}>Panorama Brasil</h1>
          <p className="lede">
            Agregados de <b className="num">{rel.cobertura.processadas}</b> das <b className="num">{rel.cobertura.com_gdb_2025}</b> distribuidoras com BDGD 2025 publicada pela ANEEL.
            {" "}{rel.cobertura.sem_publicacao_2025.length} distribuidoras históricas não publicaram esta competência e aparecem como ausentes, nunca como zero.
          </p>
        </div>
        <div className={s.chips}>
          <Pill tone={rel.status === "homologado" ? "ok" : "warn"} title={rel.release_id}>{rel.status === "homologado" ? "Release homologado" : "Release parcial · em validação"}</Pill>
          <Pill tone="accent">{ds.grupos.length} grupos verificados</Pill>
          <Pill>{ds.entidades.length} entidades BDGD</Pill>
        </div>
      </header>

      <section className={`${s.stage} rise rise-1`} aria-label="Mapa das áreas de atuação">
        <AratMap ref={mapRef} selected={selected} highlight={highlight} onSelect={select} onHover={setHover} padding={padding} reduceMotion={reduce} />
        <AnimatePresence>
          {hover && !mobile && (() => {
            const d = ds.dist(hover.dist); if (!d) return null; const g = ds.grupo(d.grupo);
            return (
              <motion.div key="tip" className={mapStyles.hoverTip} style={{ left: hover.x, top: hover.y }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.12 }}>
                <b>{displayName(d)}</b> <span>DIST {d.dist}</span><br />
                <span>{g ? g.nome : "Grupo não confirmado"} · {fmtArea(d.area_km2)}</span>
              </motion.div>
            );
          })()}
        </AnimatePresence>
        <Sheet mobile={mobile} reset={selected ?? grupo ?? "brasil"}>
          <AnimatePresence mode="wait" initial={false}>
            {selected !== null ? (
              <Pane key={`d${selected}`}><DistDetail ds={ds} dist={selected} onBack={() => select(null)} theme={resolved} /></Pane>
            ) : (
              <Pane key={`l${grupo ?? ""}`}>
                <div className={s.panelHead}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                    <div>
                      <div className="eyebrow">{grupo ? "Grupo econômico" : "Áreas de atuação"}</div>
                      <div className="headline" style={{ marginTop: 2 }}>{grupo ? ds.grupo(grupo)!.nome : "Distribuidoras"}</div>
                    </div>
                    <Tip text="Enquadrar o Brasil"><Button variant="ghost" icon size="sm" aria-label="Enquadrar o Brasil" onClick={() => mapRef.current?.resetView()}><Maximize2 size={15} /></Button></Tip>
                  </div>
                  {grupo && <GroupNote ds={ds} id={grupo} />}
                  <label className={s.searchBox}>
                    <Search size={14} aria-hidden />
                    <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar por nome, sigla, DIST ou UF" aria-label="Buscar distribuidora" data-testid="panel-search" />
                    {q && <button onClick={() => setQ("")} aria-label="Limpar busca" style={{ border: 0, background: "transparent", color: "inherit", display: "inline-flex" }}><X size={14} /></button>}
                  </label>
                  <div className={s.legend} role="group" aria-label="Grupos econômicos (filtra o mapa)">
                    {ds.grupos.map((g) => (
                      <button key={g.id} className={s.legendItem} aria-pressed={grupo === g.id} data-dim={!!grupo && grupo !== g.id} onClick={() => setGrupo(grupo === g.id ? null : g.id)}>
                        <span className={s.sw} style={{ background: groupColor(g.id, resolved) }} />{g.nome}
                      </button>
                    ))}
                    <Tip text="Sem fonte verificável de controlador para 31/12/2025. Não entram em somas de grupo.">
                      <span className={s.legendItem} style={{ cursor: "help" }} tabIndex={0}><span className={`${s.sw} ${s.swHatch}`} />Não confirmado</span>
                    </Tip>
                  </div>
                </div>
                <div className={s.panelBody}>
                  <div className={s.listHead}><span>{listed.length} distribuidora{listed.length === 1 ? "" : "s"}</span><span>{kpi.label}</span></div>
                  <ul className={s.list} aria-label="Distribuidoras">
                    {listed.map((d) => (
                      <li key={d.dist}>
                        <button className={s.row} data-hover={hover?.dist === d.dist} onClick={() => select(d.dist)} data-testid={`dist-${d.dist}`}>
                          <span className={`${s.sw} ${d.grupo_status !== "verificado" ? s.swHatch : ""}`} style={d.grupo_status === "verificado" ? { background: groupColor(d.grupo, resolved) } : undefined} />
                          <span style={{ minWidth: 0 }}>
                            <div className={s.rowName}>{displayName(d)}</div>
                            <div className={s.rowMeta}>DIST {d.dist}{d.ufs.length ? ` · ${d.ufs.join(", ")}` : ""}</div>
                          </span>
                          <span className={s.rowVal}>{fmtCompact(kpiValue(ds, kpi, [d.dist]).v, kpi.metric)}</span>
                        </button>
                      </li>
                    ))}
                    {listed.length === 0 && <li className="caption" style={{ padding: 16 }}>Nenhuma distribuidora encontrada.</li>}
                  </ul>
                  <p className={s.mapNote}>Áreas sem cor no mapa pertencem a distribuidoras ainda não publicadas neste release ou sem BDGD 2025 — ausência, não zero.</p>
                </div>
              </Pane>
            )}
          </AnimatePresence>
        </Sheet>
      </section>

      <div className={s.kpiHead}>
        <div>
          <h2 className="title" style={{ fontSize: "1.375rem" }}>{ds.scopeLabel(scope)}</h2>
          <div className="caption">{scope.tipo === "brasil" ? `${scopeDists.length} distribuidoras processadas` : scope.tipo === "grupo" ? `${scopeDists.length} distribuidoras do grupo (vínculo verificado)` : `DIST ${selected}`} · indicadores reconciliados com o GDB de origem</div>
        </div>
        {scope.tipo !== "brasil" && <Button size="sm" onClick={() => patch({ dist: null, grupo: null }, true)}><X size={14} /> Voltar ao Brasil</Button>}
      </div>
      <div className={`${s.kpis} rise rise-2`} role="group" aria-label="Indicadores principais">
        {KPIS.map((k) => <KpiCell key={k.key} ds={ds} k={k} dists={scopeDists} active={kpi.key === k.key} onClick={() => setKpi(k.key)} />)}
      </div>

      <div className={s.grid2}>
        <GroupBlock ds={ds} kpi={kpi} theme={resolved} grupo={grupo} onGroup={setGrupo} />
        <RankingBlock ds={ds} kpi={kpi} dists={scope.tipo === "dist" ? ds.scopeDists({ tipo: "brasil" }) : scopeDists} selected={selected} onSelect={select} theme={resolved} />
      </div>

      <Inventory ds={ds} dists={scopeDists} />
      <Coverage ds={ds} />
    </>
  );
}

function Pane({ children }: { children: React.ReactNode }) {
  return (
    <motion.div style={{ display: "flex", flexDirection: "column", minHeight: 0, flex: 1 }} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}>
      {children}
    </motion.div>
  );
}

/** Painel contextual: flutuante no desktop; no celular, folha inferior com três apoios (recolhida, meia, inteira). */
type Detent = "peek" | "half" | "full";
const ORDER: Detent[] = ["peek", "half", "full"];
function Sheet({ mobile, reset, children }: { mobile: boolean; reset: string | number; children: React.ReactNode }) {
  const controls = useAnimationControls();
  const box = useRef<HTMLDivElement>(null);
  const [h, setH] = useState(560);
  const [detent, setDetent] = useState<Detent>(typeof reset === "number" ? "half" : "peek");
  const [lastReset, setLastReset] = useState(reset);
  if (lastReset !== reset) { setLastReset(reset); setDetent(typeof reset === "number" ? "half" : "peek"); }
  useEffect(() => {
    if (!box.current) return;
    const ro = new ResizeObserver(([e]) => setH(e.contentRect.height));
    ro.observe(box.current);
    return () => ro.disconnect();
  }, [mobile]);
  const offset = (d: Detent) => (d === "full" ? 0 : d === "half" ? Math.round(h * 0.42) : Math.max(0, h - 168));
  useEffect(() => {
    if (!mobile) { controls.set({ y: 0 }); return; }
    controls.start({ y: offset(detent), transition: { type: "spring", stiffness: 380, damping: 38 } });
  }, [mobile, detent, h]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!mobile) return <div className={s.panel}>{children}</div>;
  const onEnd = (_: unknown, i: PanInfo) => {
    const k = ORDER.indexOf(detent);
    const up = i.offset.y < -40 || i.velocity.y < -400;
    const down = i.offset.y > 40 || i.velocity.y > 400;
    const next = up ? ORDER[Math.min(2, k + 1)] : down ? ORDER[Math.max(0, k - 1)] : detent;
    if (next === detent) controls.start({ y: offset(detent) }); else setDetent(next);
  };
  return (
    <motion.div ref={box} className={s.panel} drag="y" dragConstraints={{ top: 0, bottom: offset("peek") }} dragElastic={0.08} onDragEnd={onEnd}
      animate={controls} initial={{ y: 400 }} aria-label="Painel de detalhes">
      <button className={s.handle} aria-label={detent === "full" ? "Recolher painel" : "Expandir painel"} onClick={() => setDetent(detent === "full" ? "peek" : "full")} style={{ border: 0, padding: 0 }} />
      {children}
    </motion.div>
  );
}

function GroupNote({ ds, id }: { ds: Dataset; id: string }) {
  const g = ds.grupo(id)!;
  return (
    <p className="caption" style={{ margin: "8px 0 0", lineHeight: 1.5 }}>
      Controlador em 31/12/2025: <span className="muted">{g.controlador}</span>.{" "}
      <a href={g.fontes[0]} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>Fonte <ExternalLink size={11} style={{ display: "inline", verticalAlign: -1 }} /></a>
    </p>
  );
}

const DETAIL: Array<{ label: string; k: string }> = [
  { label: "Unidades consumidoras", k: "uc" }, { label: "Rede MT", k: "ssdmt" }, { label: "Rede BT", k: "ssdbt" },
  { label: "Transformadores MT", k: "untrmt" }, { label: "Potência de transformação", k: "eqtrmt" }, { label: "Geração conectada BT", k: "ugbt" },
  { label: "Subestações", k: "sub" }, { label: "Rede AT", k: "ssdat" },
];

function DistDetail({ ds, dist, onBack, theme }: { ds: Dataset; dist: number; onBack: () => void; theme: "light" | "dark" }) {
  const d = ds.dist(dist)!;
  const g = ds.grupo(d.grupo);
  const alerts = Object.entries(d.alertas);
  const filtros = ds.raw.filtrosIndisponiveis.filter((f) => f.dist === dist);
  return (
    <>
      <div className={s.panelHead}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <button className={s.back} onClick={onBack} data-testid="panel-back"><ArrowLeft size={15} /> Distribuidoras</button>
          <Pill tone={alerts.length ? "warn" : "ok"}>{alerts.length ? `${alerts.reduce((a, [, n]) => a + n, 0)} alertas de QA` : "Sem alertas"}</Pill>
        </div>
        <h2 className={s.dTitle} data-testid="dist-title">{displayName(d)}</h2>
        <div className={s.dMeta}>
          <span className="num">DIST {d.dist}</span>
          {d.ufs.length > 0 && <Tip text="UF aproximada por interseção da ARAT com limites estaduais Natural Earth 1:50m"><span tabIndex={0}>{d.ufs.join(", ")}</span></Tip>}
          <span>{fmtArea(d.area_km2)}</span>
        </div>
        <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {g ? (
            <Pill><span className={s.sw} style={{ background: groupColor(g.id, theme) }} />{g.nome} · verificado</Pill>
          ) : (
            <Pill tone="nd"><span className={`${s.sw} ${s.swHatch}`} />Grupo não confirmado</Pill>
          )}
        </div>
      </div>
      <div className={s.panelBody}>
        <div className={s.metrics} style={{ margin: 0 }}>
          {DETAIL.map(({ label, k }) => {
            const def = ALL_KPIS.find((x) => x.key === k)!; const a = kpiValue(ds, def, [dist]);
            const c = def.ent ? ds.cell(dist, def.ent, def.metric) : null;
            return (
              <div key={k} className={s.metric}>
                <div className={s.metricLabel}>{label}{c && c.status !== "a" && <StatusDot status={c.status} />}</div>
                <div className={s.metricValue}><Value v={a.v} metric={def.metric} /></div>
              </div>
            );
          })}
        </div>
        <div className={s.section}>
          <div className={s.actions}>
            <Link href={`/matriz/?dist=${dist}`} className="focus-ring" style={{ display: "contents" }}><Button style={{ width: "100%" }} tabIndex={-1}><Table2 size={15} /> Matriz</Button></Link>
            <Link href={`/comparar/?a=dist:${dist}${g ? `&b=grupo:${g.id}` : ""}`} style={{ display: "contents" }}><Button style={{ width: "100%" }} tabIndex={-1}><GitCompareArrows size={15} /> Comparar</Button></Link>
            <Link href={`/explorar/?escopo=dist:${dist}`} style={{ display: "contents" }}><Button style={{ width: "100%", gridColumn: "1 / -1" }} tabIndex={-1}><Layers3 size={15} /> Explorar entidades e filtros DDA</Button></Link>
          </div>
        </div>
        {(alerts.length > 0 || filtros.length > 0) && (
          <div className={s.section}>
            <h3 className={s.sectionTitle}>Qualidade dos dados</h3>
            <ul className={s.alertList}>
              {alerts.map(([t, n]) => <li key={t}><TriangleAlert size={12} color="var(--warn)" aria-hidden /><span>{ALERT_LABEL[t] ?? t}{n > 1 ? ` (${n})` : ""}</span></li>)}
            </ul>
            <div className="caption" style={{ marginTop: 8 }}>Alertas não bloqueiam métricas independentes corretas. <Link href="/metodologia/#qualidade" style={{ color: "var(--accent)" }}>Detalhes</Link></div>
          </div>
        )}
        <div className={s.section} style={{ borderBottom: 0 }}>
          <h3 className={s.sectionTitle}>Proveniência</h3>
          <div className={s.prov}>
            Arquivo GDB {d.versao} · <a href={d.fonte} target="_blank" rel="noreferrer">item ANEEL</a><br />
            SHA-256 <span className="mono">{d.sha256.slice(0, 16)}…</span><br />
            BASE.DAT_FNL validada = 31/12/2025
          </div>
        </div>
      </div>
    </>
  );
}

function KpiCell({ ds, k, dists, active, onClick }: { ds: Dataset; k: KpiDef; dists: number[]; active: boolean; onClick: () => void }) {
  const a = kpiValue(ds, k, dists);
  return (
    <button className={s.kpi} aria-pressed={active} onClick={onClick} data-testid={`kpi-${k.key}`}>
      <div className={s.kpiLabel}>{k.label}</div>
      <div className={s.kpiValue}><Ticker v={a.v} metric={k.metric} compact /></div>
      <div className={s.kpiFoot}>
        {k.ent && <span className={s.kpiEnt}>{k.ent}</span>}
        <span>{a.total > 1 ? `${a.n}/${a.total} DIST` : a.n ? "reconciliado" : ""}{a.nd ? ` · ${a.nd} N/D` : ""}</span>
        <Tip text={k.regra + (k.nota ? " " + k.nota : "")}><Info size={12} aria-label="Regra do indicador" tabIndex={0} /></Tip>
      </div>
    </button>
  );
}

function GroupBlock({ ds, kpi, theme, grupo, onGroup }: { ds: Dataset; kpi: KpiDef; theme: "light" | "dark"; grupo: string | null; onGroup: (g: string | null) => void }) {
  const rows = useMemo(() => {
    const r = ds.grupos.map((g) => ({ id: g.id, nome: g.nome, a: kpiValue(ds, kpi, ds.groupDists(g.id).map((d) => d.dist)) }));
    r.sort((x, y) => (y.a.v ?? -1) - (x.a.v ?? -1));
    return r;
  }, [ds, kpi]);
  const sem = useMemo(() => kpiValue(ds, kpi, ds.dists.filter((d) => d.grupo_status !== "verificado").map((d) => d.dist)), [ds, kpi]);
  const build = useCallback((t: import("@/components/charts/EChart").ChartTokens) => ({
    grid: { left: 4, right: 70, top: 6, bottom: 6, containLabel: true },
    tooltip: { trigger: "item", backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
      formatter: (p: { dataIndex: number }) => { const r = rows[p.dataIndex]; return `<b>${r.nome}</b><br/>${fmt(r.a.v, kpi.metric)} ${kpi.metric === "extensao_km" ? "km" : kpi.metric === "potencia_kva" ? "kVA" : ""}<br/><span style="opacity:.7">${r.a.n} distribuidora(s)${r.a.nd ? ` · ${r.a.nd} N/D` : ""}</span>`; } },
    xAxis: { type: "value", show: false },
    yAxis: { type: "category", inverse: true, data: rows.map((r) => r.nome), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 12 } },
    series: [{ type: "bar", barWidth: 12, data: rows.map((r) => ({ value: r.a.v ?? 0, itemStyle: { color: groupColor(r.id, theme), opacity: grupo && grupo !== r.id ? 0.3 : 1, borderRadius: 4 } })),
      label: { show: true, position: "right", color: t.text2, fontFamily: t.font, fontSize: 11, formatter: (p: { dataIndex: number }) => fmtCompact(rows[p.dataIndex].a.v, kpi.metric) } }],
  }), [rows, kpi, theme, grupo]);
  return (
    <section className={s.block} aria-labelledby="g-title">
      <div className={s.blockHead}>
        <div>
          <h2 className={s.blockTitle} id="g-title">{kpi.label} por grupo econômico</h2>
          <div className={s.blockSub}>Somente vínculos DIST→grupo verificados para 31/12/2025 · clique para filtrar o mapa</div>
        </div>
      </div>
      <EChart build={build} height={Math.max(220, rows.length * 30)} ariaLabel={`${kpi.label} por grupo econômico`} onClickIndex={(i) => onGroup(rows[i].id === grupo ? null : rows[i].id)} testId="chart-grupos" />
      <div className="caption" style={{ marginTop: 6, display: "flex", justifyContent: "space-between", gap: 12 }}>
        <span>{ds.dists.filter((d) => d.grupo_status !== "verificado").length} distribuidoras sem grupo verificado (não somadas a grupos)</span>
        <span className="num">{fmtCompact(sem.v, kpi.metric)}</span>
      </div>
    </section>
  );
}

function RankingBlock({ ds, kpi, dists, selected, onSelect, theme }: { ds: Dataset; kpi: KpiDef; dists: number[]; selected: number | null; onSelect: (d: number) => void; theme: "light" | "dark" }) {
  const [all, setAll] = useState(false);
  const rows = useMemo(() => dists.map((d) => ({ d: ds.dist(d)!, v: kpiValue(ds, kpi, [d]).v })).sort((a, b) => (b.v ?? -1) - (a.v ?? -1)), [ds, kpi, dists]);
  const max = rows[0]?.v ?? 1;
  const shown = all ? rows : rows.slice(0, 12);
  return (
    <section className={s.block} aria-labelledby="r-title">
      <div className={s.blockHead}>
        <div>
          <h2 className={s.blockTitle} id="r-title">Distribuidoras por {kpi.label.toLowerCase()}</h2>
          <div className={s.blockSub}>{rows.filter((r) => r.v === null).length ? `${rows.filter((r) => r.v === null).length} com indicador N/D listadas ao final` : "Todas com valor reconciliado"}</div>
        </div>
        <Button size="sm" variant="ghost" onClick={() => setAll((a) => !a)} aria-expanded={all}>{all ? "Mostrar 12" : `Todas (${rows.length})`} <ChevronRight size={14} style={{ transform: all ? "rotate(-90deg)" : "rotate(90deg)", transition: "transform var(--dur-2) var(--ease-out)" }} /></Button>
      </div>
      <ol className={s.bars}>
        {shown.map((r) => (
          <li key={r.d.dist}>
            <button className={s.bar} aria-current={selected === r.d.dist} onClick={() => onSelect(r.d.dist)}>
              <span className={s.barName}>{displayName(r.d)}</span>
              <span className={s.barTrack}><span className={s.barFill} style={{ display: "block", transform: `scaleX(${r.v ? Math.max(0.004, r.v / (max || 1)) : 0})`, background: r.d.grupo_status === "verificado" ? groupColor(r.d.grupo, theme) : "var(--nd)" }} /></span>
              <span className={s.barVal}>{fmtCompact(r.v, kpi.metric)}</span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Inventory({ ds, dists }: { ds: Dataset; dists: number[] }) {
  return (
    <section style={{ marginTop: 40 }} aria-labelledby="inv-title">
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <h2 className="title" id="inv-title" style={{ fontSize: "1.375rem" }}>Inventário de entidades</h2>
        <Link href="/matriz/" className="label" style={{ color: "var(--accent)" }}>Abrir matriz completa →</Link>
      </div>
      <p className="caption" style={{ marginTop: 4 }}>Todas as {ds.entidades.length} entidades com dados no recorte, pela métrica principal de cada uma. Entidades de uma mesma família não são somadas entre si.</p>
      <div className={s.families}>
        {ds.familias.map((f) => (
          <div key={f} className={s.family}>
            <h3 className={s.familyName}><span>{f}</span><span className="caption">{ds.entidadesDaFamilia(f).length}</span></h3>
            {ds.entidadesDaFamilia(f).map((e) => {
              const a = ds.aggregate(dists, e.id, e.metrica);
              return (
                <div key={e.id} className={s.entLine}>
                  <Link href={`/explorar/?ent=${e.id}`} title={e.regra}><span className="mono faint" style={{ marginRight: 8 }}>{e.id}</span>{e.nome}</Link>
                  <span className="num">{fmtCompact(a.v, e.metrica)}{a.nd ? <span className="faint"> · {a.nd} N/D</span> : null}</span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </section>
  );
}

function Coverage({ ds }: { ds: Dataset }) {
  const rel = ds.raw.release;
  const sem = ds.raw.cobertura.filter((c) => c.status === "sem_publicacao_2025");
  const proc = ds.raw.cobertura.filter((c) => c.status === "em_processamento" || c.status === "quarentena");
  return (
    <section style={{ marginTop: 40 }} aria-labelledby="cov-title">
      <h2 className="title" id="cov-title" style={{ fontSize: "1.375rem" }}>Cobertura da competência 2025</h2>
      <div className={s.cov}>
        <div className={s.covCell}><div className={s.covNum}>{rel.cobertura.processadas}</div><div className="label">distribuidoras publicadas neste release</div></div>
        <div className={s.covCell}>
          <div className={s.covNum}>{proc.length}</div><div className="label">com GDB 2025 ainda em processamento ou quarentena</div>
          <div className={s.covChips}>{proc.slice(0, 16).map((c) => <Pill key={c.dist}>{c.sigla.replaceAll("_", " ")}</Pill>)}</div>
        </div>
        <div className={s.covCell}>
          <div className={s.covNum}>{sem.length}</div><div className="label">sem BDGD 2025 publicada (sem substituição por outro ano)</div>
          <div className={s.covChips}>{sem.map((c) => <Pill key={c.dist} tone="nd" title={c.motivo}>{c.sigla.replaceAll("_", " ")} · {c.dist}</Pill>)}</div>
        </div>
      </div>
    </section>
  );
}
