"use client";
import { ObservacoesDados } from "@/components/ui/ObservacoesDados";
import { ArrowLeft, Check, ChevronDown, ExternalLink, GitCompareArrows, Layers3, Locate, Search, SlidersHorizontal, Table2, X } from "lucide-react";
import { AnimatePresence, motion, useAnimationControls, type PanInfo } from "motion/react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { EChart } from "@/components/charts/EChart";
import { AratMap, type AratMapHandle, type HoverInfo } from "@/components/map/AratMap";
import mapStyles from "@/components/map/map.module.css";
import { Button } from "@/components/ui/Button";
import { Explain } from "@/components/ui/Explain";
import { DataError, LoadingBlock, Tip } from "@/components/ui/Feedback";
import { Pill, StatusDot, Ticker, Value } from "@/components/ui/Value";
import { nomeNegocio } from "@/lib/catalogo";
import { marcosDaDistribuidora } from "@/lib/marcos-distribuidoras";
import { groupColor } from "@/lib/colors";
import { displayName, type Dataset } from "@/lib/dataset";
import { useData } from "@/lib/data-context";
import { fmt, fmtArea, fmtCompact, METRIC_UNIT } from "@/lib/format";
import { coberturaTexto } from "@/lib/kpis";
import { coberturaNacionalIncompleta, PANORAMA_IDS, PANORAMA_KPIS, PANORAMA_PRESETS, panoramaIndicador, panoramaSubtotal, panoramaValue, type PanoramaKpi as KpiDef } from "@/lib/panorama-r3";
import { useMediaQuery, useStoredValue } from "@/lib/hooks";
import { useTheme, useReducedMotion } from "@/lib/theme";
import type { Metric, Scope } from "@/lib/types";
import { useQueryPatch, useQueryState } from "@/lib/url-state";
import s from "@/app/panorama.module.css";

