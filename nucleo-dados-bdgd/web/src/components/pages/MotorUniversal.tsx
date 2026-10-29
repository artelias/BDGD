"use client";
import { ObservacoesDados } from "@/components/ui/ObservacoesDados";
import { useEffect, useRef, useState } from "react";
import { formatarFisico, naturezaDe } from "@/lib/natureza-fisica";
import { exportarExperimentoMotor, parseResumoMotor, type ResumoMotor } from "@/lib/motor-universal";
import { COOPERA_UCBT_2025 } from "@/lib/observacoes-auditoria";
import s from "./motor-universal.module.css";

const names: Record<string, string> = { persistencia: "Persistência", tendencia_ols: "Tendência OLS", crescimento_historico: "Crescimento histórico" };
const number = (n: number | null | undefined) => n == null ? "N/D" : n.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
const statusName: Record<string, string> = { observado: "Observado", zero_tecnico: "Zero técnico — fora do treino", zero_verificado: "Zero com evidência independente", ausente: "Ausente", nao_homologado: "Não homologado", nao_aplicavel: "Não aplicável" };

/** Consulta sob demanda; não treina modelos nem baixa o artefato de pesquisa completo no navegador. */
export function MotorUniversal() {
  const [data, setData] = useState<ResumoMotor | null>(null);
  const [error, setError] = useState("");
  const loading = useRef(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const [family, setFamily] = useState("");
  const [asset, setAsset] = useState("");
  const [metric, setMetric] = useState("");
  const [dist, setDist] = useState("");
  const [model, setModel] = useState("");
  const [year, setYear] = useState(2030);
  async function load() {
    if (data || loading.current) return;
    loading.current = true; setError("");
    try {
      controller.current = new AbortController();
      const response = await fetch("/data/previsoes/motor-universal-resumo.json.gz", { signal: controller.current.signal });
      if (!response.ok) throw Error("Não foi possível carregar o experimento.");
      const buffer = await response.arrayBuffer(), bytes = new Uint8Array(buffer);
      const text = bytes[0] === 31 && bytes[1] === 139
        ? await new Response(new Blob([buffer]).stream().pipeThrough(new DecompressionStream("gzip"))).text()
        : new TextDecoder().decode(buffer); // servidores podem já aplicar Content-Encoding
      setData(parseResumoMotor(JSON.parse(text)));
    } catch (e) { if (!(e instanceof DOMException && e.name === "AbortError")) setError(e instanceof Error ? e.message : "Falha ao carregar experimento."); }
    finally { loading.current = false; }
  }
  const assets = data?.objetivos.filter((t) => !family || t.familia === family) ?? [];
  const assetId = assets.some((t) => t.objetivo_id === asset) ? asset : assets[0]?.objetivo_id;
  const metrics = assets.filter((t) => t.objetivo_id === assetId);
  const target = metrics.find((t) => t.metrica === metric) ?? metrics.find((t) => t.padrao) ?? metrics[0];
  const dists = data ? [...new Map(data.series.filter((r) => r.territorio.nivel === "dist").map((r) => [r.DIST, r.empresa])).entries()].sort((a, b) => a[1].localeCompare(b[1], "pt-BR")) : [];
  const distId = dists.some(([id]) => id === dist) ? dist : dists[0]?.[0];
  const series = data?.series.find((r) => r.DIST === distId && r.objetivo_id === assetId && r.metrica === target?.metrica && r.territorio.nivel === "dist");
  const chosen = series?.modelos.find((m) => m.modelo === model) ?? series?.modelos.find((m) => m.modelo === series.modelo_selecionado);
  const projection = data && chosen ? chosen.futuro[data.horizontes.indexOf(year)] : undefined;
  // contagens sem casas decimais (contrato de natureza física); extensão e potência com decimais
  const fis = (n: number | null | undefined) => formatarFisico(n, naturezaDe(target?.unidade ?? "itens"));
  const bloqueioCoopera = String(distId) === String(COOPERA_UCBT_2025.dist) && assetId === "consumidores" && target?.metrica === "quantidade";
  return <section className={s.section} aria-labelledby="motor-universal-title" data-testid="motor-universal">
    <h2 id="motor-universal-title">Motor universal de ativos BDGD</h2>
    <p>Infraestrutura de experimentos para todos os ativos catalogados. Os resultados atuais são retrospectivos e condicionais; não são previsões homologadas de demanda, obras ou investimento.</p>
    <details onToggle={(e) => { if (e.currentTarget.open) void load(); }}>
      <summary>Explorar experimentos do motor universal</summary>
      {!data ? error ? <div role="alert"><p>{error}</p><button onClick={() => void load()}>Tentar novamente</button></div> : <p role="status">Carregando o experimento auditável…</p> : <>
        <p data-testid="motor-universal-cobertura"><b>{data.objetivos_catalogados} ativos catalogados</b> · {data.objetivos.length} objetivos/métricas · {data.series_elegiveis.toLocaleString("pt-BR")} séries com baseline executável · <b>0 previsões homologadas</b>.</p>
        <p data-testid="motor-universal-universo">Nas {dists.length} DIST do painel: {number(data.cobertura.esperado)} combinações esperadas de distribuidora, ativo e métrica; {number(data.cobertura.observado)} séries com linhas no contrato, das quais {number(data.cobertura.bloqueado)} bloqueadas; {number(data.cobertura.ausente_no_contrato)} combinações sem histórico. Esse universo não certifica cobertura nacional completa.</p>
        <details><summary>Cobertura por métrica</summary><div className={s.scroll} role="region" tabIndex={0} aria-label="Cobertura das métricas do motor"><table><thead><tr><th scope="col">Métrica</th><th scope="col">Esperadas</th><th scope="col">Com linhas</th><th scope="col">Executáveis</th><th scope="col">Bloqueadas</th><th scope="col">Sem histórico</th></tr></thead><tbody>{data.cobertura.por_metrica.map((m) => <tr key={m.METRICA}><th scope="row">{m.METRICA}</th><td>{number(m.ESPERADO)}</td><td>{number(m.OBSERVADO)}</td><td>{number(m.ELEGIVEL)}</td><td>{number(m.BLOQUEADO)}</td><td>{number(m.AUSENTE)}</td></tr>)}</tbody></table></div><p>Potência em kVA está catalogada para transformadores de distribuição, força, medida e reguladores, mas não possui linhas no contrato histórico atual. Ausência de potência permanece N/D.</p></details>
        <div className={s.filters}>
          <label>Família do motor<select value={family} onChange={(e) => { setFamily(e.target.value); setAsset(""); setMetric(""); setModel(""); }}><option value="">Todas as famílias</option>{[...new Set(data.objetivos.map((t) => t.familia))].map((f) => <option key={f}>{f}</option>)}</select></label>
          <label>Ativo do motor<select value={assetId ?? ""} onChange={(e) => { setAsset(e.target.value); setMetric(""); setModel(""); }}>{[...new Map(assets.map((t) => [t.objetivo_id, t.nome])).entries()].map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
          <label>Métrica do motor<select value={target?.metrica ?? ""} onChange={(e) => { setMetric(e.target.value); setModel(""); }}>{metrics.map((t) => <option key={t.metrica} value={t.metrica}>{t.metrica} ({t.unidade})</option>)}</select></label>
          <label>Distribuidora do motor<select value={distId ?? ""} onChange={(e) => { setDist(e.target.value); setModel(""); }}>{dists.map(([id, name]) => <option key={id} value={id}>{name} · DIST {id}</option>)}</select></label>
          <label>Modelo do motor<select value={chosen?.modelo ?? ""} onChange={(e) => setModel(e.target.value)} disabled={!series?.modelos.length}><option value="" disabled>Sem modelo executável</option>{series?.modelos.map((m) => <option key={m.modelo} value={m.modelo} disabled={!m.futuro.length}>{names[m.modelo] ?? m.modelo}{m.motivo ? " — indisponível" : ""}</option>)}</select></label>
          <label>Horizonte do motor<select value={year} onChange={(e) => setYear(Number(e.target.value))}>{data.horizontes.map((y) => <option key={y}>{y}</option>)}</select></label>
        </div>
        {bloqueioCoopera && <p role="status" data-testid="motor-coopera-ausencia"><b>Coopera (DIST 5370): previsão de consumidores indisponível.</b> A UCBT 2025 está vazia na fonte (0*); o valor legado de 225 contém apenas UCMT+UCAT AT. Não utilizar esse subtotal como população completa, nem ajustar KNN com zero artificial. A estimativa com análogos exógenos aguarda dados reais e validação.</p>}
        {!series || series.status === "dados_insuficientes" || bloqueioCoopera ? <p role="status" data-testid="motor-universal-vazio"><b>Sem simulação elegível.</b> {series?.motivos.join(" · ") || target?.motivo || "Não há série por distribuidora para esta métrica no contrato atual."} Nenhum valor foi preenchido.</p> : <>
          <p role="status"><b>Simulação condicional para {year}: {fis(projection)} {target?.unidade}</b>. Método consultado: {names[chosen?.modelo ?? ""] ?? chosen?.modelo}. Seleção conservadora: {names[series.modelo_selecionado ?? ""] ?? series.modelo_selecionado}.</p>
          <p>Backtest diagnóstico de um ano: {chosen?.metricas.n ?? 0} origens · MAE {number(chosen?.metricas.mae)} · RMSE {number(chosen?.metricas.rmse)} · WAPE {chosen?.metricas.wape == null ? "N/D" : number(chosen.metricas.wape * 100) + "%"} · viés {number(chosen?.metricas.vies)}. Última origem reservada para auditoria: MAE {number(chosen?.auditoria.mae)}.</p>
          <p>Somente estoque passado e tempo nos baselines. O painel atual não contém variáveis demográficas, econômicas, energéticas ou climáticas enriquecidas. Não há intervalo probabilístico calibrado.</p>
          <p><b>Alvo: estoque físico.</b> A variação líquida é uma diferença entre estoques, não uma medida de entradas, baixas, substituições ou necessidade de expansão. Erros de um ano não validam o horizonte de cinco anos.</p>
          <div className={s.scroll} role="region" tabIndex={0} aria-label="Histórico e simulações do motor universal">
            <table><thead><tr><th scope="col">Ano</th><th scope="col">Estoque ({target?.unidade})</th><th scope="col">Variação líquida</th><th scope="col">Natureza</th></tr></thead><tbody>
              {series.historico.map((h) => <tr key={h.ano}><td>{h.ano}</td><td>{fis(h.valor)}</td><td>{number(h.variacao_liquida)}</td><td>{statusName[h.estado] ?? h.estado}</td></tr>)}
              {data.horizontes.map((y, i) => {
                const value = chosen?.futuro[i], before = i ? chosen?.futuro[i-1] : series.historico.find((h) => h.ano === data.base_year)?.valor;
                return y <= year && <tr key={y}><td>{y}</td><td>{fis(value)}</td><td>{fis(value != null && before != null ? value - before : null)}</td><td>Simulação condicional</td></tr>;
              })}
            </tbody></table>
          </div>
        </>}
        {series && <a className={s.export} download={`motor_bdgd_${assetId}_${target?.metrica}_DIST_${distId}.json`} href={`data:application/json;charset=utf-8,${encodeURIComponent(exportarExperimentoMotor(data, series, chosen))}`}>Exportar diagnóstico e seleção (JSON)</a>}
        <p className={s.provenance}>Dataset {data.dataset_version} · corte {data.as_of}. Experimento <code>{data.experiment_id}</code>. Fonte SHA-256 <code>{data.source_sha256}</code>. A prova detalhada por publicação permanece no contrato versionado e no registro completo do experimento.</p>
        <details><summary>Limites e dependências dos dados</summary><ul>{data.limites.map((limit) => <li key={limit}>{limit}</li>)}</ul><p>Totais nacionais não são gerados sem prova de cobertura completa e ausência de sobreposição. Variáveis futuras exigem cenário explícito e data de disponibilidade.</p></details>
      </>}
    </details>
    <ObservacoesDados dists={[distId ?? ""]} ativos={[assetId ?? ""]} anos={[2022,2023,2024,2025]} />
  </section>;
}
