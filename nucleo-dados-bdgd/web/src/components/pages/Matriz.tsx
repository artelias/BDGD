"use client";
import { ArrowDown, Building2, Download, Info, Layers3, MapPin, Rows3, Search, Star, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Explain } from "@/components/ui/Explain";
import { DataError, downloadText, EmptyState, LoadingBlock, Tip, useToast } from "@/components/ui/Feedback";
import { MultiPick, type MultiOption } from "@/components/ui/MultiPick";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { CONCEITOS, nomeNegocio } from "@/lib/catalogo";
import { groupColor } from "@/lib/colors";
import { displayName, type Dataset } from "@/lib/dataset";
import { useData } from "@/lib/data-context";
import { fmt, METRIC_UNIT, ND } from "@/lib/format";
import { useStoredValue } from "@/lib/hooks";
import { aplicavel, csvRecorte, filtraDists, metricaDe, MODOS, type Modo } from "@/lib/matriz";
import { useTheme } from "@/lib/theme";
import type { Entidade } from "@/lib/types";
import { useQueryPatch, useQueryState } from "@/lib/url-state";
import s from "./pages.module.css";

const ESSENCIAIS = ["UCBT", "UCMT", "UCAT", "SSDMT", "SSDBT", "SSDAT", "UNTRMT", "EQTRMT", "UGBT", "SUB"];
const lista = (q: string) => (q ? q.split(",").filter(Boolean) : []);

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
  const [entsQ, setEntsQ] = useQueryState("ativos", "");
  const [distsQ, setDistsQ] = useQueryState("dists", "");
  const [ufsQ, setUfsQ] = useQueryState("ufs", "");
  const [sortQ, setSort] = useQueryState("ordem", "");
  const [distQ] = useQueryState("dist");
  const [fav, setFav] = useStoredValue("bdgd.matriz.favoritos", "");
  const [q, setQ] = useState("");
  const [transposed, setTransposed] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const m = (MODOS.some((x) => x.value === mode) ? mode : "principal") as Modo;

  const aplic = useMemo(() => ds.entidades.filter((e) => aplicavel(ds, e, m)), [ds, m]);
  const entSel = lista(entsQ).filter((id) => ds.entidade(id));
  const ents = useMemo(() => {
    const base = entSel.length ? aplic.filter((e) => entSel.includes(e.id)) : aplic;
    return [...base].sort((a, b) => ds.familias.indexOf(a.familia) - ds.familias.indexOf(b.familia));
  }, [ds, aplic, entsQ]); // eslint-disable-line react-hooks/exhaustive-deps
  const fams = useMemo(() => ds.familias.map((f) => ({ f, n: ents.filter((e) => e.familia === f).length })).filter((x) => x.n), [ds, ents]);
  const distSel = lista(distsQ).map(Number).filter((d) => ds.dist(d));
  const ufSel = lista(ufsQ);

  const rows = useMemo(() => {
    const t = q.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
    let r = filtraDists(ds, { grupo, dists: distSel, ufs: ufSel });
    if (t) r = r.filter((d) => `${d.sigla} ${d.nome} ${d.dist} ${d.ufs.join(" ")}`.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().includes(t));
    const [se, dir] = sortQ.split(":");
    const e = se ? ds.entidade(se) : null;
    if (e) {
      const met = metricaDe(e, m);
      r = [...r].sort((a, b) => {
        const va = ds.cell(a.dist, e.id, met)?.v ?? null, vb = ds.cell(b.dist, e.id, met)?.v ?? null;
        if (va === null && vb === null) return 0; if (va === null) return 1; if (vb === null) return -1; // N/D sempre ao final
        return dir === "asc" ? va - vb : vb - va;
      });
    }
    return r;
  }, [ds, grupo, distsQ, ufsQ, q, sortQ, m]); // eslint-disable-line react-hooks/exhaustive-deps

  const selected = distQ ? Number(distQ) : null;
  useEffect(() => {
    if (selected === null) return;
    const el = wrap.current?.querySelector(`[data-dist="${selected}"]`);
    el?.scrollIntoView({ block: "center" });
  }, [selected]);

  const sortBy = (id: string) => {
    const [se, dir] = sortQ.split(":");
    setSort(se !== id ? `${id}:desc` : dir === "desc" ? `${id}:asc` : "");
  };

  const exportCSV = () => {
    const name = `bdgd_2025-12-31_matriz_${m}${grupo !== "todos" ? `_grupo-${grupo}` : ""}${ufSel.length ? `_uf-${ufSel.join("-")}` : ""}.csv`;
    downloadText(name, csvRecorte(ds, rows, ents, m));
    toast(`${name} exportado · ${rows.length} distribuidoras × ${ents.length} tipos de ativo`);
  };

  const entOpts: MultiOption[] = aplic.map((e) => {
    const presentes = ds.dists.filter((d) => ds.hasEntity(d.dist, e.id)).length;
    return { value: e.id, label: nomeNegocio(e.id, e.nome), group: e.familia, meta: e.id, keywords: `${e.nome} ${e.id}`, hint: `Presente em ${presentes} de ${ds.dists.length} distribuidoras` };
  });
  const presets = [
    { id: "essenciais", label: "Essenciais", values: ESSENCIAIS.filter((id) => aplic.some((e) => e.id === id)) },
    ...CONCEITOS.map((c) => ({ id: c.id, label: c.nome, values: c.entidades.filter((id) => aplic.some((e) => e.id === id)) })).filter((p) => p.values.length),
    ...(fav ? [{ id: "favoritos", label: "★ Meus favoritos", values: lista(fav).filter((id) => aplic.some((e) => e.id === id)) }] : []),
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
  if (entSel.length) chips.push({ k: "e", label: `${ents.length} tipos de ativo`, clear: () => setEntsQ("") });
  if (q) chips.push({ k: "q", label: `Busca: ${q}`, clear: () => setQ("") });

  return (
    <>
      <header className={`${s.head} rise`}>
        <div className="eyebrow">Uma linha por distribuidora · uma coluna por tipo de ativo</div>
        <h1 className="display" style={{ marginTop: 8 }}>Matriz nacional</h1>
        <p className="lede">Todos os tipos de ativo de cada distribuidora, com unidade explícita. Os valores vêm do total reconciliado com o arquivo de 31/12/2025; células vazias são N/D (tipo inexistente ou indicador não homologado), nunca zero.</p>
      </header>

      <div className={s.toolbar} role="toolbar" aria-label="Opções da matriz">
        <Segmented label="Medida" options={MODOS} value={m} onChange={(v) => { setMode(v); setSort(""); }} />
        <MultiPick label="Ativos" options={entOpts} value={entSel} onChange={(v) => setEntsQ(v.join(","))} presets={presets} icon={<Layers3 size={14} aria-hidden />} testId="matriz-ativos" allLabel={`Todos (${aplic.length})`} width={380}
          footer={entSel.length > 0 ? <button type="button" className={s.linkBtn} onClick={() => { setFav(entSel.join(",")); toast("Seleção salva em ★ Meus favoritos"); }}><Star size={12} aria-hidden /> Salvar como favorito</button> : null} />
        <Picker label="Grupo" value={grupo} options={groupOpts} onChange={(v) => setGrupo(v)} width={220} testId="matriz-grupo" compact />
        <MultiPick label="Distribuidoras" options={distOpts} value={distSel.map(String)} onChange={(v) => setDistsQ(v.join(","))} icon={<Building2 size={14} aria-hidden />} testId="matriz-dists" allLabel="Todas" />
        <MultiPick label="UF" options={ufOpts} value={ufSel} onChange={(v) => setUfsQ(v.join(","))} icon={<MapPin size={14} aria-hidden />} testId="matriz-ufs" allLabel="Todas" width={240}
          footer={<span>Distribuidoras com área na UF (aproximado)</span>} />
        <Tip text="Recorte por município exige o cubo município × tipo de ativo, disponível hoje só para tipos com código de município (consumidores, geração, instalações, iluminação, estruturas). Use Explorar ativos.">
          <span className={s.disabledChip} tabIndex={0} aria-disabled="true"><MapPin size={13} aria-hidden /> Município <span className="faint">· em Explorar</span></span>
        </Tip>
        <label className={s.field}><Search size={14} aria-hidden /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar distribuidora" aria-label="Buscar distribuidoras" data-testid="matriz-busca" />{q && <button onClick={() => setQ("")} aria-label="Limpar" style={{ border: 0, background: "transparent", color: "inherit", display: "flex" }}><X size={14} /></button>}</label>
        <span className={s.spacer} />
        <Button variant="ghost" onClick={() => setTransposed((t) => !t)} aria-pressed={transposed} title="Alternar linhas e colunas"><Rows3 size={15} /> {transposed ? "Distribuidoras nas colunas" : "Transpor"}</Button>
        <Button variant="primary" onClick={exportCSV} data-testid="matriz-csv"><Download size={15} /> CSV do recorte</Button>
      </div>

      {chips.length > 0 && (
        <div className={s.chips} aria-label="Filtros ativos" data-testid="matriz-chips">
          {chips.map((c) => <button key={c.k} type="button" className={s.chip} onClick={c.clear} aria-label={`Remover filtro ${c.label}`}>{c.label} <X size={12} aria-hidden /></button>)}
          <button type="button" className={s.linkBtn} onClick={() => { patch({ grupo: null, dists: null, ufs: null, ativos: null }); setQ(""); }}>Limpar tudo</button>
        </div>
      )}

      <p className={s.note}><Info size={14} aria-hidden />
        <span>
          {rows.length} distribuidoras × {ents.length} tipos de ativo · {MODOS.find((x) => x.value === m)!.title}.
          {(m === "extensao_km" || m === "potencia_kva") && <> Aplicável a <b>{aplic.length}</b> de {ds.entidades.length} tipos de ativo.</>}
          {" "}Instalações (UN) e equipamentos (EQ) do mesmo ativo não são somados. Ponto âmbar = alerta de qualidade documentado.{" "}
          <Explain title="Como a matriz é calculada" tecnico="valor(d, e) = total-base reconciliado do GDB 2025 (contagem ou SUM exato); total do recorte = Σ_d valor(d, e) somente para d com valor homologado."
            ressalva="O filtro por UF seleciona distribuidoras cuja área toca a UF; os valores continuam sendo da distribuidora inteira.">
            Cada célula é o total do tipo de ativo na distribuidora, conferido contra o arquivo original da ANEEL. A linha &quot;Total do recorte&quot; soma só as distribuidoras com valor.
          </Explain>
        </span>
      </p>

      {rows.length === 0 || ents.length === 0 ? <EmptyState title="Nada no recorte">Ajuste os filtros de ativos, grupo, distribuidora ou UF.</EmptyState> : transposed ? (
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
                  const met = metricaDe(e, m); const [se, dir] = sortQ.split(":"); const on = se === e.id;
                  return (
                    <th key={e.id} scope="col" aria-sort={on ? (dir === "asc" ? "ascending" : "descending") : "none"}>
                      <button className={s.colHead} onClick={() => sortBy(e.id)} title={`${e.nome} — ${e.regra}`}>
                        <span className={s.colCode}>{on && <ArrowDown size={11} className={s.sortIcon} style={{ transform: dir === "asc" ? "rotate(180deg)" : undefined }} />}{e.id}</span>
                        <span className={s.colName}>{nomeNegocio(e.id, e.nome)}</span>
                        <span className={s.colUnit}>{METRIC_UNIT[met] || "itens"}</span>
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              <tr className={s.totalRow}>
                <td className={s.sticky}><div className={s.distCell}><span><div className={s.distName}>Total do recorte</div><div className={s.distMeta}>soma entre distribuidoras com valor</div></span></div></td>
                {ents.map((e) => {
                  const a = ds.aggregate(rows.map((d) => d.dist), e.id, metricaDe(e, m));
                  return <td key={e.id} className={`${s.cell} ${a.v === null ? s.cellNd : ""}`} title={`${a.n} de ${a.total} distribuidoras com valor${a.nd ? `; ${a.nd} sem valor homologado` : ""}${a.ausentes ? `; ${a.ausentes} sem esse tipo de ativo` : ""}`}>{fmt(a.v, metricaDe(e, m))}{a.nd > 0 && <span className="faint" style={{ fontSize: 10, marginLeft: 4 }}>*</span>}</td>;
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
                    const c = ds.cell(d.dist, e.id, metricaDe(e, m));
                    const nd = !c || c.v === null;
                    return (
                      <td key={e.id} className={`${s.cell} ${nd ? s.cellNd : ""} ${c && c.status === "l" ? s.cellAlert : ""}`}
                        title={!c ? "Tipo de ativo inexistente no arquivo desta distribuidora" : c.v === null ? `N/D — ${c.motivo || "indicador não homologado"}` : c.status === "l" ? `Alerta: ${c.motivo}` : undefined}>
                        {nd ? ND : fmt(c!.v, metricaDe(e, m))}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="caption" style={{ marginTop: 10 }}>* total parcial: ao menos uma distribuidora do recorte não tem valor homologado e fica fora da soma. Detalhes por indicador em <Link href="/metodologia/#dicionario" style={{ color: "var(--accent)", textDecoration: "underline", textUnderlineOffset: 3 }}>Dicionário de indicadores</Link>.</p>
    </>
  );
}

function Transposed({ ds, ents, rows, m, theme }: { ds: Dataset; ents: Entidade[]; rows: Dataset["dists"]; m: Modo; theme: "light" | "dark" }) {
  return (
    <div className={s.tableWrap} data-testid="matriz-transposta">
      <table className={s.table}>
        <thead>
          <tr>
            <th className={`${s.corner} ${s.sticky}`} style={{ top: 0 }}>Tipo de ativo</th>
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
              <td className={s.sticky}><div className={s.distCell}><span><div className={s.distName}>{nomeNegocio(e.id, e.nome)}</div><div className={s.distMeta}><span className="mono">{e.id}</span> · {METRIC_UNIT[metricaDe(e, m)] || "itens"} · {e.familia}</div></span></div></td>
              {rows.map((d) => { const c = ds.cell(d.dist, e.id, metricaDe(e, m)); const nd = !c || c.v === null; return <td key={d.dist} className={`${s.cell} ${nd ? s.cellNd : ""} ${c?.status === "l" ? s.cellAlert : ""}`}>{nd ? ND : fmt(c!.v, metricaDe(e, m))}</td>; })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
