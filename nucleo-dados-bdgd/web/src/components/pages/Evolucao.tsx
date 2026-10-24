"use client";
import { Download, Flag, History, Info } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { EscopoSeletor } from "@/components/explorar/EscopoSeletor";
import { Button } from "@/components/ui/Button";
import { Explain } from "@/components/ui/Explain";
import { DataError, downloadText, EmptyState, LoadingBlock, useToast } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { ativos as listaAtivos, UNIDADE } from "@/lib/ativos";
import type { Dataset } from "@/lib/dataset";
import { useData } from "@/lib/data-context";
import { distsDoEscopo, escreverEscopo, lerEscopo, rotuloEscopo, type Escopo } from "@/lib/escopo";
import { anoAno, anoCompleto, ESTADO, indexar, indice100, painelBalanceado, serieDist, serieSoma, STATUS_ANO, variacao, type Serie, type SerieData } from "@/lib/evolucao";
import { fmt, fmtCompact, toCSV } from "@/lib/format";
import { useQueryPatch, useQueryState } from "@/lib/url-state";
import p from "./pages.module.css";
import s from "./evolucao.module.css";

const MAX_LINHAS = 8;
const pct = (x: number | null) => (x === null ? "N/D" : `${x >= 0 ? "+" : ""}${(x * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`);

function useSerie() {
  const [st, set] = useState<{ data?: SerieData; error?: string }>({});
  useEffect(() => {
    let alive = true;
    fetch("/data/historico/serie.json", { cache: "force-cache" }).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: SerieData) => alive && set({ data: d })).catch((e: Error) => alive && set({ error: e.message }));
    return () => { alive = false; };
  }, []);
  return st;
}

export function Evolucao() {
  const data = useData();
  const serie = useSerie();
  if (data.status === "loading" || (!serie.data && !serie.error)) return <LoadingBlock lines={6} label="Carregando séries" />;
  if (data.status === "error") return <DataError error={data.error} />;
  if (serie.error || !serie.data) return <DataError error={serie.error ?? "série indisponível"} />;
  return <EvolucaoReady ds={data.ds} sd={serie.data} />;
}

