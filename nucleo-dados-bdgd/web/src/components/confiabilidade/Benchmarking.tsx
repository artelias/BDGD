"use client";
import { Info } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { DataError, EmptyState, LoadingBlock } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { CRITERIOS_PADRAO, NOME_IND, UNIDADE_IND, chave, escalas, fmtInd, fmtMetrica, linhasNacionais, num, paresSemelhantes, percentilDe, perfilPorQuartil, ranking, razaoLimite, resumo, temInfra, type Linha, type TipoRanking } from "@/lib/confiabilidade/calculo";
import { useNacional } from "@/lib/confiabilidade/dados";
import type { EstadoConf } from "@/lib/confiabilidade/estado";
import { dispersao, type Ponto } from "@/lib/confiabilidade/graficos";
import type { Indice } from "@/lib/confiabilidade/tipos";
import s from "./conf.module.css";

type Escopo = "brasil" | "grupo" | "dist";
type TipoRank = TipoRanking | "pares";
const PERFIL = ["uc", "uc_por_km2", "pct_uc_rural", "mwh_por_uc", "km_mt_por_mil_uc", "km_mt_por_alim", "uc_por_alim", "conc_uc_top1", "pct_km_mt_tri", "uc_por_trafo", "sec_por_100km", "relig_por_100km", "tlcd_por_100km", "na_por_100km"];
const EIXOS_X = ["km_mt_por_mil_uc", "uc_por_km2", "pct_uc_rural", "uc_por_alim", "km_mt_por_alim", "relig_por_100km", "tlcd_por_100km", "sec_por_100km", "uc_por_trafo", "conc_uc_top1", "mwh_por_uc", "uc"];
const LOG_X = new Set(["km_mt_por_mil_uc", "uc_por_km2", "uc_por_alim", "km_mt_por_alim", "uc_por_trafo", "mwh_por_uc", "uc", "sec_por_100km"]);

