"use client";
import { ObservacoesDados } from "@/components/ui/ObservacoesDados";
import { camposObservacoes, COLUNAS_OBSERVACOES } from "@/lib/observacoes";
import { ArrowDown, Building2, Download, Layers3, MapPin, Rows3, Search, Star, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { FiltroAtivo } from "@/components/matriz/FiltroAtivo";
import mx from "@/components/matriz/matriz.module.css";
import { Button } from "@/components/ui/Button";
import { Explain } from "@/components/ui/Explain";
import { DataError, downloadText, EmptyState, LoadingBlock, useToast } from "@/components/ui/Feedback";
import { MultiPick, type MultiOption } from "@/components/ui/MultiPick";
import { Picker } from "@/components/ui/Picker";
import { ativos as listaAtivos, recorteDe, UNIDADE } from "@/lib/ativos";
import { agregarPorDist, escreverRecorte, juntar, rotulo } from "@/lib/cubo";
import { groupColor } from "@/lib/colors";
import { displayName, type Dataset } from "@/lib/dataset";
import { useConceitos, useData } from "@/lib/data-context";
import { fmt, ND, toCSV } from "@/lib/format";
import { useStoredValue } from "@/lib/hooks";
import { escreverColunas, filtraDists, lerColunas, type ColunaEstado } from "@/lib/matriz";
import { useTheme } from "@/lib/theme";
import type { AtivoCfg, MedidaConceito, Status } from "@/lib/types";
import { useQueryPatch, useQueryState } from "@/lib/url-state";
import s from "./pages.module.css";

const lista = (q: string) => (q ? q.split(",").filter(Boolean) : []);
type CelulaR3 = { v: number | null; st: Status | "x"; motivo: string };
const ST_TXT: Record<string, string> = { a: "aprovado", l: "alerta", b: "bloqueado", e: "em_validacao", n: "nao_aplicavel", x: "ativo_inexistente" };

export function Matriz() {
  const data = useData();
  if (data.status === "loading") return <LoadingBlock lines={6} />;
  if (data.status === "error") return <DataError error={data.error} />;
  if (!data.ds.raw.conceitos) return <EmptyState title="Catálogo de ativos indisponível" tone="warn">O pacote publicado não contém o catálogo de ativos.</EmptyState>;
  return <MatrizReady ds={data.ds} />;
}

function MatrizReady({ ds }: { ds: Dataset }) {
  const { resolved } = useTheme();
  const toast = useToast();
  const patch = useQueryPatch();
  const cat = ds.raw.conceitos!;
  const todos = listaAtivos(ds);
  const [grupo, setGrupo] = useQueryState("grupo", "todos");
  const [ativosQ, setAtivosQ] = useQueryState("ativos", "");
  const [distsQ, setDistsQ] = useQueryState("dists", "");
  const [ufsQ, setUfsQ] = useQueryState("ufs", "");
  const [sortQ, setSort] = useQueryState("ordem", "");
  const [cfQ] = useQueryState("cf");
  const [cmQ] = useQueryState("cm");
  const [distQ] = useQueryState("dist");
  const [fav, setFav] = useStoredValue("bdgd.matriz.ativos.favoritos", "");
  const [q, setQ] = useState("");
  const [transposed, setTransposed] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);

  const sel = lista(ativosQ).filter((id) => todos.some((a) => a.id === id));
  const cols: AtivoCfg[] = useMemo(() => {
    const fams = [...new Set(todos.map((a) => a.familia))];
    const base = sel.length ? todos.filter((a) => sel.includes(a.id)) : todos;
    return [...base].sort((a, b) => fams.indexOf(a.familia) - fams.indexOf(b.familia));
  }, [todos, ativosQ]); // eslint-disable-line react-hooks/exhaustive-deps
  const fams = useMemo(() => [...new Set(cols.map((a) => a.familia))].map((f) => ({ f, n: cols.filter((a) => a.familia === f).length })), [cols]);
  const estado = useMemo(() => lerColunas(cfQ, cmQ), [cfQ, cmQ]);
  const est = (a: AtivoCfg): Required<ColunaEstado> => ({ filtro: estado[a.id]?.filtro ?? {}, medida: estado[a.id]?.medida ?? a.medida });
  const filtradas = cols.filter((a) => Object.values(est(a).filtro).some((v) => v.length) || est(a).medida !== a.medida && !(a.medidas_extra ?? []).includes(est(a).medida));
  const comFiltro = cols.filter((a) => Object.values(est(a).filtro).some((v) => v.length));
  const conceitos = useConceitos(comFiltro.map((a) => a.conceito));

  const distSel = lista(distsQ).map(Number).filter((d) => ds.dist(d));
  const ufSel = lista(ufsQ);
  const totaisIdx = useMemo(() => {
    const m = new Map<string, Map<number, [number | null, Status, string]>>();
    for (const [id, porMed] of Object.entries(ds.raw.ativosTotais ?? {}))
      for (const [med, rows] of Object.entries(porMed ?? {})) m.set(`${id}|${med}`, new Map((rows ?? []).map((r) => [r[0], [r[1], r[2], r[3]]])));
    return m;
  }, [ds]);

  /** valores da coluna por DIST: totais pré-calculados (sem filtro) ou o cubo do conceito (com filtro) — mesmo motor do Explorar */
  const valores = useMemo(() => {
    const out = new Map<string, Map<number, CelulaR3>>();
    for (const a of cols) {
      const { filtro, medida } = est(a);
      const temFiltro = Object.values(filtro).some((v) => v.length);
      const m = new Map<number, CelulaR3>();
      if (!temFiltro) {
        const t = totaisIdx.get(`${a.id}|${medida}`);
        for (const d of ds.dists) { const r = t?.get(d.dist); m.set(d.dist, r ? { v: r[0], st: r[1], motivo: r[2] } : { v: null, st: "x", motivo: "medida indisponível para este ativo" }); }
      } else {
        const cd = conceitos.data[a.conceito];
        const pd = cd ? agregarPorDist(cd, juntar(recorteDe(a), { filtro }), medida) : null;
        for (const d of ds.dists) {
          if (!cd) { m.set(d.dist, { v: null, st: "e", motivo: "carregando" }); continue; }
          if (!pd) { m.set(d.dist, { v: null, st: "b", motivo: "combinação sem cubo calculado" }); continue; }
          const v = pd.get(d.dist);
          m.set(d.dist, v === undefined ? { v: null, st: "x", motivo: "tipo de ativo inexistente no GDB desta distribuidora" } : v === null ? { v: null, st: "b", motivo: "sem valor homologado nesta medida" } : { v, st: "a", motivo: "" });
        }
      }
      out.set(a.id, m);
    }
    return out;
  }, [cols, estado, conceitos.data, totaisIdx, ds]); // eslint-disable-line react-hooks/exhaustive-deps
  const cell = (a: AtivoCfg, d: number) => valores.get(a.id)?.get(d) ?? { v: null, st: "x" as const, motivo: "" };

  const rows = useMemo(() => {
    const t = q.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
    let r = filtraDists(ds, { grupo, dists: distSel, ufs: ufSel });
    if (t) r = r.filter((d) => `${d.sigla} ${d.nome} ${d.dist} ${d.ufs.join(" ")}`.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().includes(t));
    const [sid, dir] = sortQ.split(":");
    const a = cols.find((x) => x.id === sid);
    if (a) r = [...r].sort((x, y) => {
      const vx = cell(a, x.dist).v, vy = cell(a, y.dist).v;
      if (vx === null && vy === null) return 0; if (vx === null) return 1; if (vy === null) return -1;
      return dir === "asc" ? vx - vy : vy - vx;
    });
    return r;
  }, [ds, grupo, distsQ, ufsQ, q, sortQ, valores, cols]); // eslint-disable-line react-hooks/exhaustive-deps

  const totalCol = (a: AtivoCfg) => {
    let v = 0, n = 0, nd = 0;
    for (const d of rows) { const c = cell(a, d.dist); if (c.st === "x" || c.st === "n") continue; if (c.v === null) nd++; else { v += c.v; n++; } }
    return { v: n ? v : null, n, nd };
  };

  const selected = distQ ? Number(distQ) : null;
  useEffect(() => {
    if (selected === null) return;
    wrap.current?.querySelector(`[data-dist="${selected}"]`)?.scrollIntoView({ block: "center" });
  }, [selected]);

  const setColuna = (a: AtivoCfg, filtro: ColunaEstado["filtro"], medida: MedidaConceito) => {
    const next = { ...estado, [a.id]: { filtro, medida: medida === a.medida ? undefined : medida } };
    patch(escreverColunas(next));
  };
  const sortBy = (id: string) => { const [sid, dir] = sortQ.split(":"); setSort(sid !== id ? `${id}:desc` : dir === "desc" ? `${id}:asc` : ""); };
  const unidadeCol = (a: AtivoCfg) => UNIDADE[est(a).medida];
  const fmtCel = (a: AtivoCfg, v: number | null) => (v === null ? ND : fmt(v, est(a).medida));
  const recorteTxt = (a: AtivoCfg) => {
    const { filtro } = est(a);
    const cd = conceitos.data[a.conceito];
    return Object.entries(filtro).filter(([, v]) => v.length).map(([d, v]) => `${cat.dimensoes[d]?.rotulo ?? d}: ${v.length === 1 && cd ? rotulo(cd, d, v[0]) : `${v.length} valores`}`).join(" · ");
  };

  const exportCSV = () => {
    const nome = `bdgd_2025-12-31_matriz_ativos${grupo !== "todos" ? `_grupo-${grupo}` : ""}${ufSel.length ? `_uf-${ufSel.join("-")}` : ""}.csv`;
    const header = ["data_base", "versao", "dist", "sigla", "grupo_economico", "grupo_status", "ativo", "nome_ativo", "medida", "unidade", "recorte", "valor", "status", "motivo", "regra", ...COLUNAS_OBSERVACOES];
    const body: Array<Array<string | number | null>> = [];
    for (const a of cols) for (const d of rows) {
      const c = cell(a, d.dist);
      body.push(["2025-12-31", ds.raw.release.release_id, d.dist, d.sigla, d.grupo, d.grupo_status, a.id, a.nome, est(a).medida, unidadeCol(a), escreverRecorte(est(a).filtro) || "(população do ativo)", c.v, ST_TXT[c.st] ?? c.st, c.motivo, a.tecnico, ...camposObservacoes({ dists: [d.dist], ativos: [a.id], anos: [2025], metricas: [est(a).medida], filtro: est(a).filtro })]);
    }
    downloadText(nome, toCSV(header, body));
    toast(`${nome} exportado · ${rows.length} distribuidoras × ${cols.length} ativos`);
  };

  const entOpts: MultiOption[] = todos.map((a) => ({ value: a.id, label: a.nome, group: a.familia, hint: a.resumo }));
  const presets = [
    { id: "essenciais", label: "Essenciais", values: cat.kpis_padrao.filter((id) => todos.some((a) => a.id === id)) },
    ...[...new Set(todos.map((a) => a.familia))].map((f) => ({ id: f, label: f, values: todos.filter((a) => a.familia === f).map((a) => a.id) })),
    ...(fav ? [{ id: "favoritos", label: "★ Meus favoritos", values: lista(fav).filter((id) => todos.some((a) => a.id === id)) }] : []),
  ];
  const distOpts: MultiOption[] = ds.dists.map((d) => ({ value: String(d.dist), label: displayName(d), meta: `DIST ${d.dist}`, group: d.grupo_status === "verificado" ? ds.grupo(d.grupo)?.nome : "Grupo não confirmado",
    keywords: `${d.nome} ${d.ufs.join(" ")}`, color: d.grupo_status === "verificado" ? groupColor(d.grupo, resolved) : undefined }))
    .sort((a, b) => (a.group ?? "").localeCompare(b.group ?? "") || a.label.localeCompare(b.label));
  const ufs = [...new Set(ds.dists.flatMap((d) => d.ufs))].sort();
  const ufOpts: MultiOption[] = ufs.map((u) => ({ value: u, label: u, meta: `${ds.dists.filter((d) => d.ufs.includes(u)).length} DIST` }));
  const groupOpts = [{ value: "todos", label: "Todos os grupos" }, ...ds.grupos.map((g) => ({ value: g.id, label: g.nome, color: groupColor(g.id, resolved), meta: `${ds.groupDists(g.id).length}` })), { value: "nao_confirmado", label: "Grupo não confirmado", meta: `${ds.dists.filter((d) => d.grupo_status !== "verificado").length}` }];

  const chips: Array<{ k: string; label: string; clear: () => void }> = [];
  if (grupo !== "todos") chips.push({ k: "g", label: `Grupo: ${grupo === "nao_confirmado" ? "não confirmado" : ds.grupo(grupo)?.nome ?? grupo}`, clear: () => setGrupo("todos") });
  for (const d of distSel) chips.push({ k: `d${d}`, label: displayName(ds.dist(d)!), clear: () => setDistsQ(distSel.filter((x) => x !== d).join(",")) });
  for (const u of ufSel) chips.push({ k: `u${u}`, label: `UF: ${u}`, clear: () => setUfsQ(ufSel.filter((x) => x !== u).join(",")) });
  if (sel.length) chips.push({ k: "e", label: `${cols.length} ativos`, clear: () => setAtivosQ("") });
  for (const a of cols) if (recorteTxt(a) || est(a).medida !== a.medida) chips.push({ k: `f${a.id}`, label: `${a.nome}: ${[recorteTxt(a), est(a).medida !== a.medida ? `medida ${unidadeCol(a)}` : ""].filter(Boolean).join(" · ")}`, clear: () => setColuna(a, {}, a.medida) });
  if (q) chips.push({ k: "q", label: `Busca: ${q}`, clear: () => setQ("") });

  const header = (a: AtivoCfg) => {
    const [sid, dir] = sortQ.split(":"); const on = sid === a.id;
    const filtrada = !!recorteTxt(a);
    return (
      <th key={a.id} scope="col" aria-sort={on ? (dir === "asc" ? "ascending" : "descending") : "none"}>
        <div className={mx.colTop}>
          <button className={s.colHead} onClick={() => sortBy(a.id)} title={a.explicacao}>
            <span className={s.colName}>{on && <ArrowDown size={11} className={s.sortIcon} style={{ transform: dir === "asc" ? "rotate(180deg)" : undefined }} />}{a.nome}</span>
            <span className={s.colUnit}>{unidadeCol(a)}{filtrada && <span className={mx.colTag}>filtrado</span>}</span>
          </button>
          <FiltroAtivo ds={ds} ativo={a} filtro={est(a).filtro} medida={est(a).medida} onChange={(f, m) => setColuna(a, f, m)} testId={`filtro-col-${a.id}`} />
        </div>
      </th>
    );
  };

  return (
    <>
      <header className={`${s.head} rise`}>
        <div className="eyebrow">BDGD · data-base 31/12/2025</div>
        <h1 className="display" style={{ marginTop: 8 }}>Matriz Nacional</h1>
        <p className="lede">Explore e compare os ativos das distribuidoras brasileiras.</p>
      </header>

      <div className={s.toolbar} role="toolbar" aria-label="Opções da matriz">
        <MultiPick label="Ativos" options={entOpts} value={sel} onChange={(v) => setAtivosQ(v.join(","))} presets={presets} icon={<Layers3 size={14} aria-hidden />} testId="matriz-ativos" allLabel={`Todos (${todos.length})`} width={380}
          footer={sel.length > 0 ? <button type="button" className={s.linkBtn} onClick={() => { setFav(sel.join(",")); toast("Seleção salva em ★ Meus favoritos"); }}><Star size={12} aria-hidden /> Salvar como favorito</button> : null} />
        <Picker label="Grupo" value={grupo} options={groupOpts} onChange={(v) => setGrupo(v)} width={220} testId="matriz-grupo" compact />
        <MultiPick label="Distribuidoras" options={distOpts} value={distSel.map(String)} onChange={(v) => setDistsQ(v.join(","))} icon={<Building2 size={14} aria-hidden />} testId="matriz-dists" allLabel="Todas" />
        <MultiPick label="UF" options={ufOpts} value={ufSel} onChange={(v) => setUfsQ(v.join(","))} icon={<MapPin size={14} aria-hidden />} testId="matriz-ufs" allLabel="Todas" width={240}
          footer={<span>Distribuidoras com área na UF; valores da distribuidora inteira</span>} />
        <label className={s.field}><Search size={14} aria-hidden /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar distribuidora" aria-label="Buscar distribuidoras" data-testid="matriz-busca" />{q && <button onClick={() => setQ("")} aria-label="Limpar" style={{ border: 0, background: "transparent", color: "inherit", display: "flex" }}><X size={14} /></button>}</label>
        <span className={s.spacer} />
        <Explain title="Como a matriz é calculada" align="end" tecnico="Cada coluna é um ativo do catálogo semântico (conceito + recorte patrimonial) com a sua medida física. Com filtro, o valor sai do cubo exato do conceito; sem filtro, do total pré-calculado do mesmo cubo."
          ressalva="O filtro por UF seleciona distribuidoras cuja área toca a UF; os valores continuam sendo da distribuidora inteira. Para recortes por município, use o filtro de município de cada coluna.">
          Cada célula mostra quanto daquele ativo a distribuidora tem, na sua medida própria (quantidade, km ou kVA). Use o ícone de filtro no topo de cada coluna para recortar por características do próprio ativo.
        </Explain>
        <Button variant="ghost" onClick={() => setTransposed((t) => !t)} aria-pressed={transposed} title="Alternar linhas e colunas"><Rows3 size={15} /> {transposed ? "Distribuidoras nas colunas" : "Transpor"}</Button>
        <Button variant="primary" onClick={exportCSV} disabled={rows.length === 0 || cols.length === 0} data-testid="matriz-csv"><Download size={15} /> CSV</Button>
      </div>

      {chips.length > 0 && (
        <div className={s.chips} aria-label="Filtros ativos" data-testid="matriz-chips">
          {chips.map((c) => <button key={c.k} type="button" className={s.chip} onClick={c.clear} aria-label={`Remover filtro ${c.label}`}>{c.label} <X size={12} aria-hidden /></button>)}
          <button type="button" className={s.linkBtn} onClick={() => { patch({ grupo: null, dists: null, ufs: null, ativos: null, cf: null, cm: null }); setQ(""); }}>Limpar tudo</button>
        </div>
      )}
      {filtradas.length > 0 && conceitos.loading && <p className={s.note} aria-live="polite">Carregando os recortes das colunas filtradas…</p>}

      {rows.length === 0 || cols.length === 0 ? <EmptyState title="Nada no recorte">Revise a busca ou ajuste os ativos, o grupo, as distribuidoras ou a UF.</EmptyState> : transposed ? (
        <div className={s.tableWrap} data-testid="matriz-transposta">
          <table className={s.table}>
            <thead>
              <tr>
                <th className={`${s.corner} ${s.sticky}`} style={{ top: 0 }}>Ativo</th>
                {rows.map((d) => <th key={d.dist} scope="col" style={{ top: 0, height: "auto", padding: "8px 12px", textAlign: "right", textTransform: "none", letterSpacing: 0, fontSize: 12 }}>{displayName(d)}</th>)}
              </tr>
            </thead>
            <tbody>
              {cols.map((a) => (
                <tr key={a.id}>
                  <td className={s.sticky}><div className={s.distCell}><span><div className={s.distName}>{a.nome}</div><div className={s.distMeta}>{unidadeCol(a)} · {a.familia}{recorteTxt(a) ? " · filtrado" : ""}</div></span></div></td>
                  {rows.map((d) => { const c = cell(a, d.dist); return <td key={d.dist} className={`${s.cell} ${c.v === null ? s.cellNd : ""} ${c.st === "l" ? s.cellAlert : ""}`} title={c.motivo || undefined}>{fmtCel(a, c.v)}</td>; })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className={s.tableWrap} ref={wrap} data-testid="matriz-tabela">
          <table className={s.table}>
            <thead>
              <tr>
                <th className={`${s.corner} ${s.sticky}`}>Família</th>
                {fams.map(({ f, n }) => <th key={f} colSpan={n} scope="colgroup">{f}</th>)}
              </tr>
              <tr>
                <th className={`${s.corner} ${s.sticky}`} scope="col" style={{ top: 30 }}>Distribuidora</th>
                {cols.map(header)}
              </tr>
            </thead>
            <tbody>
              <tr className={s.totalRow}>
                <td className={s.sticky}><div className={s.distCell}><span><div className={s.distName}>Total do recorte</div><div className={s.distMeta}>{rows.length} distribuidoras</div></span></div></td>
                {cols.map((a) => { const t = totalCol(a); return <td key={a.id} className={`${s.cell} ${t.v === null ? s.cellNd : ""}`} title={`${t.n} distribuidoras com valor${t.nd ? `; ${t.nd} sem valor homologado` : ""}`} data-testid={`total-${a.id}`}>{fmtCel(a, t.v)}{t.nd > 0 && <span className="faint" style={{ fontSize: 11, marginLeft: 4 }}>parcial*</span>}</td>; })}
              </tr>
              {rows.map((d) => (
                <tr key={d.dist} data-dist={d.dist} data-selected={selected === d.dist} onClick={() => patch({ dist: String(d.dist) })}>
                  <td className={s.sticky}>
                    <div className={s.distCell}>
                      <span className={`${s.sw} ${d.grupo_status !== "verificado" ? s.swHatch : ""}`} style={d.grupo_status === "verificado" ? { background: groupColor(d.grupo, resolved) } : undefined} />
                      <span style={{ minWidth: 0 }}><div className={s.distName}>{displayName(d)}</div><div className={s.distMeta}>DIST {d.dist}{d.ufs.length ? ` · ${d.ufs.join(", ")}` : ""}</div></span>
                    </div>
                  </td>
                  {cols.map((a) => { const c = cell(a, d.dist); return <td key={a.id} className={`${s.cell} ${c.v === null ? s.cellNd : ""} ${c.st === "l" ? s.cellAlert : ""}`} title={c.motivo || undefined}>{fmtCel(a, c.v)}</td>; })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="caption" style={{ marginTop: 10 }}>* soma parcial, sem as distribuidoras que não têm valor homologado nessa medida. N/D indica valor indisponível ou não homologado; não comprova ausência física do ativo. Zero técnico é um resultado da regra de contagem, e não se confunde com dado ausente. Consulte o motivo de cada célula e os estados na Metodologia.</p>
      <ObservacoesDados dists={rows.map((d) => d.dist)} ativos={cols.map((a) => a.id)} anos={[2025]} filtro={cols.length === 1 ? est(cols[0]).filtro : undefined} />
    </>
  );
}
