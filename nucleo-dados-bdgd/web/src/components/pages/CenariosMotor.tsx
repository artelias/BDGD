"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { EChartsCoreOption } from "echarts/core";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { useData } from "@/lib/data-context";
import { ehContagem, formatarFisico } from "@/lib/natureza-fisica";
import { COOPERA_UCBT_2025 } from "@/lib/observacoes-auditoria";
import {
  CENARIOS, ROTULO_CENARIO, ROTULO_ESTADO, exportarCsv, naturezaMetrica, parseCenarios, somaGrupo, variacoes,
  type Cenario, type MetricaCenario, type ProdutoCenarios,
} from "@/lib/cenarios-motor";
import s from "./cenarios-motor.module.css";

const URL = "/data/previsoes/cenarios-motor.json";
const MEDIDA: Record<string, string> = { quantidade: "Quantidade", extensao_km: "Extensão", potencia_kva: "Potência" };
const num = (n: number | null | undefined, d = 0) => n == null ? "N/D" : n.toLocaleString("pt-BR", { maximumFractionDigits: d });
const pct = (n: number | null | undefined, d = 1) => n == null ? "N/D" : `${n.toLocaleString("pt-BR", { maximumFractionDigits: d, minimumFractionDigits: d })}%`;

/** Explorador dos cenários pré-calculados. Não treina modelos no navegador; carrega o produto compacto sob demanda. */
export function CenariosMotor() {
  const [data, setData] = useState<ProdutoCenarios | null>(null);
  const [erro, setErro] = useState("");
  const [tentativa, setTentativa] = useState(0);
  useEffect(() => {
    const c = new AbortController();
    fetch(URL, { signal: c.signal })
      .then((r) => { if (!r.ok) throw Error("Não foi possível carregar os cenários do motor."); return r.json(); })
      .then((j) => { setData(parseCenarios(j)); setErro(""); })
      .catch((e) => { if (!(e instanceof DOMException && e.name === "AbortError")) setErro(e instanceof Error ? e.message : "Falha ao carregar os cenários."); });
    return () => c.abort();
  }, [tentativa]);
  return <section className={s.section} aria-labelledby="cenarios-title" data-testid="cenarios-motor">
    <div className="eyebrow">Modelos executados · backtest com origem móvel</div>
    <h2 id="cenarios-title">Cenários de expansão por métrica física</h2>
    <p className={s.lede}>Trajetórias 2026–2030 de modelos efetivamente executados e comparados nos mesmos pontos de backtest. Os cenários são interpretações dos modelos validados — não são nomes de algoritmos, previsões homologadas, necessidade técnica de expansão ou CAPEX.</p>
    {!data ? erro ? <div role="alert" className={s.alert}><p>{erro}</p><button type="button" onClick={() => { setErro(""); setTentativa((t) => t + 1); }}>Tentar novamente</button></div>
      : <p role="status">Carregando cenários do motor…</p> : <Explorador data={data} />}
  </section>;
}