export function Benchmarking({ indice, e }: { indice: Indice; e: EstadoConf }) {
  const [eixoX, setEixoX] = useState("km_mt_por_mil_uc");
  const [tipo, setTipo] = useState<TipoRank>("piores");
  const atual = useNacional(e.ano), anterior = useNacional(indice.anos.includes(e.ano - 1) ? e.ano - 1 : null);
  const I = NOME_IND[e.ind];
  const distSel = e.dist !== null ? indice.distribuidoras.find((d) => d.dist === e.dist) ?? null : null;
  const grupoSel = e.grupo ?? null;
  const escopo: Escopo = distSel ? "dist" : grupoSel ? "grupo" : "brasil";
  const nomeDist = useMemo(() => new Map(indice.distribuidoras.map((d) => [d.dist, d])), [indice]);
  const met = useMemo(() => new Map(indice.metricas.map((m) => [m.id, m])), [indice]);

  const todas = useMemo(() => (atual.dados ? linhasNacionais(atual.dados) : []), [atual.dados]);
  const ant = useMemo(() => (anterior.dados ? linhasNacionais(anterior.dados) : null), [anterior.dados]);
  const noEscopo = useCallback((l: Linha) => (escopo === "dist" ? l.dist === distSel!.dist : escopo === "grupo" ? nomeDist.get(l.dist)?.grupo === grupoSel : true), [escopo, distSel, grupoSel, nomeDist]);
  const universo = useMemo(() => todas.filter(noEscopo), [todas, noEscopo]);
  const res = useMemo(() => resumo(universo.map((l) => l[e.ind])), [universo, e.ind]);
  const esc = useMemo(() => escalas(todas), [todas]);

  const alvo = useMemo(() => (e.dist !== null && e.conj !== null ? todas.find((l) => l.dist === e.dist && l.c === e.conj) ?? null : null), [todas, e.dist, e.conj]);
  const pares = useMemo(() => (alvo ? paresSemelhantes(alvo, todas.filter((l) => l.dist !== alvo.dist), 20, CRITERIOS_PADRAO, esc) : null), [alvo, todas, esc]);
  const resPares = useMemo(() => (pares ? resumo(pares.pares.map((p) => p.linha[e.ind])) : null), [pares, e.ind]);
  const perfil = useMemo(() => perfilPorQuartil(universo.filter(temInfra), e.ind, PERFIL), [universo, e.ind]);

  // desempenho relativo aos pares: apurado − mediana dos 20 conjuntos mais semelhantes de OUTRAS distribuidoras
  const relativo = useMemo(() => {
    if (tipo !== "pares") return null;
    const base = todas.filter(temInfra);
    return universo.filter(temInfra).filter((l) => num(l[e.ind])).map((l) => {
      const p = paresSemelhantes(l, base.filter((x) => x.dist !== l.dist), 20, CRITERIOS_PADRAO, esc).pares;
      const med = resumo(p.map((x) => x.linha[e.ind]))?.mediana ?? null;
      return med === null || p.length < 10 ? null : { linha: l, valor: (l[e.ind] as number) - med, anterior: med };
    }).filter((x): x is { linha: Linha; valor: number; anterior: number } => x !== null).sort((a, b) => a.valor - b.valor).slice(0, 15);
  }, [tipo, todas, universo, e.ind, esc]);
  const lista = tipo === "pares" ? relativo ?? [] : ranking(universo, ant, e.ind, tipo, 15);

  const mx = met.get(eixoX);
  const gDisp = useCallback((t: ChartTokens) => {
    const ponto = (l: Linha): Ponto | null => { const x = l.infra[eixoX], y = l[e.ind]; return num(x) && num(y) && (!LOG_X.has(eixoX) || x > 0) ? [x, y, `${l.n} · ${nomeDist.get(l.dist)?.sigla ?? l.dist}`] : null; };
    const fundo = (escopo === "brasil" ? [] : todas.filter((l) => !noEscopo(l))).map(ponto).filter((x): x is Ponto => x !== null);
    const destaque = universo.map(ponto).filter((x): x is Ponto => x !== null);
    const pa = alvo ? ponto(alvo) : null;
    return dispersao(t, { fundo, destaque, marcados: pa ? [{ ponto: [pa[0], pa[1], alvo!.n], cor: t.sideB }] : [], nomeX: `${mx?.nome ?? eixoX} (${mx?.unidade ?? ""})`, nomeY: `${I} (${UNIDADE_IND[e.ind]})`, logX: LOG_X.has(eixoX),
      rotFundo: "Demais conjuntos do Brasil", rotDestaque: escopo === "dist" ? `Conjuntos de ${distSel!.nome}` : escopo === "grupo" ? "Conjuntos do grupo" : "Conjuntos do Brasil" });
  }, [todas, universo, noEscopo, escopo, eixoX, e.ind, alvo, mx, I, distSel, nomeDist]);

  if (atual.carregando) return <LoadingBlock label="Carregando a tabela nacional de conjuntos" />;
  if (atual.erro) return <DataError error={atual.erro} />;
  const grupos = [...new Map(indice.distribuidoras.filter((d) => d.grupo).map((d) => [d.grupo!, d.grupo_nome ?? d.grupo!])).entries()].sort((a, b) => a[1].localeCompare(b[1]));
  const rotEscopo = escopo === "dist" ? distSel!.nome : escopo === "grupo" ? `grupo ${grupos.find(([id]) => id === grupoSel)?.[1] ?? grupoSel}` : "Brasil";
  const ROT_TIPO: Record<TipoRank, string> = { piores: `Maiores ${I}`, melhores: `Menores ${I}`, pioras: `Maiores aumentos contra ${e.ano - 1}`, melhorias: `Maiores reduções contra ${e.ano - 1}`, acima_limite: "Maior distância ao limite (apurado ÷ limite)", pares: "Menor que os pares semelhantes (apurado − mediana dos pares)" };

  return (
    <>
      <div className={s.filtros} role="toolbar" aria-label="Recorte do benchmarking">
        <Segmented label="Indicador" value={e.ind} onChange={(v) => e.set({ ind: v === "dec" ? null : v })} options={[{ value: "dec", label: "DEC" }, { value: "fec", label: "FEC" }]} />
        <Picker label="Ano" compact value={String(e.ano)} width={110} onChange={(v) => e.set({ ano: v })} options={indice.anos.map((a) => ({ value: String(a), label: String(a) }))} />
        <Picker label="Grupo" compact value={grupoSel ?? "todos"} width={210} onChange={(v) => e.set({ grupo: v === "todos" ? null : v, dist: null, conj: null })} options={[{ value: "todos", label: "Todos os grupos" }, ...grupos.map(([id, nome]) => ({ value: id, label: nome }))]} />
        <Picker label="Distribuidora" compact value={distSel ? String(distSel.dist) : "todas"} width={250} searchPlaceholder="Buscar distribuidora" testId="conf-bench-dist" onChange={(v) => e.set({ dist: v === "todas" ? null : v, conj: null })}
          options={[{ value: "todas", label: "Todas" }, ...indice.distribuidoras.filter((d) => !grupoSel || d.grupo === grupoSel).sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR")).map((d) => ({ value: String(d.dist), label: d.nome }))]} />
        {distSel && <Picker label="Conjunto em foco" compact value={alvo ? String(alvo.c) : "nenhum"} width={240} searchPlaceholder="Buscar conjunto" testId="conf-bench-conj" onChange={(v) => e.set({ conj: v === "nenhum" ? null : v })}
          options={[{ value: "nenhum", label: "Nenhum" }, ...universo.slice().sort((a, b) => a.n.localeCompare(b.n, "pt-BR")).map((l) => ({ value: String(l.c), label: l.n, meta: String(l.c) }))]} />}
      </div>

      <div className={s.bloco}>
        <p className={s.blocoTitulo}>{I} dos conjuntos · {rotEscopo} · {e.ano}</p>
        {res ? (
          <div className={s.kpis} data-testid="conf-bench-resumo">
            <div className={s.kpi}><div className={s.kpiRotulo}>Conjuntos com {I}</div><div className={s.kpiValor}>{res.n.toLocaleString("pt-BR")}</div></div>
            <div className={s.kpi}><div className={s.kpiRotulo}>1º quartil</div><div className={s.kpiValor}>{fmtInd(res.q1)}</div></div>
            <div className={s.kpi}><div className={s.kpiRotulo}>Mediana</div><div className={s.kpiValor}>{fmtInd(res.mediana)}</div></div>
            <div className={s.kpi}><div className={s.kpiRotulo}>3º quartil</div><div className={s.kpiValor}>{fmtInd(res.q3)}</div></div>
            <div className={s.kpi}><div className={s.kpiRotulo}>Acima do limite</div><div className={s.kpiValor}>{universo.filter((l) => (razaoLimite(l[e.ind], e.ind === "dec" ? l.ld : l.lf) ?? 0) > 1).length.toLocaleString("pt-BR")}</div></div>
            <div className={s.kpi}><div className={s.kpiRotulo}>Com infraestrutura da BDGD</div><div className={s.kpiValor}>{universo.filter(temInfra).length.toLocaleString("pt-BR")}</div></div>
          </div>
        ) : <span className="faint">Sem conjuntos com {I} neste recorte.</span>}
        <p className={s.nota}><Info size={13} aria-hidden />Mediana e quartis são dos conjuntos (cada conjunto conta uma vez). Não equivalem ao {I} da distribuidora, que é ponderado por consumidores.</p>
      </div>

      <div className={s.duas} style={{ marginTop: 16 }}>
        <div className={s.bloco}>
          <div className={s.secaoTopo}><p className={s.blocoTitulo} style={{ margin: 0 }}>{I} × característica da rede</p><span className={s.espaco} />
            <Picker label="Eixo horizontal" compact value={eixoX} width={260} testId="conf-bench-x" onChange={setEixoX} options={EIXOS_X.map((id) => ({ value: id, label: met.get(id)?.nome ?? id, group: met.get(id)?.grupo }))} /></div>
          <p className={s.blocoSub}>Cada ponto é um conjunto em {e.ano}. {LOG_X.has(eixoX) ? "Eixo horizontal em escala logarítmica. " : ""}Uma nuvem inclinada indica associação, não causa; o contexto (ruralidade, densidade) costuma variar junto.</p>
          <EChart build={gDisp} height={360} ariaLabel={`Dispersão de ${I} contra ${mx?.nome ?? eixoX} por conjunto em ${e.ano}`} testId="conf-g-disp" />
        </div>
        <div className={`${s.bloco} ${s.rolagem}`}>
          <p className={s.blocoTitulo}>O que diferencia os conjuntos de menor e de maior {I}</p>
          <p className={s.blocoSub}>Mediana de cada característica no quartil de menor {I} e no de maior {I}, em {rotEscopo}. Contraste = diferença das medianas em intervalos interquartis: tamanho da diferença, não explicação.</p>
          {!perfil.cortes ? <EmptyState title="Amostra insuficiente">São necessários pelo menos 12 conjuntos com {I} e infraestrutura no recorte ({perfil.n} disponíveis).</EmptyState> : (
            <table className={s.tabela} data-testid="conf-perfil">
              <thead><tr><th scope="col">Característica</th><th scope="col">Menor {I} (≤ {fmtInd(perfil.cortes.q1)})</th><th scope="col">Maior {I} (≥ {fmtInd(perfil.cortes.q3)})</th><th scope="col">Contraste</th></tr></thead>
              <tbody>{[...perfil.linhas].sort((a, b) => Math.abs(b.contraste ?? 0) - Math.abs(a.contraste ?? 0)).map((l) => { const m = met.get(l.id)!; return (
                <tr key={l.id} title={m.definicao}><td>{m.nome} <span className="faint">({m.unidade})</span></td><td>{fmtMetrica(l.melhores, m)}</td><td>{fmtMetrica(l.piores, m)}</td>
                  <td>{l.contraste === null ? <span className="faint">N/D</span> : <><span className={s.barra} style={{ width: `${Math.min(60, Math.round(Math.abs(l.contraste) * 30))}px` }} aria-hidden /> {l.contraste > 0 ? "+" : ""}{l.contraste.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}</>}</td></tr>); })}</tbody>
            </table>
          )}
        </div>
      </div>

      <div className={s.secaoTopo} style={{ marginTop: 22 }}><h3 className="headline">Pares tecnicamente semelhantes{alvo ? ` de ${alvo.n}` : ""}</h3></div>
      {!alvo ? <EmptyState title="Escolha uma distribuidora e um conjunto em foco">Os pares são os 20 conjuntos de outras distribuidoras mais próximos em {CRITERIOS_PADRAO.map((c) => c.rotulo).join(", ")}.</EmptyState>
        : !pares || !pares.pares.length ? <EmptyState title="Sem pares definidos">{pares?.motivo ?? "O conjunto não tem infraestrutura da BDGD neste ano."}</EmptyState> : (
          <div className={`${s.bloco} ${s.rolagem}`}>
            <p className={s.blocoSub}>Critérios usados: {pares.usados.map((id) => CRITERIOS_PADRAO.find((c) => c.id === id)?.rotulo).join("; ")}. Distância em intervalos interquartis nacionais (0 = idêntico). {I} de {alvo.n}: <b>{fmtInd(alvo[e.ind])}</b>; mediana dos pares: <b>{fmtInd(resPares?.mediana)}</b> (quartis {fmtInd(resPares?.q1)}–{fmtInd(resPares?.q3)}); posição entre os pares: <b>{(() => { const p = percentilDe(alvo[e.ind], pares.pares.map((x) => x.linha[e.ind])); return p === null ? "N/D" : `P${Math.round(p * 100)}`; })()}</b>.</p>
            <table className={s.tabela} data-testid="conf-pares">
              <thead><tr><th scope="col">Conjunto</th><th scope="col">Distância</th><th scope="col">{I}</th>{pares.usados.map((id) => <th key={id} scope="col">{met.get(id)?.nome}</th>)}</tr></thead>
              <tbody>
                <tr><td><b>{alvo.n}</b><span className={s.sub}>{nomeDist.get(alvo.dist)?.nome} · em foco</span></td><td>—</td><td><b>{fmtInd(alvo[e.ind])}</b></td>{pares.usados.map((id) => <td key={id}>{fmtMetrica(alvo.infra[id], met.get(id)!)}</td>)}</tr>
                {pares.pares.map((p) => (
                  <tr key={chave(p.linha)} style={{ cursor: "pointer" }} onClick={() => e.set({ a: `${alvo.dist}-${alvo.c}`, b: `${p.linha.dist}-${p.linha.c}`, aba: "comparar" }, true)} title="Comparar com o conjunto em foco">
                    <td>{p.linha.n}<span className={s.sub}>{nomeDist.get(p.linha.dist)?.nome}</span></td><td>{p.distancia.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}</td><td>{fmtInd(p.linha[e.ind])}</td>
                    {pares.usados.map((id) => <td key={id}>{fmtMetrica(p.linha.infra[id], met.get(id)!)}</td>)}
                  </tr>))}
              </tbody>
            </table>
            <p className={s.nota}><Info size={13} aria-hidden />Clique num par para abrir a comparação A × B. Semelhança de contexto não garante igualdade de clima, vegetação ou idade da rede, que não estão nestes dados.</p>
          </div>
        )}

      <div className={s.secaoTopo} style={{ marginTop: 22 }}><h3 className="headline">Ranking contextualizado · {rotEscopo}</h3><span className={s.espaco} />
        <Picker label="Ordenar por" compact value={tipo} width={330} testId="conf-rank-tipo" onChange={(v) => setTipo(v as TipoRank)} options={(Object.keys(ROT_TIPO) as TipoRank[]).map((k) => ({ value: k, label: ROT_TIPO[k], disabled: (k === "pioras" || k === "melhorias") && !ant }))} /></div>
      <div className={`${s.bloco} ${s.rolagem}`}>
        {!lista.length ? <span className="faint">Sem conjuntos para este critério no recorte.</span> : (
          <table className={s.tabela} data-testid="conf-ranking">
            <thead><tr><th scope="col">Conjunto</th><th scope="col">{tipo === "acima_limite" ? "Apurado ÷ limite" : tipo === "pares" ? "Apurado − mediana dos pares" : tipo === "pioras" || tipo === "melhorias" ? `Variação do ${I}` : I}</th><th scope="col">{I} {e.ano}</th><th scope="col">Limite</th><th scope="col">{tipo === "pares" ? "Mediana dos pares" : `${I} ${e.ano - 1}`}</th><th scope="col">Consumidores</th><th scope="col">Não urbano</th><th scope="col">km MT / mil UC</th></tr></thead>
            <tbody>{lista.map((it) => { const l = it.linha, antL = ant?.find((x) => chave(x) === chave(l)); return (
              <tr key={chave(l)} style={{ cursor: "pointer" }} onClick={() => e.set({ aba: "mapa", dist: l.dist, conj: l.c }, true)} title="Abrir o diagnóstico do conjunto">
                <td>{l.n}<span className={s.sub}>{nomeDist.get(l.dist)?.nome}</span></td>
                <td><b>{tipo === "acima_limite" ? `${Math.round(it.valor * 100)}%` : `${(tipo === "pioras" || tipo === "melhorias" || tipo === "pares") && it.valor > 0 ? "+" : ""}${fmtInd(it.valor)}`}</b></td>
                <td>{fmtInd(l[e.ind])}</td><td>{fmtInd(e.ind === "dec" ? l.ld : l.lf)}</td><td>{fmtInd(tipo === "pares" ? it.anterior : antL?.[e.ind])}</td>
                <td>{fmtMetrica(l.nuc, { tipo: "contagem" })}</td><td>{fmtMetrica(l.infra.pct_uc_rural, { tipo: "pct" })}</td><td>{fmtMetrica(l.infra.km_mt_por_mil_uc, { tipo: "razao" })}</td>
              </tr>); })}</tbody>
          </table>
        )}
        <p className={s.nota}><Info size={13} aria-hidden />Um {I} absoluto menor num território mais favorável não indica rede ou operação melhor. Por isso o ranking traz o contexto ao lado e a opção de ordenar pela diferença para a mediana dos pares semelhantes. Nenhuma ordenação aqui é evidência de eficiência causal.</p>
      </div>
    </>
  );
}
