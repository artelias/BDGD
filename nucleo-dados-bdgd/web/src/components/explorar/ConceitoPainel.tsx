"use client";
import { Code2, Download, Info, SlidersHorizontal, X } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { Button } from "@/components/ui/Button";
import { Explain } from "@/components/ui/Explain";
import { downloadText, EmptyState, LoadingBlock, useToast } from "@/components/ui/Feedback";
import { MultiPick, type MultiOption } from "@/components/ui/MultiPick";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { ativo, ESSENCIAIS, recorteDe, ROTULO_MEDIDA, UNIDADE } from "@/lib/ativos";
import { agregar, dimsCompativeis, distribuicao, escolherCubo, escreverRecorte, foraDoCubo, juntar, lerRecorte, participacao, rotulo, type Recorte } from "@/lib/cubo";
import type { Dataset } from "@/lib/dataset";
import { useConceito } from "@/lib/data-context";
import { distsDoEscopo, noEscopo, rotuloEscopo, type Escopo } from "@/lib/escopo";
import { fmt, fmtCompact, toCSV } from "@/lib/format";
import type { ConceitoData, MedidaConceito, MenuItem } from "@/lib/types";
import { useQueryPatch, useQueryState } from "@/lib/url-state";
import { EntidadeTecnica } from "./EntidadeTecnica";
import { InventarioObjetos } from "./InventarioObjetos";
import s from "./explorar.module.css";

const pct = (x: number | null | undefined) => (x === null || x === undefined ? "N/D" : `${(x * 100).toLocaleString("pt-BR", { maximumFractionDigits: x < 0.001 ? 3 : 1 })}%`);
const comUnidade = (v: number | null | undefined, m: MedidaConceito, compact = false) =>
  v === null || v === undefined ? "N/D" : `${compact ? fmtCompact(v, m) : fmt(v, m)}${m === "quantidade" ? "" : compact ? "" : ` ${UNIDADE[m]}`}`;

export function ConceitoPainel({ ds, item, escopo, avancado }: { ds: Dataset; item: MenuItem; escopo: Escopo; avancado: boolean }) {
  const cfg = ds.raw.conceitos!.conceitos[item.conceito!];
  const asset = useConceito(item.conceito!);
  if (asset.loading) return <LoadingBlock lines={6} label="Carregando o conceito" />;
  if (asset.error || !asset.data) return <EmptyState title="Conceito indisponível" tone="warn">{asset.error ?? "Arquivo do conceito não encontrado."}</EmptyState>;
  return <Painel key={item.id} ds={ds} item={item} cfg={cfg} cd={asset.data} escopo={escopo} avancado={avancado} />;
}