const MAX_KPIS = 10;
const RANK_TOP = 12;

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
  const [kpiIdsRaw, setKpiIds] = useStoredValue("bdgd.panorama.r3.indicadores", PANORAMA_IDS.join(","));
  const patch = useQueryPatch();
  const mapRef = useRef<AratMapHandle>(null);
  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [q, setQ] = useState("");

  const selected = distQ && ds.dist(Number(distQ)) ? Number(distQ) : null;
  const grupo = grupoQ && ds.grupo(grupoQ) ? grupoQ : null;
  const scope: Scope = selected !== null ? { tipo: "dist", id: selected } : grupo ? { tipo: "grupo", id: grupo } : { tipo: "brasil" };
  const scopeDists = useMemo(() => ds.scopeDists(scope), [ds, scope.tipo, selected, grupo]); // eslint-disable-line react-hooks/exhaustive-deps
  const highlight = useMemo(() => (grupo ? new Set(ds.groupDists(grupo).map((d) => d.dist)) : null), [ds, grupo]);
  const kpis = useMemo(() => {
    const ids = kpiIdsRaw.split(",").filter((id) => panoramaIndicador(id));
    return (ids.length ? ids : PANORAMA_IDS).slice(0, MAX_KPIS).map((id) => panoramaIndicador(id)!);
  }, [kpiIdsRaw]);
  const kpi = panoramaIndicador(kpiQ) ?? kpis[0];
  const rel = ds.raw.release;

  // Clicar de novo na mesma distribuidora (ou fora dos polígonos) volta ao enquadramento nacional.
  const select = useCallback((d: number | null) => {
    if (d === null || d === selected) {
      if (selected === null) mapRef.current?.resetView();
      patch({ dist: null }, true);
      return;
    }
    patch({ dist: String(d) }, true);
  }, [patch, selected]);
  const setGrupo = (g: string | null) => patch({ grupo: g, dist: null }, true);
  const verBrasil = () => { patch({ dist: null, grupo: null }, true); mapRef.current?.resetView(); };

  const padding = mobile ? { left: 0, right: 0, top: 0, bottom: 260 } : { left: 382, right: 0, top: 0, bottom: 0 };

  const listed = useMemo(() => {
    const t = q.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
    return ds.dists.filter((d) => (!grupo || (d.grupo === grupo && d.grupo_status === "verificado")) &&
      (!t || `${d.sigla} ${d.nome} ${d.dist} ${d.ufs.join(" ")}`.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().includes(t)));
  }, [ds, q, grupo]);

  const homologado = rel.status === "homologado";

  return (
    <>
      <header className={`${s.head} rise`}>
        <div>
          <div className="eyebrow">BDGD · ANEEL · data-base 31/12/2025</div>
          <h1 className="display" style={{ marginTop: 8 }}>Panorama Brasil</h1>
          <p className="lede">
            Explore os ativos cadastrados pelas <b className="num">{rel.cobertura.processadas}</b> distribuidoras com BDGD publicada em 2025. <Link href="/metodologia/#qualidade">Cobertura e metodologia</Link>.
          </p>
          {!homologado && (
            <p className={s.notice} data-testid="aviso-validacao">
              <StatusDot status="e" /> Pacote em validação: os valores já foram reconciliados com os arquivos de origem, e a homologação final está em andamento.{" "}
              <Link href="/metodologia/#qualidade">Ver qualidade e cobertura</Link>
            </p>
          )}
        </div>
        <div className={s.chips}>
          <Pill tone="accent">{ds.grupos.length} grupos econômicos verificados</Pill>
        </div>
      </header>

      <section className={`${s.stage} rise rise-1`} aria-label="Mapa das áreas de atuação">
        <AratMap ref={mapRef} selected={selected} highlight={highlight} onSelect={select} onHover={setHover} padding={padding} reduceMotion={reduce} />
        <button type="button" className={s.brasilBtn} onClick={verBrasil} data-testid="ver-brasil" aria-label="Ver Brasil: limpar seleção e enquadrar o país">
          <Locate size={15} aria-hidden /> Ver Brasil
        </button>
        <AnimatePresence>
          {hover && !mobile && (() => {
            const d = ds.dist(hover.dist); if (!d) return null; const g = d.grupo_status === "verificado" ? ds.grupo(d.grupo) : null;
            const v = panoramaValue(ds, kpi, [d.dist]).v;
            return (
              <motion.div key="tip" className={mapStyles.hoverTip} style={{ left: hover.x, top: hover.y }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.12 }}>
                <b>{displayName(d)}</b> <span>{d.nome !== d.sigla ? d.nome : `DIST ${d.dist}`}</span><br />
                <span>{g ? g.nome : "Grupo não confirmado"} · {d.ufs.join(", ") || "UF N/D"} · {fmtArea(d.area_km2)}</span><br />
                <span>{kpi.nome}: <b className="num">{fmtCompact(v, kpi.metric)}</b></span><br />
                <span style={{ opacity: 0.8 }}>{selected === d.dist ? "Clique para voltar ao Brasil" : "Clique para ver detalhes"}</span>
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
                  <div>
                    <div className="eyebrow">{grupo ? "Grupo econômico" : "Áreas de atuação"}</div>
                    <div className="headline" style={{ marginTop: 2 }}>{grupo ? ds.grupo(grupo)!.nome : "Distribuidoras"}</div>
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
                  <div className={s.listHead}><span>{listed.length} distribuidora{listed.length === 1 ? "" : "s"}</span><span>{kpi.nome}</span></div>
                  <ul className={s.list} aria-label="Distribuidoras">
                    {listed.map((d) => (
                      <li key={d.dist}>
                        <button className={s.row} data-hover={hover?.dist === d.dist} onClick={() => select(d.dist)} data-testid={`dist-${d.dist}`}>
                          <span className={`${s.sw} ${d.grupo_status !== "verificado" ? s.swHatch : ""}`} style={d.grupo_status === "verificado" ? { background: groupColor(d.grupo, resolved) } : undefined} />
                          <span style={{ minWidth: 0 }}>
                            <div className={s.rowName}>{displayName(d)}</div>
                            <div className={s.rowMeta}>DIST {d.dist}{d.ufs.length ? ` · ${d.ufs.join(", ")}` : ""}</div>
                          </span>
                          <span className={s.rowVal}>{fmtCompact(panoramaValue(ds, kpi, [d.dist]).v, kpi.metric)}</span>
                        </button>
                      </li>
                    ))}
                    {listed.length === 0 && <li className="caption" style={{ padding: 16 }}>Nenhuma distribuidora encontrada.</li>}
                  </ul>
                  <p className={s.mapNote}>Áreas sem cor no mapa pertencem a distribuidoras sem BDGD 2025 publicada: ausência, não zero. Clique fora das áreas para voltar ao Brasil.</p>
                </div>
              </Pane>
            )}
          </AnimatePresence>
        </Sheet>
      </section>

      {coberturaNacionalIncompleta(ds, scopeDists) && <p className="caption" role="note">Indicadores de {scopeDists.length} distribuidoras com BDGD publicada em 2025. Cobertura nacional parcial; valores não representam o total de todas as concessionárias.</p>}
      <div className={s.kpiHead}>
        <div>
          <h2 className="title" style={{ fontSize: "1.375rem" }}>{ds.scopeLabel(scope)}</h2>
          <div className="caption">{scope.tipo === "brasil" ? `${scopeDists.length} distribuidoras processadas` : scope.tipo === "grupo" ? `${scopeDists.length} distribuidoras do grupo (vínculo verificado)` : `DIST ${selected}`} · valores reconciliados com os arquivos de origem</div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <KpiPicker ids={kpis.map((k) => k.id)} onChange={(ids) => setKpiIds(ids.join(","))} />
          {scope.tipo !== "brasil" && <Button size="sm" onClick={verBrasil}><X size={14} /> Voltar ao Brasil</Button>}
        </div>
      </div>
      <div className={`${s.kpis} rise rise-2`} role="group" aria-label="Indicadores principais" data-count={kpis.length}>
        {kpis.map((k) => <KpiCell key={k.id} ds={ds} k={k} dists={scopeDists} active={kpi.id === k.id} onClick={() => setKpi(k.id)} />)}
      </div>

      <div className={s.grid2}>
        <GroupBlock ds={ds} kpi={kpi} theme={resolved} grupo={grupo} onGroup={setGrupo} />
        <RankingBlock ds={ds} kpi={kpi} dists={scope.tipo === "dist" ? ds.scopeDists({ tipo: "brasil" }) : scopeDists} selected={selected} onSelect={select} theme={resolved} />
      </div>

      <Inventory ds={ds} dists={scopeDists} />
      <ObservacoesDados dists={scopeDists} anos={[2025]} />
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

const DETAIL = PANORAMA_IDS;

function DistDetail({ ds, dist, onBack, theme }: { ds: Dataset; dist: number; onBack: () => void; theme: "light" | "dark" }) {
  const d = ds.dist(dist)!;
  const g = d.grupo_status === "verificado" ? ds.grupo(d.grupo) : null;
  const marcos = marcosDaDistribuidora(dist);
  return (
    <>
      <div className={s.panelHead}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <button className={s.back} onClick={onBack} data-testid="panel-back"><ArrowLeft size={15} /> Brasil</button>
          
        </div>
        <h2 className={s.dTitle} data-testid="dist-title">{displayName(d)}</h2>
        {d.nome && d.nome !== d.sigla && <div className="caption" style={{ marginBottom: 4 }}>{d.nome}</div>}
        <div className={s.dMeta}>
          <span className="num">DIST {d.dist}</span>
          {d.ufs.length > 0 && <Tip text="UF aproximada por interseção da área de atuação com limites estaduais Natural Earth 1:50m"><span tabIndex={0}>{d.ufs.join(", ")}</span></Tip>}
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
          {DETAIL.map((id) => {
            const def = panoramaIndicador(id)!; const a = panoramaValue(ds, def, [dist]);
            return (
              <div key={id} className={s.metric}>
                <div className={s.metricLabel}>{def.nome}</div>
                <div className={s.metricValue}><Value v={a.v} metric={def.metric} /></div>
                {a.v === null && <div className={s.metricNd}>Dado indisponível; consulte a metodologia.</div>}
              </div>
            );
          })}
        </div>
        <div className={s.section}>
          <div className={s.actions}>
            <Link href={`/matriz/?dist=${dist}`} className="focus-ring" style={{ display: "contents" }}><Button style={{ width: "100%" }} tabIndex={-1}><Table2 size={15} /> Matriz</Button></Link>
            <Link href={`/comparar/?a=dist:${dist}${g ? `&b=grupo:${g.id}` : ""}`} style={{ display: "contents" }}><Button style={{ width: "100%" }} tabIndex={-1}><GitCompareArrows size={15} /> Comparar</Button></Link>
            <Link href={`/explorar/?escopo=dist:${dist}`} style={{ display: "contents" }}><Button style={{ width: "100%", gridColumn: "1 / -1" }} tabIndex={-1}><Layers3 size={15} /> Explorar ativos</Button></Link>
          </div>
        </div>
        {marcos.length > 0 && (
          <div className={s.section} data-testid="marcos-distribuidora">
            <h3 className={s.sectionTitle}>Destaques da distribuidora</h3>
            <p className="caption" style={{ marginBottom: 12 }}>Marcos com fonte identificada; o ano do resultado pode ser diferente do ano da divulgação.</p>
            {marcos.map((m) => (
              <article key={m.titulo} style={{ marginBottom: 14 }}>
                <strong>{m.titulo}</strong>
                <p className="caption" style={{ marginTop: 4 }}>{m.descricao}</p>
                <a href={m.fonte} target="_blank" rel="noopener noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 4, minHeight: 24 }}>
                  {m.fonteNome} <ExternalLink size={12} aria-hidden />
                </a>
                <div className="caption">Referência {m.anoReferencia} · divulgado em {m.dataDivulgacao.split("-").reverse().join("/")}</div>
              </article>
            ))}
          </div>
        )}
        <div className={s.section} style={{ borderBottom: 0 }}>
          <h3 className={s.sectionTitle}>Proveniência</h3>
          <div className={s.prov}>
            Arquivo GDB {d.versao} · <a href={d.fonte} target="_blank" rel="noreferrer">item ANEEL</a><br />
            SHA-256 <span className="mono">{d.sha256.slice(0, 16)}…</span><br />
            Data-base conferida no arquivo: 31/12/2025
          </div>
        </div>
      </div>
    </>
  );
}

function KpiCell({ ds, k, dists, active, onClick }: { ds: Dataset; k: KpiDef; dists: number[]; active: boolean; onClick: () => void }) {
  const a = panoramaValue(ds, k, dists);
  const subtotal = a.partial ? panoramaSubtotal(ds, k, dists) : a;
  const valorExibido = a.v ?? (a.partial && subtotal.n > 0 ? subtotal.v : null);
  return (
    <div className={s.kpi} data-active={active}>
      <button className={s.kpiHit} aria-pressed={active} onClick={onClick} data-testid={`kpi-${k.id}`} aria-label={`${k.nome}: usar nos gráficos abaixo`} />
      <div className={s.kpiLabel}>{k.nome}</div>
      <div className={s.kpiBox}><div className={s.kpiValue}><Ticker v={valorExibido} metric={k.metric} compact /></div></div>
      <div className={s.kpiFoot}>
        <span className={s.kpiSum}>{k.resumo}</span>
        <span className={s.kpiActions}>
          <Explain title={k.nome} tecnico={k.tecnico} ressalva={k.ressalva} cobertura={coberturaTexto(subtotal)} testId={`explain-${k.id}`}>{k.explicacao}</Explain>
        </span>
      </div>
    </div>
  );
}

/** "Ver mais indicadores": escolha livre (até 8) ou por conjunto pronto. Fica salva neste navegador. */
function KpiPicker({ ids, onChange }: { ids: string[]; onChange: (ids: string[]) => void }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", away); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", esc); };
  }, [open]);
  const toggle = (id: string) => {
    if (ids.includes(id)) { if (ids.length > 1) onChange(ids.filter((x) => x !== id)); }
    else if (ids.length < MAX_KPIS) onChange([...ids, id]);
  };
  return (
    <div ref={box} style={{ position: "relative" }}>
      <Button size="sm" onClick={() => setOpen((o) => !o)} aria-expanded={open} data-testid="kpi-picker"><SlidersHorizontal size={14} /> Ver mais indicadores <ChevronDown size={14} /></Button>
      <AnimatePresence>
        {open && (
          <motion.div className={s.picker} role="dialog" aria-label="Escolher indicadores" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -2 }} transition={{ duration: 0.16 }}>
            <div className={s.pickerHead}>Conjuntos prontos</div>
            <div className={s.pickerPresets}>
              {PANORAMA_PRESETS.map((p) => {
                const on = p.ids.join(",") === ids.join(",");
                return <button key={p.id} className={s.presetBtn} aria-pressed={on} onClick={() => onChange(p.ids)}>{p.nome}</button>;
              })}
            </div>
            <div className={s.pickerHead}>Indicadores <span className="faint">({ids.length} de até {MAX_KPIS})</span></div>
            <ul className={s.pickerList}>
              {PANORAMA_KPIS.map((i) => {
                const on = ids.includes(i.id);
                return (
                  <li key={i.id}>
                    <button className={s.pickerItem} aria-pressed={on} onClick={() => toggle(i.id)} disabled={!on && ids.length >= MAX_KPIS}>
                      <span className={s.check} aria-hidden>{on && <Check size={12} />}</span>
                      <span><b>{i.nome}</b><span className={s.pickerSum}>{i.resumo}</span></span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function unitOf(m: Metric) { return METRIC_UNIT[m] ? ` ${METRIC_UNIT[m]}` : ""; }

function GroupBlock({ ds, kpi, theme, grupo, onGroup }: { ds: Dataset; kpi: KpiDef; theme: "light" | "dark"; grupo: string | null; onGroup: (g: string | null) => void }) {
  const rows = useMemo(() => {
    const r = ds.grupos.map((g) => ({ id: g.id, nome: g.nome, a: panoramaValue(ds, kpi, ds.groupDists(g.id).map((d) => d.dist)) }));
    r.sort((x, y) => (y.a.v ?? -1) - (x.a.v ?? -1));
    return r;
  }, [ds, kpi]);
  const sem = useMemo(() => panoramaValue(ds, kpi, ds.dists.filter((d) => d.grupo_status !== "verificado").map((d) => d.dist)), [ds, kpi]);
  const build = useCallback((t: import("@/components/charts/EChart").ChartTokens) => ({
    grid: { left: 4, right: 70, top: 6, bottom: 6, containLabel: true },
    tooltip: { trigger: "item", backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
      formatter: (p: { dataIndex: number }) => { const r = rows[p.dataIndex]; return `<b>${r.nome}</b><br/>${fmt(r.a.v, kpi.metric)}${unitOf(kpi.metric)}<br/><span style="opacity:.7">${r.a.n} distribuidora(s) com valor${r.a.nd ? ` · ${r.a.nd} sem valor homologado` : ""}</span>`; } },
    xAxis: { type: "value", show: false },
    yAxis: { type: "category", inverse: true, data: rows.map((r) => r.nome), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 12 } },
    series: [{ type: "bar", barWidth: 12, data: rows.map((r) => ({ value: r.a.v, itemStyle: { color: groupColor(r.id, theme), opacity: grupo && grupo !== r.id ? 0.3 : 1, borderRadius: 4 } })),
      label: { show: true, position: "right", color: t.text2, fontFamily: t.font, fontSize: 11, formatter: (p: { dataIndex: number }) => fmtCompact(rows[p.dataIndex].a.v, kpi.metric) } }],
  }), [rows, kpi, theme, grupo]);
  return (
    <section className={s.block} aria-labelledby="g-title">
      <div className={s.blockHead}>
        <div>
          <h2 className={s.blockTitle} id="g-title">{kpi.nome} por grupo econômico</h2>
          <div className={s.blockSub}>Somente vínculos distribuidora→grupo verificados para 31/12/2025 · clique para filtrar o mapa</div>
        </div>
      </div>
      <EChart build={build} height={Math.max(220, rows.length * 30)} ariaLabel={`${kpi.nome} por grupo econômico`} onClickIndex={(i) => onGroup(rows[i].id === grupo ? null : rows[i].id)} testId="chart-grupos" />
      <div className="caption" style={{ marginTop: 6, display: "flex", justifyContent: "space-between", gap: 12 }}>
        <span>{ds.dists.filter((d) => d.grupo_status !== "verificado").length} distribuidoras sem grupo verificado (não somadas a grupos)</span>
        <span className="num">{fmtCompact(sem.v, kpi.metric)}</span>
      </div>
    </section>
  );
}

function RankingBlock({ ds, kpi, dists, selected, onSelect, theme }: { ds: Dataset; kpi: KpiDef; dists: number[]; selected: number | null; onSelect: (d: number) => void; theme: "light" | "dark" }) {
  const [all, setAll] = useState(false);
  const sec = useRef<HTMLElement>(null);
  const list = useRef<HTMLOListElement>(null);
  const rows = useMemo(() => dists.map((d) => ({ d: ds.dist(d)!, v: panoramaValue(ds, kpi, [d]).v })).sort((a, b) => (b.v ?? -1) - (a.v ?? -1)), [ds, kpi, dists]);
  const max = rows[0]?.v ?? 1;
  const shown = all ? rows : rows.slice(0, RANK_TOP);
  const nd = rows.filter((r) => r.v === null).length;
  const toggle = () => {
    const next = !all;
    setAll(next);
    // Ao recolher, volta o bloco para a tela; ao expandir, a lista rola dentro do próprio bloco.
    requestAnimationFrame(() => {
      if (next) list.current?.scrollTo({ top: 0 });
      else sec.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    });
  };
  return (
    <section ref={sec} className={s.block} aria-labelledby="r-title">
      <div className={s.blockHead}>
        <div>
          <h2 className={s.blockTitle} id="r-title">Distribuidoras por {kpi.nome.toLowerCase()}</h2>
          <div className={s.blockSub} aria-live="polite" data-testid="ranking-status">
            Mostrando {shown.length} de {rows.length}{nd ? ` · ${nd} sem valor homologado ao final` : ""}
          </div>
        </div>
        {rows.length > RANK_TOP && (
          <Button size="sm" variant="ghost" onClick={toggle} aria-expanded={all} aria-controls="ranking-list" data-testid="ranking-toggle">
            {all ? `Mostrar ${RANK_TOP} maiores` : `Ver todas (${rows.length})`} <ChevronDown size={14} style={{ transform: all ? "rotate(180deg)" : undefined, transition: "transform var(--dur-2) var(--ease-out)" }} />
          </Button>
        )}
      </div>
      <ol ref={list} id="ranking-list" className={`${s.bars} ${all ? s.barsAll : ""}`} data-testid="ranking-list">
        {shown.map((r, i) => (
          <li key={r.d.dist}>
            <button className={s.bar} aria-current={selected === r.d.dist} onClick={() => onSelect(r.d.dist)}>
              <span className={s.barName}><span className={s.barRank}>{i + 1}</span>{displayName(r.d)}</span>
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
        <h2 className="title" id="inv-title" style={{ fontSize: "1.375rem" }}>Inventário de ativos</h2>
        <Link href="/matriz/" className="label" style={{ color: "var(--accent)" }}>Abrir matriz nacional →</Link>
      </div>
      <p className="caption" style={{ marginTop: 4 }}>Cada tipo de ativo pela sua medida principal. Tipos da mesma família não são somados entre si, porque descrevem partes diferentes do mesmo sistema.</p>
      <div className={s.families}>
        {ds.familias.map((f) => (
          <div key={f} className={s.family}>
            <h3 className={s.familyName}><span>{f}</span><span className="caption">{ds.entidadesDaFamilia(f).length}</span></h3>
            {ds.entidadesDaFamilia(f).map((e) => <InvLine key={e.id} ds={ds} dists={dists} ent={e.id} nome={e.nome} metric={e.metrica} regra={e.regra} />)}
          </div>
        ))}
      </div>
    </section>
  );
}

function InvLine({ ds, dists, ent, nome, metric, regra }: { ds: Dataset; dists: number[]; ent: string; nome: string; metric: Metric; regra: string }) {
  const a = ds.aggregate(dists, ent, metric);
  const incompleto = a.partial || a.ausentes > 0 || coberturaNacionalIncompleta(ds, dists);
  const escopo = dists.length < ds.dists.length ? `&escopo=dists&dists=${dists.join(",")}` : "";
  return (
    <div className={s.entLine}>
      <Link href={`/explorar/?ent=${ent}&tec=${ent}${escopo}`} title={regra}>{nomeNegocio(ent, nome)}<span className="mono faint" style={{ marginLeft: 6, fontSize: "0.6875rem" }}>{ent}</span></Link>
      <span className="num" style={{ textAlign: "right" }}>{fmtCompact(incompleto ? null : a.v, metric)}</span>
      {incompleto && <span className={s.entNd}><Link href="/metodologia/#qualidade">Valor não disponível para todo o recorte · ver cobertura</Link></span>}
      {!incompleto && a.v === 0 && <span className={s.entNd}>Zero no agregado processado; verificação independente pendente.</span>}
    </div>
  );
}
