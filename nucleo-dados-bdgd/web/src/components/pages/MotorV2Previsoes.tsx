"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { EChartsCoreOption } from "echarts/core";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import {
  CENARIOS_V2, URL_INDICE, csvSerieV2, ehContagemV2, fmtV2, motorV2Habilitado, pctV2, projetada, somaGrupo, urlDist, validarDist, validarIndice,
  type CenarioV2, type DistV2, type IndiceV2, type SerieV2,
} from "@/lib/motor-v2";
import s from "./cenarios-motor.module.css";

/** Resultados experimentais do Motor V2 por distribuidora, ativo e métrica. Produto pré-calculado; nada é treinado aqui.
 * Fora de uma build de homologação a seção só mostra o portão de publicação. */
export function MotorV2Previsoes() {
  if (!motorV2Habilitado()) {
    return <section className={s.section} aria-labelledby="motor-v2-title" data-testid="motor-v2-portao">
      <div className="eyebrow">Motor V2 · portão de publicação</div>
      <h2 id="motor-v2-title">Projeções por distribuidora do Motor V2</h2>
      <p className={s.lede}>Os resultados do Motor V2 são experimentais, sem homologação científica, e aparecem somente na versão de homologação. A publicação em produção depende da autorização final.</p>
    </section>;
  }
  return <MotorV2 />;
}

function useJson<T>(url: string | null, parse: (j: unknown) => T) {
  const [st, set] = useState<{ url: string | null; data: T | null; erro: string }>({ url: null, data: null, erro: "" });
  const [tentativa, setTentativa] = useState(0);
  useEffect(() => {
    if (!url) return;
    const c = new AbortController();
    fetch(url, { signal: c.signal })
      .then((r) => { if (!r.ok) throw Error(`Não foi possível carregar ${url}.`); return r.json(); })
      .then((j) => set({ url, data: parse(j), erro: "" }))
      .catch((e) => { if (!(e instanceof DOMException && e.name === "AbortError")) set({ url, data: null, erro: e instanceof Error ? e.message : "Falha ao carregar." }); });
    return () => c.abort();
  }, [url, tentativa, parse]);
  return { data: st.url === url ? st.data : null, erro: st.url === url ? st.erro : "", repetir: () => setTentativa((t) => t + 1) };
}

function MotorV2() {
  const indice = useJson(URL_INDICE, validarIndice);
  return <section className={s.section} aria-labelledby="motor-v2-title" data-testid="motor-v2">
    <div className="eyebrow">Motor V2 · homologação · experimental, não homologado</div>
    <h2 id="motor-v2-title">Projeções por distribuidora, ativo e métrica</h2>
    <p className={s.lede}>Para cada distribuidora e métrica física: histórico observado 2022–2025, modelo escolhido pela comparação retrospectiva, erros medidos e três cenários 2026–2030. Comparação retrospectiva não é validação científica: há 2 origens temporais e nenhum horizonte acima de 1 ano verificado. Cenários extremos não são intervalos de confiança.</p>
    {!indice.data ? indice.erro ? <div role="alert" className={s.alert}><p>{indice.erro}</p><button type="button" onClick={indice.repetir}>Tentar novamente</button></div>
      : <p role="status">Carregando o índice do Motor V2…</p> : <Explorador ix={indice.data} />}
  </section>;
}

