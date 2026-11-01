"use client";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  CENARIOS_V2, URL_INDICE, ehContagemV2, fmtV2, motorV2Habilitado, pctV2, projetada, urlDist, validarDist, validarIndice,
  type DistV2, type IndiceV2, type SerieV2,
} from "@/lib/motor-v2";

const NOME_FEATURE: Record<string, string> = {
  log_estoque: "log(1 + estoque em t−1)", log_consumidores: "log(1 + consumidores em t−1)", log_rede_mt_km: "log(1 + km de rede MT em t−1)",
  crescimento_anterior: "crescimento log1p de t−2 para t−1",
};

/** Metodologia do Motor V2 para uma empresa, ativo e métrica: histórico, publicações, modelo, equação, variáveis, baselines,
 * erros e status. Lê o mesmo produto da página Previsões; sem build de homologação mostra só o método geral. */
export function MetodologiaMotorV2() {
  return <div data-testid="metodologia-motor-v2">
    <p>O Motor V2 projeta, para cada distribuidora e cada objetivo físico do contrato nacional (contagens, km e kVA), uma trajetória moderada e dois cenários extremos para 2026–2030. A trajetória moderada vem do modelo escolhido pela <b>comparação retrospectiva</b> em duas origens (2023 e 2024, horizonte de 1 ano) entre persistência, deriva, CAGR e seis algoritmos (OLS, Ridge, Elastic Net, Poisson, Random Forest e HistGradientBoosting) treinados em painéis de distribuidoras comparáveis ou do mesmo grupo econômico. Um modelo de ML só é escolhido se for pelo menos 5% melhor que o melhor baseline no escore robusto e não pior em nenhuma origem; senão vale o baseline por política.</p>
    <p>Conservador e Agressivo deslocam o crescimento log1p anual da trajetória moderada para o menor e o maior crescimento observado nas transições comparáveis da própria série (após a triagem de saltos atípicos), quando são mais extremos; senão coincidem com o Moderado e a degeneração é registrada. <b>Não são intervalos de confiança.</b> Nenhum modelo é cientificamente homologado: a regra exige 3 origens independentes e um teste point-in-time, e só há 2 origens sem vintage comprovada.</p>
    <p>Variáveis explicativas efetivamente usadas: log do estoque, log dos consumidores e log dos km de rede MT da mesma distribuidora em t−1, e o crescimento anterior. PIB e população municipais (IBGE), DEC/FEC, densidade e área urbana/rural estão no registro de features, mas não entraram nas séries por distribuidora desta execução. EPE e IPEA não estão integrados. A fração de ligações recentes (DAT_CON) segue desligada até uma auditoria por DIST separar ligação nova de alteração cadastral. Não há covariáveis futuras: o passo de um ano do modelo é mantido constante no horizonte.</p>
    {motorV2Habilitado() ? <Auditoria /> : <p className="caption" data-testid="metodologia-motor-v2-portao">A auditoria interativa por empresa usa o produto experimental do Motor V2, disponível somente na versão de homologação.</p>}
  </div>;
}

function Auditoria() {
  const [ix, setIx] = useState<IndiceV2 | null>(null);
  const [dist, setDist] = useState<DistV2 | null>(null);
  const [erro, setErro] = useState("");
  const [d, setD] = useState("6600");
  const [k, setK] = useState("trafo_dist|quantidade");
  useEffect(() => {
    const c = new AbortController();
    fetch(URL_INDICE, { signal: c.signal }).then((r) => { if (!r.ok) throw Error("Índice do Motor V2 indisponível."); return r.json(); })
      .then((j) => setIx(validarIndice(j))).catch((e) => { if (!(e instanceof DOMException && e.name === "AbortError")) setErro(e.message); });
    return () => c.abort();
  }, []);
  useEffect(() => {
    const c = new AbortController();
    fetch(urlDist(d), { signal: c.signal }).then((r) => { if (!r.ok) throw Error(`Série da DIST ${d} indisponível.`); return r.json(); })
      .then((j) => { setDist(validarDist(j)); setErro(""); }).catch((e) => { if (!(e instanceof DOMException && e.name === "AbortError")) setErro(e.message); });
    return () => c.abort();
  }, [d]);
  const dists = useMemo(() => ix ? [...ix.dists].sort((a, b) => a.empresa.localeCompare(b.empresa, "pt-BR")) : [], [ix]);
  if (erro) return <p role="alert">{erro}</p>;
  if (!ix) return <p role="status">Carregando o índice do Motor V2…</p>;
  const serie = dist && String(dist.dist) === d ? dist.series.find((x) => `${x.objetivo}|${x.metrica}` === k) : undefined;
  return <section aria-labelledby="motor-v2-auditoria" data-testid="metodologia-motor-v2-auditoria">
    <h3 id="motor-v2-auditoria">Auditoria por empresa, ativo e métrica</h3>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,220px),1fr))", gap: 12, marginBottom: 16 }}>
      <label>Distribuidora<select value={d} onChange={(e) => setD(e.target.value)} aria-label="Distribuidora da metodologia do Motor V2" style={{ display: "block", width: "100%", padding: 10, marginTop: 6 }}>
        {dists.map((x) => <option key={x.dist} value={String(x.dist)}>{x.empresa} · DIST {x.dist}</option>)}</select></label>
      <label>Ativo e métrica<select value={k} onChange={(e) => setK(e.target.value)} aria-label="Ativo e métrica da metodologia do Motor V2" style={{ display: "block", width: "100%", padding: 10, marginTop: 6 }}>
        {ix.objetivos.map((o) => <option key={`${o.objetivo}|${o.metrica}`} value={`${o.objetivo}|${o.metrica}`}>{o.nome} · {o.metrica} ({o.unidade})</option>)}</select></label>
    </div>
    {!serie ? <p role="status">Carregando…</p> : <Ficha ix={ix} dist={dist!} serie={serie} />}
  </section>;
}

