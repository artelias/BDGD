"use client";
import { ArrowDown, ArrowUp, Info } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { DataError, EmptyState, LoadingBlock } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { Pill } from "@/components/ui/Value";
import { MESES, NOME_IND, UNIDADE_IND, anualCompleto, completoDist, fmtInd, limiteInd, linhasNacionais, mediaPonderada, num, razaoLimite, situacao, valorComparavel, valorInd, variacao } from "@/lib/confiabilidade/calculo";
import { carregarGeo, useDist, useNacional } from "@/lib/confiabilidade/dados";
import { COR_ND, corDe, legenda, quebrasQuantis } from "@/lib/confiabilidade/escala";
import type { EstadoConf } from "@/lib/confiabilidade/estado";
import type { BlocoAno, Conjunto, Indice } from "@/lib/confiabilidade/tipos";
import { useTheme } from "@/lib/theme";
import m from "@/components/map/map.module.css";
import { FichaConjunto } from "./FichaConjunto";
import { MapaConfiabilidade, bboxDe, type HoverMapa, type MapaHandle } from "./MapaConfiabilidade";
import s from "./conf.module.css";

type Ordem = { col: "nome" | "valor" | "razao" | "nuc"; desc: boolean };
const pct = (v: number | null) => (v === null ? "N/D" : `${Math.round(v * 100)}%`);