function Explorador({ ix }: { ix: IndiceV2 }) {
  const familias = useMemo(() => [...new Set(ix.objetivos.map((o) => o.familia))].sort((a, b) => a.localeCompare(b, "pt-BR")), [ix]);
  const dists = useMemo(() => [...ix.dists].sort((a, b) => a.empresa.localeCompare(b.empresa, "pt-BR")), [ix]);
  const grupos = useMemo(() => Object.entries(ix.grupos).filter(([g]) => ix.dists.some((d) => d.grupo === g)).sort((a, b) => a[1].localeCompare(b[1], "pt-BR")), [ix]);
  const [familia, setFamilia] = useState("");
  const [chave, setChave] = useState("consumidores|quantidade");
  const [escopo, setEscopo] = useState("dist:6600");
  const [cenario, setCenario] = useState<CenarioV2>("Moderado");
  const [comparar, setComparar] = useState(true);
  const objetivos = ix.objetivos.filter((o) => !familia || o.familia === familia);
  const obj = objetivos.find((o) => `${o.objetivo}|${o.metrica}` === chave) ?? objetivos[0];
  const [tipo, id] = escopo.split(":");
  const distSel = tipo === "dist" ? (dists.find((d) => String(d.dist) === id) ?? dists[0]) : undefined;
  const membros = tipo === "grupo" ? dists.filter((d) => d.grupo === id) : distSel ? [distSel] : [];
  const arquivos = useArquivos(membros.map((d) => d.dist));
  if (!obj) return <p role="status">Sem métricas no índice do Motor V2.</p>;
  const k = `${obj.objetivo}|${obj.metrica}`;
  const series = membros.map((d) => ({ dist: d.dist, empresa: d.empresa, serie: arquivos.dados[d.dist]?.series.find((x) => `${x.objetivo}|${x.metrica}` === k) }));
  const carregando = membros.some((d) => !arquivos.dados[d.dist] && !arquivos.erros[d.dist]);
  const erro = membros.map((d) => arquivos.erros[d.dist]).find(Boolean);
  const nomeEscopo = distSel ? `${distSel.empresa} · DIST ${distSel.dist}` : `Grupo ${ix.grupos[id] ?? id} (${membros.length} distribuidoras)`;

  return <>
    <div className={s.filters}>
      <label>Família<select value={familia} onChange={(e) => setFamilia(e.target.value)} aria-label="Família de ativos do Motor V2"><option value="">Todas</option>{familias.map((f) => <option key={f}>{f}</option>)}</select></label>
      <label>Ativo e métrica<select value={k} onChange={(e) => setChave(e.target.value)} aria-label="Ativo e métrica do Motor V2">
        {objetivos.map((o) => <option key={`${o.objetivo}|${o.metrica}`} value={`${o.objetivo}|${o.metrica}`}>{o.nome} · {o.metrica} ({o.unidade})</option>)}
      </select></label>
      <label>Distribuidora ou grupo<select value={distSel ? `dist:${distSel.dist}` : escopo} onChange={(e) => setEscopo(e.target.value)} aria-label="Distribuidora ou grupo do Motor V2">
        <optgroup label="Distribuidoras">{dists.map((d) => <option key={d.dist} value={`dist:${d.dist}`}>{d.empresa} · DIST {d.dist}</option>)}</optgroup>
        {grupos.length > 0 && <optgroup label="Grupos econômicos">{grupos.map(([g, nome]) => <option key={g} value={`grupo:${g}`}>{nome}</option>)}</optgroup>}
      </select></label>
    </div>
    <div className={s.cenarios} role="radiogroup" aria-label="Cenário do Motor V2">
      {CENARIOS_V2.map((c) => <button key={c} type="button" role="radio" aria-checked={cenario === c} className={s.cenario} data-ativo={cenario === c} onClick={() => setCenario(c)}>
        <span className={s.cenarioNome}>{c}</span>
        <span className={s.cenarioModelo}>{c === "Moderado" ? "trajetória do modelo" : c === "Conservador" ? "menor crescimento observado" : "maior crescimento observado"}</span>
      </button>)}
      <label className={s.check}><input type="checkbox" checked={comparar} onChange={(e) => setComparar(e.target.checked)} /> Comparar os três cenários</label>
    </div>
    {erro ? <div role="alert" className={s.alert}><p>{erro}</p><button type="button" onClick={arquivos.repetir}>Tentar novamente</button></div>
      : carregando ? <p role="status">Carregando as séries de {nomeEscopo}…</p>
        : distSel ? <SerieDist ix={ix} d={arquivos.dados[distSel.dist]!} serie={series[0]?.serie} cenario={cenario} comparar={comparar} />
          : <SerieGrupo ix={ix} nome={nomeEscopo} series={series} cenario={cenario} comparar={comparar} />}
    <Cobertura ix={ix} chave={k} />
    <details className={s.detalhes}><summary>Limitações e proveniência do Motor V2</summary>
      <ul>{ix.limitacoes.map((l) => <li key={l}>{l}</li>)}</ul>
      <p className={s.limite}>Contrato nacional SHA-256 <span className="mono">{ix.contrato_sha256.slice(0, 16)}…</span> · status de publicação <b>{ix.status_publicacao}</b> · coeficientes lineares recuperados e verificados: {ix.coeficientes.recuperados} de {ix.coeficientes.tentados}.</p>
    </details>
    <div className={s.acoes}><Link className={s.export} href="/metodologia/#motor-v2">Metodologia do Motor V2 por empresa e métrica</Link></div>
  </>;
}

