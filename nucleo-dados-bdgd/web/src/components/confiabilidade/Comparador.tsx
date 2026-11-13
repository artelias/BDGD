"use client";
import { ArrowLeftRight, Download, Info } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { EChart, type ChartTokens } from "@/components/charts/EChart";
import { Button } from "@/components/ui/Button";
import { EmptyState, LoadingBlock, downloadText } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { toCSV } from "@/lib/format";
import { NOME_IND, UNIDADE_IND, anualCompleto, chave, comparar, fmtInd, fmtMetrica, frasesComparacao, limiteInd, linhasNacionais, num, paresSemelhantes, razaoLimite, resumo, valorComparavel, valorInd, type Linha } from "@/lib/confiabilidade/calculo";
import { useDist, useNacional } from "@/lib/confiabilidade/dados";
import type { EstadoConf, Lado } from "@/lib/confiabilidade/estado";
import { linhasAnuais } from "@/lib/confiabilidade/graficos";
import type { BlocoAno, Conjunto, Indicador, Indice } from "@/lib/confiabilidade/tipos";
import s from "./conf.module.css";

const pct = (v: number | null, d = 0) => (v === null ? "N/D" : `${v > 0 ? "+" : ""}${(v * 100).toLocaleString("pt-BR", { maximumFractionDigits: d })}%`);

function EscolhaLado({ k, indice, lado, conjuntos, carregando, onChange }: {
  k: "a" | "b"; indice: Indice; lado: Lado | null; conjuntos: Conjunto[] | null; carregando: boolean; onChange: (l: string | null) => void;
}) {
  const d = lado ? indice.distribuidoras.find((x) => x.dist === lado.dist) : null;
  const c = lado && conjuntos ? conjuntos.find((x) => x.c === lado.conj) : null;
  return (
    <div className={s.lado} style={{ ["--c" as string]: `var(--side-${k})` }} data-testid={`conf-lado-${k}`}>
      <div><span className={s.ladoTag} aria-hidden>{k.toUpperCase()}</span><b>{c ? c.n : lado && carregando ? "Carregando…" : "Escolha um conjunto"}</b></div>
      <div className="faint" style={{ fontSize: "var(--fs-caption)", marginTop: 2 }}>{d ? `${d.nome}${d.grupo_nome ? ` · grupo ${d.grupo_nome}` : ""}${c ? ` · conjunto ${c.c}` : ""}` : "Empresa e conjunto"}</div>
      <div className={s.ladoPick}>
        <Picker label={`Empresa ${k.toUpperCase()}`} compact width={230} value={lado ? String(lado.dist) : null} searchPlaceholder="Buscar distribuidora" testId={`conf-${k}-dist`}
          onChange={(v) => onChange(`${v}-0`)} options={[...indice.distribuidoras].sort((x, y) => x.nome.localeCompare(y.nome, "pt-BR")).map((x) => ({ value: String(x.dist), label: x.nome, group: x.grupo_nome ?? "Sem grupo verificado", keywords: `${x.sigla} ${x.agente_aneel}` }))} />
        <Picker label={`Conjunto ${k.toUpperCase()}`} compact width={230} value={c ? String(c.c) : null} searchPlaceholder="Buscar conjunto" testId={`conf-${k}-conj`} placeholder={lado ? "Selecionar conjunto" : "Escolha a empresa"}
          onChange={(v) => lado && onChange(`${lado.dist}-${v}`)} options={(conjuntos ?? []).slice().sort((x, y) => x.n.localeCompare(y.n, "pt-BR")).map((x) => ({ value: String(x.c), label: x.n, meta: String(x.c) }))} />
      </div>
    </div>
  );
}