export function VisaoMapa({ indice, e }: { indice: Indice; e: EstadoConf }) {
  const { resolved: tema } = useTheme();
  const mapa = useRef<MapaHandle>(null);
  const ficha = useRef<HTMLDivElement>(null);
  const rolarFicha = useRef(false);
  const [hover, setHover] = useState<HoverMapa | null>(null);
  const [mapaPronto, setMapaPronto] = useState(false);
  const [ordem, setOrdem] = useState<Ordem>({ col: "valor", desc: true });
  const [geoCarregada, setGeo] = useState<{ dist: number; fc: GeoJSON.FeatureCollection | null; erro?: string } | null>(null);
  const I = NOME_IND[e.ind], ano = String(e.ano);
  const mensal = e.mes !== null;
  const modo = mensal ? "absoluto" : e.modo;   // os limites são anuais: no recorte mensal só há valor absoluto

  const dists = useMemo(() => indice.distribuidoras.filter((d) => !e.grupo || d.grupo === e.grupo), [indice, e.grupo]);
  const distSel = e.dist !== null ? indice.distribuidoras.find((d) => d.dist === e.dist) ?? null : null;
  const doc = useDist(distSel ? distSel.dist : null);
  // o arquivo nacional (~1 MB) só serve às quebras da escala "Conjuntos do Brasil": não é baixado no nível Brasil nem no recorte mensal
  const nacional = useNacional(distSel && e.ref === "brasil" && !mensal && modo === "absoluto" ? e.ano : null);
  const grupos = useMemo(() => [...new Map(indice.distribuidoras.filter((d) => d.grupo).map((d) => [d.grupo!, d.grupo_nome ?? d.grupo!])).entries()].sort((a, b) => a[1].localeCompare(b[1])), [indice]);

  // geometria dos conjuntos sob demanda
  useEffect(() => {
    if (!distSel || !distSel.geo) return;
    let vivo = true;
    carregarGeo(distSel.dist).then((fc) => vivo && setGeo({ dist: distSel.dist, fc })).catch((er: Error) => vivo && setGeo({ dist: distSel.dist, fc: null, erro: er.message }));
    return () => { vivo = false; };
  }, [distSel]);
  // sem polígonos publicados, a distribuidora fica com geometria nula (nada é desenhado); enquanto carrega, geo é null
  const geo = useMemo(() => (!distSel ? null : !distSel.geo ? { dist: distSel.dist, fc: null as GeoJSON.FeatureCollection | null, erro: undefined as string | undefined } : geoCarregada?.dist === distSel.dist ? geoCarregada : null), [distSel, geoCarregada]);
  useEffect(() => {
    if (!distSel) { mapa.current?.enquadrarBrasil(); return; }
    if (geo?.dist !== distSel.dist) return;
    const b = (geo.fc && bboxDe(geo.fc)) || distSel.bbox;
    if (b) mapa.current?.enquadrar(b);
  }, [distSel, geo, mapaPronto]);

  // conjunto selecionado: enquadra o polígono dele (sem polígono, mantém a distribuidora)
  useEffect(() => {
    if (!mapaPronto || !geo?.fc || e.conj === null) return;
    const b = bboxDe(geo.fc, (f) => Number(f.properties?.c) === e.conj);
    if (b) mapa.current?.enquadrar(b);
  }, [e.conj, geo, mapaPronto]);

  // valor exibido de um conjunto, conforme indicador, período e modo de cor
  const valorDe = (b: BlocoAno | undefined) => (!b ? null : mensal ? b.m[e.ind][e.mes! - 1] : valorInd(b, e.ind));
  // cor, quebras e % do limite: valor anual parcial (menos de 12 meses) fica N/D; a lista ainda mostra o valor, marcado como parcial
  const valorCor = (b: BlocoAno | undefined) => (!b ? null : mensal ? b.m[e.ind][e.mes! - 1] : valorComparavel(b, e.ind));
  const parcialDe = (b: BlocoAno | undefined) => !mensal && !!b && !anualCompleto(b, e.ind);
  const medidaDe = (b: BlocoAno | undefined) => (modo === "regulatorio" ? razaoLimite(valorComparavel(b, e.ind), limiteInd(b, e.ind)) : valorCor(b));

  // nível Brasil: valor por distribuidora (derivado dos conjuntos, ponderado por consumidores) ou parcela de conjuntos acima do limite
  const valorDist = (d: (typeof dists)[number]) => {
    const a = d.anual[ano];
    if (!a) return null;
    return modo === "regulatorio" ? (a.conjuntos ? (e.ind === "dec" ? a.acima_dec : a.acima_fec) / a.conjuntos : null) : completoDist(a, e.ind) ? a[e.ind] : null;
  };
  const quebrasDist = useMemo(() => quebrasQuantis(indice.distribuidoras.map((d) => { const a = d.anual[ano]; return !a ? null : modo === "regulatorio" ? (a.conjuntos ? (e.ind === "dec" ? a.acima_dec : a.acima_fec) / a.conjuntos : null) : completoDist(a, e.ind) ? a[e.ind] : null; })), [indice, ano, modo, e.ind]);
  const coresDist = useMemo(() => new Map(dists.map((d) => [d.dist, corDe(valorDist(d), quebrasDist, "absoluto", tema)] as [number, string])),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [dists, quebrasDist, tema, ano, modo, e.ind]);

  // nível distribuidora: quebras pela referência escolhida (Brasil = todos os conjuntos do ano; distribuidora = só os dela)
  const conjuntos = useMemo(() => doc.dados?.conjuntos.filter((c) => c.a[ano]) ?? [], [doc.dados, ano]);
  const quebrasConj = useMemo(() => {
    if (modo === "regulatorio") return [];
    if (e.ref === "brasil" && !mensal && nacional.dados) return quebrasQuantis(linhasNacionais(nacional.dados).map((l) => l[e.ind]));
    return quebrasQuantis(conjuntos.map((c) => valorCor(c.a[ano])));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modo, e.ref, e.ind, e.mes, nacional.dados, conjuntos, ano]);
  const refEfetiva = modo === "regulatorio" ? null : e.ref === "brasil" && !mensal && nacional.dados ? "brasil" : "dist";
  const coresConj = useMemo(() => new Map(conjuntos.map((c) => [c.c, corDe(medidaDe(c.a[ano]), quebrasConj, modo, tema)] as [number, string])),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [conjuntos, quebrasConj, modo, tema, ano, e.ind, e.mes]);
  const passa = (c: Conjunto) => e.sit === "todos" || situacao(valorComparavel(c.a[ano], e.ind), limiteInd(c.a[ano], e.ind)) === e.sit;
  const esmaecer = useMemo(() => (e.sit === "todos" ? null : new Set(conjuntos.filter((c) => !passa(c)).map((c) => c.c))),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [conjuntos, e.sit, e.ind, ano]);
  const conjSel = e.conj !== null ? doc.dados?.conjuntos.find((c) => c.c === e.conj) ?? null : null;
  // escolha pela lista em layout de uma coluna (celular/tablet): a ficha abre abaixo da lista, então leva o usuário até ela
  const escolherDaLista = (c: number) => {
    rolarFicha.current = window.matchMedia("(max-width: 1100px)").matches;
    e.set({ conj: c });
  };
  useEffect(() => {
    if (!rolarFicha.current || !conjSel || !ficha.current) return;
    rolarFicha.current = false;
    ficha.current.scrollIntoView({ block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }, [conjSel]);

  // apuração parcial (menos de 12 meses) fica sem cor; a legenda diz quantos, para o N/D não parecer falta de dado
  const nParciais = distSel && !mensal ? conjuntos.filter((c) => parcialDe(c.a[ano])).length : !distSel && modo === "absoluto" ? dists.filter((d) => d.anual[ano] && !completoDist(d.anual[ano], e.ind)).length : 0;
  const itensLegenda = distSel ? legenda(quebrasConj, modo, tema, fmtInd) : legenda(quebrasDist, "absoluto", tema, (v) => (modo === "regulatorio" ? pct(v) : fmtInd(v)));
  const tituloLegenda = distSel
    ? modo === "regulatorio" ? `${I} apurado ÷ limite, ${ano}` : `${I} ${mensal ? `de ${MESES[e.mes! - 1]}/${ano}` : `anual ${ano}`} · ${UNIDADE_IND[e.ind]}`
    : modo === "regulatorio" ? `Conjuntos acima do limite de ${I}, ${ano}` : `${I} ${ano} da distribuidora · ${UNIDADE_IND[e.ind]}`;

  const listaConj = useMemo(() => {
    const linhas = conjuntos.filter(passa).map((c) => { const b = c.a[ano]; return { c, valor: valorDe(b), parcial: parcialDe(b), razao: razaoLimite(valorComparavel(b, e.ind), limiteInd(b, e.ind)), nuc: b.nuc }; });
    const k = ordem.col; const sinal = ordem.desc ? -1 : 1;
    return linhas.sort((x, y) => {
      if (k === "nome") return sinal * x.c.n.localeCompare(y.c.n, "pt-BR");
      const a = x[k], b = y[k];
      if (!num(a) && !num(b)) return x.c.n.localeCompare(y.c.n, "pt-BR");
      if (!num(a)) return 1; if (!num(b)) return -1;   // N/D sempre no fim
      return sinal * (a - b) || x.c.n.localeCompare(y.c.n, "pt-BR");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conjuntos, ordem, ano, e.ind, e.mes, e.sit]);
  const listaDist = useMemo(() => [...dists].filter((d) => d.anual[ano]).sort((a, b) => {
    const x = a.anual[ano][e.ind], y = b.anual[ano][e.ind];
    if (!num(x)) return 1; if (!num(y)) return -1;
    return y - x;
  }), [dists, ano, e.ind]);

  const brasil = useMemo(() => {
    const comAno = dists.filter((d) => d.anual[ano]);
    const total = comAno.reduce((t, d) => t + d.anual[ano].conjuntos, 0);
    const acima = comAno.reduce((t, d) => t + (e.ind === "dec" ? d.anual[ano].acima_dec : d.anual[ano].acima_fec), 0);
    return { n: comAno.length, total, acima, media: mediaPonderada(comAno.map((d) => ({ v: completoDist(d.anual[ano], e.ind) ? d.anual[ano][e.ind] : null, w: d.anual[ano].nuc }))), nuc: comAno.reduce((t, d) => t + d.anual[ano].nuc, 0) };
  }, [dists, ano, e.ind]);

  const cab = (col: Ordem["col"], rotulo: string) => (
    <th scope="col" aria-sort={ordem.col === col ? (ordem.desc ? "descending" : "ascending") : "none"}>
      <button className={s.th} onClick={() => setOrdem({ col, desc: ordem.col === col ? !ordem.desc : col !== "nome" })}>{rotulo}{ordem.col === col && (ordem.desc ? <ArrowDown size={11} aria-hidden /> : <ArrowUp size={11} aria-hidden />)}</button>
    </th>
  );
  const dica = (() => {
    if (!hover) return null;
    if (hover.tipo === "dist") {
      const d = indice.distribuidoras.find((x) => x.dist === hover.id), a = d?.anual[ano];
      if (!d) return null;
      return <><b>{d.nome}</b><div className={s.dicaGrade}><span>DEC {ano}</span><span>{fmtInd(a?.dec)}</span><span>FEC {ano}</span><span>{fmtInd(a?.fec)}</span><span>Conjuntos</span><span>{a?.conjuntos ?? "N/D"}</span><span>Acima do limite de {I}</span><span>{a ? (e.ind === "dec" ? a.acima_dec : a.acima_fec) : "N/D"}</span></div></>;
    }
    const c = doc.dados?.conjuntos.find((x) => x.c === hover.id), b = c?.a[ano], ant = c?.a[String(e.ano - 1)];
    if (!c) return null;
    const dv = variacao(valorInd(b, e.ind), valorInd(ant, e.ind));
    return <><b>{c.n}</b><span>conjunto {c.c} · {distSel?.nome}</span><div className={s.dicaGrade}>
      <span>DEC · limite</span><span>{fmtInd(b?.dec)} · {fmtInd(b?.ld)}</span><span>FEC · limite</span><span>{fmtInd(b?.fec)} · {fmtInd(b?.lf)}</span>
      <span>{I} contra {e.ano - 1}</span><span>{dv ? `${dv.abs > 0 ? "+" : ""}${fmtInd(dv.abs)}` : "N/D"}</span>
      <span>Consumidores</span><span>{num(b?.nuc) ? b!.nuc!.toLocaleString("pt-BR") : "N/D"}</span>
      <span>Cobertura</span><span>{!b ? `sem apuração em ${ano}` : b.infra ? "continuidade e infraestrutura" : "só continuidade"}</span></div></>;
  })();

  return (
    <>
      <div className={s.filtros} role="toolbar" aria-label="Filtros do mapa de confiabilidade">
        <Picker label="Grupo" compact value={e.grupo ?? "todos"} width={210} testId="conf-grupo" onChange={(v) => e.set({ grupo: v === "todos" ? null : v, dist: null, conj: null })}
          options={[{ value: "todos", label: "Todos" }, ...grupos.map(([id, nome]) => ({ value: id, label: nome }))]} />
        <Picker label="Distribuidora" compact value={distSel ? String(distSel.dist) : "brasil"} width={250} testId="conf-dist" searchPlaceholder="Buscar distribuidora" onChange={(v) => e.set({ dist: v === "brasil" ? null : v, conj: null }, true)}
          options={[{ value: "brasil", label: e.grupo ? "Todas do grupo" : "Brasil (todas)" }, ...[...dists].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR")).map((d) => ({ value: String(d.dist), label: d.nome, meta: `${d.conjuntos} conj.`, keywords: `${d.sigla} ${d.agente_aneel} ${d.dist}` }))]} />
        {distSel && <Picker label="Conjunto" compact value={conjSel ? String(conjSel.c) : "nenhum"} width={240} testId="conf-conj" searchPlaceholder="Buscar conjunto" onChange={(v) => e.set({ conj: v === "nenhum" ? null : v })}
          options={[{ value: "nenhum", label: "Todos os conjuntos" }, ...[...conjuntos].sort((a, b) => a.n.localeCompare(b.n, "pt-BR")).map((c) => ({ value: String(c.c), label: c.n, meta: String(c.c) }))]} />}
        <Segmented label="Indicador" value={e.ind} onChange={(v) => e.set({ ind: v === "dec" ? null : v })} options={[{ value: "dec", label: "DEC", title: "Duração equivalente de interrupção por consumidor (horas)" }, { value: "fec", label: "FEC", title: "Frequência equivalente de interrupção por consumidor (interrupções)" }]} />
        <Picker label="Ano" compact value={ano} width={118} testId="conf-ano" onChange={(v) => e.set({ ano: v })} options={indice.anos.map((a) => ({ value: String(a), label: String(a) }))} />
        <Picker label="Período" compact value={e.mes === null ? "ano" : String(e.mes)} width={176} testId="conf-periodo" onChange={(v) => e.set({ mes: v === "ano" ? null : v })}
          options={[{ value: "ano", label: "Ano inteiro" }, ...MESES.map((nome, i) => ({ value: String(i + 1), label: `${nome}/${ano}` }))]} />
        <Segmented label="Cor do mapa" value={modo === "regulatorio" ? "limite" : "valor"} onChange={(v) => e.set({ cor: v === "limite" ? "limite" : null })}
          options={[{ value: "valor", label: "Valor" }, { value: "limite", label: "% do limite", disabled: mensal, title: mensal ? "Os limites regulatórios são anuais; escolha o ano inteiro" : "Apurado dividido pelo limite regulatório" }]} />
        {distSel && <Picker label="Situação" compact value={e.sit} width={190} testId="conf-sit" onChange={(v) => e.set({ sit: v === "todos" ? null : v })}
          options={[{ value: "todos", label: "Todas" }, { value: "acima", label: `Acima do limite de ${I}` }, { value: "dentro", label: `Dentro do limite de ${I}` }]} />}
        {distSel && modo === "absoluto" && <Picker label="Escala" compact value={e.ref} width={236} testId="conf-ref" onChange={(v) => e.set({ ref: v === "dist" ? "dist" : null })}
          options={[{ value: "brasil", label: "Conjuntos do Brasil", disabled: mensal }, { value: "dist", label: "Só desta empresa" }]} />}
      </div>

      <div className={s.palco}>
        <div className={s.mapa}>
          <MapaConfiabilidade ref={mapa} coresDist={coresDist} corNd={COR_ND[tema]} dist={distSel?.dist ?? null}
            conjuntos={distSel && geo?.dist === distSel.dist ? geo.fc : null} coresConj={coresConj} selecionado={conjSel?.c ?? null}
            ladoA={e.a && e.a.dist === distSel?.dist ? e.a.conj : null} ladoB={e.b && e.b.dist === distSel?.dist ? e.b.conj : null} esmaecer={esmaecer}
            onDist={(d) => e.set({ dist: d, conj: null }, true)} onConj={(c) => e.set({ conj: c })} onHover={setHover} onPronto={() => setMapaPronto(true)}
            rotulo={`Mapa de ${I} ${ano}. ${distSel ? `Conjuntos elétricos de ${distSel.nome}` : "Distribuidoras do Brasil"}. Use a lista ao lado para selecionar pelo teclado.`} />
          {hover && dica && <div className={`${m.hoverTip} ${s.dica}`} style={{ left: hover.x, top: hover.y }} role="status">{dica}</div>}
          <div className={s.legenda} data-testid="conf-legenda">
            <div className={s.legendaTitulo}>{tituloLegenda}</div>
            {itensLegenda.map((it) => <div key={it.rotulo} className={s.legendaItem}><i style={{ background: it.cor }} />{it.rotulo}</div>)}
            <div className={s.legendaItem}><i style={{ background: COR_ND[tema] }} />N/D{!distSel && e.grupo ? " ou fora do grupo" : ""}{nParciais ? ` (inclui ${nParciais} com apuração parcial de ${I})` : ""}</div>
            <div className={s.legendaNota}>
              {distSel ? (modo === "regulatorio" ? "Classes fixas de apurado ÷ limite." : `Classes por quintis dos conjuntos ${refEfetiva === "brasil" ? "do Brasil" : "desta distribuidora"}.`) : "Classes por quintis das distribuidoras."} Mais {tema === "dark" && modo === "absoluto" ? "claro" : "escuro"}{modo === "regulatorio" && distSel ? "/vermelho" : ""} = pior continuidade.
            </div>
          </div>
          {distSel && geo?.dist === distSel.dist && !geo.fc && <div className={m.mapError} role="status">{geo.erro ? `A geometria dos conjuntos não pôde ser carregada (${geo.erro}).` : "Esta distribuidora não tem polígonos de conjuntos publicados na BDGD 2025."} Nenhum limite é desenhado; os valores estão na lista.</div>}
        </div>

        <aside className={s.lateral} aria-label={distSel ? `Conjuntos de ${distSel.nome}` : "Distribuidoras"}>
          <div className={s.lateralTopo}>
            <div className={s.caminho}>
              <button onClick={() => e.set({ dist: null, conj: null, grupo: null }, true)}>Brasil</button>
              {(e.grupo || distSel?.grupo) && <>› <button onClick={() => e.set({ grupo: e.grupo ?? distSel?.grupo ?? null, dist: null, conj: null }, true)}>{grupos.find(([id]) => id === (e.grupo ?? distSel?.grupo))?.[1]}</button></>}
              {distSel && <>› <button onClick={() => e.set({ conj: null })}>{distSel.nome}</button></>}
              {conjSel && <>› <span>{conjSel.n}</span></>}
            </div>
            {!distSel ? <>
              <p className={s.lateralTitulo}>{e.grupo ? grupos.find(([id]) => id === e.grupo)?.[1] : "Brasil"} · {ano}</p>
              <div className={s.kpis}>
                <div className={s.kpi}><div className={s.kpiRotulo}>Conjuntos com {I}</div><div className={s.kpiValor} data-testid="conf-total-conjuntos">{brasil.total.toLocaleString("pt-BR")}</div><div className={s.kpiSub}>{brasil.n} distribuidoras</div></div>
                <div className={s.kpi}><div className={s.kpiRotulo}>Acima do limite de {I}</div><div className={s.kpiValor}>{brasil.acima.toLocaleString("pt-BR")}<small>{brasil.total ? pct(brasil.acima / brasil.total) : ""}</small></div><div className={s.kpiSub}>conjuntos</div></div>
                <div className={s.kpi}><div className={s.kpiRotulo}>{I} médio ponderado</div><div className={s.kpiValor}>{fmtInd(brasil.media.v)}</div><div className={s.kpiSub}>pelas distribuidoras do recorte</div></div>
              </div>
            </> : <>
              <p className={s.lateralTitulo}>{distSel.nome} <Pill tone="nd" title="Média dos conjuntos ponderada pelo NumCon de cada mês, somada nos 12 meses. Derivado dos dados oficiais por conjunto.">derivado dos conjuntos</Pill></p>
              {distSel.anual[ano] ? (
                <div className={s.kpis}>
                  <div className={s.kpi}><div className={s.kpiRotulo}>DEC {ano}</div><div className={s.kpiValor} data-testid="conf-dist-dec">{fmtInd(distSel.anual[ano].dec)}<small>h</small></div>{!completoDist(distSel.anual[ano], "dec") && <div className={s.kpiSub}>parcial: menos de 12 meses</div>}</div>
                  <div className={s.kpi}><div className={s.kpiRotulo}>FEC {ano}</div><div className={s.kpiValor} data-testid="conf-dist-fec">{fmtInd(distSel.anual[ano].fec)}<small>int.</small></div>{!completoDist(distSel.anual[ano], "fec") && <div className={s.kpiSub}>parcial: menos de 12 meses</div>}</div>
                  <div className={s.kpi}><div className={s.kpiRotulo}>Acima do limite de {I}</div><div className={s.kpiValor}>{e.ind === "dec" ? distSel.anual[ano].acima_dec : distSel.anual[ano].acima_fec}<small>de {distSel.anual[ano].conjuntos}</small></div></div>
                </div>
              ) : <p className={s.kpiSub}>Sem apuração de continuidade em {ano}.</p>}
            </>}
          </div>
          <div className={s.lateralLista}>
            {!distSel ? (
              <table className={s.linhas} data-testid="conf-lista-dist">
                <thead><tr><th scope="col">Distribuidora</th><th scope="col">{I}</th><th scope="col">Acima do limite</th></tr></thead>
                <tbody>{listaDist.map((d) => { const a = d.anual[ano]; return (
                  <tr key={d.dist} onClick={() => e.set({ dist: d.dist, conj: null }, true)} tabIndex={0} onKeyDown={(ev) => { if (ev.key === "Enter") e.set({ dist: d.dist, conj: null }, true); }}>
                    <td><i className={s.amostra} style={{ background: coresDist.get(d.dist) ?? COR_ND[tema] }} aria-hidden /><span className={s.nomeConj}>{d.nome}</span></td>
                    <td>{fmtInd(a[e.ind])}{!completoDist(a, e.ind) && <span className={s.sub}>parcial</span>}</td><td>{e.ind === "dec" ? a.acima_dec : a.acima_fec} de {a.conjuntos}</td>
                  </tr>); })}</tbody>
              </table>
            ) : doc.carregando ? <div style={{ padding: 18 }}><LoadingBlock label="Carregando conjuntos" /></div>
              : doc.erro ? <div style={{ padding: 18 }}><DataError error={doc.erro} /></div>
              : !listaConj.length ? <div style={{ padding: 18 }}><EmptyState title="Nenhum conjunto neste filtro">Mude a situação ou o ano.</EmptyState></div> : (
                <table className={s.linhas} data-testid="conf-lista-conj">
                  <thead><tr>{cab("nome", "Conjunto")}{cab("valor", mensal ? `${I} ${MESES[e.mes! - 1]}` : I)}{cab("razao", "% limite")}{cab("nuc", "Consum.")}</tr></thead>
                  <tbody>{listaConj.map(({ c, valor, parcial, razao, nuc }) => (
                    <tr key={c.c} data-sel={c.c === conjSel?.c} onClick={() => escolherDaLista(c.c)} tabIndex={0} onKeyDown={(ev) => { if (ev.key === "Enter") escolherDaLista(c.c); }}>
                      <td><i className={s.amostra} style={{ background: coresConj.get(c.c) ?? COR_ND[tema] }} aria-hidden /><span className={s.nomeConj}>{c.n}</span>{!c.geo && <span className={s.sub}>sem polígono na BDGD 2025</span>}</td>
                      <td>{fmtInd(valor)}{parcial && <span className={s.sub}>parcial</span>}</td>
                      <td className={razao === null ? s.nd : razao > 1 ? s.acima : s.dentro}>{pct(razao)}</td>
                      <td>{num(nuc) ? nuc.toLocaleString("pt-BR") : "N/D"}</td>
                    </tr>))}</tbody>
                </table>
              )}
          </div>
        </aside>
      </div>
      <p className={s.nota}><Info size={13} aria-hidden />
        DEC e FEC por conjunto são os valores publicados pela ANEEL. {distSel ? `Os polígonos são os conjuntos da camada CONJ da BDGD de 31/12/2025, simplificados para visualização; conjuntos extintos antes dessa data não têm polígono.${Number(ano) < 2025 ? ` Os valores de ${ano} são desenhados sobre esses limites de 2025: conjuntos reconfigurados desde então podem ter tido outra delimitação, e a área usada na densidade é a de 2025.` : ""}` : "No nível Brasil o mapa usa as áreas de atuação das distribuidoras; o valor de cada distribuidora é derivado dos seus conjuntos, ponderado por consumidores. Selecione uma distribuidora para ver os conjuntos."}
      </p>

      {distSel && conjSel && doc.dados && (
        <div ref={ficha} className={s.ancoraFicha}><FichaConjunto indice={indice} doc={doc.dados} conj={conjSel} ano={e.ano} ind={e.ind}
          onA={() => e.set({ a: `${distSel.dist}-${conjSel.c}`, aba: "comparar" }, true)} onB={() => e.set({ b: `${distSel.dist}-${conjSel.c}`, aba: "comparar" }, true)} onFechar={() => e.set({ conj: null })} /></div>
      )}
      {distSel && e.conj !== null && doc.dados && !conjSel && <EmptyState title="Conjunto não encontrado">O código {e.conj} não pertence a {distSel.nome}.</EmptyState>}
    </>
  );
}