function Explorador({ data }: { data: ProdutoCenarios }) {
  const ds = useData();
  const grupos = ds.status === "ready" ? ds.ds.grupos : [];
  const familias = [...new Set(data.metricas.map((m) => m.familia))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const [familia, setFamilia] = useState("");
  const [ativo, setAtivo] = useState("trafo_dist");
  const [metrica, setMetrica] = useState("quantidade");
  const [escopo, setEscopo] = useState<string>("dist:");
  const [cenario, setCenario] = useState<Cenario>("moderado");
  const [comparar, setComparar] = useState(true);
  const ativos = [...new Map(data.metricas.filter((m) => !familia || m.familia === familia).map((m) => [m.conceito, m.ativo])).entries()]
    .sort((a, b) => a[1].localeCompare(b[1], "pt-BR"));
  const ativoId = ativos.some(([id]) => id === ativo) ? ativo : ativos[0]?.[0];
  const metricas = data.metricas.filter((m) => m.conceito === ativoId);
  const m: MetricaCenario | undefined = metricas.find((x) => x.metrica === metrica) ?? metricas[0];
  const dists = m ? Object.keys(m.series).sort((a, b) => (data.empresas[a] ?? a).localeCompare(data.empresas[b] ?? b, "pt-BR")) : [];
  const [tipo, id] = escopo.split(":");
  const distId = tipo === "dist" ? (dists.includes(id) ? id : dists[0]) : undefined;
  const grupo = tipo === "grupo" ? grupos.find((g) => g.id === id) : undefined;
  const membros = grupo && ds.status === "ready" ? ds.ds.groupDists(grupo.id).map((d) => String(d.dist)) : [];
  const cenarioAtivo: Cenario = m && m.cenarios[cenario] ? cenario : "moderado";
  const n = data.horizonte.length;
  const coopera = m?.conceito === "consumidores" && (distId === String(COOPERA_UCBT_2025.dist) || membros.includes(String(COOPERA_UCBT_2025.dist)));

  const serie = (() => {
    if (!m) return null;
    if (distId) {
      const x = m.series[distId];
      if (!x) return null;
      return { hist: new Map(x.hist), traj: Object.fromEntries(CENARIOS.map((c) => [c, x[c]])) as Record<Cenario, number[] | null>, faltantes: [] as string[], erro: x.erro_moderado };
    }
    const por = Object.fromEntries(CENARIOS.map((c) => [c, somaGrupo(m, membros.filter((d) => m.series[d]), c, n)])) as Record<Cenario, ReturnType<typeof somaGrupo>>;
    const semSerie = membros.filter((d) => !m.series[d]);
    return { hist: por.moderado.hist ?? new Map<number, number>(), traj: Object.fromEntries(CENARIOS.map((c) => [c, semSerie.length ? null : por[c].traj])) as Record<Cenario, number[] | null>,
      faltantes: [...new Set([...semSerie, ...por[cenarioAtivo].faltantes])], erro: null };
  })();

  const base = serie ? serie.hist.get(data.base) ?? null : null;
  const anosHist = serie ? [...serie.hist.keys()].sort() : [];
  const build = (t: ChartTokens): EChartsCoreOption => {
    const anos = [...anosHist, ...data.horizonte];
    const cores: Record<Cenario, string> = { conservador: t.sideB, moderado: t.accent, agressivo: t.warn };
    const visiveis = comparar ? CENARIOS : [cenarioAtivo];
    return {
      textStyle: { fontFamily: t.font, color: t.text2 },
      grid: { left: 64, right: 18, top: 34, bottom: 34, containLabel: false },
      legend: { top: 0, textStyle: { color: t.text2 } },
      // contagens nunca aparecem com casas decimais no gráfico; extensão e potência mantêm 1 casa
      tooltip: { trigger: "axis", valueFormatter: (v: unknown) => { if (typeof v !== "number" || !m) return "N/D"; try { return formatarFisico(v, naturezaMetrica(m)); } catch { return "valor inválido"; } } },
      xAxis: { type: "category", data: anos.map(String), axisLine: { lineStyle: { color: t.hairline } }, axisLabel: { color: t.text2 } },
      yAxis: { type: "value", scale: true, minInterval: m && ehContagem(naturezaMetrica(m)) ? 1 : undefined,
        // rótulos do eixo em pt-BR (milhar com ponto): "260,000" em formato en-US seria lido como 260 com três casas decimais
        axisLabel: { color: t.text2, formatter: (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: m && ehContagem(naturezaMetrica(m)) ? 0 : 1 }) }, splitLine: { lineStyle: { color: t.hairline, opacity: 0.5 } } },
      series: [
        { name: "Observado", type: "line", data: anos.map((a) => serie?.hist.get(a) ?? null), lineStyle: { width: 2.5, color: t.text }, itemStyle: { color: t.text }, symbolSize: 7 },
        ...visiveis.filter((c) => serie?.traj[c]).map((c) => ({
          name: ROTULO_CENARIO[c], type: "line",
          data: anos.map((a) => a === data.base ? base : a > data.base ? serie!.traj[c]![data.horizonte.indexOf(a)] : null),
          lineStyle: { width: c === cenarioAtivo ? 2.5 : 1.5, type: "dashed", color: cores[c] }, itemStyle: { color: cores[c] }, symbolSize: c === cenarioAtivo ? 6 : 4,
        })),
      ],
    };
  };

  if (!m) return <p role="status">Sem métricas no produto de cenários.</p>;
  const fis = (n: number | null | undefined) => formatarFisico(n, naturezaMetrica(m));   // contagem fracionária lança erro, nunca é arredondada
  const modeloId = m.cenarios[cenarioAtivo];
  const modelo = modeloId ? data.modelos[modeloId] : null;
  const erroM = modeloId ? m.modelos[modeloId] : null;
  const pers = m.modelos.persistencia;
  const traj = serie?.traj[cenarioAtivo] ?? null;
  const vars = modeloId ? data.variaveis.filter((v) => v.modelos_que_usaram.split("|").includes(modeloId)) : [];
  const nomeEscopo = distId ? `${data.empresas[distId] ?? distId} · DIST ${distId}` : grupo ? `Grupo ${grupo.nome} (${membros.length} distribuidoras)` : "";
  const csv = distId && m.series[distId] ? exportarCsv(data, m, distId) : null;

  return <>
    <div className={s.filters}>
      <label>Família<select value={familia} onChange={(e) => setFamilia(e.target.value)}><option value="">Todas</option>{familias.map((f) => <option key={f}>{f}</option>)}</select></label>
      <label>Ativo<select value={ativoId} onChange={(e) => setAtivo(e.target.value)}>{ativos.map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}</select></label>
      <label>Métrica<select value={m.metrica} onChange={(e) => setMetrica(e.target.value)}>{metricas.map((x) => <option key={x.metrica} value={x.metrica}>{MEDIDA[x.metrica] ?? x.metrica} ({x.unidade}){x.experimental ? " — experimental" : ""}</option>)}</select></label>
      <label>Distribuidora ou grupo<select value={distId ? `dist:${distId}` : escopo} onChange={(e) => setEscopo(e.target.value)}>
        <optgroup label="Distribuidoras">{dists.map((d) => <option key={d} value={`dist:${d}`}>{data.empresas[d] ?? d} · DIST {d}</option>)}</optgroup>
        {grupos.length > 0 && <optgroup label="Grupos econômicos">{grupos.map((g) => <option key={g.id} value={`grupo:${g.id}`}>{g.nome}</option>)}</optgroup>}
      </select></label>
    </div>
    <div className={s.cenarios} role="radiogroup" aria-label="Cenário">
      {CENARIOS.map((c) => {
        const disp = !!m.cenarios[c];
        return <button key={c} type="button" role="radio" aria-checked={cenarioAtivo === c} disabled={!disp} className={s.cenario} data-ativo={cenarioAtivo === c} onClick={() => setCenario(c)}>
          <span className={s.cenarioNome}>{ROTULO_CENARIO[c]}</span>
          <span className={s.cenarioModelo}>{disp ? data.modelos[m.cenarios[c]!].nome : "Indisponível"}</span>
        </button>;
      })}
      <label className={s.check}><input type="checkbox" checked={comparar} onChange={(e) => setComparar(e.target.checked)} /> Comparar os cenários disponíveis</label>
    </div>
    <p className={s.estado} data-testid="cenarios-estado"><b>{ROTULO_ESTADO[m.estado] ?? m.estado}</b>{m.experimental && " · métrica experimental derivada fora do contrato homologado (potência via vínculo EQ→UN)"}. {m.justificativas[cenarioAtivo]}</p>
    {coopera ? <p role="status" className={s.alert} data-testid="cenarios-coopera"><b>Coopera (DIST {COOPERA_UCBT_2025.dist}): consumidores sem projeção.</b> A UCBT 2025 está vazia na fonte; o subtotal não é tratado como população completa nem convertido em zero.</p>
      : !serie || !traj ? <p role="status" className={s.alert} data-testid="cenarios-vazio"><b>Sem trajetória para este cenário em {nomeEscopo || "o escopo"}.</b> {serie?.faltantes.length ? `Distribuidoras sem projeção completa no grupo: ${serie.faltantes.map((d) => data.empresas[d] ?? d).join(", ")}. A soma não é completada.` : "A série não tem três anos contíguos comparáveis terminando em 2025, ou a trajetória foi rejeitada por implausibilidade física."} Nenhum valor foi preenchido.</p>
      : <>
        {(() => {
          const fim = (c: Cenario) => serie.traj[c]?.[n - 1];
          const [c0, m0, a0] = [fim("conservador"), fim("moderado"), fim("agressivo")];
          const invertido = (c0 != null && m0 != null && c0 > m0) || (a0 != null && m0 != null && a0 < m0) || (c0 != null && a0 != null && c0 > a0);
          return invertido && <p className={s.estado} data-testid="cenarios-ordem">Neste recorte, a ordem das trajetórias difere da ordem dos cenários: Conservador e Agressivo são definidos pelo crescimento agregado da métrica em todas as distribuidoras, e um modelo pode crescer menos ou mais em uma distribuidora ou grupo específico.</p>;
        })()}
        <EChart build={build} height={320} ariaLabel={`Histórico observado e cenários de ${m.ativo} (${m.unidade}) — ${nomeEscopo}`} testId="cenarios-grafico" />
        <div className={s.scroll} role="region" tabIndex={0} aria-label="Tabela anual de histórico e cenários">
          <table>
            <caption className={s.caption}>{m.ativo} — {MEDIDA[m.metrica]} ({m.unidade}) · {nomeEscopo}</caption>
            <thead><tr><th scope="col">Ano</th><th scope="col">Natureza</th>{CENARIOS.map((c) => <th scope="col" key={c}>{ROTULO_CENARIO[c]}</th>)}<th scope="col">Variação vs {data.base} ({ROTULO_CENARIO[cenarioAtivo]})</th></tr></thead>
            <tbody>
              {anosHist.map((a) => <tr key={a}><th scope="row">{a}</th><td>Observado</td><td colSpan={3}>{fis(serie.hist.get(a))}</td><td>—</td></tr>)}
              {data.horizonte.map((a, i) => {
                const v = base != null ? variacoes(base, traj)?.[i] : null;
                return <tr key={a}><th scope="row">{a}</th><td>Simulação condicional</td>
                  {CENARIOS.map((c) => <td key={c} data-ativo={c === cenarioAtivo}>{serie.traj[c] ? fis(serie.traj[c]![i]) : "Indisponível"}</td>)}
                  <td>{v ? `${v.abs >= 0 ? "+" : ""}${fis(v.abs)} (${pct(v.pct)})` : "N/D"}</td></tr>;
              })}
            </tbody>
          </table>
        </div>
      </>}
    {modelo && erroM && <div className={s.modelo} data-testid="cenarios-modelo">
      <h3>{ROTULO_CENARIO[cenarioAtivo]}: {modelo.nome}</h3>
      <p>{modelo.familia}. <code>{modelo.formula}</code></p>
      <p>Backtest com origens {data.origens_backtest.join(" e ")} sobre os mesmos {num(erroM.n)} pontos para todos os modelos: WAPE {pct((erroM.wape ?? 0) * 100, 2)} (h=1: {pct(erroM.wape_h1 == null ? null : erroM.wape_h1 * 100, 2)}; h=2: {pct(erroM.wape_h2 == null ? null : erroM.wape_h2 * 100, 2)}) · MdAPE {pct(erroM.mdape == null ? null : erroM.mdape * 100, 2)} · viés relativo {pct(erroM.vies == null ? null : erroM.vies * 100, 2)} · persistência WAPE {pct(pers?.wape == null ? null : pers.wape * 100, 2)}.{distId && serie?.erro != null && cenarioAtivo === "moderado" ? ` Erro mediano nesta distribuidora: ${pct(serie.erro * 100, 2)}.` : ""}</p>
      <p>Variáveis utilizadas: {vars.length ? vars.map((v) => `${v.variavel} (${v.tipo})`).join(", ") : "somente o histórico da própria série e o tempo"}.</p>
      <p className={s.limite}>Limites: o backtest cobre horizontes de 1 e 2 anos; 2028–2030 são extrapolações sem verificação retrospectiva. Sem intervalo probabilístico calibrado: a diferença entre cenários não é intervalo de confiança. Estoque físico não identifica entradas, baixas, obras ou investimento.</p>
    </div>}
    <div className={s.acoes}>
      {csv && <a className={s.export} download={`cenarios_${m.conceito}_${m.metrica}_DIST_${distId}.csv`} href={`data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`}>Exportar série e cenários (CSV)</a>}
      <Link className={s.export} href="/metodologia/#motor-cenarios">Metodologia dos modelos executados</Link>
    </div>
    <details className={s.detalhes}><summary>Todos os modelos avaliados para esta métrica</summary>
      <div className={s.scroll} role="region" tabIndex={0} aria-label="Comparação de modelos">
        <table><thead><tr><th scope="col">Modelo</th><th scope="col">WAPE</th><th scope="col">h=1</th><th scope="col">h=2</th><th scope="col">Viés</th><th scope="col">Trajetória agregada</th><th scope="col">Situação</th></tr></thead>
          <tbody>{Object.entries(m.modelos).sort((a, b) => (a[1].wape ?? 9) - (b[1].wape ?? 9)).map(([id, e]) => <tr key={id}>
            <th scope="row">{data.modelos[id]?.nome ?? id}</th><td>{pct(e.wape == null ? null : e.wape * 100, 2)}</td><td>{pct(e.wape_h1 == null ? null : e.wape_h1 * 100, 2)}</td><td>{pct(e.wape_h2 == null ? null : e.wape_h2 * 100, 2)}</td>
            <td>{pct(e.vies == null ? null : e.vies * 100, 2)}</td><td>{e.cagr == null ? "N/D" : `${pct(e.cagr * 100, 2)}/ano`}</td>
            <td>{CENARIOS.filter((c) => m.cenarios[c] === id).map((c) => ROTULO_CENARIO[c]).join(", ") || (e.elegivel ? "Elegível, não selecionado" : `Inelegível: ${e.motivo}`)}</td></tr>)}</tbody></table>
      </div>
    </details>
  </>;
}
