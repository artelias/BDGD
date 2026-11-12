"use client";
import { Info, TriangleAlert } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Feedback";
import { Segmented } from "@/components/ui/Segmented";
import { Pill } from "@/components/ui/Value";
import { MESES, NOME_IND, ROTULO_ALERTA, UNIDADE_IND, acumulado, faixasDeExtensao, fmtInd, fmtMetrica, histograma, limiteInd, num, percentilDe, razaoLimite, resumo, situacao, valorInd, variacao } from "@/lib/confiabilidade/calculo";
import { acumuladoNoAno, anualContraLimite, barrasSimples } from "@/lib/confiabilidade/graficos";
import type { Conjunto, DistDoc, Indicador, Indice } from "@/lib/confiabilidade/tipos";
import s from "./conf.module.css";

const pct = (v: number | null, d = 0) => (v === null ? "N/D" : `${(v * 100).toLocaleString("pt-BR", { maximumFractionDigits: d })}%`);

/** Marcador da posição do conjunto entre os conjuntos da mesma distribuidora (0 = menor valor, 1 = maior). Posição, não nota. */
function Posicao({ p }: { p: number | null }) {
  if (p === null) return <span className="faint">N/D</span>;
  return <span className={s.pos} title={`${Math.round(p * 100)}% dos conjuntos da distribuidora têm valor menor ou igual`}><span className={s.trilho} aria-hidden><i style={{ left: `calc(${Math.round(p * 100)}% - 1px)` }} /></span>P{Math.round(p * 100)}</span>;
}

