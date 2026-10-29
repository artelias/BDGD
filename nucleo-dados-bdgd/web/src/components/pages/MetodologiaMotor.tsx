"use client";
import { useEffect, useMemo, useState } from "react";
import { CENARIOS, ROTULO_CENARIO, ROTULO_ESTADO, parseCenarios, type ProdutoCenarios } from "@/lib/cenarios-motor";
import s from "./metodologia.module.css";
import { MetodologiaEmpresa } from "./MetodologiaEmpresa";

const pct = (n: number | null | undefined) => n == null ? "N/D" : `${(n * 100).toLocaleString("pt-BR", { maximumFractionDigits: 2, minimumFractionDigits: 2 })}%`;

/** Documentação gerada a partir da execução real (cenarios-motor.json): só descreve modelos e variáveis que de fato rodaram. */
export function MetodologiaMotor() {
  const [p, setP] = useState<ProdutoCenarios | null>(null);
  const [erro, setErro] = useState("");
  useEffect(() => {
    const c = new AbortController();
    fetch("/data/previsoes/cenarios-motor.json", { signal: c.signal }).then((r) => { if (!r.ok) throw Error("Produto de cenários indisponível."); return r.json(); })
      .then((j) => setP(parseCenarios(j))).catch((e) => { if (!(e instanceof DOMException && e.name === "AbortError")) setErro(String(e?.message ?? e)); });
    return () => c.abort();
  }, []);
  const resumo = useMemo(() => {
    if (!p) return null;
    const porModelo = new Map<string, { metricas: number; cenarios: Record<string, number>; n: number; melhor: number }>();
    for (const m of p.metricas) for (const [id, e] of Object.entries(m.modelos)) {
      const r = porModelo.get(id) ?? { metricas: 0, cenarios: {}, n: 0, melhor: 0 };
      if (e.n > 0) r.metricas += 1;
      r.n += e.n;
      if (e.wape != null && m.modelos.persistencia?.wape != null && e.wape < m.modelos.persistencia.wape) r.melhor += 1;
      for (const c of CENARIOS) if (m.cenarios[c] === id) r.cenarios[c] = (r.cenarios[c] ?? 0) + 1;
      porModelo.set(id, r);
    }
    const estados = new Map<string, number>();
    for (const m of p.metricas) estados.set(m.estado, (estados.get(m.estado) ?? 0) + 1);
    return { porModelo, estados };
  }, [p]);
  if (erro) return <p role="alert">{erro}</p>;
  if (!p || !resumo) return <p role="status">Carregando a documentação dos modelos executados…</p>;
  const par = p.parametros as Record<string, number | number[]>;
  return <>
    <p>Esta seção é gerada a partir do produto efetivamente publicado em <span className="mono">/data/previsoes/cenarios-motor.json</span> (esquema <span className="mono">{p.schema_version}</span>). Ano-base {p.base}; horizonte {p.horizonte[0]}–{p.horizonte[p.horizonte.length - 1]}; origens de backtest {p.origens_backtest.join(" e ")}. Nenhum modelo é treinado no navegador.</p>
    <MetodologiaEmpresa p={p} />
    <h3>Alvo, amostra e validação</h3>
    <p><b>Alvo:</b> estoque físico anual por distribuidora, ativo e métrica, a partir do contrato nacional (2022–2025). Usa-se apenas o segmento contíguo de observações positivas que termina em {p.base}, cortado em ruptura cadastral; ausências, pendências e zeros não entram no treino e nunca são preenchidos. A projeção exige ao menos três anos comparáveis. Modelos de painel aprendem o log-crescimento anual <code>g(i,t) = ln y(i,t) − ln y(i,t−1)</code> a partir de variáveis observadas em <code>t−1</code>; o alvo é winsorizado nos percentis 5–95 ajustados somente no treino.</p>
    <p><b>Backtest com origem móvel:</b> na origem 2023 o treino usa 2022–2023 e prevê 2024 (h=1) e 2025 (h=2); na origem 2024 usa 2022–2024 e prevê 2025 (h=1). Todos os modelos são avaliados exatamente nos mesmos pontos; um candidato que não prevê todos os pontos fica inelegível. Métricas: <code>WAPE = Σ|ŷ−y| / Σ|y|</code>, MAE, RMSE, viés relativo <code>Σ(ŷ−y)/Σy</code>, MdAPE e estabilidade (diferença do WAPE de h=1 entre as origens). Horizontes de 3 a 5 anos não têm verificação retrospectiva.</p>
    <h3>Seleção dos cenários</h3>
    <ul>
      <li><b>Moderado:</b> menor WAPE entre modelos fisicamente plausíveis (sem valor negativo e com no máximo {pct(par.max_implausivel as number)} das séries fora da razão 2030/2025 de {(par.razao_plausivel_2030_2025 as number[]).map((x) => x.toLocaleString("pt-BR")).join(" a ")}); empate favorece o modelo mais simples.</li>
      <li><b>Conservador / Agressivo:</b> entre os modelos plausíveis com WAPE até {(par.tolerancia_erro as number).toLocaleString("pt-BR")}× o do moderado, o de menor / maior crescimento agregado 2025–2030, desde que difira do moderado em pelo menos {(par.diferenca_minima_pp_ano as number).toLocaleString("pt-BR")} p.p./ano. Sem candidato, o cenário fica <b>indisponível</b>.</li>
      <li>A distância entre cenários reflete modelos diferentes compatíveis com o erro observado; <b>não é intervalo de confiança</b> nem probabilidade.</li>
    </ul>
    <p>Situação das {p.metricas.length} métricas: {[...resumo.estados.entries()].map(([e, n]) => `${ROTULO_ESTADO[e] ?? e}: ${n}`).join(" · ")}.</p>
    <h3>Seleção por métrica</h3>
    <div className={s.scroll} role="region" tabIndex={0} aria-label="Modelo escolhido por cenário e métrica">
      <table className={s.tbl}>
        <thead><tr><th scope="col">Ativo</th><th scope="col">Métrica</th><th scope="col">Situação</th>{CENARIOS.map((c) => <th scope="col" key={c}>{ROTULO_CENARIO[c]}</th>)}<th scope="col">WAPE moderado</th><th scope="col">WAPE persistência</th><th scope="col">Pontos</th></tr></thead>
        <tbody>{[...p.metricas].sort((a, b) => a.ativo.localeCompare(b.ativo, "pt-BR") || a.metrica.localeCompare(b.metrica)).map((m) => {
          const mod = m.cenarios.moderado ? m.modelos[m.cenarios.moderado] : null;
          return <tr key={`${m.conceito}|${m.metrica}`}><th scope="row">{m.ativo}</th><td>{m.metrica}{m.experimental ? " (experimental)" : ""}</td><td>{ROTULO_ESTADO[m.estado] ?? m.estado}</td>
            {CENARIOS.map((c) => <td key={c} title={m.justificativas[c]}>{m.cenarios[c] ? p.modelos[m.cenarios[c]!]?.nome ?? m.cenarios[c] : "Indisponível"}</td>)}
            <td>{pct(mod?.wape)}</td><td>{pct(m.modelos.persistencia?.wape)}</td><td>{mod?.n ?? 0}</td></tr>;
        })}</tbody>
      </table>
    </div>
    <h3>Modelos executados</h3>
    <div className={s.scroll} role="region" tabIndex={0} aria-label="Modelos executados">
      <table className={s.tbl}>
        <thead><tr><th scope="col">Modelo</th><th scope="col">Família</th><th scope="col">Formulação implementada</th><th scope="col">Métricas avaliadas</th><th scope="col">Pontos de backtest</th><th scope="col">Melhor que persistência</th><th scope="col">Selecionado como</th></tr></thead>
        <tbody>{Object.entries(p.modelos).map(([id, m]) => {
          const r = resumo.porModelo.get(id);
          return <tr key={id}><th scope="row">{m.nome}<br /><span className="mono">{id}</span></th><td>{m.familia}</td><td><code>{m.formula}</code></td>
            <td>{r?.metricas ?? 0}</td><td>{(r?.n ?? 0).toLocaleString("pt-BR")}</td><td>{id === "persistencia" ? "referência" : `${r?.melhor ?? 0} métricas`}</td>
            <td>{CENARIOS.map((c) => r?.cenarios[c] ? `${ROTULO_CENARIO[c]} (${r.cenarios[c]})` : "").filter(Boolean).join(", ") || "—"}</td></tr>;
        })}</tbody>
      </table>
    </div>
    <p className="caption">Implementação: Python com scikit-learn 1.8.0 (Ridge α=1; KNeighborsRegressor k=9 com mediana dos vizinhos; RandomForestRegressor; HistGradientBoostingRegressor), imputação pela mediana e padronização ajustadas só no treino de cada origem. Não foram executados Lasso, Elastic Net e Poisson: na formulação em log-crescimento Lasso/Elastic Net são redundantes com o Ridge com tão poucas variáveis, e o Poisson exige alvo de contagem por período (fluxo), não estoque. Redes neurais não foram usadas.</p>
    <h3>Variáveis internas e externas</h3>
    <div className={s.scroll} role="region" tabIndex={0} aria-label="Variáveis do motor">
      <table className={s.tbl}>
        <thead><tr><th scope="col">Variável</th><th scope="col">Interna / externa</th><th scope="col">Fonte</th><th scope="col">Disponível em</th><th scope="col">Disponível?</th><th scope="col">Utilizada?</th><th scope="col">Modelo</th></tr></thead>
        <tbody>{p.variaveis.map((v) => <tr key={v.variavel}><th scope="row"><span className="mono">{v.variavel}</span>{v.transformacao && <><br /><span className="caption">{v.transformacao}</span></>}</th>
          <td>{v.tipo}</td><td>{v.fonte}</td><td>{v.disponivel_em}</td><td>{v.disponivel}</td><td>{v.utilizada}</td><td>{v.modelos_que_usaram.replaceAll("|", ", ") || "—"}</td></tr>)}</tbody>
      </table>
    </div>
    <p>As variáveis externas do IBGE são municipais e foram associadas a cada distribuidora pela participação das unidades consumidoras ativas por município (atributo <span className="mono">MUN</span> da própria UC no ano), sem proximidade espacial. Só entram variáveis divulgadas antes da primeira origem de backtest (31/12/2023), de modo que nenhuma origem usa informação posterior. Resultados por métrica, distribuidora e cenário, com erros e justificativas, estão na página <a href="/previsoes/">Previsões</a>.</p>
  </>;
}