function useArquivos(ids: number[]) {
  const [dados, setDados] = useState<Record<number, DistV2>>({});
  const [erros, setErros] = useState<Record<number, string>>({});
  const [tentativa, setTentativa] = useState(0);
  const chave = ids.join(",");
  useEffect(() => {
    const c = new AbortController();
    for (const id of chave ? chave.split(",").map(Number) : []) {
      if (dados[id]) continue;
      fetch(urlDist(id), { signal: c.signal })
        .then((r) => { if (!r.ok) throw Error(`Série da DIST ${id} indisponível.`); return r.json(); })
        .then((j) => setDados((x) => ({ ...x, [id]: validarDist(j) })))
        .catch((e) => { if (!(e instanceof DOMException && e.name === "AbortError")) setErros((x) => ({ ...x, [id]: e instanceof Error ? e.message : "Falha ao carregar." })); });
    }
    return () => c.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- recarrega só quando o recorte muda ou o usuário repete
  }, [chave, tentativa]);
  return { dados, erros, repetir: () => { setErros({}); setTentativa((t) => t + 1); } };
}

function grafico(anosHist: number[], anosProj: number[], hist: Map<number, number>, ancora: number | null, valorAncora: number | null,
  traj: Partial<Record<CenarioV2, (number | null)[] | null>>, ativo: CenarioV2, comparar: boolean, conta: boolean) {
  return (t: ChartTokens): EChartsCoreOption => {
    const anos = [...anosHist, ...anosProj];
    const cores: Record<CenarioV2, string> = { Conservador: t.sideB, Moderado: t.accent, Agressivo: t.warn };
    const vis = (comparar ? CENARIOS_V2 : [ativo]).filter((c) => traj[c]);
    return {
      textStyle: { fontFamily: t.font, color: t.text2 },
      grid: { left: 72, right: 18, top: 34, bottom: 34 },
      legend: { top: 0, textStyle: { color: t.text2 } },
      tooltip: { trigger: "axis", valueFormatter: (v: unknown) => typeof v === "number" ? v.toLocaleString("pt-BR", { maximumFractionDigits: conta ? 0 : 1 }) : "N/D" },
      xAxis: { type: "category", data: anos.map(String), axisLine: { lineStyle: { color: t.hairline } }, axisLabel: { color: t.text2 } },
      yAxis: { type: "value", scale: true, minInterval: conta ? 1 : undefined, axisLabel: { color: t.text2, formatter: (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: conta ? 0 : 1 }) }, splitLine: { lineStyle: { color: t.hairline, opacity: 0.5 } } },
      series: [
        { name: "Observado", type: "line", data: anos.map((a) => hist.get(a) ?? null), lineStyle: { width: 2.5, color: t.text }, itemStyle: { color: t.text }, symbolSize: 7, connectNulls: false },
        ...vis.map((c) => ({ name: c, type: "line", connectNulls: false,
          data: anos.map((a) => a === ancora ? valorAncora : a >= anosProj[0] ? traj[c]![anosProj.indexOf(a)] ?? null : null),
          lineStyle: { width: c === ativo ? 2.5 : 1.5, type: "dashed", color: cores[c] }, itemStyle: { color: cores[c] }, symbolSize: c === ativo ? 6 : 4 })),
      ],
    };
  };
}

