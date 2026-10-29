"use client";
import { useMemo, useState } from "react";
import {
  CENARIOS, ROTULO_CENARIO, ROTULO_ESTADO,
  type Cenario, type MetricaCenario, type ProdutoCenarios,
} from "@/lib/cenarios-motor";
import s from "./metodologia.module.css";

const pct = (v: number | null | undefined) =>
  v == null ? "N/D" : `${(100 * v).toLocaleString("pt-BR", { maximumFractionDigits: 2, minimumFractionDigits: 2 })}%`;
const numero = (v: number | null | undefined, unidade: string) =>
  v == null ? "N/D" : v.toLocaleString("pt-BR", { maximumFractionDigits: unidade === "itens" ? 0 : 2 });
const modelosSemFeatures = new Set(["persistencia", "deriva", "tendencia_ols", "crescimento_geometrico"]);

function variaveisDoModelo(p: ProdutoCenarios, modeloId: string | null): ProdutoCenarios["variaveis"] {
  if (!modeloId || modelosSemFeatures.has(modeloId)) return [];
  return p.variaveis.filter((v) => v.utilizada === "sim" && v.modelos_que_usaram.split("|").includes(modeloId));
}

/** Transparência por concessionária: métricas e modelos provenientes do MESMO contrato publicado.
 * WAPE é do painel de backtest; erro_moderado é um diagnóstico desta DIST, não intervalo de confiança. */
