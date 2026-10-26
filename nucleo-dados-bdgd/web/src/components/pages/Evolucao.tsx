"use client";
import { AlertTriangle, Download, ExternalLink, Flag, History, Info, ShieldCheck } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { EscopoSeletor } from "@/components/explorar/EscopoSeletor";
import { PublicacoesAuditadas } from "@/components/pages/PublicacoesAuditadas";
import { Button } from "@/components/ui/Button";
import { Explain } from "@/components/ui/Explain";
import { DataError, downloadText, EmptyState, LoadingBlock, useToast } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { ativos as listaAtivos, UNIDADE } from "@/lib/ativos";
import type { Dataset } from "@/lib/dataset";
import { useData } from "@/lib/data-context";
import { distsDoEscopo, escreverEscopo, lerEscopo, rotuloEscopo, type Escopo } from "@/lib/escopo";
import { anoAno, ESTADO, indice100, serieDist, serieSoma, STATUS_ANO, variacao, type Serie, type SerieData } from "@/lib/evolucao";
import {
  aplicarMatriz, coberturaAtivo, DESCRICAO_PUB, indexarHom, indiceHom, NATUREZA, naturezaVariacoes, pontosHom, ROTULO_PUB,
  serieBrasil, seriePainel, sinaisNoEscopo, urlItem, type EstadoPub, type Homologacao, type PontoHom,
} from "@/lib/homologacao";
import { fmt, fmtCompact, toCSV } from "@/lib/format";
import { aplicarEstadosContrato, pontosContrato, type EstadosContrato } from "@/lib/historico-contrato";
import { useQueryPatch, useQueryState } from "@/lib/url-state";
import p from "./pages.module.css";
import s from "./evolucao.module.css";

const MAX_LINHAS = 8;
const pct = (x: number | null) => (x === null ? "N/D" : `${x >= 0 ? "+" : ""}${(x * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`);
const ESTADOS: EstadoPub[] = ["H", "T", "R", "P", "B", "N"];

function useJson<T>(url: string) {
  const [st, set] = useState<{ data?: T; error?: string }>({});
  useEffect(() => {
    let alive = true;
    fetch(url, { cache: "force-cache" }).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: T) => alive && set({ data: d })).catch((e: Error) => alive && set({ error: e.message }));
    return () => { alive = false; };
  }, [url]);
  return st;
}

export function Evolucao() {
  const data = useData();
  const serie = useJson<SerieData>("/data/historico/serie.json");
  const hom = useJson<Homologacao>("/data/historico/homologacao.json");
  const estados = useJson<EstadosContrato>("/data/historico/estados-contrato.json");
  if (data.status === "loading" || (!serie.data && !serie.error) || (!hom.data && !hom.error) || (!estados.data && !estados.error)) return <LoadingBlock lines={6} label="Carregando séries" />;
  if (data.status === "error") return <DataError error={data.error} />;
  if (serie.error || !serie.data) return <DataError error={serie.error ?? "série indisponível"} />;
  if (hom.error || !hom.data) return <DataError error={hom.error ?? "matriz de homologação indisponível"} />;
  if (estados.error || !estados.data) return <DataError error={estados.error ?? "estados do contrato indisponíveis"} />;
  return <EvolucaoReady ds={data.ds} sd={serie.data} h={hom.data} estados={estados.data} />;
}

function Selo({ e, curto }: { e: EstadoPub; curto?: boolean }) {
  return <span className={s.selo} data-e={e} title={DESCRICAO_PUB[e]}>{curto ? ROTULO_PUB[e].split(" (")[0] : ROTULO_PUB[e]}</span>;
}

function Celula({ pt, medida }: { pt: PontoHom; medida: Parameters<typeof fmt>[1] }) {
  const motivo = pt.motivo || ESTADO[pt.estado] || "";
  if (pt.estado === "nao_aplicavel") return <span className="faint" title={motivo}>Não aplicável</span>;
  if (pt.v === null) return <><span className="faint">N/D</span>{pt.estado === "nao_homologado" ? <span className={s.mini}>Não homologado</span> : pt.pub && pt.pub !== "N" && <span className={s.mini} data-e={pt.pub}>{ROTULO_PUB[pt.pub].split(" ")[0]}</span>}<span className="sr-only">: {motivo}</span></>;
  return (
    <>
      {fmt(pt.v, medida)}
      {pt.estado === "zero_verificado" && <span className={s.mini}>Zero técnico*</span>}
      {pt.pub === "R" && <AlertTriangle size={11} className={s.warn} aria-label={`ressalva: ${motivo}`} />}
      {pt.quebra && <Flag size={11} className={s.flag} aria-label="quebra de comparabilidade" />}
    </>
  );
}