function SerieDist({ ix, d, serie, cenario, comparar }: { ix: IndiceV2; d: DistV2; serie: SerieV2 | undefined; cenario: CenarioV2; comparar: boolean }) {
  const build = useMemo(() => serie ? grafico(ix.anos_historicos, ix.anos_projecao, new Map(serie.historico.filter(([, v]) => v != null).map(([a, v]) => [a, v as number])),
    serie.ancora, serie.valor_ancora, serie.cenarios ?? {}, cenario, comparar, ehContagemV2(serie)) : null, [ix, serie, cenario, comparar]);
  if (!serie || !build) return <p role="status" className={s.alert}>Combinação sem registro para esta distribuidora.</p>;
  const est = ix.estados[serie.estado];
  const csv = csvSerieV2(d, serie);
  return <>
    <p className={s.estado} data-testid="motor-v2-estado"><b>{est?.rotulo ?? serie.estado}</b> · experimental, não homologado. {serie.motivo}</p>
    <AlertasPlausibilidade serie={serie} cenario={cenario} />
    {serie.estado === "SEM_ANCORA_2025" && <p className={s.alert} role="note">Âncora {serie.ancora}: horizonte real {serie.horizonte_real}. Esta série não entra em totais que exigem âncora 2025.</p>}
    <EChart build={build} height={320} ariaLabel={`Histórico e cenários do Motor V2 — ${serie.nome} (${serie.unidade}) — ${d.empresa}`} testId="motor-v2-grafico" />
    <div className={s.scroll} role="region" tabIndex={0} aria-label="Tabela anual do Motor V2">
      <table data-testid="motor-v2-tabela">
        <caption className={s.caption}>{serie.nome} — {serie.metrica} ({serie.unidade}) · {d.empresa} · DIST {d.dist}</caption>
        <thead><tr><th scope="col">Ano</th><th scope="col">Natureza</th>{CENARIOS_V2.map((c) => <th scope="col" key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {serie.historico.map(([a, v, e]) => <tr key={a}><th scope="row">{a}</th><td>Observado · {e}</td><td colSpan={3}>{fmtV2(v, serie)}</td></tr>)}
          {ix.anos_projecao.map((a, i) => <tr key={a}><th scope="row">{a}</th><td>Projeção experimental</td>
            {CENARIOS_V2.map((c) => <td key={c} data-ativo={c === cenario} data-estado-cenario={serie.cenarios_status?.[c] ?? ""}>{serie.cenarios && serie.cenarios[c] ? fmtV2(serie.cenarios[c]![i], serie) : serie.cenarios_status?.[c] === "BLOQUEADO" ? <span title={serie.plausibilidade?.cenarios?.[c as "Conservador" | "Agressivo"]?.motivo ?? ""}>Bloqueado</span> : "N/D"}{serie.cenarios_status?.[c] === "CORRIGIDO" ? " *" : ""}</td>)}</tr>)}
        </tbody>
      </table>
    </div>
    <Modelo serie={serie} />
    <div className={s.acoes}>
      <a className={s.export} data-testid="motor-v2-csv" download={`motor_v2_${serie.objetivo}_${serie.metrica}_DIST_${d.dist}.csv`} href={`data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`}>Exportar série e cenários (CSV)</a>
    </div>
  </>;
}

const ROTULO_CLASSE: Record<string, string> = {
  PLAUSIVEL_COM_EVIDENCIA: "plausível, com evidência na própria série", EXTRAPOLACAO_EXTREMA_NAO_SUSTENTADA: "extrapolação extrema não sustentada", RUPTURA_CADASTRAL: "ruptura cadastral",
  MUDANCA_DE_PERIMETRO: "mudança de perímetro", BASE_HISTORICA_PEQUENA: "base histórica pequena", HISTORICO_INSUFICIENTE: "histórico insuficiente", ERRO_DE_CALCULO: "erro de cálculo",
  PENDENTE_DE_HOMOLOGACAO: "pendente de homologação",
};

/** Alertas do portão de plausibilidade: o que foi bloqueado, o que foi corrigido (com o método) e o alerta de intensidade. */
function AlertasPlausibilidade({ serie, cenario }: { serie: SerieV2; cenario: CenarioV2 }) {
  const pl = serie.plausibilidade;
  if (!pl) return null;
  const cs = (["Conservador", "Agressivo"] as const).filter((c) => pl.cenarios[c] && (pl.cenarios[c].estado !== "ACEITO" || pl.cenarios[c].severidade));
  const ativoBloqueado = serie.cenarios_status?.[cenario] === "BLOQUEADO";
  return <div role="note" data-testid="motor-v2-plausibilidade" className={s.alert}>
    <p><b>Alerta de extrapolação{pl.severidade ? ` · severidade ${pl.severidade.toLowerCase()}` : ""}.</b> Os cenários extremos passam por um portão de plausibilidade: valores fora do que a própria série e as demais distribuidoras sustentaram não são publicados como previsão.</p>
    {ativoBloqueado && <p data-testid="motor-v2-cenario-bloqueado"><b>O cenário {cenario} está bloqueado</b> para esta série e não tem valor publicável. O valor original fica apenas no artefato de auditoria.</p>}
    <ul>{cs.map((c) => { const x = pl.cenarios[c]; return <li key={c}><b>{c}: {x.estado === "BLOQUEADO" ? "bloqueado" : x.estado === "CORRIGIDO" ? "corrigido (*)" : "aceito com alerta"}</b>{x.classe ? ` · ${ROTULO_CLASSE[x.classe] ?? x.classe}` : ""}. {x.motivo}</li>; })}</ul>
    {pl.alerta_intensidade && <p>{pl.alerta_intensidade}.</p>}
    {cs.some((c) => pl.cenarios[c].estado === "CORRIGIDO") && <p>* Corrigido: a taxa extrema foi substituída pelo crescimento que a própria série demonstrou nos últimos anos; o valor original está no artefato de auditoria.</p>}
  </div>;
}

function Modelo({ serie }: { serie: SerieV2 }) {
  const m = serie.modelo; const e = serie.erros;
  if (!m) return null;
  return <div className={s.modelo} data-testid="motor-v2-modelo">
    <h3>Modelo da trajetória moderada: {m.id ?? "N/D"}</h3>
    <p>{m.tipo === "baseline" ? "Baseline" : m.tipo === "reconciliacao" ? "Reconciliação hierárquica" : "Aprendizado de máquina / regressão"} · base: {m.base_da_projecao ?? "N/D"}. {m.justificativa}</p>
    {m.mecanismo && <p><code>{m.mecanismo}</code></p>}
    <p>Erro retrospectivo (horizonte de 1 ano, {e?.origens ?? 0} origem(ns)): MAE {fmtV2(e?.mae, serie)} · RMSE {fmtV2(e?.rmse, serie)} · WAPE {pctV2(e?.wape)} · viés {fmtV2(e?.vies, serie)}
      {serie.melhor_baseline_medido ? ` · melhor baseline medido: ${serie.melhor_baseline_medido}` : ""}{serie.ganho_vs_melhor_baseline != null ? ` · ganho de MAE vs baseline ${pctV2(serie.ganho_vs_melhor_baseline, 1)}` : ""}.</p>
    {serie.cenarios_meta?.degenerados && <p className={s.estado}>Cenários degenerados: o histórico comparável não tem crescimento mais extremo que o moderado, então os três cenários coincidem.</p>}
    <p className={s.limite}>Não homologado: {m.motivo_nao_homologado}.</p>
  </div>;
}

function SerieGrupo({ ix, nome, series, cenario, comparar }: { ix: IndiceV2; nome: string; series: { dist: number; empresa: string; serie: SerieV2 | undefined }[]; cenario: CenarioV2; comparar: boolean }) {
  const ref = series.find((x) => x.serie)?.serie;
  const somas = Object.fromEntries(CENARIOS_V2.map((c) => [c, somaGrupo(series, c)])) as Record<CenarioV2, ReturnType<typeof somaGrupo>>;
  const g = somas[cenario];
  const build = useMemo(() => grafico(ix.anos_historicos, ix.anos_projecao, g.hist, 2025, g.hist.get(2025) ?? null,
    Object.fromEntries(CENARIOS_V2.map((c) => [c, somas[c].total])) as Record<CenarioV2, (number | null)[] | null>, cenario, comparar, ref ? ehContagemV2(ref) : true),
  // eslint-disable-next-line react-hooks/exhaustive-deps -- somas e g derivam de series, que já está nas dependências
  [ix, series, cenario, comparar]);
  if (!ref) return <p role="status" className={s.alert}>Nenhuma distribuidora do grupo tem esta combinação.</p>;
  if (g.rotulo === "NAO_SOMAVEL") return <p role="status" className={s.alert} data-testid="motor-v2-nao-somavel">Potência de reguladores não é somável entre distribuidoras (potência própria e passante). Escolha uma distribuidora.</p>;
  return <>
    <p className={s.estado} data-testid="motor-v2-grupo-rotulo"><b>{g.rotulo === "PARCIAL" ? "Total PARCIAL" : "Total do grupo"}</b> · {g.incluidas} de {series.length} distribuidoras com série ancorada em 2025.{g.faltam.length ? ` Fora da soma (sem projeção com âncora 2025): ${g.faltam.join(", ")}. Nada foi preenchido com zero.` : ""}</p>
    {g.total && <EChart build={build} height={300} ariaLabel={`Soma do Motor V2 — ${ref.nome} — ${nome}`} testId="motor-v2-grafico-grupo" />}
    <div className={s.scroll} role="region" tabIndex={0} aria-label="Tabela do grupo no Motor V2">
      <table><caption className={s.caption}>{ref.nome} ({ref.unidade}) · {nome} · {g.rotulo}</caption>
        <thead><tr><th scope="col">Ano</th>{CENARIOS_V2.map((c) => <th scope="col" key={c}>{c}</th>)}</tr></thead>
        <tbody>{ix.anos_projecao.map((a, i) => <tr key={a}><th scope="row">{a}</th>{CENARIOS_V2.map((c) => <td key={c}>{somas[c].total ? fmtV2(somas[c].total![i], ref) : "N/D"}</td>)}</tr>)}</tbody>
      </table>
    </div>
  </>;
}

function Cobertura({ ix, chave }: { ix: IndiceV2; chave: string }) {
  const o = ix.objetivos.find((x) => `${x.objetivo}|${x.metrica}` === chave);
  if (!o) return null;
  const total = ix.dists.length;
  return <div className={s.modelo} data-testid="motor-v2-cobertura">
    <h3>Cobertura nacional de {o.nome} ({o.unidade})</h3>
    <p>{o.series_com_15_valores} de {total} distribuidoras com os 15 valores (5 anos × 3 cenários){o.series_com_cenario_bloqueado ? `; ${o.series_com_cenario_bloqueado} com cenário extremo bloqueado pela plausibilidade (sem os 15 valores)` : ""}. Estado das demais: {Object.entries(o.estados).filter(([e]) => !projetada({ estado: e })).map(([e, n]) => `${ix.estados[e]?.rotulo ?? e}: ${n}`).join(" · ") || "nenhuma"}.</p>
    {o.total_2030 ? <p>Total 2030 <b data-testid="motor-v2-rotulo-total">{o.rotulo_total}</b>{o.cobertura_estoque_2025 != null ? ` (cobre ${pctV2(o.cobertura_estoque_2025, 2)} do estoque 2025 do contrato)` : ""}: {CENARIOS_V2.map((c) => `${c} ${fmtV2(o.total_2030![c], o)}`).join(" · ")}, somando as mesmas {o.n_series_total?.Moderado ?? "N/D"} séries (as que têm os três cenários publicáveis).{o.series_com_cenario_bloqueado ? ` Moderado com todas as ${o.n_series_moderado_todas} séries projetadas: ${fmtV2(o.total_2030_moderado_todas ?? null, o)}.` : ""}</p>
      : <p>{o.observacao ?? "Sem total nacional."}</p>}
  </div>;
}