function EvolucaoReady({ ds, sd }: { ds: Dataset; sd: SerieData }) {
  const toast = useToast();
  const patch = useQueryPatch();
  const ativos = listaAtivos(ds);
  const [ativoQ, setAtivo] = useQueryState("ativo", "consumidores");
  const [escopoQ] = useQueryState("escopo", "brasil");
  const [distsQ] = useQueryState("dists");
  const [visao, setVisao] = useQueryState("visao", "original");
  const [escala, setEscala] = useQueryState("escala", "valores");
  const [layout, setLayout] = useQueryState("layout", "linhas");
  const a = ativos.find((x) => x.id === ativoQ) ?? ativos[0];
  const escopo = useMemo(() => lerEscopo(ds, escopoQ, distsQ), [ds, escopoQ, distsQ]);
  const anos = sd.anos;
  const idx = indexar((visao === "perimetro" ? sd.perimetro : sd.original)[a.id]);
  const nomeD = (d: number) => ds.dist(d)?.sigla.replaceAll("_", " ") ?? sd.nomes[String(d)] ?? `DIST ${d}`;
  const setEscopo = (e: Escopo) => { const w = escreverEscopo(e); patch({ escopo: w.escopo, dists: w.dists }); };

  // séries do escopo: Brasil (anos homologados) + painel balanceado; grupo (composição de referência 2025) + DIST; DIST selecionadas
  const series: Serie[] = useMemo(() => {
    const todas = [...idx.keys()];
    if (escopo.modo === "brasil") {
      const br = serieSoma(idx, todas, anos, "brasil", "Brasil");
      br.pontos = br.pontos.map((pt) => (anoCompleto(sd.cobertura.find((c) => c.ano === pt.ano)?.status_ano) ? pt : { ...pt, v: null, estado: "p" }));
      const painel = painelBalanceado(idx, todas, anos);
      return [{ ...br, nota: "somente anos com todas as publicações validadas" },
        { ...serieSoma(idx, painel, anos, "painel", `Painel balanceado (${painel.length} distribuidoras)`), nota: "distribuidoras com os quatro anos validados para este ativo" }];
    }
    const dists = distsDoEscopo(ds, escopo);
    const out: Serie[] = [];
    if (escopo.modo === "grupo") out.push({ ...serieSoma(idx, dists, anos, "grupo", `${rotuloEscopo(ds, escopo)} (composição de 2025)`), nota: "soma só nos anos com todas as distribuidoras validadas" });
    const top = [...dists].sort((x, y) => (idx.get(y)?.get(2025)?.[2] ?? 0) - (idx.get(x)?.get(2025)?.[2] ?? 0)).slice(0, MAX_LINHAS);
    for (const d of top) out.push(serieDist(idx, d, anos, nomeD(d)));
    return out;
  }, [idx, escopo, anos, ds, sd]); // eslint-disable-line react-hooks/exhaustive-deps
  const exibidas = escala === "indice" ? series.map(indice100) : series;
  const principal = series[0];
  const varP = principal ? variacao(principal) : null;
  const yoy = principal ? anoAno(principal) : [];
  const unidade = escala === "indice" ? "índice (base 100)" : UNIDADE[a.medida];
  const distsEscopo = escopo.modo === "brasil" ? [...idx.keys()] : distsDoEscopo(ds, escopo);
  const algumHistorico = series.some((x) => x.pontos.some((pt) => pt.ano < 2025 && pt.v !== null));

  const buildLinhas = (t: ChartTokens) => ({
    grid: { left: 8, right: 20, top: 30, bottom: 24, containLabel: true },
    legend: { top: 0, left: 0, type: "scroll", textStyle: { color: t.text2, fontFamily: t.font, fontSize: 11 } },
    tooltip: { trigger: "axis", backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
      valueFormatter: (v: number | null) => (v === null || v === undefined ? "N/D" : escala === "indice" ? v.toLocaleString("pt-BR", { maximumFractionDigits: 1 }) : `${fmt(v, a.medida)} ${UNIDADE[a.medida]}`) },
    xAxis: { type: "category", data: anos.map(String), axisLine: { lineStyle: { color: t.hairline } }, axisLabel: { color: t.text2, fontFamily: t.font } },
    yAxis: { type: "value", scale: true, axisLabel: { color: t.text3, fontFamily: t.font, fontSize: 10, formatter: (v: number) => (escala === "indice" ? String(v) : fmtCompact(v, a.medida)) }, splitLine: { lineStyle: { color: t.hairline } } },
    series: exibidas.map((x, i) => ({ name: x.nome, type: "line", connectNulls: false, symbolSize: 7, data: x.pontos.map((pt) => pt.v),
      lineStyle: { width: i === 0 ? 2.5 : 1.6 }, emphasis: { focus: "series" },
      markPoint: undefined })),
  });
  const heatRows = useMemo(() => {
    const ds2 = [...distsEscopo].map((d) => ({ d, s: serieDist(idx, d, anos, nomeD(d)) })).filter((x) => x.s.pontos.some((pt) => pt.v !== null));
    ds2.sort((x, y) => (variacao(y.s).cagr ?? -9) - (variacao(x.s).cagr ?? -9));
    return ds2.slice(0, 40);
  }, [distsEscopo, idx, anos]); // eslint-disable-line react-hooks/exhaustive-deps
  const buildHeat = (t: ChartTokens) => {
    const cols = anos.slice(1).map(String);
    const data: Array<[number, number, number | null]> = [];
    heatRows.forEach((r, y) => anoAno(r.s).forEach((c, x) => data.push([x, y, c.pct === null ? null : Math.round(c.pct * 1000) / 10])));
    return {
      grid: { left: 8, right: 60, top: 8, bottom: 30, containLabel: true },
      tooltip: { backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
        formatter: (q: { value: [number, number, number | null] }) => `<b>${heatRows[q.value[1]].s.nome}</b><br/>${cols[q.value[0]]}: ${q.value[2] === null ? "N/D" : `${q.value[2]}% ao ano`}` },
      xAxis: { type: "category", data: cols.map((c) => `${Number(c) - 1}→${c}`), axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 11 } },
      yAxis: { type: "category", data: heatRows.map((r) => r.s.nome), inverse: true, axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 11 } },
      visualMap: { min: -10, max: 10, calculable: false, orient: "vertical", right: 0, top: "middle", itemHeight: 120, textStyle: { color: t.text3, fontSize: 10 }, inRange: { color: [t.sideB, t.surface, t.sideA] } },
      series: [{ type: "heatmap", data: data.filter((d) => d[2] !== null), label: { show: true, color: t.text, fontSize: 10, formatter: (q: { value: [number, number, number] }) => `${q.value[2]}%` } }],
    };
  };

  const exportCSV = () => {
    const nome = `bdgd_2022-2025_evolucao_${a.id}_${visao}.csv`;
    const rows: Array<Array<string | number | null>> = [];
    for (const x of series) for (const pt of x.pontos) rows.push([x.nome, a.id, a.medida, UNIDADE[a.medida], pt.ano, pt.v, ESTADO[pt.estado] ?? pt.estado, pt.quebra ? "quebra" : "comparavel", visao === "perimetro" ? "perimetro_2025" : "publicacao_original", sd.versao_regra]);
    downloadText(nome, toCSV(["serie", "ativo", "medida", "unidade", "ano", "valor", "estado", "comparabilidade", "visao", "versao_regra"], rows));
    toast(`${nome} exportado`);
  };

  return (
    <>
      <header className={`${p.head} rise`}>
        <div className="eyebrow">2022 · 2023 · 2024 · 2025</div>
        <h1 className="display" style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 14 }}><History size={34} strokeWidth={1.6} color="var(--accent)" aria-hidden /> Evolução histórica</h1>
        <p className="lede">Como os ativos mudaram de 2022 a 2025, com a mesma regra de cálculo em todos os anos. Só aparecem valores observados e validados: anos ausentes não são preenchidos nem projetados.</p>
      </header>

      <div className={s.anos} role="list" aria-label="Situação de cada ano" data-testid="anos">
        {sd.cobertura.map((c) => (
          <div key={c.ano} role="listitem" className={s.ano} data-status={c.status_ano}>
            <div className={s.anoNum}>31/12/{c.ano}</div>
            <div className={s.anoSt}>{STATUS_ANO[c.status_ano] ?? "em validação"}</div>
            <div className={s.anoFoot}>{c.validadas} de {c.publicadas} publicações validadas{c.pendentes ? ` · ${c.pendentes} pendente${c.pendentes > 1 ? "s" : ""}` : ""}</div>
            <div className={s.bar}><span style={{ transform: `scaleX(${c.publicadas ? c.validadas / c.publicadas : 0})` }} /></div>
          </div>
        ))}
      </div>

      <EscopoSeletor ds={ds} value={escopo} onChange={setEscopo} testId="evo-escopo" />
      <div className={p.toolbar} role="toolbar" aria-label="Opções da evolução" style={{ marginTop: 12 }}>
        <Picker label="Ativo" value={a.id} width={280} testId="evo-ativo" options={ativos.map((x) => ({ value: x.id, label: x.nome, group: x.familia, meta: UNIDADE[x.medida] }))} onChange={setAtivo} />
        <Segmented label="Visão" size="sm" value={visao} onChange={setVisao} options={[{ value: "original", label: "Publicação original" }, { value: "perimetro", label: "Perímetro de 2025" }]} />
        <Segmented label="Escala" size="sm" value={escala} onChange={setEscala} options={[{ value: "valores", label: "Valores" }, { value: "indice", label: "Índice 100" }]} />
        <Segmented label="Visualização" size="sm" value={layout} onChange={setLayout} options={[{ value: "linhas", label: "Linhas" }, { value: "calor", label: "Mapa de calor" }]} />
        <span className={p.spacer} />
        <Explain title="Como a evolução é calculada" align="end" tecnico={`Regra ${sd.versao_regra}: o mesmo catálogo de ativos e o mesmo ETL de 2025 aplicados aos arquivos de cada competência. CAGR = (último/primeiro)^(1/anos) − 1, só com base > 0 e sem quebra.`}
          ressalva="Quebra de classificação: a parcela sem tipo patrimonial (TUC) mudou mais de 10 p.p. entre anos; o salto reflete recadastro, não crescimento físico. Grupos usam a composição de 2025.">
          Cada ponto é o total do ativo publicado pela distribuidora naquele ano. “Perímetro de 2025” soma predecessoras incorporadas (por exemplo, Energisa Borborema na Energisa Paraíba) somente quando os conjuntos das duas não se sobrepõem.
        </Explain>
        <Button size="sm" onClick={exportCSV} data-testid="evo-csv"><Download size={14} /> CSV</Button>
      </div>

      {principal && (
        <div className={s.cards} data-testid="evo-cards">
          <div className={s.card}><div className={s.cardL}>{principal.nome}</div><div className={s.cardV}>{principal.pontos[3]?.v === null ? "N/D" : `${fmt(principal.pontos[3]?.v, a.medida)}`}<span className={s.cardU}> {UNIDADE[a.medida]} em 2025</span></div></div>
          <div className={s.card}><div className={s.cardL}>Variação acumulada</div><div className={s.cardV} data-testid="evo-var">{pct(varP?.pct ?? null)}</div><div className={s.cardF}>{varP?.motivo ?? (varP?.abs !== null && varP ? `${varP.abs >= 0 ? "+" : ""}${fmt(varP.abs, a.medida)} ${UNIDADE[a.medida]}` : "")}</div></div>
          <div className={s.card}><div className={s.cardL}>Crescimento médio anual (CAGR)</div><div className={s.cardV} data-testid="evo-cagr">{pct(varP?.cagr ?? null)}</div><div className={s.cardF}>{varP?.motivo ?? "entre o primeiro e o último ano com valor"}</div></div>
          <div className={s.card}><div className={s.cardL}>Ano a ano</div><div className={s.yoy}>{yoy.map((y) => <span key={y.ano}><b>{y.ano}</b> {pct(y.pct)}</span>)}</div></div>
        </div>
      )}

      <section className={s.stage} aria-label="Série temporal">
        {!algumHistorico && (
          <p className={s.note} data-testid="historico-preparacao"><Info size={14} aria-hidden /><span><b>Histórico em validação para este recorte.</b> As competências 2022–2024 ainda não têm valor validado para {escopo.modo === "brasil" ? "o Brasil completo" : "as distribuidoras escolhidas"}. Escolha “Distribuidoras” para ver as que já estão validadas, ou acompanhe o andamento acima.</span></p>
        )}
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={layout} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.18 }}>
            {layout === "calor"
              ? (heatRows.length ? <EChart build={buildHeat} height={Math.max(200, heatRows.length * 24 + 50)} ariaLabel="Variação anual por distribuidora; os valores estão na tabela" testId="chart-calor" /> : <EmptyState title="Sem variações calculáveis">Nenhuma distribuidora do escopo tem dois anos consecutivos validados.</EmptyState>)
              : <EChart build={buildLinhas} height={340} ariaLabel={`Evolução de ${a.nome} de 2022 a 2025; os valores estão na tabela`} testId="chart-linhas" />}
          </motion.div>
        </AnimatePresence>
        <div className={s.scroll} tabIndex={0} role="region" aria-label="Tabela da série">
        <table className={s.table} data-testid="evo-tabela">
          <caption className="sr-only">Valores anuais de {a.nome} ({unidade})</caption>
          <thead><tr><th scope="col">Série</th>{anos.map((y) => <th key={y} scope="col">{y}</th>)}<th scope="col">Variação</th><th scope="col">CAGR</th></tr></thead>
          <tbody>
            {series.map((x) => { const v = variacao(x); return (
              <tr key={x.id}>
                <th scope="row">{x.nome}{x.nota && <div className="caption">{x.nota}</div>}</th>
                {x.pontos.map((pt) => (
                  <td key={pt.ano} title={pt.v === null ? (sd.notas[`${x.id}|${pt.ano}|${a.id}`] || ESTADO[pt.estado] || "") : pt.quebra ? "quebra de classificação neste ano" : undefined}>
                    {pt.v === null ? <span className="faint">N/D</span> : fmt(pt.v, a.medida)}{pt.quebra && <Flag size={11} className={s.flag} aria-label="quebra de comparabilidade" />}
                  </td>
                ))}
                <td>{pct(v.pct)}</td><td>{pct(v.cagr)}</td>
              </tr>
            ); })}
          </tbody>
        </table>
        </div>
        <p className={s.note}><Info size={13} aria-hidden /><span>N/D: ano sem valor validado (passe o mouse para ver o motivo). A bandeira marca quebra de comparabilidade: a variação nesse ano não é tratada como crescimento. Unidade: {UNIDADE[a.medida]}.</span></p>
      </section>

      {visao === "perimetro" && (
        <section className={s.stage} aria-labelledby="suc-t" data-testid="sucessoes">
          <h2 className="headline" id="suc-t" style={{ fontSize: "1rem" }}>Sucessões consideradas no perímetro de 2025</h2>
          <ul className={s.suc}>
            {sd.eventos.map((e) => {
              const pts = sd.ponte.filter((x) => x.evento_id === e.evento_id);
              return (
                <li key={e.evento_id}>
                  <b>{nomeD(e.dist_origem)} → {nomeD(e.dist_destino_2025)}</b> · incorporação efetivada em {e.data_efetivacao.split("-").reverse().join("/")}
                  <div className="caption">{pts.length ? pts.map((x) => `${x.ano_base}: ${x.status_qualidade === "validado" ? "somada (conjuntos sem sobreposição)" : x.status_qualidade === "ja_incluida" ? "já contida na sucessora (não somada, para não duplicar)" : "não somada (sem prova de disjunção ou absorção)"}`).join(" · ") : "predecessora ainda em processamento: não somada"}</div>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </>
  );
}