function Painel({ ds, item, cfg, cd, escopo, avancado }: { ds: Dataset; item: MenuItem; cfg: NonNullable<Dataset["raw"]["conceitos"]>["conceitos"][string]; cd: ConceitoData; escopo: Escopo; avancado: boolean }) {
  const toast = useToast();
  const patch = useQueryPatch();
  const [fQ] = useQueryState("f");
  const [cQ] = useQueryState("c");
  const [mQ, setM] = useQueryState("m");
  const [porQ, setPor] = useQueryState("por");
  const [tecnico, setTecnico] = useState(false);

  const todasDims = useMemo(() => [...new Set(Object.values(cd.cubos).flatMap((c) => c.dims))], [cd]);
  const base = useMemo(() => recorteDe(item), [item]);
  const user = useMemo<Recorte>(() => {
    const f = lerRecorte(fQ);
    for (const k of Object.keys(f)) if (!todasDims.includes(k)) delete f[k];
    return { filtro: f };
  }, [fQ, todasDims]);
  // cartões: tipo patrimonial (ou outra categoria do conceito); se o item já fixa a categoria, os cartões passam ao tipo de bem (A1)
  const fixa = !!cfg.categoria && (item.filtro?.[cfg.categoria]?.length ?? 0) > 0;
  const cardsDim = fixa ? (cfg.cubos.principal.includes("a1") ? "a1" : null) : cfg.categoria;
  const cardSel = cardsDim && cQ && cd.valores[cardsDim]?.includes(cQ) ? cQ : null;
  const semCard = useMemo(() => juntar(base, user), [base, user]);
  const recorte = useMemo(() => (cardSel && cardsDim ? juntar(semCard, { filtro: { [cardsDim]: [cardSel] } }) : semCard), [semCard, cardSel, cardsDim]);
  const m: MedidaConceito = cd.medidas.includes(mQ as MedidaConceito) ? (mQ as MedidaConceito) : cd.medidas[0];
  const S = useMemo(() => new Set(distsDoEscopo(ds, escopo)), [ds, escopo]);
  const B = useMemo(() => new Set(ds.dists.map((d) => d.dist)), [ds]);
  const brasil = escopo.modo === "brasil";
  const temSelecao = !!cardSel || Object.values(user.filtro).some((v) => v.length);
  const escopoNome = rotuloEscopo(ds, escopo);

  const ess = (ESSENCIAIS[item.conceito!] ?? []).filter((d) => todasDims.includes(d) && d !== cardsDim);
  const fixadas = new Set(Object.entries(base.filtro).filter(([, v]) => v.length === 1).map(([k]) => k));
  const outras = todasDims.filter((d) => !ess.includes(d) && d !== cardsDim && !fixadas.has(d));
  const essenciais = ess.filter((d) => !fixadas.has(d));
  const compat = useMemo(() => dimsCompativeis(cd, recorte), [cd, recorte]);
  const porOpts = todasDims.filter((d) => compat.has(d) && !(recorte.filtro[d]?.length === 1));
  // padrão de análise: a primeira característica que de fato se divide em mais de uma categoria no recorte
  const candidatos = [...(!cardSel && cardsDim ? [cardsDim] : []), ...essenciais, ...porOpts].filter((d, i, a) => porOpts.includes(d) && a.indexOf(d) === i);
  const porDefault = candidatos.find((d) => (distribuicao(cd, d, recorte, cd.medidas[0], S)?.categorias.length ?? 0) > 1) ?? candidatos[0];
  const por = porOpts.includes(porQ) ? porQ : porDefault;

  const total = useMemo(() => agregar(cd, recorte, m, S), [cd, recorte, m, S]);
  const pot = useMemo(() => (m !== "potencia_kva" && cd.medidas.includes("potencia_kva") ? agregar(cd, recorte, "potencia_kva", S) : null), [cd, recorte, m, S]);
  const part = useMemo(() => participacao(cd, base, recorte, m, S, B), [cd, base, recorte, m, S, B]);
  const partBr = useMemo(() => (brasil && temSelecao ? participacao(cd, base, recorte, m, B, B) : null), [cd, base, recorte, m, B, brasil, temSelecao]);
  const cards = useMemo(() => (cardsDim ? distribuicao(cd, cardsDim, semCard, m, S) : null), [cd, cardsDim, semCard, m, S]);
  const cardsPot = useMemo(() => (cardsDim && m === "quantidade" && cd.medidas.includes("potencia_kva") ? distribuicao(cd, cardsDim, semCard, "potencia_kva", S) : null), [cd, cardsDim, semCard, m, S]);
  const totalSemCard = useMemo(() => agregar(cd, semCard, m, S), [cd, semCard, m, S]);
  const dist = por ? distribuicao(cd, por, recorte, m, S) : null;
  const distBr = por && !brasil ? distribuicao(cd, por, recorte, m, B) : null;
  const cubo = escolherCubo(cd, [...Object.keys(recorte.filtro).filter((k) => recorte.filtro[k].length), ...(por ? [por] : [])]);
  const fora = cubo ? foraDoCubo(cd, cubo) : [];
  const somaCat = dist?.categorias.reduce((x, c) => x + (c.v ?? 0), 0) ?? 0;
  const brMap = new Map(distBr?.categorias.map((c) => [c.code, c.v]) ?? []);
  const unidade = UNIDADE[m];
  const at = ativo(ds, item.id);
  const rot = (dim: string) => ds.raw.conceitos!.dimensoes[dim]?.rotulo ?? dim;

  const setFiltro = (dim: string, vals: string[]) => {
    const f = { ...user.filtro, [dim]: vals };
    patch({ f: escreverRecorte(f) || null });
  };
  const opcoes = (dim: string): MultiOption[] => {
    const semDim: Recorte = { filtro: { ...recorte.filtro, [dim]: [] }, excluir: recorte.excluir };
    const d = distribuicao(cd, dim, semDim, m, S);
    const vals = new Map(d?.categorias.map((c) => [c.code, c.v]) ?? []);
    return (cd.valores[dim] ?? []).map((code) => ({ value: code, label: rotulo(cd, dim, code, recorte), meta: vals.has(code) ? comUnidade(vals.get(code), m, true) : "—", keywords: code }))
      .sort((a, b) => (vals.get(b.value) ?? -1) - (vals.get(a.value) ?? -1));
  };
  const filtroPick = (dim: string) => {
    const ok = compat.has(dim) || (user.filtro[dim]?.length ?? 0) > 0;
    return (
      <span key={dim} title={ok ? undefined : "Combinação sem cubo exato calculado: remova outro filtro para usar esta característica."} style={ok ? undefined : { opacity: 0.45, pointerEvents: "none" }}>
        <MultiPick label={rot(dim)} options={ok ? opcoes(dim) : []} value={user.filtro[dim] ?? []} onChange={(v) => setFiltro(dim, v)} allLabel="Todos" testId={`filtro-${dim}`} width={dim === "municipio" ? 360 : 320} />
      </span>
    );
  };
  const [mais, setMais] = useState(false);

  const exportCSV = () => {
    if (!dist || !por) return;
    const nome = `bdgd_2025-12-31_${item.id}_${por}_${m}_${escopo.modo === "brasil" ? "brasil" : escopo.modo === "grupo" ? `grupo-${escopo.grupo}` : "dists"}.csv`;
    downloadText(nome, toCSV(["data_base", "versao", "ativo", "escopo", "distribuidoras", "recorte", "dimensao", "codigo", "categoria", "medida", "unidade", "valor", "participacao_no_recorte", "participacao_brasil_mesma_categoria", "distribuidoras_com_valor", "distribuidoras_nd", "fonte"],
      dist.categorias.map((c) => ["2025-12-31", ds.raw.release.release_id, item.nome, escopoNome, [...S].join(" "), escreverRecorte(recorte.filtro) || "(sem filtro)", rot(por), c.code, c.label, m, unidade, c.v,
        c.v !== null && somaCat ? c.v / somaCat : null, !brasil && c.v !== null && brMap.get(c.code) ? c.v / (brMap.get(c.code) as number) : null, c.n, c.nd,
        `BDGD 2025 (ANEEL); ${cfg.entidades.join(", ")}; DDA M10 / MCPSE`])));
    toast(`${nome} exportado`);
  };

  const chips = [...(cardSel && cardsDim ? [{ k: "card", t: `${rot(cardsDim)}: ${rotulo(cd, cardsDim, cardSel, recorte)}`, clear: () => patch({ c: null }) }] : []),
    ...Object.entries(user.filtro).filter(([, v]) => v.length).map(([dim, v]) => ({ k: dim, t: `${rot(dim)}: ${v.length === 1 ? rotulo(cd, dim, v[0], recorte) : `${v.length} valores`}`, clear: () => setFiltro(dim, []) }))];

  return (
    <div data-testid="conceito-painel">
      <div className={s.head}>
        <div style={{ minWidth: 0 }}>
          <div className="eyebrow">{cfg.nome !== item.nome ? cfg.nome : "Ativo"}{avancado && <> · <span className="mono">{cfg.entidades.join(", ")}{cfg.vinculos ? ` → ${cfg.vinculos.join(", ")}` : ""}</span></>}</div>
          <h2 className={s.title} data-testid="conceito-titulo">{item.nome}</h2>
          <p className={s.desc}>
            {item.descricao ?? cfg.descricao}{" "}
            <Explain title={item.nome} tecnico={at?.tecnico} ressalva={at?.ressalva} testId="explain-conceito">{at?.explicacao ?? cfg.descricao}</Explain>
          </p>
        </div>
        <div className={s.headActions}>
          {cd.medidas.length > 1 && <Segmented label="Medida" size="sm" value={m} onChange={(v) => setM(v)} options={cd.medidas.map((x) => ({ value: x, label: ROTULO_MEDIDA[x] }))} />}
          {avancado && <Button size="sm" variant="ghost" onClick={() => setTecnico((t) => !t)} aria-pressed={tecnico} data-testid="abrir-tecnico"><Code2 size={14} /> Visão por entidade</Button>}
        </div>
      </div>

      {cardsDim && cards && cards.categorias.length > 1 && (
        <div className={s.cards} role="group" aria-label={`Tipos de ${item.nome.toLowerCase()}`} data-testid="cartoes">
          <button type="button" className={s.card} aria-pressed={!cardSel} onClick={() => patch({ c: null, por: null })} data-testid="cartao-todos">
            <span className={s.cardName}>Todos</span>
            <span className={s.cardValue}>{comUnidade(totalSemCard?.v, m, true)}{m !== "quantidade" && <span className={s.cardSub}> {unidade}</span>}</span>
            <span className={s.cardSub}>{cards.categorias.length} {cardsDim === "a1" ? "tipos de bem" : "tipos"}</span>
          </button>
          {cards.categorias.map((c) => {
            const p = cardsPot?.categorias.find((x) => x.code === c.code);
            return (
              <button key={c.code} type="button" className={s.card} aria-pressed={cardSel === c.code} onClick={() => patch({ c: cardSel === c.code ? null : c.code, por: null })} data-testid={`cartao-${c.code}`}>
                <span className={s.cardName}>{c.label}</span>
                <span className={s.cardValue}>{comUnidade(c.v, m, true)}{m !== "quantidade" && <span className={s.cardSub}> {unidade}</span>}</span>
                <span className={s.cardSub}>{p && p.v !== null ? fmtCompact(p.v, "potencia_kva") : totalSemCard?.v ? pct((c.v ?? 0) / totalSemCard.v) + " do total" : ""}</span>
              </button>
            );
          })}
        </div>
      )}

      {(essenciais.length > 0 || outras.length > 0) && (
        <div className={s.filters} role="group" aria-label="Características">
          <span className={s.filtersLabel}><SlidersHorizontal size={13} aria-hidden style={{ verticalAlign: -2 }} /> Características</span>
          {essenciais.map(filtroPick)}
          {outras.length > 0 && !mais && <button type="button" className={s.linkBtn} onClick={() => setMais(true)} data-testid="mais-caracteristicas">Mais características ({outras.length})</button>}
          {mais && outras.map(filtroPick)}
        </div>
      )}
      {chips.length > 0 && (
        <div className={s.chips} aria-label="Recorte aplicado" data-testid="chips-recorte">
          {chips.map((c) => <button key={c.k} type="button" className={s.chip} onClick={c.clear} aria-label={`Remover ${c.t}`}>{c.t} <X size={12} aria-hidden /></button>)}
          <button type="button" className={s.linkBtn} onClick={() => patch({ f: null, c: null, por: null })}>Limpar</button>
        </div>
      )}

      <div className={s.summary} data-testid="resumo">
        <div className={s.sumCell}>
          <div className={s.sumLabel}>{ROTULO_MEDIDA[m]} · {escopoNome}</div>
          <div className={s.sumValue} data-testid="valor-recorte">{comUnidade(total?.v, m)}</div>
          <div className={s.sumFoot}>{total ? (S.size > 1 ? `${total.n} de ${S.size} distribuidoras com o ativo` : total.n ? "valor da distribuidora" : "ativo não cadastrado") : "combinação sem cubo calculado"}{total?.nd ? ` · ${total.nd} sem valor nesta medida` : ""}</div>
        </div>
        {pot && (
          <div className={s.sumCell}>
            <div className={s.sumLabel}>Potência nominal</div>
            <div className={s.sumValue}>{comUnidade(pot.v, "potencia_kva")}</div>
            <div className={s.sumFoot}>{pot.nd ? `${pot.nd} distribuidora(s) sem potência homologada fora da soma` : "mesmo recorte, medida separada"}</div>
          </div>
        )}
        {!brasil && temSelecao && (
          <div className={s.sumCell}>
            <div className={s.sumLabel}>Participação {noEscopo(escopo)}</div>
            <div className={s.sumValue} data-testid="part-escopo">{pct(part.noEscopo)}</div>
            <div className={s.sumFoot}>{part.noEscopo !== null ? `recorte ÷ total de ${item.nome.toLowerCase()} ${noEscopo(escopo)}` : part.motivo}</div>
          </div>
        )}
        {!brasil && (
          <div className={s.sumCell}>
            <div className={s.sumLabel}>Participação no Brasil
              <Explain title="Participação dupla" align="end" tecnico="no escopo = valor(escopo, recorte) / valor(escopo, população do ativo); no Brasil = valor(escopo, recorte) / valor(Brasil, mesmo recorte). Mesma medida e mesmo cubo exato."
                ressalva="Fica N/D quando a combinação não tem cubo calculado ou quando alguma distribuidora não tem valor homologado nesta medida.">
                Duas leituras diferentes: quanto o recorte representa dentro do escopo e quanto o escopo representa do Brasil nesse mesmo recorte. Os denominadores são distintos e não se comparam entre si.
              </Explain>
            </div>
            <div className={s.sumValue} data-testid="part-brasil">{pct(part.doBrasil)}</div>
            <div className={s.sumFoot}>{part.doBrasil !== null ? `${escopoNome} ÷ Brasil, mesmo recorte` : part.motivo}</div>
          </div>
        )}
        {partBr && (
          <div className={s.sumCell}>
            <div className={s.sumLabel}>Participação no total do Brasil</div>
            <div className={s.sumValue} data-testid="part-escopo">{pct(partBr.noEscopo)}</div>
            <div className={s.sumFoot}>{partBr.noEscopo !== null ? `recorte ÷ total de ${item.nome.toLowerCase()} no Brasil` : partBr.motivo}</div>
          </div>
        )}
      </div>

      {item.conceito === "transformadores" && <OndeInstalados ds={ds} dists={[...S]} />}

      {por && (
        <section className={s.analysis} aria-label="Análise por característica" data-testid="analise">
          <div className={s.analysisHead}>
            <div>
              <div className="headline" style={{ fontSize: "1rem" }}>{ROTULO_MEDIDA[m]} por {rot(por).toLowerCase()}</div>
              <div className="caption">{escopoNome} · {unidade}{fora.length ? ` · não inclui ${fora.join(", ")} (sem esse campo)` : ""}</div>
            </div>
            <div className={s.headActions}>
              <Picker label="Analisar por" value={por} compact width={240} options={porOpts.map((d) => ({ value: d, label: rot(d) }))} onChange={(v) => setPor(v)} testId="analisar-por" />
              <Button size="sm" onClick={exportCSV} data-testid="explorar-csv"><Download size={13} /> CSV</Button>
            </div>
          </div>
          {!dist || dist.categorias.length === 0 ? <EmptyState title="Sem dados no recorte">Nenhuma distribuidora do escopo tem este ativo com as características escolhidas.</EmptyState> : (
            <>
              <Barras data={dist.categorias.slice(0, 14)} m={m} onPick={(code) => por === cardsDim ? patch({ c: cardSel === code ? null : code, por: null }) : setFiltro(por, (user.filtro[por] ?? []).includes(code) ? [] : [code])} />
              <table className={s.table} data-testid="tabela-categorias">
                <caption className="sr-only">{ROTULO_MEDIDA[m]} por {rot(por)} em {escopoNome}</caption>
                <thead><tr><th scope="col">{rot(por)}</th><th scope="col">{ROTULO_MEDIDA[m]} ({unidade})</th><th scope="col">No recorte</th>{!brasil && <th scope="col">Do Brasil</th>}<th scope="col">Distribuidoras</th></tr></thead>
                <tbody>
                  {dist.categorias.map((c) => (
                    <tr key={c.code} className={s.row} tabIndex={0} aria-selected={(user.filtro[por] ?? []).includes(c.code) || (por === cardsDim && cardSel === c.code)}
                      onClick={() => por === cardsDim ? patch({ c: cardSel === c.code ? null : c.code, por: null }) : setFiltro(por, (user.filtro[por] ?? []).includes(c.code) ? [] : [c.code])}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); (e.currentTarget as HTMLElement).click(); } }}>
                      <td>{c.label}{avancado && <span className={s.code}>{c.code}</span>}</td>
                      <td>{comUnidade(c.v, m).replace(` ${unidade}`, "")}</td>
                      <td>{c.v !== null && somaCat ? <>{pct(c.v / somaCat)}<span className={s.share}><span className={s.shareFill} style={{ transform: `scaleX(${c.v / somaCat})` }} /></span></> : "N/D"}</td>
                      {!brasil && <td>{c.v !== null && brMap.get(c.code) ? pct(c.v / (brMap.get(c.code) as number)) : "N/D"}</td>}
                      <td className="faint">{c.n}{c.nd ? ` · ${c.nd} N/D` : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className={s.note}><Info size={13} aria-hidden /><span>“No recorte”: parte de cada categoria no total mostrado. {!brasil && "“Do Brasil”: parte do escopo no total brasileiro da mesma categoria. "}Clique numa linha para filtrar.</span></p>
            </>
          )}
        </section>
      )}

      {cfg.inventario && <InventarioObjetos ds={ds} tipo={cfg.inventario} dists={[...S]} />}
      {avancado && tecnico && (
        <div style={{ marginTop: 20 }}>
          <EntidadeTecnica ds={ds} entidades={[...cfg.entidades, ...(cfg.vinculos ?? [])]} dists={S} scope={S.size === 1 ? { tipo: "dist", id: [...S][0] } : { tipo: "brasil" }} />
        </div>
      )}
    </div>
  );
}