function Ficha({ ix, dist, serie }: { ix: IndiceV2; dist: DistV2; serie: SerieV2 }) {
  const m = serie.modelo; const e = serie.erros; const c = m?.coeficientes;
  const usadas = serie.historico.filter(([, v]) => v != null).length;
  const linha = (rotulo: string, valor: ReactNode) => <tr><th scope="row">{rotulo}</th><td>{valor}</td></tr>;
  return <div data-testid="metodologia-motor-v2-ficha">
    <p><b>{ix.estados[serie.estado]?.rotulo ?? serie.estado}</b> — {serie.motivo}</p>
    <div style={{ overflowX: "auto" }} role="region" tabIndex={0} aria-label="Ficha metodológica do Motor V2">
      <table><tbody>
        {linha("Empresa e DIST", `${dist.empresa} · DIST ${dist.dist}${dist.grupo ? ` · grupo ${ix.grupos[dist.grupo] ?? dist.grupo}` : ""}`)}
        {linha("Família, ativo e métrica", `${serie.familia} · ${serie.nome} · ${serie.metrica} (${serie.unidade})${serie.variante ? ` · série ${serie.variante}` : ""}`)}
        {linha("Competências históricas", `${usadas} com valor de ${serie.historico.length}: ${serie.historico.map(([a, v, st]) => `${a} ${fmtV2(v, serie)} (${st})`).join(" · ")}`)}
        {linha("Fonte", `${serie.fonte} · publicação ordinária selecionada no contrato nacional (extraordinárias nunca entram automaticamente)`)}
        {linha("Âncora e horizonte", serie.ancora ? `${serie.ancora}; horizonte real ${serie.horizonte_real ?? "N/D"}` : "N/D")}
        {m && linha("Algoritmo escolhido", `${m.id} (${m.tipo}; escopo ${m.escopo ?? "N/D"}); base ${m.base_da_projecao ?? "N/D"}`)}
        {m && linha("Razão da escolha", m.justificativa ?? "N/D")}
        {m && linha("Equação da projeção", m.mecanismo ?? "N/D")}
        {m && linha("Coeficientes", c?.status === "recuperado_e_verificado"
          ? <>d = {c.intercepto?.toLocaleString("pt-BR", { maximumFractionDigits: 6 })} {c.termos?.map((t) => <span key={t.variavel}> + ({t.coeficiente.toLocaleString("pt-BR", { maximumFractionDigits: 6 })}) × {NOME_FEATURE[t.variavel] ?? t.variavel}</span>)}; passo de um ano d = {c.crescimento_log1p_um_passo?.toLocaleString("pt-BR", { maximumFractionDigits: 6 })}; {c.linhas_treino} linhas de {c.dist_no_pool} DIST no treino. Coeficientes recuperados por reajuste determinístico que reproduz a trajetória armazenada.</>
          : `N/D — ${c?.motivo ?? "sem coeficientes"}`)}
        {linha("Erro retrospectivo do modelo", e ? `MAE ${fmtV2(e.mae, serie)} · RMSE ${fmtV2(e.rmse, serie)} · WAPE ${pctV2(e.wape)} · viés ${fmtV2(e.vies, serie)} · ${e.origens} origem(ns) de teste` : "N/D — sem par de competências comparáveis para medir")}
        {linha("Baselines comparados", serie.baselines ? Object.entries(serie.baselines).map(([b, x]) => `${b}: MAE ${fmtV2(x.mae, serie)}, WAPE ${pctV2(x.wape)}`).join(" · ") : "N/D")}
        {linha("Ganho contra o melhor baseline", serie.ganho_vs_melhor_baseline == null ? "N/D" : `${pctV2(serie.ganho_vs_melhor_baseline, 1)} de MAE (${serie.melhor_baseline_medido})`)}
        {serie.cenarios_meta && linha("Cenários extremos", `${serie.cenarios_meta.regra} Crescimento log1p anual: ${CENARIOS_V2.map((x) => `${x} ${serie.cenarios_meta!.crescimento_log1p[x.toLowerCase()]?.toLocaleString("pt-BR", { maximumFractionDigits: 4 }) ?? "N/D"}`).join(" · ")}; ${serie.cenarios_meta.transicoes_historicas ?? 0} transições comparáveis${serie.cenarios_meta.degenerados ? "; cenários degenerados (coincidem)" : ""}${serie.cenarios_meta.piso_zero ? "; piso zero aplicado" : ""}.`)}
        {linha("Restrições de extrapolação", ehContagemV2(serie) ? "Contagem inteira e não negativa; Conservador ≤ Moderado ≤ Agressivo; horizonte acima de 1 ano sem validação." : "Valor contínuo não negativo; Conservador ≤ Moderado ≤ Agressivo; horizonte acima de 1 ano sem validação.")}
        {linha("Status de homologação", m ? `Não homologado: ${m.motivo_nao_homologado}` : projetada(serie) ? "Não homologado" : "Sem projeção")}
      </tbody></table>
    </div>
  </div>;
}