function EvolucaoReady({ ds, sd, h, estados }: { ds: Dataset; sd: SerieData; h: Homologacao; estados: EstadosContrato }) {
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
  const familias = [...new Set(ativos.map((x) => x.familia))];
  const escopo = useMemo(() => lerEscopo(ds, escopoQ, distsQ), [ds, escopoQ, distsQ]);
  const anos = sd.anos;
  const ih = indiceHom(h, a.id);
  const idx = indexarHom(aplicarEstadosContrato(aplicarMatriz((visao === "perimetro" ? sd.perimetro : sd.original)[a.id], ih), estados, a.id));
  const nomeD = (d: number) => ds.dist(d)?.sigla.replaceAll("_", " ") ?? sd.nomes[String(d)] ?? `DIST ${d}`;
  const setEscopo = (e: Escopo) => { const w = escreverEscopo(e); patch({ escopo: w.escopo, dists: w.dists }); };

  // Brasil e painel vêm da matriz de homologação (agregados elegíveis); grupo e DIST somam/mostram só células publicáveis
  const series: Serie[] = useMemo(() => {
    if (escopo.modo === "brasil") {
      const out: Serie[] = [serieBrasil(h, a.id, anos, estados)];
      const painel = seriePainel(h, a.id, anos);
      if (painel) out.push(painel);
      return out;
    }
    const dists = distsDoEscopo(ds, escopo);
    const out: Serie[] = [];
    if (escopo.modo === "grupo") out.push({ ...serieSoma(idx, dists, anos, "grupo", `${rotuloEscopo(ds, escopo)} (composição de 2025)`), nota: "soma só nos anos com todas as distribuidoras publicáveis" });
    const top = [...dists].sort((x, y) => (idx.get(y)?.get(2025)?.[2] ?? 0) - (idx.get(x)?.get(2025)?.[2] ?? 0)).slice(0, MAX_LINHAS);
    for (const d of top) out.push(pontosContrato(pontosHom(serieDist(idx, d, anos, nomeD(d)), h, ih, d), estados, a.id, d));
    return out;
  }, [idx, escopo, anos, ds, h, estados, a.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const exibidas = escala === "indice" ? series.map(indice100) : series;
  const principal = series[0];
  const varP = principal ? variacao(principal) : null;
  const yoy = principal ? anoAno(principal) : [];
  const unidade = escala === "indice" ? "índice (base 100)" : UNIDADE[a.medida];
  const distsEscopo = escopo.modo === "brasil" ? [...idx.keys()] : distsDoEscopo(ds, escopo);
  const distsSeries = series.filter((x) => /^\d+$/.test(x.id)).map((x) => Number(x.id));
  const algumHistorico = series.some((x) => x.pontos.some((pt) => pt.ano < 2025 && pt.v !== null));
  const cob = coberturaAtivo(h, a.id, anos, escopo.modo === "brasil" ? undefined : distsEscopo);
  const distPrincipal = principal && /^\d+$/.test(principal.id) ? Number(principal.id) : null;
  const natureza = distPrincipal !== null ? naturezaVariacoes(h, distPrincipal, a.id, anos) : null;
  const sinaisEsc = sinaisNoEscopo(h, distsEscopo, a.id, anos);
  const ressalvas2025 = (h.celulas[a.id] ?? []).filter((c) => c[1] === 2025 && (c[2] === "R" || c[2] === "P") && (escopo.modo === "brasil" || distsEscopo.includes(c[0])) && !h.motivos[c[3]].startsWith("tag “Extra”"));
  const pendPares = Object.entries(h.pares).filter(([k]) => escopo.modo === "brasil" || distsEscopo.includes(Number(k.split("|")[0])));
  const pendOutras = (h.celulas[a.id] ?? []).filter((c) => c[2] === "P" && !h.pares[`${c[0]}|${c[1]}`] && (escopo.modo === "brasil" || distsEscopo.includes(c[0])));
  const conceito = a.conceito;
  const semTuc0 = distPrincipal !== null ? anos.map((ano) => h.sem_tuc[`${distPrincipal}|${ano}|${conceito}`]) : null;
  const semTuc = semTuc0 && semTuc0.some((v) => v !== undefined) ? semTuc0 : null; // conceito sem TUC (ex.: redes): linha omitida
  const semDado = escopo.modo !== "brasil" && series.every((x) => x.pontos.every((pt) => pt.v === null));

  const buildLinhas = (t: ChartTokens) => ({
    grid: { left: 8, right: 20, top: 30, bottom: 24, containLabel: true },
    legend: { top: 0, left: 0, type: "scroll", tooltip: { show: true }, textStyle: { color: t.text2, fontFamily: t.font, fontSize: 11, width: 140, overflow: "truncate" } },
    tooltip: { trigger: "axis", backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
      valueFormatter: (v: number | null) => (v === null || v === undefined ? "N/D" : escala === "indice" ? v.toLocaleString("pt-BR", { maximumFractionDigits: 1 }) : `${fmt(v, a.medida)} ${UNIDADE[a.medida]}`) },
    xAxis: { type: "category", data: anos.map(String), axisLine: { lineStyle: { color: t.hairline } }, axisLabel: { color: t.text2, fontFamily: t.font } },
    yAxis: { type: "value", scale: true, axisLabel: { color: t.text3, fontFamily: t.font, fontSize: 10, formatter: (v: number) => (escala === "indice" ? String(v) : fmtCompact(v, a.medida)) }, splitLine: { lineStyle: { color: t.hairline } } },
    series: exibidas.map((x, i) => ({ name: x.nome, type: "line", connectNulls: false, symbolSize: 7,
      data: x.pontos.map((pt) => ({ value: pt.v, symbol: (pt as PontoHom).pub === "R" || pt.quebra ? "triangle" : "circle" })),
      lineStyle: { width: i === 0 ? 2.5 : 1.6, type: x.id === "painel" ? "dashed" : "solid" }, emphasis: { focus: "series" } })),
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
        formatter: (q: { value: [number, number, number | null] }) => { const r = heatRows[q.value[1]]; const sg = h.sinais[`${r.d}|${a.id}|${Number(cols[q.value[0]]) - 1}|${cols[q.value[0]]}`];
          return `<b>${r.s.nome}</b><br/>${cols[q.value[0]]}: ${q.value[2] === null ? "N/D" : `${q.value[2]}% ao ano`}${sg ? `<br/>${NATUREZA[sg[0]] ?? sg[0]}` : ""}`; } },
      xAxis: { type: "category", data: cols.map((c) => `${Number(c) - 1}→${c}`), axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 11 } },
      yAxis: { type: "category", data: heatRows.map((r) => r.s.nome), inverse: true, axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 11 } },
      visualMap: { min: -10, max: 10, calculable: false, orient: "vertical", right: 0, top: "middle", itemHeight: 120, textStyle: { color: t.text3, fontSize: 10 }, inRange: { color: [t.sideB, t.surface, t.sideA] } },
      series: [{ type: "heatmap", data: data.filter((d) => d[2] !== null), label: { show: true, color: t.text, fontSize: 10, formatter: (q: { value: [number, number, number] }) => `${q.value[2]}%` } }],
    };
  };

  const exportCSV = () => {
    const nome = `bdgd_2022-2025_evolucao_${a.id}_${visao}.csv`;
    const rows: Array<Array<string | number | null>> = [];
    for (const x of series) for (const pt of x.pontos as PontoHom[]) {
      const prov = /^\d+$/.test(x.id) ? (h.proveniencia[`${x.id}|${pt.ano}`] ?? []).filter((q) => q.uso !== "excluido_competencia").map((q) => q.item).join(" ") : "";
      rows.push([x.nome, a.id, a.medida, UNIDADE[a.medida], pt.ano, pt.v, ESTADO[pt.estado] ?? pt.estado, pt.pub ? ROTULO_PUB[pt.pub] : "", pt.motivo ?? "", pt.quebra ? "quebra" : "comparavel",
        visao === "perimetro" ? "perimetro_2025" : "publicacao_original", prov, sd.versao_regra, h.versao]);
    }
    downloadText(nome, toCSV(["serie", "ativo", "medida", "unidade", "ano", "valor", "estado", "estado_publicacao", "motivo", "comparabilidade", "visao", "publicacao_arcgis", "versao_regra", "versao_homologacao"], rows));
    toast(`${nome} exportado`);
  };

  return (
    <>
      <header className={`${p.head} rise`}>
        <div className="eyebrow">2022 · 2023 · 2024 · 2025</div>
        <h1 className="display" style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 14 }}><History size={34} strokeWidth={1.6} color="var(--accent)" aria-hidden /> Evolução histórica</h1>
        <p className="lede">Como os ativos físicos mudaram de 2022 a 2025, com a mesma regra de cálculo em todos os anos e a matriz de homologação aplicada a cada distribuidora, ano e ativo. Valores ausentes, pendentes ou bloqueados aparecem como N/D, nunca como zero, e nada é projetado.</p>
      </header>

      <div className={s.anos} role="list" aria-label="Situação de cada ano" data-testid="anos">
        {sd.cobertura.map((c, i) => (
          <div key={c.ano} role="listitem" className={s.ano} data-status={c.status_ano}>
            <div className={s.anoNum}>31/12/{c.ano}</div>
            <div className={s.anoSt}>{STATUS_ANO[c.status_ano] ?? "em validação"}</div>
            <div className={s.anoFoot}>{c.validadas} de {c.publicadas} publicações validadas{c.pendentes ? ` · ${c.pendentes} pendente${c.pendentes > 1 ? "s" : ""}` : ""}</div>
            <div className={s.bar}><span style={{ transform: `scaleX(${c.publicadas ? c.validadas / c.publicadas : 0})` }} /></div>
            <div className={s.anoFoot} data-testid={`cob-${c.ano}`}>{a.nome}: {cob[i]?.publicaveis ?? 0} DIST com valor · {(cob[i]?.P ?? 0) + (cob[i]?.B ?? 0)} pendentes/bloqueadas</div>
          </div>
        ))}
      </div>


      <PublicacoesAuditadas />

      <aside className={s.ressalvas} data-testid="evo-ressalvas" aria-label="Ressalvas de publicação">
        <ShieldCheck size={16} aria-hidden />
        <div>
          <b>Ressalvas vigentes.</b> 2022 e 2023 não têm cobertura nacional completa. O contrato também registra publicações não localizadas em 2024 e 2025: o total Brasil fica N/D em qualquer ano com lacunas. O painel balanceado mostra somente as mesmas distribuidoras comparáveis. Validação automática e zero técnico não equivalem a homologação humana. Não aplicável é um estado próprio; ausência e pendência nunca viram zero. A comprovação independente dos zeros técnicos permanece pendente.
          {ressalvas2025.length > 0 && <ul className={s.lista}>{ressalvas2025.slice(0, 4).map((c) => <li key={c[0]}><b>{nomeD(c[0])} 2025</b> · {ROTULO_PUB[c[2]]}: {h.motivos[c[3]]}</li>)}</ul>}
        </div>
      </aside>

      <EscopoSeletor ds={ds} value={escopo} onChange={setEscopo} testId="evo-escopo" />
      <div className={p.toolbar} role="toolbar" aria-label="Opções da evolução" style={{ marginTop: 12 }}>
        <Picker label="Família" value={a.familia} width={200} testId="evo-familia" options={familias.map((f) => ({ value: f, label: f, meta: `${ativos.filter((x) => x.familia === f).length} ativos` }))}
          onChange={(f) => setAtivo(ativos.find((x) => x.familia === f)?.id ?? a.id)} />
        <Picker label="Ativo" value={a.id} width={260} testId="evo-ativo" options={ativos.filter((x) => x.familia === a.familia).map((x) => ({ value: x.id, label: x.nome, meta: UNIDADE[x.medida] }))} onChange={setAtivo} />
        <Segmented label="Visão" size="sm" value={visao} onChange={setVisao} options={[{ value: "original", label: "Publicação original" }, { value: "perimetro", label: "Perímetro de 2025" }]} />
        <Segmented label="Escala" size="sm" value={escala} onChange={setEscala} options={[{ value: "valores", label: "Valores" }, { value: "indice", label: "Índice 100" }]} />
        <Segmented label="Visualização" size="sm" value={layout} onChange={setLayout} options={[{ value: "linhas", label: "Linhas" }, { value: "calor", label: "Mapa de calor" }]} />
        <span className={p.spacer} />
        <Explain title="Como a evolução é calculada" align="end" tecnico={`Regra ${sd.versao_regra} e matriz de homologação ${h.versao} (auditoria/fase4). CAGR = (último/primeiro)^(1/anos) − 1, só com base > 0 e sem quebra. Brasil = soma das DIST publicáveis; células pendentes ou bloqueadas ficam fora e são contadas.`}
          ressalva="Quebra de classificação: a codificação TUC mudou entre anos e o salto não é crescimento físico. Grupos usam a composição de 2025. Republicações divergentes não são escolhidas automaticamente.">
          Cada ponto é o total do ativo publicado pela distribuidora naquele ano, exibido só quando a célula é publicável pela matriz (homologado, completo técnico ou apto com ressalvas). “Perímetro de 2025” soma predecessoras incorporadas apenas com ponte comprovada.
        </Explain>
        <Button size="sm" onClick={exportCSV} data-testid="evo-csv"><Download size={14} /> CSV</Button>
      </div>

      {principal && (
        <div className={s.cards} data-testid="evo-cards">
          <div className={s.card}><div className={s.cardL}>{principal.nome}</div><div className={s.cardV}>{principal.pontos[3]?.v === null ? "N/D" : `${fmt(principal.pontos[3]?.v, a.medida)}`}<span className={s.cardU}> {UNIDADE[a.medida]} em 2025</span></div>
            {(principal.pontos[3] as PontoHom | undefined)?.pub && <div className={s.cardF}><Selo e={(principal.pontos[3] as PontoHom).pub!} /></div>}</div>
          <div className={s.card}><div className={s.cardL}>Variação acumulada</div><div className={s.cardV} data-testid="evo-var">{pct(varP?.pct ?? null)}</div><div className={s.cardF}>{varP?.motivo ?? (varP?.abs !== null && varP ? `${varP.abs >= 0 ? "+" : ""}${fmt(varP.abs, a.medida)} ${UNIDADE[a.medida]}` : "")}</div></div>
          <div className={s.card}><div className={s.cardL}>Crescimento médio anual (CAGR)</div><div className={s.cardV} data-testid="evo-cagr">{pct(varP?.cagr ?? null)}</div><div className={s.cardF}>{varP?.motivo ?? "entre o primeiro e o último ano com valor"}</div></div>
          <div className={s.card}><div className={s.cardL}>Ano a ano</div><div className={s.yoy}>{yoy.map((y) => <span key={y.ano}><b>{y.ano}</b> {pct(y.pct)}</span>)}</div></div>
        </div>
      )}

      <section className={s.stage} aria-label="Série temporal">
        {semDado && <EmptyState title="Sem valor publicável neste recorte">Nenhuma das distribuidoras escolhidas tem {a.nome.toLowerCase()} publicável em 2022–2025. Veja o motivo de cada ano na tabela e em “Qualidade e proveniência”.</EmptyState>}
        {!semDado && !algumHistorico && (
          <p className={s.note} data-testid="historico-preparacao"><Info size={14} aria-hidden /><span><b>Sem histórico publicável para este recorte.</b> As competências 2022–2024 não têm valor publicável para {escopo.modo === "brasil" ? "o agregado" : "as distribuidoras escolhidas"}; o motivo de cada ano está na tabela.</span></p>
        )}
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={layout} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.18 }}>
            {layout === "calor"
              ? (heatRows.length ? <EChart build={buildHeat} height={Math.max(200, heatRows.length * 24 + 50)} ariaLabel="Variação anual por distribuidora; os valores estão na tabela" testId="chart-calor" /> : <EmptyState title="Sem variações calculáveis">Nenhuma distribuidora do escopo tem dois anos consecutivos publicáveis.</EmptyState>)
              : <EChart build={buildLinhas} height={340} ariaLabel={`Evolução de ${a.nome} de 2022 a 2025; os valores estão na tabela`} testId="chart-linhas" />}
          </motion.div>
        </AnimatePresence>
        <div className={s.scroll} tabIndex={0} role="region" aria-label="Tabela da série">
        <table className={s.table} data-testid="evo-tabela">
          <caption className="sr-only">Valores anuais de {a.nome} ({unidade}), com o estado de publicação de cada ano</caption>
          <thead><tr><th scope="col">Série</th>{anos.map((y) => <th key={y} scope="col">{y}</th>)}<th scope="col">Variação</th><th scope="col">CAGR</th></tr></thead>
          <tbody>
            {series.map((x) => { const v = variacao(x); return (
              <tr key={x.id}>
                <th scope="row">{x.nome}{x.nota && <div className="caption">{x.nota}</div>}</th>
                {(x.pontos as PontoHom[]).map((pt) => (
                  <td key={pt.ano} title={pt.v === null ? (pt.motivo || sd.notas[`${x.id}|${pt.ano}|${a.id}`] || ESTADO[pt.estado] || "") : pt.pub === "R" ? pt.motivo : pt.quebra ? "quebra de classificação neste ano" : undefined}>
                    <Celula pt={pt} medida={a.medida} />
                  </td>
                ))}
                <td>{pct(v.pct)}</td><td>{pct(v.cagr)}</td>
              </tr>
            ); })}
          </tbody>
        </table>
        </div>
        <ul className={s.legenda} aria-label="Legenda da tabela">
          <li><Info size={13} aria-hidden /> N/D: sem valor publicável; o motivo aparece ao passar o mouse e em “Cobertura e qualidade”</li>
          <li><AlertTriangle size={12} className={s.warn} aria-hidden /> apto com ressalvas</li>
          <li><Flag size={12} className={s.flag} aria-hidden /> quebra de comparabilidade: a variação não é tratada como crescimento</li>
          <li>linha tracejada: painel balanceado · unidade: {UNIDADE[a.medida]}</li>
        </ul>
      </section>

      <section className={s.stage} aria-labelledby="var-t" data-testid="evo-variacoes">
        <h2 className="headline" id="var-t" style={{ fontSize: "1rem" }}>Natureza das variações · {principal?.nome}</h2>
        <p className="caption">Distingue expansão física de mudanças cadastrais e de classificação, a partir da auditoria de sinais temporais (identidade dos registros entre anos, parcela sem TUC e publicação de origem). Classificação indicativa, não é homologação.</p>
        <div className={s.scroll} tabIndex={0} role="region" aria-label="Variações anuais">
          <table className={s.table}>
            <caption className="sr-only">Variações anuais de {principal?.nome} com a natureza de cada mudança</caption>
            <thead><tr><th scope="col">Período</th><th scope="col">Variação absoluta</th><th scope="col">Variação %</th><th scope="col">Natureza</th></tr></thead>
            <tbody>
              {principal && principal.pontos.slice(1).map((pt, i) => {
                const ant = principal.pontos[i];
                const dabs = pt.v !== null && ant.v !== null ? pt.v - ant.v : null;
                const nat = natureza?.[i];
                const esc = sinaisEsc[i];
                const txt = nat ? (nat.natureza ? `${NATUREZA[nat.natureza] ?? nat.natureza} · ${nat.confianca?.toLowerCase().replaceAll("_", " ")}` : "sem sinal de anomalia")
                  : esc.total ? `${esc.total} sinal(is) nas distribuidoras: ${Object.entries(esc.contagem).map(([k, n]) => `${n} ${NATUREZA[k] ?? k}`).join(", ")}` : "sem sinal de anomalia nas distribuidoras";
                return (
                  <tr key={pt.ano}>
                    <th scope="row">{ant.ano}→{pt.ano}</th>
                    <td>{dabs === null ? <span className="faint">N/D</span> : `${dabs >= 0 ? "+" : ""}${fmt(dabs, a.medida)}`}</td>
                    <td>{pct(yoy[i]?.pct ?? null)}</td>
                    <td className={s.esq} title={nat?.causa ?? undefined}>{pt.quebra && <Flag size={11} className={s.flag} aria-label="quebra" />} {txt}{nat?.causa && nat.natureza && nat.natureza !== "expansao_fisica" ? <div className="caption">{nat.causa}</div> : null}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className={s.stage} aria-labelledby="qual-t" data-testid="evo-qualidade">
        <h2 className="headline" id="qual-t" style={{ fontSize: "1rem" }}>Cobertura e qualidade · {a.nome}</h2>
        <p className="caption">Estado de publicação das distribuidoras do recorte em cada ano, pela matriz de homologação. Só os três primeiros estados têm valor.</p>
        <div className={s.scroll} tabIndex={0} role="region" aria-label="Cobertura por estado">
          <table className={s.table}>
            <caption className="sr-only">Quantidade de distribuidoras por estado de publicação e ano</caption>
            <thead><tr><th scope="col">Estado</th>{anos.map((y) => <th key={y} scope="col">{y}</th>)}</tr></thead>
            <tbody>
              {ESTADOS.map((e) => (
                <tr key={e}><th scope="row"><Selo e={e} /><div className="caption">{DESCRICAO_PUB[e]}</div></th>{cob.map((c) => <td key={c.ano}>{c[e]}</td>)}</tr>
              ))}
              {semTuc && <tr data-testid="evo-tuc-linha"><th scope="row">Parcela sem TUC ({nomeD(distPrincipal!)})<div className="caption">registros do conceito sem tipo patrimonial; mudança brusca indica reclassificação</div></th>{semTuc.map((v, i) => <td key={i}>{v === undefined ? <span className="faint">N/D</span> : `${(v * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`}</td>)}</tr>}
            </tbody>
          </table>
        </div>
        <p className={s.note} data-testid="evo-tuc"><Info size={13} aria-hidden /><span><b>Recortes por TUC e atributos.</b> Para 2022–2024, a série histórica homologa apenas o total de cada ativo; os recortes por tipo patrimonial (TUC) e atributos DDA não foram validados para esses anos e por isso não são exibidos. Para 31/12/2025 eles estão em <Link href={`/explorar/?ativo=${a.conceito}`}>Explorar ativos</Link>.</span></p>
      </section>

      {escopo.modo !== "brasil" && distsSeries.length > 0 && (
        <section className={s.stage} aria-labelledby="prov-t" data-testid="evo-proveniencia">
          <h2 className="headline" id="prov-t" style={{ fontSize: "1rem" }}>Proveniência · publicações oficiais usadas</h2>
          <p className="caption">Cada valor rastreia até o arquivo publicado pela ANEEL (catálogo ArcGIS), com a versão, o intervalo da tabela BASE e o SHA-256 do arquivo baixado.</p>
          {distsSeries.map((d) => (
            <details key={d} className={s.prov} open={distsSeries.length === 1}>
              <summary><b>{nomeD(d)}</b> · DIST {d}</summary>
              <div className={s.scroll} tabIndex={0} role="region" aria-label={`Publicações de ${nomeD(d)}`}>
                <table className={s.table}>
                  <caption className="sr-only">Publicações oficiais de {nomeD(d)} por ano</caption>
                  <thead><tr><th scope="col">Ano</th><th scope="col">Estado</th><th scope="col">Publicação ANEEL</th><th scope="col">Base (DAT_INC–DAT_FNL)</th><th scope="col">Tag Extra</th><th scope="col">SHA-256</th></tr></thead>
                  <tbody>
                    {anos.map((ano) => { const pubs = h.proveniencia[`${d}|${ano}`] ?? []; const c = ih.get(`${d}|${ano}`); return (
                      <tr key={ano}>
                        <th scope="row">{ano}</th>
                        <td className={s.esq}>{c ? <><Selo e={c[0]} curto />{c[0] !== "T" && c[0] !== "H" && <div className="caption">{h.motivos[c[1]]}</div>}</> : <span className="faint">sem publicação</span>}</td>
                        <td className={s.esq}>{pubs.length ? pubs.map((q) => <div key={q.item}><a href={urlItem(q.item)} target="_blank" rel="noopener noreferrer">{q.versao || q.item.slice(0, 8)} <ExternalLink size={11} aria-hidden /><span className="sr-only"> (abre o catálogo ANEEL)</span></a><span className="caption"> · {q.uso.replaceAll("_", " ")}</span></div>) : <span className="faint">não disponível</span>}</td>
                        <td className={s.esq}>{pubs.map((q) => <div key={q.item}>{q.inc}–{q.fnl}{q.intervalo !== "INTERVALO_ANUAL_COMPATIVEL" && <span className={s.mini} data-e="R">{q.intervalo === "INCONSISTENTE" ? "inconsistente" : "não anual"}</span>}</div>)}</td>
                        <td>{pubs.map((q) => <div key={q.item}>{q.extra}</div>)}</td>
                        <td className={s.mono}>{pubs.map((q) => <div key={q.item} title={q.sha}>{q.sha.slice(0, 12)}…</div>)}</td>
                      </tr>
                    ); })}
                  </tbody>
                </table>
              </div>
            </details>
          ))}
        </section>
      )}

      {(pendPares.length > 0 || pendOutras.length > 0) && (
        <section className={s.stage} aria-labelledby="pend-t" data-testid="evo-pendencias">
          <h2 className="headline" id="pend-t" style={{ fontSize: "1rem" }}>Decisões pendentes que afetam este recorte</h2>
          <p className="caption">Nada aqui foi decidido automaticamente: as células ficam N/D até a decisão humana registrada. A recomendação técnica é só uma sugestão.</p>
          <ul className={s.suc}>
            {pendPares.sort((x, y) => x[1].ordem - y[1].ordem).slice(0, escopo.modo === "brasil" ? 13 : 20).map(([k, q]) => { const [d, ano] = k.split("|"); const dif = q.dif[a.id]; return (
              <li key={k}><b>{nomeD(Number(d))} {ano}</b> · duas publicações divergentes ({q.A.versao} × {q.B.versao}) · {q.grupo === "SEM_DIFERENCA_TOTAIS" ? "mesmos totais nos 25 ativos" : `${q.ativos_dif} ativo(s) com totais diferentes`} · risco {q.risco.toLowerCase()}
                {dif && <div className="caption">{a.nome}: {fmt(dif[0], a.medida)} × {fmt(dif[1], a.medida)} {UNIDADE[a.medida]}</div>}
                <div className="caption">Recomendação técnica: {q.recomendacao}</div></li>
            ); })}
            {pendOutras.slice(0, 10).map((c) => <li key={`${c[0]}|${c[1]}`}><b>{nomeD(c[0])} {c[1]}</b> · {h.motivos[c[3]]}</li>)}
          </ul>
        </section>
      )}

      {visao === "perimetro" && (
        <section className={s.stage} aria-labelledby="suc-t" data-testid="sucessoes">
          <h2 className="headline" id="suc-t" style={{ fontSize: "1rem" }}>Sucessões consideradas no perímetro de 2025</h2>
          <ul className={s.suc}>
            {sd.eventos.map((e) => {
              const pts = sd.ponte.filter((x) => x.evento_id === e.evento_id);
              const pt = h.pontes.find((x) => x.evento === e.evento_id);
              return (
                <li key={e.evento_id}>
                  <b>{nomeD(e.dist_origem)} → {nomeD(e.dist_destino_2025)}</b> · incorporação efetivada em {e.data_efetivacao.split("-").reverse().join("/")}
                  <div className="caption">{pts.length ? pts.map((x) => `${x.ano_base}: ${x.status_qualidade === "validado" ? "somada (conjuntos sem sobreposição)" : x.status_qualidade === "ja_incluida" ? "já contida na sucessora (não somada, para não duplicar)" : "não somada até decisão (ponte pendente)"}`).join(" · ") : "predecessora ainda em processamento: não somada"}</div>
                  {e.evento_id === "EPB_EBO_2023" && h.absorcao_epb.consumidores && <div className="caption">Evidência: em 2023 a Energisa Paraíba equivale a {h.absorcao_epb.consumidores[1]?.toLocaleString("pt-BR")}× a soma 2022 (EPB + EBO) em unidades consumidoras, contra {h.absorcao_epb.consumidores[0]?.toLocaleString("pt-BR")}× a EPB isolada: absorção provável, aguardando decisão.</div>}
                  {pt && <div className="caption">{pt.prova}</div>}
                </li>
              );
            })}
            {h.pontes.filter((x) => x.tipo.startsWith("renomeacao")).map((x) => <li key={x.evento}><b>{x.origem === x.destino ? `${nomeD(Number(x.destino))}` : x.origem}</b> · renomeação com o mesmo código de distribuidora: série contínua, sem soma</li>)}
          </ul>
        </section>
      )}
    </>
  );
}