/** Instalações transformadoras: onde os equipamentos estão. Mostradas à parte, nunca somadas aos equipamentos. */
function OndeInstalados({ ds, dists }: { ds: Dataset; dists: number[] }) {
  const mt = ds.aggregate(dists, "UNTRMT", "quantidade"), at = ds.aggregate(dists, "UNTRAT", "quantidade");
  return (
    <p className={s.note} data-testid="onde-instalados"><Info size={13} aria-hidden />
      <span>Onde estão instalados: <b className="num">{fmt(mt.v)}</b> instalações transformadoras de distribuição e <b className="num">{fmt(at.v)}</b> de alta tensão no escopo. Instalações são o local do equipamento e não são somadas aos transformadores.</span>
    </p>
  );
}

function Barras({ data, m, onPick }: { data: Array<{ code: string; label: string; v: number | null }>; m: MedidaConceito; onPick: (code: string) => void }) {
  const build = useCallback((t: ChartTokens) => ({
    grid: { left: 8, right: 70, top: 10, bottom: 4, containLabel: true },
    tooltip: { trigger: "item", backgroundColor: t.surface, borderColor: t.hairline, textStyle: { color: t.text, fontFamily: t.font, fontSize: 12 },
      formatter: (q: { dataIndex: number }) => `<b>${data[q.dataIndex].label}</b><br/>${comUnidade(data[q.dataIndex].v, m)}${m === "quantidade" ? " itens" : ""}` },
    xAxis: { type: "value", show: false },
    yAxis: { type: "category", inverse: true, data: data.map((c) => (c.label.length > 36 ? c.label.slice(0, 35) + "…" : c.label)), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: t.text2, fontFamily: t.font, fontSize: 11 } },
    series: [{ type: "bar", barWidth: 11, data: data.map((c) => ({ value: c.v ?? 0, itemStyle: { color: c.v === null ? t.nd : t.accent, borderRadius: 3 } })),
      label: { show: true, position: "right", color: t.text2, fontFamily: t.font, fontSize: 11, formatter: (q: { dataIndex: number }) => fmtCompact(data[q.dataIndex].v, m) } }],
  }), [data, m]);
  return <EChart build={build} height={Math.max(140, data.length * 26 + 20)} ariaLabel="Distribuição por categoria; os valores estão na tabela abaixo" onClickIndex={(i) => onPick(data[i].code)} testId="chart-categorias" />;
}
