"use client";
import { Info } from "lucide-react";
import { useMemo } from "react";
import { EmptyState, LoadingBlock } from "@/components/ui/Feedback";
import { Segmented } from "@/components/ui/Segmented";
import { Pill } from "@/components/ui/Value";
import { NOME_IND, fmtInd } from "@/lib/confiabilidade/calculo";
import { useFatores } from "@/lib/confiabilidade/dados";
import type { EstadoConf } from "@/lib/confiabilidade/estado";
import type { Indice } from "@/lib/confiabilidade/tipos";
import s from "./conf.module.css";

const ROT_VEREDITO = { COMPATIVEL: "compatível com os dados", NAO_SUSTENTADA: "não sustentada", INCONCLUSIVA: "inconclusiva", SEM_DADOS: "sem dados" } as const;
const f2 = (v: number | null | undefined) => (v === null || v === undefined ? "N/D" : `${v > 0 ? "+" : ""}${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);

/** Coeficiente com intervalo de 95% num eixo fixo de −1 a +1 (SVG; texto ao lado traz os números). */
function Intervalo({ v, ic, lim = 1 }: { v: number | null; ic: [number, number] | null; lim?: number }) {
  if (v === null) return <span className="faint">N/D</span>;
  const x = (z: number) => 60 + (Math.max(-lim, Math.min(lim, z)) / lim) * 56;
  const cruza = ic ? ic[0] <= 0 && ic[1] >= 0 : true;
  return (
    <svg width={120} height={16} role="img" aria-label={`${f2(v)}${ic ? `, intervalo de 95% de ${f2(ic[0])} a ${f2(ic[1])}` : ""}`} style={{ verticalAlign: "middle" }}>
      <line x1={60} x2={60} y1={1} y2={15} stroke="var(--hairline-strong)" />
      {ic && <line x1={x(ic[0])} x2={x(ic[1])} y1={8} y2={8} stroke={cruza ? "var(--text-3)" : "var(--text)"} strokeWidth={2} strokeLinecap="round" />}
      <circle cx={x(v)} cy={8} r={4} fill={cruza ? "var(--text-3)" : "var(--accent)"} stroke="var(--surface)" strokeWidth={1.5} />
    </svg>
  );
}

export function Fatores({ indice, e }: { indice: Indice; e: EstadoConf }) {
  const f = useFatores();
  const met = useMemo(() => new Map(indice.metricas.map((m) => [m.id, m])), [indice]);
  const nome = (id: string) => met.get(id)?.nome ?? id;
  if (f.carregando) return <LoadingBlock label="Carregando o estudo estatístico" />;
  if (f.erro || !f.dados) return <EmptyState title="Estudo estatístico ainda não publicado">O arquivo de fatores associados não está neste pacote. As telas de exploração funcionam sem ele; nenhum coeficiente é exibido sem execução real do estudo.</EmptyState>;
  const d = f.dados;
  const alvo = d.alvos.find((a) => a.alvo === e.ind);
  const I = NOME_IND[e.ind];
  const distSel = e.dist !== null ? indice.distribuidoras.find((x) => x.dist === e.dist) ?? null : null;
  const ref = (d.referencias ?? (d.referencia ? [d.referencia] : [])).find((r) => r.alvo === e.ind) ?? null;
  const ix = ref ? new Map(ref.campos.map((c, i) => [c, i])) : null;
  const linhasRef = ref && ix && distSel ? ref.linhas.filter((r) => r[ix.get("dist")!] === distSel.dist).sort((a, b) => ((b[ix.get("residuo")!] as number) ?? 0) - ((a[ix.get("residuo")!] as number) ?? 0)) : [];

  return (
    <>
      <div className={s.filtros} role="toolbar" aria-label="Indicador do estudo">
        <Segmented label="Indicador" value={e.ind} onChange={(v) => e.set({ ind: v === "dec" ? null : v })} options={[{ value: "dec", label: "DEC" }, { value: "fec", label: "FEC" }]} />
        <Pill tone="nd" title="Estudo observacional com dados já publicados; sem validação externa">exploratório · associação não é causa</Pill>
      </div>
      <div className={s.bloco}>
        <p className={s.blocoTitulo}>O que este estudo é</p>
        <p className={s.blocoSub} style={{ marginBottom: 0 }}>{d.metodo}</p>
        <div className={s.kpis}>
          <div className={s.kpi}><div className={s.kpiRotulo}>Conjunto-anos na amostra</div><div className={s.kpiValor} data-testid="conf-fat-n">{d.amostra.conjunto_anos.toLocaleString("pt-BR")}</div></div>
          <div className={s.kpi}><div className={s.kpiRotulo}>Conjuntos</div><div className={s.kpiValor}>{d.amostra.conjuntos.toLocaleString("pt-BR")}</div></div>
          <div className={s.kpi}><div className={s.kpiRotulo}>Distribuidoras</div><div className={s.kpiValor}>{d.amostra.distribuidoras}</div></div>
          <div className={s.kpi}><div className={s.kpiRotulo}>Anos</div><div className={s.kpiValor}>{d.amostra.anos.join(", ")}</div></div>
        </div>
      </div>

      <div className={s.secaoTopo} style={{ marginTop: 22 }}><h3 className="headline">Hipóteses</h3></div>
      <div className={`${s.bloco} ${s.rolagem}`}>
        <table className={s.tabela} data-testid="conf-hipoteses">
          <thead><tr><th scope="col">Hipótese</th><th scope="col" style={{ textAlign: "left" }}>Leitura</th><th scope="col" style={{ textAlign: "left" }}>Evidência</th></tr></thead>
          <tbody>{d.hipoteses.map((h) => (
            <tr key={h.id}><td style={{ maxWidth: 330 }}><b>{h.id}</b> · {h.enunciado}</td><td style={{ textAlign: "left" }}><span className={`${s.veredito} ${s[`v_${h.veredito}`]}`}>{ROT_VEREDITO[h.veredito]}</span></td><td style={{ textAlign: "left", maxWidth: 520, whiteSpace: "normal" }}>{h.evidencia}</td></tr>))}</tbody>
        </table>
        <p className={s.nota}><Info size={13} aria-hidden />“Compatível com os dados” significa que a associação tem o sinal esperado e intervalo de 95% que não inclui zero, também depois de controlar o contexto e dentro das distribuidoras. Não prova a hipótese nem indica o efeito de uma intervenção.</p>
      </div>

      {!alvo ? <EmptyState title={`Sem resultados para ${I}`}>A amostra não foi suficiente para este indicador.</EmptyState> : <>
        <div className={s.secaoTopo} style={{ marginTop: 22 }}><h3 className="headline">Associações com o {I} anual</h3></div>
        <div className={`${s.bloco} ${s.rolagem}`}>
          <p className={s.blocoSub}>Correlação de postos (Spearman) entre cada característica e o {I} do conjunto. <b>Bruta</b>: todos os conjunto-anos. <b>Parcial</b>: depois de retirar o que é explicado por porte, densidade, ruralidade e consumo por consumidor. <b>Dentro da distribuidora</b>: desvios em relação à média da distribuidora no ano. Intervalos de 95% por reamostragem de distribuidoras inteiras.</p>
          <table className={s.tabela} data-testid="conf-associacoes">
            <thead><tr><th scope="col">Característica</th><th scope="col">n</th><th scope="col" style={{ textAlign: "left" }}>Bruta</th><th scope="col" style={{ textAlign: "left" }}>Parcial (contexto)</th><th scope="col" style={{ textAlign: "left" }}>Dentro da distribuidora</th><th scope="col">Mesmo sinal nos 4 anos</th></tr></thead>
            <tbody>{[...alvo.associacoes].sort((a, b) => Math.abs(b.parcial ?? 0) - Math.abs(a.parcial ?? 0)).map((a) => (
              <tr key={a.variavel} title={met.get(a.variavel)?.definicao}>
                <td>{nome(a.variavel)}</td><td>{a.n.toLocaleString("pt-BR")}</td>
                <td style={{ textAlign: "left" }}><Intervalo v={a.spearman} ic={a.ic95} /> {f2(a.spearman)}</td>
                <td style={{ textAlign: "left" }}><Intervalo v={a.parcial} ic={a.parcial_ic95} /> {f2(a.parcial)}</td>
                <td style={{ textAlign: "left" }}><Intervalo v={a.dentro_dist} ic={a.dentro_dist_ic95} /> {f2(a.dentro_dist)}</td>
                <td>{a.estavel_por_ano === null ? "N/D" : a.estavel_por_ano ? "sim" : "não"}</td>
              </tr>))}</tbody>
          </table>
          <p className={s.nota}><Info size={13} aria-hidden />Escala de −1 a +1. Positivo: conjuntos com mais dessa característica tendem a ter {I} maior. Ponto cinza: o intervalo inclui zero.</p>
        </div>

        <div className={s.duas} style={{ marginTop: 16 }}>
          <div className={`${s.bloco} ${s.rolagem}`}>
            <p className={s.blocoTitulo}>Capacidade de explicar o {I} fora da amostra</p>
            <p className={s.blocoSub}>Validação cruzada por distribuidora: o modelo é avaliado em distribuidoras que não viu. Alvo em logaritmo.</p>
            <table className={s.tabela} data-testid="conf-modelos">
              <thead><tr><th scope="col">Modelo</th><th scope="col">R² fora da amostra</th><th scope="col">Erro absoluto médio (log)</th><th scope="col">n</th></tr></thead>
              <tbody>{alvo.modelos.map((m) => <tr key={m.modelo} title={m.nota}><td>{m.modelo}</td><td>{m.r2_fora === null ? "N/D" : m.r2_fora.toLocaleString("pt-BR", { maximumFractionDigits: 3 })}</td><td>{m.mae_fora === null ? "N/D" : m.mae_fora.toLocaleString("pt-BR", { maximumFractionDigits: 3 })}</td><td>{m.n.toLocaleString("pt-BR")}</td></tr>)}</tbody>
            </table>
            <p className={s.nota}><Info size={13} aria-hidden />R² baixo fora da amostra indica que a infraestrutura cadastrada explica pouco das diferenças entre distribuidoras: clima, vegetação, operação e manutenção não estão nos dados.</p>
          </div>
          <div className={`${s.bloco} ${s.rolagem}`}>
            <p className={s.blocoTitulo}>Regressão regularizada (coeficientes padronizados)</p>
            <p className={s.blocoSub}>Efeito de um desvio-padrão da característica sobre o log do {I}, mantidas as demais; inclui efeito fixo de ano. Intervalos por reamostragem de distribuidoras.</p>
            <table className={s.tabela}>
              <thead><tr><th scope="col">Característica</th><th scope="col" style={{ textAlign: "left" }}>Coeficiente (IC 95%)</th></tr></thead>
              <tbody>{[...alvo.coeficientes].sort((a, b) => Math.abs(b.beta) - Math.abs(a.beta)).map((c) => <tr key={c.variavel}><td>{nome(c.variavel)}</td><td style={{ textAlign: "left" }}><Intervalo v={c.beta} ic={c.ic95} lim={0.5} /> {f2(c.beta)} <span className="faint">[{f2(c.ic95[0])}; {f2(c.ic95[1])}]</span></td></tr>)}</tbody>
            </table>
          </div>
        </div>

        <div className={s.duas} style={{ marginTop: 16 }}>
          <div className={`${s.bloco} ${s.rolagem}`}>
            <p className={s.blocoTitulo}>Importância por permutação (floresta aleatória)</p>
            <p className={s.blocoSub}>Queda do R² fora da amostra quando a característica é embaralhada. Mede uso pelo modelo, não efeito físico; características correlacionadas dividem a importância.</p>
            <table className={s.tabela}>
              <thead><tr><th scope="col">Característica</th><th scope="col" style={{ textAlign: "left" }}>Importância</th></tr></thead>
              <tbody>{alvo.importancias.slice(0, 12).map((i) => { const mx = Math.max(...alvo.importancias.map((x) => x.importancia), 1e-9); return <tr key={i.variavel}><td>{nome(i.variavel)}</td><td style={{ textAlign: "left" }}><span className={s.barra} style={{ width: `${Math.max(1, Math.round((90 * Math.max(0, i.importancia)) / mx))}px` }} aria-hidden /> {i.importancia.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} <span className="faint">± {i.desvio.toLocaleString("pt-BR", { maximumFractionDigits: 3 })}</span></td></tr>; })}</tbody>
            </table>
          </div>
          <div className={`${s.bloco} ${s.rolagem}`}>
            <p className={s.blocoTitulo}>Mudança da infraestrutura × mudança do {I} (2022 → 2025)</p>
            <p className={s.blocoSub}>Correlação entre a variação de cada característica e a variação do {I} no mesmo conjunto, só em conjuntos sem alerta de reconfiguração cadastral.</p>
            {alvo.variacao.length ? (
              <table className={s.tabela} data-testid="conf-variacao">
                <thead><tr><th scope="col">Variação de</th><th scope="col">n</th><th scope="col" style={{ textAlign: "left" }}>Spearman (IC 95%)</th></tr></thead>
                <tbody>{alvo.variacao.map((v) => <tr key={v.variavel}><td>{nome(v.variavel)}</td><td>{v.n.toLocaleString("pt-BR")}</td><td style={{ textAlign: "left" }}><Intervalo v={v.spearman} ic={v.ic95} /> {f2(v.spearman)}</td></tr>)}</tbody>
              </table>
            ) : <span className="faint">Amostra insuficiente para a análise de variações.</span>}
          </div>
        </div>

        <div className={s.secaoTopo} style={{ marginTop: 22 }}><h3 className="headline">Distância à referência ajustada por contexto{distSel ? ` · ${distSel.nome}` : ""}</h3></div>
        <div className={`${s.bloco} ${s.rolagem}`}>
          {!ref ? <span className="faint">Referência não calculada para {I}.</span> : !distSel ? <EmptyState title="Escolha uma distribuidora">Selecione a distribuidora na aba Mapa e conjuntos ou em Benchmarking para ver os conjuntos dela contra a referência.</EmptyState> : !linhasRef.length ? <span className="faint">Sem conjuntos desta distribuidora na referência.</span> : <>
            <p className={s.blocoSub}>Referência = {I} previsto para o conjunto por um modelo treinado nas OUTRAS distribuidoras, só com variáveis de contexto ({ref.modelo}; R² fora da amostra {ref.r2_fora?.toLocaleString("pt-BR", { maximumFractionDigits: 2 }) ?? "N/D"}), ano {ref.ano}. A faixa é o intervalo de 80% dos erros fora da amostra. Não é limite regulatório nem meta.</p>
            <table className={s.tabela} data-testid="conf-referencia">
              <thead><tr><th scope="col">Conjunto</th><th scope="col">{I} apurado</th><th scope="col">Referência</th><th scope="col">Faixa de 80%</th><th scope="col">Apurado − referência</th><th scope="col">Leitura</th></tr></thead>
              <tbody>{linhasRef.map((r) => { const g = (c: string) => r[ix!.get(c)!] as number | null; const fora = g("obs") !== null && g("lo") !== null && g("hi") !== null ? (g("obs")! > g("hi")! ? "acima da faixa" : g("obs")! < g("lo")! ? "abaixo da faixa" : "dentro da faixa") : "N/D"; return (
                <tr key={String(g("c"))} style={{ cursor: "pointer" }} onClick={() => e.set({ aba: "mapa", dist: distSel.dist, conj: g("c") }, true)}>
                  <td>{String(r[ix!.get("n")!] ?? g("c"))}</td><td>{fmtInd(g("obs"))}</td><td>{fmtInd(g("ref"))}</td><td>{fmtInd(g("lo"))} – {fmtInd(g("hi"))}</td><td>{f2(g("residuo"))}</td><td className={fora === "acima da faixa" ? s.acima : fora === "abaixo da faixa" ? s.dentro : "faint"}>{fora}</td>
                </tr>); })}</tbody>
            </table>
          </>}
        </div>
      </>}

      <div className={s.bloco} style={{ marginTop: 16 }}>
        <p className={s.blocoTitulo}>Limitações</p>
        <ul className={s.frases}>{d.limitacoes.map((l) => <li key={l}>{l}</li>)}</ul>
      </div>
    </>
  );
}