export function Comparador({ indice, e }: { indice: Indice; e: EstadoConf }) {
  const [vista, setVista] = useState<"relativas" | "absolutas">("relativas");
  const docA = useDist(e.a?.dist ?? null), docB = useDist(e.b?.dist ?? null);
  const nacional = useNacional(e.ano);
  const ano = String(e.ano), I = NOME_IND[e.ind];
  const cA = e.a && docA.dados ? docA.dados.conjuntos.find((c) => c.c === e.a!.conj) ?? null : null;
  const cB = e.b && docB.dados ? docB.dados.conjuntos.find((c) => c.c === e.b!.conj) ?? null : null;
  const bA: BlocoAno | null = cA?.a[ano] ?? null, bB: BlocoAno | null = cB?.a[ano] ?? null;
  const nomeA = cA ? `${cA.n} (A)` : "A", nomeB = cB ? `${cB.n} (B)` : "B";

  const universo = useMemo(() => (nacional.dados ? linhasNacionais(nacional.dados) : null), [nacional.dados]);
  const pares = useMemo(() => {
    const de = (l: Lado | null) => {
      const alvo = l && universo ? universo.find((x) => chave(x) === `${l.dist}:${l.conj}`) : null;
      if (!alvo || !universo) return { alvo: null as Linha | null, mediana: null as number | null, n: 0 };
      const r = paresSemelhantes(alvo, universo, 20);
      return { alvo, mediana: resumo(r.pares.map((p) => p.linha[e.ind]))?.mediana ?? null, n: r.pares.length };
    };
    return { a: de(e.a), b: de(e.b) };
  }, [universo, e.a, e.b, e.ind]);
  // a distância usa as escalas do universo nacional (não só dos dois conjuntos)
  const dist2 = useMemo(() => {
    if (!pares.a.alvo || !pares.b.alvo || !universo) return null;
    const r = paresSemelhantes(pares.a.alvo, universo, universo.length);
    return r.pares.find((p) => chave(p.linha) === chave(pares.b.alvo!))?.distancia ?? null;
  }, [pares, universo]);

  const linhas = useMemo(() => comparar(bA?.infra ?? null, bB?.infra ?? null, indice.metricas).filter((l) => (vista === "relativas" ? l.tipo === "razao" || l.tipo === "pct" : l.tipo === "contagem" || l.tipo === "continua")), [bA, bB, indice, vista]);
  const frases = useMemo(() => (cA && cB ? frasesComparacao({ nomeA: cA.n, nomeB: cB.n, ind: e.ind, a: bA, b: bB, metricas: indice.metricas, medianaParesA: pares.a.mediana, medianaParesB: pares.b.mediana, distancia: dist2 }) : []), [cA, cB, bA, bB, e.ind, indice, pares, dist2]);
  const anos = indice.anos.map(String);
  // ano com apuração parcial fica fora da linha (lacuna), como no resto do comparador; a nota abaixo do gráfico diz quais
  const parciaisEvol = ([["A", cA], ["B", cB]] as const).flatMap(([lado, c]) => anos.filter((a) => c?.a[a] && num(valorInd(c.a[a], e.ind)) && !anualCompleto(c.a[a], e.ind)).map((a) => `${lado} em ${a}`));
  const gEvol = useCallback((t: ChartTokens) => linhasAnuais(t, { anos, unidade: UNIDADE_IND[e.ind], series: [
    { nome: nomeA, dados: anos.map((a) => valorComparavel(cA?.a[a], e.ind)), cor: t.sideA }, { nome: nomeB, dados: anos.map((a) => valorComparavel(cB?.a[a], e.ind)), cor: t.sideB },
    { nome: "Limite de A", dados: anos.map((a) => limiteInd(cA?.a[a], e.ind)), cor: t.sideA, tracejada: true }, { nome: "Limite de B", dados: anos.map((a) => limiteInd(cB?.a[a], e.ind)), cor: t.sideB, tracejada: true },
  ] }), [anos, cA, cB, e.ind, nomeA, nomeB]);

  const exportar = () => {
    // A − B só entre valores anuais completos, como na tela (auditoria de 13/11/2026: o CSV subtraía o FEC parcial da Elektro 2025)
    const cab = ["metrica", "unidade", "A", "B", "A_menos_B", "diferenca_relativa", "conjunto_A", "conjunto_B", "ano", "observacao"];
    const parcial = (k: Indicador) => ([["A", bA], ["B", bB]] as const).flatMap(([lado, b]) => (b && num(valorInd(b, k)) && valorComparavel(b, k) === null ? [`apuração parcial em ${lado} (${k === "dec" ? b.meses_dec : b.meses_fec} de 12 meses): fora da diferença e do limite`] : [])).join("; ");
    const qual: Array<Array<string | number | null>> = (["dec", "fec"] as Indicador[]).flatMap((k) => {
      const ca = valorComparavel(bA, k), cb = valorComparavel(bB, k);
      return [
        [`${NOME_IND[k]} apurado (oficial ANEEL)`, UNIDADE_IND[k], valorInd(bA, k), valorInd(bB, k), num(ca) && num(cb) ? Number((ca - cb).toFixed(2)) : null, null, cA?.n ?? "", cB?.n ?? "", ano, parcial(k)],
        [`${NOME_IND[k]} limite`, UNIDADE_IND[k], limiteInd(bA, k), limiteInd(bB, k), null, null, cA?.n ?? "", cB?.n ?? "", ano, ""],
      ];
    });
    const inf = comparar(bA?.infra ?? null, bB?.infra ?? null, indice.metricas).map((l) => [l.nome, l.unidade, l.a, l.b, l.dif === null ? null : Number(l.dif.toFixed(4)), l.rel === null ? null : Number(l.rel.toFixed(4)), cA?.n ?? "", cB?.n ?? "", ano, "derivado BDGD"]);
    downloadText(`confiabilidade_comparacao_${e.a?.dist}-${e.a?.conj}_x_${e.b?.dist}-${e.b?.conj}_${ano}.csv`, toCSV(cab, [...qual, ...inf]));
  };
  const maxRel = (a: number | null, b: number | null) => (num(a) && num(b) ? Math.max(Math.abs(a), Math.abs(b)) : null);

  return (
    <>
      <div className={s.filtros} role="toolbar" aria-label="Período e indicador da comparação">
        <Segmented label="Indicador" value={e.ind} onChange={(v) => e.set({ ind: v === "dec" ? null : v })} options={[{ value: "dec", label: "DEC" }, { value: "fec", label: "FEC" }]} />
        <Picker label="Ano" compact value={ano} width={110} onChange={(v) => e.set({ ano: v })} options={indice.anos.map((a) => ({ value: String(a), label: String(a) }))} />
        <Button size="sm" variant="ghost" onClick={() => e.set({ a: e.b ? `${e.b.dist}-${e.b.conj}` : null, b: e.a ? `${e.a.dist}-${e.a.conj}` : null })} aria-label="Trocar A e B" data-testid="conf-trocar"><ArrowLeftRight size={15} aria-hidden /> Trocar</Button>
        <span className={s.espaco} />
        <Button size="sm" onClick={exportar} disabled={!cA || !cB} data-testid="conf-csv"><Download size={14} aria-hidden /> CSV</Button>
      </div>
      <div className={s.lados}>
        <EscolhaLado k="a" indice={indice} lado={e.a} conjuntos={docA.dados?.conjuntos ?? null} carregando={docA.carregando} onChange={(v) => e.set({ a: v })} />
        <EscolhaLado k="b" indice={indice} lado={e.b} conjuntos={docB.dados?.conjuntos ?? null} carregando={docB.carregando} onChange={(v) => e.set({ b: v })} />
      </div>

      {(e.a && docA.carregando) || (e.b && docB.carregando) ? <LoadingBlock label="Carregando conjuntos" /> : !cA || !cB ? (
        <EmptyState title="Escolha os dois conjuntos">Selecione a empresa e o conjunto de cada lado. Vale comparar conjuntos da mesma distribuidora ou de empresas diferentes; o ano e as definições são os mesmos nos dois lados.</EmptyState>
      ) : <>
        <div className={s.duas}>
          <div className={s.bloco}>
            <p className={s.blocoTitulo}>Continuidade em {ano} <span className="faint">· oficial ANEEL</span></p>
            <table className={s.tabela} data-testid="conf-comp-qualidade">
              <thead><tr><th scope="col">Indicador</th><th scope="col"><span className={s.vA}>A</span></th><th scope="col"><span className={s.vB}>B</span></th><th scope="col">A − B</th></tr></thead>
              <tbody>
                {(["dec", "fec"] as Indicador[]).flatMap((k) => {
                  const a = valorInd(bA, k), b = valorInd(bB, k), ca = valorComparavel(bA, k), cb = valorComparavel(bB, k), ra = razaoLimite(ca, limiteInd(bA, k)), rb = razaoLimite(cb, limiteInd(bB, k));
                  const parc = (v: number | null, c: number | null) => (num(v) && c === null ? <span className={s.sub}>apuração parcial</span> : null);
                  return [
                    <tr key={k}><td>{NOME_IND[k]} apurado <span className="faint">({UNIDADE_IND[k]})</span></td><td className={s.vA}>{fmtInd(a)}{parc(a, ca)}</td><td className={s.vB}>{fmtInd(b)}{parc(b, cb)}</td><td>{num(ca) && num(cb) ? fmtInd(ca - cb) : "N/D"}</td></tr>,
                    <tr key={`${k}l`}><td>{NOME_IND[k]} limite</td><td>{fmtInd(limiteInd(bA, k))}</td><td>{fmtInd(limiteInd(bB, k))}</td><td className="faint">—</td></tr>,
                    <tr key={`${k}r`}><td>{NOME_IND[k]} ÷ limite</td><td className={ra === null ? s.nd : ra > 1 ? s.acima : s.dentro}>{ra === null ? "N/D" : `${Math.round(ra * 100)}%`}</td><td className={rb === null ? s.nd : rb > 1 ? s.acima : s.dentro}>{rb === null ? "N/D" : `${Math.round(rb * 100)}%`}</td><td>{ra !== null && rb !== null ? `${Math.round((ra - rb) * 100)} p.p.` : "N/D"}</td></tr>,
                  ];
                })}
                <tr><td>Consumidores (NumCon médio)</td><td>{fmtMetrica(bA?.nuc, { tipo: "contagem" })}</td><td>{fmtMetrica(bB?.nuc, { tipo: "contagem" })}</td><td className="faint">—</td></tr>
                <tr><td>{I}: mediana dos 20 pares mais semelhantes</td><td>{fmtInd(pares.a.mediana)}</td><td>{fmtInd(pares.b.mediana)}</td><td className="faint">—</td></tr>
              </tbody>
            </table>
          </div>
          <div className={s.bloco}>
            <p className={s.blocoTitulo}>{I} e limites, 2022–2025</p>
            <p className={s.blocoSub}>Linhas cheias: apurado. Tracejadas: limite regulatório de cada conjunto.</p>
            <EChart build={gEvol} height={236} ariaLabel={`${I} anual dos conjuntos A e B de 2022 a 2025, com os limites`} testId="conf-g-comp" />
            {parciaisEvol.length > 0 && <p className={s.nota} data-testid="conf-g-comp-parcial"><Info size={13} aria-hidden />Fora da linha por apuração parcial (menos de 12 meses): {parciaisEvol.join(", ")}.</p>}
          </div>
        </div>

        <div className={s.bloco} style={{ marginTop: 16 }}>
          <p className={s.blocoTitulo}>Leitura da comparação</p>
          <p className={s.blocoSub}>Frases geradas por regra a partir dos valores acima. Descrevem diferenças; não indicam causa.</p>
          <ul className={s.frases} data-testid="conf-frases">{frases.map((f) => <li key={f}>{f}</li>)}</ul>
        </div>

        <div className={s.secaoTopo} style={{ marginTop: 22 }}>
          <h3 className="headline">Infraestrutura em {ano}</h3>
          <span className={s.espaco} />
          <Segmented label="Tipo de métrica" size="sm" value={vista} onChange={setVista} options={[{ value: "relativas", label: "Normalizadas" }, { value: "absolutas", label: "Absolutas" }]} />
        </div>
        {!bA?.infra && !bB?.infra ? <EmptyState title="Sem infraestrutura nos dois conjuntos">A BDGD de {ano} não tem agregados utilizáveis para estes conjuntos.</EmptyState> : (
          <div className={`${s.bloco} ${s.rolagem}`}>
            <table className={s.tabela} data-testid="conf-comp-infra">
              <thead><tr><th scope="col">Métrica</th><th scope="col"><span className={s.vA}>A</span></th><th scope="col"><span className={s.vB}>B</span></th><th scope="col" style={{ textAlign: "left" }}>Unidade</th><th scope="col">A − B</th><th scope="col">Dif. relativa</th><th scope="col" style={{ textAlign: "left" }}>Proporção entre A e B</th></tr></thead>
              <tbody>
                {[...new Set(linhas.map((l) => l.grupo))].flatMap((g) => [
                  <tr key={`g-${g}`} className={s.grupo}><td colSpan={7}>{g}</td></tr>,
                  ...linhas.filter((l) => l.grupo === g).map((l) => {
                    const mx = maxRel(l.a, l.b);
                    return (
                      <tr key={l.id} title={indice.metricas.find((m) => m.id === l.id)?.definicao}>
                        <td>{l.nome}</td><td className={s.vA}>{fmtMetrica(l.a, l)}</td><td className={s.vB}>{fmtMetrica(l.b, l)}</td><td className={s.un}>{l.unidade}</td>
                        <td>{l.dif === null ? "N/D" : l.tipo === "pct" ? `${(l.dif * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} p.p.` : `${l.dif < 0 ? "−" : ""}${fmtMetrica(Math.abs(l.dif), { tipo: l.tipo === "contagem" ? "contagem" : "razao" })}`}</td>
                        <td>{pct(l.rel)}</td>
                        <td>{mx ? <span className={s.parRel} aria-hidden><span style={{ width: `${Math.round((150 * Math.abs(l.a!)) / mx)}px`, background: "var(--side-a)" }} /><span style={{ width: `${Math.round((150 * Math.abs(l.b!)) / mx)}px`, background: "var(--side-b)" }} /></span> : <span className="faint">N/D</span>}</td>
                      </tr>
                    );
                  }),
                ])}
              </tbody>
            </table>
            <p className={s.nota}><Info size={13} aria-hidden />As barras mostram cada métrica na sua própria escala (o maior dos dois lados = barra cheia); métricas de unidades diferentes não são comparadas entre si. Diferença relativa = (A − B) ÷ |B|.</p>
          </div>
        )}
      </>}
    </>
  );
}