export function MetodologiaEmpresa({ p }: { p: ProdutoCenarios }) {
  const empresas = useMemo(() => Object.entries(p.empresas).sort((a, b) => a[1].localeCompare(b[1], "pt-BR")), [p.empresas]);
  const [dQ, setDist] = useState("6600");
  const dist = p.empresas[dQ] ? dQ : empresas[0]?.[0] ?? "";
  const metricas = useMemo(
    () => [...p.metricas].sort((a, b) => a.familia.localeCompare(b.familia, "pt-BR") || a.ativo.localeCompare(b.ativo, "pt-BR") || a.metrica.localeCompare(b.metrica)),
    [p.metricas],
  );
  const [q, setQ] = useState("trafo_dist|quantidade");
  const [cen, setCen] = useState<Cenario>("moderado");
  const selecionada = metricas.find((m) => `${m.conceito}|${m.metrica}` === q) ?? metricas[0];
  const serie = selecionada?.series[dist] ?? null;
  const atualId = selecionada?.cenarios[cen] ?? null;
  const modelo = atualId ? p.modelos[atualId] : null;
  const erro = atualId ? selecionada?.modelos[atualId] : null;
  const vars = variaveisDoModelo(p, atualId);
  const historico = serie?.hist ?? [];
  const base = historico.find((x) => x[0] === p.base)?.[1] ?? null;
  const ultimo = serie?.[cen]?.at(-1) ?? null;
  const salto = base && ultimo != null ? ultimo / base : null;
  const instavel = salto != null && (salto > 3 || salto < 0.5);
  const limites = selecionada?.experimental || historico.length < 4 || instavel;

  if (!selecionada) return null;

  return (
    <section aria-labelledby="modelos-por-empresa" data-testid="metodologia-por-empresa">
      <h3 id="modelos-por-empresa">Auditoria de modelos por distribuidora</h3>
      <p>Escolha uma distribuidora, uma métrica e um cenário para conferir os valores efetivamente calculados, a equação, as variáveis e a evidência retrospectiva. A seleção dos algoritmos foi feita por <b>métrica no painel de distribuidoras</b>, não treinando um algoritmo inteiramente diferente para cada empresa. As trajetórias e os diagnósticos individuais mudam conforme a empresa.</p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 12, marginBottom: 16 }}>
        <label>Distribuidora
          <select value={dist} onChange={(e) => setDist(e.target.value)} aria-label="Selecionar distribuidora da metodologia"
            style={{ display: "block", width: "100%", padding: 10, marginTop: 6 }}>
            {empresas.map(([id, nome]) => <option key={id} value={id}>{nome} · DIST {id}</option>)}
          </select>
        </label>
        <label>Ativo e métrica
          <select value={`${selecionada.conceito}|${selecionada.metrica}`} onChange={(e) => setQ(e.target.value)} aria-label="Selecionar ativo e métrica da metodologia"
            style={{ display: "block", width: "100%", padding: 10, marginTop: 6 }}>
            {metricas.map((m) => <option key={`${m.conceito}|${m.metrica}`} value={`${m.conceito}|${m.metrica}`}>
              {m.ativo} · {m.metrica} ({m.unidade}){m.experimental ? " · experimental" : ""}
            </option>)}
          </select>
        </label>
        <label>Cenário
          <select value={cen} onChange={(e) => setCen(e.target.value as Cenario)} aria-label="Selecionar cenário da metodologia"
            style={{ display: "block", width: "100%", padding: 10, marginTop: 6 }}>
            {CENARIOS.map((c) => <option key={c} value={c}>{ROTULO_CENARIO[c]}{!selecionada.cenarios[c] ? " — indisponível" : ""}</option>)}
          </select>
        </label>
      </div>

      <p><b>{p.empresas[dist]} · DIST {dist}</b> — {selecionada.ativo} ({selecionada.unidade}). Situação: {ROTULO_ESTADO[selecionada.estado] ?? selecionada.estado}{selecionada.experimental ? "; métrica experimental" : ""}.</p>
      <div className={s.scroll} role="region" tabIndex={0} aria-label="Modelos selecionados por cenário nesta métrica">
        <table className={s.tbl}>
          <thead><tr><th>Cenário</th><th>Modelo aplicado</th><th>WAPE no painel (h=1 e h=2)</th><th>Quantidade de avaliações</th><th>Decisão</th></tr></thead>
          <tbody>{CENARIOS.map((c) => {
            const id = selecionada.cenarios[c];
            const e = id ? selecionada.modelos[id] : null;
            return <tr key={c}><th scope="row">{ROTULO_CENARIO[c]}</th><td>{id ? p.modelos[id]?.nome ?? id : "Indisponível"}</td>
              <td>{pct(e?.wape)}</td><td>{e?.n ?? 0}</td><td>{selecionada.justificativas[c]}</td></tr>;
          })}</tbody>
        </table>
      </div>

      {modelo && erro ? <>
        <h4>Função aplicada — {modelo.nome}</h4>
        <p><code>{modelo.formula}</code></p>
        <p>Família: {modelo.familia}. Parâmetros de implementação e tratamento de entradas são documentados no catálogo do motor. {atualId === "ridge_painel_ext" || atualId === "ridge_painel" ? "Ridge utiliza regularização L2 (α=1) sobre variáveis transformadas/padronizadas. O produto atual não exporta os coeficientes β e o intercepto estimados por métrica; por isso não permite reproduzir a equação numérica a partir da interface." : atualId === "knn_analogos" ? "KNN usa 9 vizinhos em espaço de atributos padronizado e a mediana dos crescimentos. O produto não publica a lista e distância dos vizinhos selecionados para cada empresa." : atualId === "random_forest_painel" || atualId === "hgb_painel" ? "Modelos de árvores não têm um único coeficiente linear interpretável. A versão atual não exporta atribuições locais ou importâncias por variável para cada empresa." : "O modelo usa somente o histórico da própria série e o tempo, sem coeficientes externos de regressão em painel."}</p>
        <h4>Variáveis efetivamente usadas pelo modelo</h4>
        {vars.length ? <div className={s.scroll} role="region" tabIndex={0} aria-label="Features efetivas do modelo">
          <table className={s.tbl}><thead><tr><th>Variável</th><th>Tipo</th><th>Transformação</th><th>Fonte</th><th>Disponibilidade</th></tr></thead>
            <tbody>{vars.map((v) => <tr key={v.variavel}><th scope="row">{v.variavel}</th><td>{v.tipo}</td><td>{v.transformacao}</td><td>{v.fonte}</td><td>{v.disponivel_em}</td></tr>)}</tbody></table>
        </div> : <p>Modelo univariado: utiliza o estoque histórico e a posição temporal, sem variáveis exógenas.</p>}
        <h4>Evidência de erro e limites de confiança</h4>
        <dl>
          <div className={s.rule}><dt>WAPE do painel de validação</dt><dd>{pct(erro.wape)} · {erro.n} pares de avaliação de diferentes distribuidoras e origens; h=1: {pct(erro.wape_h1)}; h=2: {pct(erro.wape_h2)}.</dd></div>
          <div className={s.rule}><dt>MAE e RMSE da métrica</dt><dd>{numero(erro.mae, selecionada.unidade)} e {numero(erro.rmse, selecionada.unidade)} {selecionada.unidade}, respectivamente; calculados no painel, não como erro garantido desta distribuidora.</dd></div>
          <div className={s.rule}><dt>Viés relativo e estabilidade</dt><dd>{pct(erro.vies)} de viés relativo; diferença de WAPE h=1 entre origens: {pct(erro.estabilidade)}.</dd></div>
          <div className={s.rule}><dt>Diagnóstico individual da distribuidora</dt><dd>{cen === "moderado" && serie?.erro_moderado != null ? `Erro percentual retrospectivo mediano da DIST: ${pct(serie.erro_moderado)}.` : "Não há erro individual neste produto para este cenário; apenas para o moderado, quando disponível."} Este valor não é probabilidade nem intervalo de confiança.</dd></div>
          <div className={s.rule}><dt>Confiança estatística da previsão</dt><dd><b>Não estimada.</b> Não há intervalo preditivo calibrado de 80%, 90% ou 95%, nem distribuição de erros por empresa e horizonte suficiente para atribuir probabilidade à projeção. Os dados de 2022–2025 oferecem validação retrospectiva apenas até h=2.</dd></div>
        </dl>
        {limites && <p role="note"><b>Ressalva adicional:</b> {selecionada.experimental ? "A potência desta métrica é experimental. " : ""}{historico.length < 4 ? "O histórico desta empresa contém menos de quatro observações elegíveis. " : ""}{instavel ? "A trajetória 2030/2025 está fora do intervalo ilustrativo de 0,5 a 3 vezes e precisa de auditoria específica. " : ""}Não interpretar a simulação como plano de investimentos.</p>}
      </> : <p role="status">Não há modelo elegível para este cenário. Nenhum coeficiente, resultado ou intervalo de confiança foi imputado.</p>}

      <h4>Histórico e projeção publicados para a distribuidora</h4>
      <div className={s.scroll} role="region" tabIndex={0} aria-label="Histórico e projeções individuais">
        <table className={s.tbl}><thead><tr><th>Ano</th><th>Observado</th>{CENARIOS.map((c) => <th key={c}>{ROTULO_CENARIO[c]}</th>)}</tr></thead>
          <tbody>{[...Array.from({ length: 4 }, (_, i) => 2022 + i), ...p.horizonte].map((ano) => {
            const v = historico.find((x) => x[0] === ano)?.[1] ?? null;
            const i = p.horizonte.indexOf(ano);
            return <tr key={ano}><th scope="row">{ano}</th><td>{i < 0 ? numero(v, selecionada.unidade) : "—"}</td>
              {CENARIOS.map((c) => <td key={c}>{i < 0 ? "—" : numero(serie?.[c]?.[i], selecionada.unidade)}</td>)}</tr>;
          })}</tbody>
        </table>
      </div>
      <p className="caption">Fonte dos valores: produto estático cenarios-motor.json e contrato anual BDGD. O histórico observado pode ter anos indisponíveis. Modelos e variáveis são globais por métrica; projeções são individuais por distribuidora.</p>
      <h4>Variáveis externas ainda não integradas</h4>
      <p><b>SAMP/mercado ANEEL, DEC/FEC, EPE e IPEA:</b> não há evidência no contrato atual de que essas séries tenham sido associadas por distribuidora, competência e data de disponibilidade, com um backtest sem vazamento temporal. Isso significa <b>não integradas neste release</b>, e não que as fontes sejam inadequadas ou inexistentes. O IPEA nem sequer consta no inventário de 15 variáveis do produto; as demais constam como não utilizadas. Incorporá-las requer ETL, compatibilização geográfica e comparação fora da amostra.</p>
    </section>
  );
}