export function FichaConjunto({ indice, doc, conj, ano, ind, onA, onB, onFechar }: {
  indice: Indice; doc: DistDoc; conj: Conjunto; ano: number; ind: Indicador;
  onA: () => void; onB: () => void; onFechar: () => void;
}) {
  const [vistaInfra, setVistaInfra] = useState<"relativas" | "absolutas">("relativas");
  const [limiares, setLimiares] = useState<[number, number]>([10, 40]);
  const b = conj.a[String(ano)] ?? null, ant = conj.a[String(ano - 1)] ?? null;
  const I = NOME_IND[ind];
  const v = valorInd(b, ind), lim = limiteInd(b, ind), r = razaoLimite(v, lim), sit = situacao(v, lim);
  const dv = variacao(v, valorInd(ant, ind));
  const irmaos = useMemo(() => doc.conjuntos.map((c) => c.a[String(ano)]).filter(Boolean), [doc, ano]);
  const posInd = percentilDe(v, irmaos.map((x) => valorInd(x, ind)));
  const resDist = resumo(irmaos.map((x) => valorInd(x, ind)));
  const anos = useMemo(() => indice.anos.map(String), [indice]);

  const gAcum = useCallback((t: ChartTokens) => {
    const atual = conj.a[String(ano)] ?? null, anterior = conj.a[String(ano - 1)] ?? null, nome = NOME_IND[ind];
    return acumuladoNoAno(t, { meses: MESES, atual: acumulado(atual?.m[ind] ?? []), anterior: anterior ? acumulado(anterior.m[ind]) : null, limite: limiteInd(atual, ind),
      rotAtual: `${nome} acumulado em ${ano}`, rotAnterior: `${nome} acumulado em ${ano - 1}`, unidade: UNIDADE_IND[ind] });
  }, [conj, ano, ind]);
  const gAnual = useCallback((t: ChartTokens) => anualContraLimite(t, {
    anos, obs: anos.map((a) => valorInd(conj.a[a], ind)), lim: anos.map((a) => limiteInd(conj.a[a], ind)), unidade: UNIDADE_IND[ind], nome: NOME_IND[ind],
  }), [anos, conj, ind]);

  const metricas = indice.metricas.filter((m) => (vistaInfra === "relativas" ? m.tipo === "razao" || m.tipo === "pct" : m.tipo === "contagem" || m.tipo === "continua"));
  const grupos = [...new Set(metricas.map((m) => m.grupo))];
  const al = useMemo(() => conj.al?.lista.filter((a) => num(a.km_mt) && a.km_mt > 0) ?? [], [conj]);
  const faixas = faixasDeExtensao(al.map((a) => a.km_mt), limiares);
  const hist = useMemo(() => histograma(al.map((a) => a.km_mt), Math.min(10, Math.max(3, al.length))), [al]);
  const gHist = useCallback((t: ChartTokens) => barrasSimples(t, { rotulos: hist.map((h) => `${h.de.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}–${h.ate.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`), valores: hist.map((h) => h.n), unidade: "alimentadores" }), [hist]);
  const comp = b?.comp[ind];

  return (
    <section className={s.secao} aria-label={`Diagnóstico técnico do conjunto ${conj.n}`} data-testid="conf-ficha">
      <div className={s.fichaTopo}>
        <div>
          <div className="eyebrow">Conjunto elétrico {conj.c} · {doc.nome} · {ano}</div>
          <h2 className="title" style={{ marginTop: 4 }} data-testid="conf-ficha-nome">{conj.n}</h2>
        </div>
        <div className={s.acoes}>
          <Button size="sm" onClick={onA} data-testid="conf-add-a">Comparar como A</Button>
          <Button size="sm" onClick={onB} data-testid="conf-add-b">Comparar como B</Button>
          <Button size="sm" variant="ghost" onClick={onFechar}>Fechar</Button>
        </div>
      </div>

      {!b ? <EmptyState title={`Sem apuração de continuidade em ${ano}`}>Este conjunto não tem DEC/FEC publicados pela ANEEL para o ano escolhido (pode ter sido criado depois ou extinto antes). Escolha outro ano.</EmptyState> : <>
        {b.alertas.length > 0 && <ul className={s.avisos}>{b.alertas.map((a) => <li key={a}><TriangleAlert size={14} aria-hidden />{ROTULO_ALERTA[a] ?? a}</li>)}</ul>}

        <div className={s.bloco}>
          <p className={s.blocoTitulo}>Qualidade do fornecimento <Pill tone="ok" title="Publicado pela ANEEL nos dados abertos de continuidade">oficial ANEEL</Pill></p>
          <div className={s.kpis}>
            {(["dec", "fec"] as Indicador[]).map((k) => {
              const vv = valorInd(b, k), ll = limiteInd(b, k), rr = razaoLimite(vv, ll), st = situacao(vv, ll);
              return (
                <div className={s.kpi} key={k} data-testid={`conf-kpi-${k}`}>
                  <div className={s.kpiRotulo}>{NOME_IND[k]} apurado · {UNIDADE_IND[k]}</div>
                  <div className={s.kpiValor}>{fmtInd(vv)}</div>
                  <div className={`${s.kpiSub} ${st === "acima" ? s.acima : st === "dentro" ? s.dentro : s.nd}`}>
                    {ll === null ? "sem limite publicado" : <>limite {fmtInd(ll)} · {rr === null ? "N/D" : `${pct(rr)} do limite`}</>}
                  </div>
                </div>
              );
            })}
            <div className={s.kpi}>
              <div className={s.kpiRotulo}>{I} contra {ano - 1}</div>
              <div className={s.kpiValor}>{dv ? `${dv.abs > 0 ? "+" : ""}${fmtInd(dv.abs)}` : "N/D"}</div>
              <div className={s.kpiSub}>{dv?.rel != null ? `${dv.rel > 0 ? "+" : ""}${pct(dv.rel, 1)}` : ant ? "sem valor no ano anterior" : "ano anterior fora do período"}</div>
            </div>
            <div className={s.kpi}>
              <div className={s.kpiRotulo}>Consumidores (NumCon médio)</div>
              <div className={s.kpiValor}>{num(b.nuc) ? b.nuc.toLocaleString("pt-BR") : "N/D"}</div>
              <div className={s.kpiSub}>denominador regulatório · {b.meses_dec} de 12 meses apurados</div>
            </div>
            <div className={s.kpi}>
              <div className={s.kpiRotulo}>Posição do {I} na distribuidora</div>
              <div className={s.kpiValor} style={{ fontSize: "1rem", marginTop: 6 }}><Posicao p={posInd} /></div>
              <div className={s.kpiSub}>{resDist ? `mediana dos ${resDist.n} conjuntos: ${fmtInd(resDist.mediana)}` : "N/D"}</div>
            </div>
          </div>
        </div>

        <div className={s.duas} style={{ marginTop: 16 }}>
          <div className={s.bloco}>
            <p className={s.blocoTitulo}>{I} acumulado ao longo de {ano}</p>
            <p className={s.blocoSub}>Soma dos valores mensais apurados; o limite regulatório vale para o ano inteiro. {sit === "acima" ? "O acumulado ultrapassou o limite." : sit === "dentro" ? "O acumulado ficou dentro do limite." : ""}</p>
            <EChart build={gAcum} height={230} ariaLabel={`${I} acumulado mês a mês em ${ano} do conjunto ${conj.n}, com o limite anual`} testId="conf-g-acumulado" />
          </div>
          <div className={s.bloco}>
            <p className={s.blocoTitulo}>{I} anual e limite, 2022–2025</p>
            <p className={s.blocoSub}>Barras: valor apurado no ano. Marcadores: limite regulatório do mesmo ano.</p>
            <EChart build={gAnual} height={230} ariaLabel={`${I} anual apurado e limite regulatório do conjunto ${conj.n} de 2022 a 2025`} testId="conf-g-anual" />
          </div>
        </div>

        <div className={s.duas} style={{ marginTop: 16 }}>
          <div className={s.bloco}>
            <p className={s.blocoTitulo}>Origem das interrupções no {I} de {ano}</p>
            <p className={s.blocoSub}>Componentes publicados pela ANEEL. As parcelas expurgadas (dia crítico, situação de emergência e afins) não compõem o indicador apurado.</p>
            {comp ? (
              <table className={s.tabela}>
                <thead><tr><th scope="col">Componente</th><th scope="col">{UNIDADE_IND[ind]}</th><th scope="col">Parcela do {I}</th></tr></thead>
                <tbody>
                  {([["Interna, não programada", comp.ind], ["Interna, programada", comp.ip], ["Externa, não programada", comp.xn], ["Externa, programada", comp.xp]] as Array<[string, number | null]>).map(([nome, x]) => (
                    <tr key={nome}><td>{nome}</td><td>{fmtInd(x)}</td><td>{num(x) && num(v) && v > 0 ? <><span className={s.barra} style={{ width: `${Math.round((60 * x) / v)}px` }} aria-hidden /> {pct(x / v)}</> : <span className="faint">N/D</span>}</td></tr>
                  ))}
                  <tr><td>Expurgado (fora do {I})</td><td>{fmtInd(comp.exp)}</td><td className="faint">não compõe</td></tr>
                </tbody>
              </table>
            ) : <span className="faint">N/D</span>}
          </div>
          <div className={s.bloco}>
            <p className={s.blocoTitulo}>Reconstrução a partir da BDGD <Pill tone={b.rec?.estado === "RECONSTRUIDO_VALIDADO" ? "ok" : "nd"}>{b.rec ? (b.rec.estado === "RECONSTRUIDO_VALIDADO" ? "reconciliada" : "divergente") : "indisponível"}</Pill></p>
            <p className={s.blocoSub}>Auditoria: soma dos DIC/FIC mensais das unidades consumidoras da BDGD dividida pelo NumCon oficial de cada mês. O valor oficial é sempre a referência; o reconstruído nunca o substitui.</p>
            {b.rec ? (
              <table className={s.tabela} data-testid="conf-reconstrucao">
                <thead><tr><th scope="col">Indicador</th><th scope="col">Oficial</th><th scope="col">Reconstruído</th><th scope="col">Diferença</th><th scope="col">Com denominador da BDGD</th></tr></thead>
                <tbody>
                  <tr><td>DEC</td><td>{fmtInd(b.dec)}</td><td>{fmtInd(b.rec.dec)}</td><td>{fmtInd(b.rec.dif_dec)}</td><td>{fmtInd(b.rec.dec_bdgd)}</td></tr>
                  <tr><td>FEC</td><td>{fmtInd(b.fec)}</td><td>{fmtInd(b.rec.fec)}</td><td>{fmtInd(b.rec.dif_fec)}</td><td>{fmtInd(b.rec.fec_bdgd)}</td></tr>
                </tbody>
              </table>
            ) : <span className="faint">Sem DIC/FIC utilizáveis na BDGD deste conjunto e ano.</span>}
            <p className={s.nota}><Info size={13} aria-hidden />A fotografia da BDGD é de 31/12; o NumCon regulatório muda mês a mês. Por isso a coluna com o denominador da BDGD é só comparativa.</p>
          </div>
        </div>

        <div className={s.secaoTopo} style={{ marginTop: 22 }}>
          <h3 className="headline">Infraestrutura física <Pill tone="nd" title="Agregado calculado neste módulo a partir da BDGD; não homologado">derivado da BDGD · exploratório</Pill></h3>
          <span className={s.espaco} />
          <Segmented label="Tipo de métrica" size="sm" value={vistaInfra} onChange={setVistaInfra} options={[{ value: "relativas", label: "Relativas" }, { value: "absolutas", label: "Absolutas" }]} />
        </div>
        {!b.infra ? <EmptyState title="Infraestrutura indisponível neste ano">{b.infra_motivo ?? "Sem dados da BDGD para este conjunto e ano."} A continuidade oficial continua disponível acima.</EmptyState> : (
          <div className={`${s.bloco} ${s.rolagem}`}>
            <table className={s.tabela} data-testid="conf-infra">
              <thead><tr><th scope="col">Métrica</th><th scope="col">{ano}</th><th scope="col" style={{ textAlign: "left" }}>Unidade</th><th scope="col">{ano - 1}</th><th scope="col">Posição na distribuidora</th></tr></thead>
              <tbody>
                {grupos.flatMap((g) => [
                  <tr key={`g-${g}`} className={s.grupo}><td colSpan={5}>{g}</td></tr>,
                  ...metricas.filter((m) => m.grupo === g).map((m) => (
                    <tr key={m.id} title={m.definicao}>
                      <td>{m.nome}</td>
                      <td>{b.infra![m.id] === null && m.id === "uc_mt_at" ? <span className="faint">suprimido</span> : fmtMetrica(b.infra![m.id], m)}</td>
                      <td className={s.un}>{m.unidade}</td>
                      <td className="faint">{fmtMetrica(ant?.infra?.[m.id], m)}</td>
                      <td><Posicao p={percentilDe(b.infra![m.id], irmaos.map((x) => x.infra?.[m.id]))} /></td>
                    </tr>
                  )),
                ])}
              </tbody>
            </table>
            <p className={s.nota}><Info size={13} aria-hidden />Posição: percentil do valor entre os conjuntos de {doc.nome} em {ano} (P50 = mediana). Descreve a estrutura; não é nota de desempenho. Passe o cursor sobre a linha para ver a definição.</p>
          </div>
        )}

        <div className={s.secaoTopo} style={{ marginTop: 22 }}>
          <h3 className="headline">Composição por alimentador{conj.al ? ` · ${conj.al.ano}` : ""}</h3>
          <span className={s.espaco} />
          <span className={s.limiares}>Faixas (km):
            <input type="number" min={1} max={500} value={limiares[0]} aria-label="Limite entre curto e médio, em km" onChange={(e) => { const x = Number(e.target.value); if (x > 0 && x < limiares[1]) setLimiares([x, limiares[1]]); }} />
            <input type="number" min={2} max={1000} value={limiares[1]} aria-label="Limite entre médio e longo, em km" onChange={(e) => { const x = Number(e.target.value); if (x > limiares[0]) setLimiares([limiares[0], x]); }} />
          </span>
        </div>
        {!al.length ? <EmptyState title="Sem vínculo de alimentadores">A BDGD deste conjunto não traz trechos de rede MT com alimentador (CTMT) identificado.</EmptyState> : (
          <div className={s.duas}>
            <div className={s.bloco}>
              <p className={s.blocoTitulo}>Extensão MT dos alimentadores dentro do conjunto</p>
              <p className={s.blocoSub}>{al.length} alimentadores com rede no conjunto. As faixas são parâmetros de leitura que você pode alterar; não são padrão regulatório.</p>
              <table className={s.tabela}><tbody>{faixas.map((f) => <tr key={f.rotulo}><td>{f.rotulo}</td><td>{f.n} alim.</td><td>{f.km.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} km</td></tr>)}</tbody></table>
              <EChart build={gHist} height={170} ariaLabel="Distribuição da extensão MT dos alimentadores dentro do conjunto, em km" />
            </div>
            <div className={`${s.bloco} ${s.rolagem}`} style={{ maxHeight: 420, overflowY: "auto" }}>
              <p className={s.blocoTitulo}>Alimentadores</p>
              <p className={s.blocoSub}>Parcela de cada alimentador dentro deste conjunto, pelos vínculos cadastrais (CTMT). O DEC/FEC do conjunto não é atribuído a alimentadores.</p>
              <table className={s.tabela} data-testid="conf-alimentadores">
                <thead><tr><th scope="col">Alimentador</th><th scope="col">km MT</th><th scope="col">Consumidores</th><th scope="col">Trafos</th><th scope="col">Seccion.</th><th scope="col">Relig.</th><th scope="col">Telecom.</th></tr></thead>
                <tbody>{al.map((a) => {
                  const uc = a.uc_suprimido || (a.uc_bt === null && a.uc_mt === null) ? null : (a.uc_bt ?? 0) + (a.uc_mt ?? 0);
                  return (
                    <tr key={a.ctmt}>
                      <td><span className={s.nomeConj}>{a.nome || a.ctmt}</span><span className={s.sub}>{a.sub_nome ?? "subestação N/D"}{a.predominante ? "" : " · predominante em outro conjunto"}</span></td>
                      <td>{fmtMetrica(a.km_mt, { tipo: "continua" })}</td>
                      <td>{a.uc_suprimido ? <span className="faint" title={`Menos de ${indice.supressao_k} unidades: não publicado`}>suprimido</span> : fmtMetrica(uc, { tipo: "contagem" })}</td>
                      <td>{fmtMetrica(a.trafos, { tipo: "contagem" })}</td><td>{fmtMetrica(a.sec, { tipo: "contagem" })}</td><td>{fmtMetrica(a.religadores, { tipo: "contagem" })}</td><td>{fmtMetrica(a.telecomandadas, { tipo: "contagem" })}</td>
                    </tr>
                  );
                })}</tbody>
              </table>
            </div>
          </div>
        )}
      </>}
    </section>
  );
}
