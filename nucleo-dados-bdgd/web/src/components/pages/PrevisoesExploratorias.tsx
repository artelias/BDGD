"use client";

import { useEffect, useMemo, useState } from "react";
import { toCSV } from "@/lib/format";
import { COOPERA_UCBT_2025 } from "@/lib/observacoes-auditoria";
import { avaliarRiscosCenario } from "@/lib/risco-cenarios";
import s from "./previsoes-exploratorias.module.css";

/** Pacote agregado público, sem registros individuais. Cada linha é uma série DIST × ativo. */
type Serie = [
  dist: number, empresa: string, conceitoId: string, metrica: string, unidade: string,
  historico: number[], tendenciaLinear: number[], erros2025: number[],
  publicacoes: string[], homologacao: string[], estadosHistoricos: string[],
];
interface Pacote {
  versao: string;
  origem: string;
  commitOrigem: string;
  blobShaOrigem: string;
  anosObservados: number[];
  anosSimulados: number[];
  numeroOrigensBacktest: number;
  previsaoValidada: boolean;
  series: Serie[];
}
type Metodo = "persistencia" | "tendencia_linear";

const NOMES: Record<string, string> = {
  alimentadores: "Alimentadores", bancos_capacitores: "Bancos de capacitores",
  barramentos: "Barramentos", chaves: "Chaves", circuitos_at: "Circuitos AT",
  conjuntos: "Conjuntos", consumidores: "Consumidores", disjuntores: "Disjuntores",
  geradores: "Geradores", iluminacao: "Iluminação pública", medidores: "Medidores",
  postes: "Postes", ramais: "Ramais", reatores: "Reatores", rede_at: "Rede AT",
  rede_bt: "Rede BT", rede_mt: "Rede MT", reguladores: "Reguladores",
  religadores: "Religadores", seccionalizadores: "Seccionalizadores",
  subestacoes: "Subestações", torres: "Torres", trafo_dist: "Transformadores de distribuição",
  trafo_forca: "Transformadores de força", trafo_medida: "Transformadores de medida",
};
const ANOS = [2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030];
const NUM = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const formatar = (valor: number, unidade: string) =>
  new Intl.NumberFormat("pt-BR", { maximumFractionDigits: unidade === "itens" ? 0 : 2 }).format(valor);

function Grafico({ historico, futuro, unidade, modelo }: {
  historico: number[]; futuro: number[]; unidade: string; modelo: Metodo;
}) {
  const valores = [...historico, ...futuro];
  const maximo = Math.max(1, ...valores) * 1.08;
  const x = (i: number) => 120 + (i * 92);
  const y = (v: number) => 217 - (v / maximo) * 185;
  const caminho = (val: number[], inicio: number) =>
    val.map((v, i) => (i === 0 ? "M" : "L") + x(inicio + i) + " " + y(v).toFixed(2)).join(" ");
  const previsao = [historico[3], ...futuro];
  return (
    <div className={s.grafico} tabIndex={0} role="region" aria-label="Gráfico rolável dos cenários">
      <div role="img" aria-label={"Evolução histórica 2022 a 2025 e simulação condicional 2026 a 2030 pelo método " + (modelo === "persistencia" ? "persistência" : "tendência linear")}>
      <svg viewBox="0 0 900 264" aria-hidden="true">
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1="120" x2="862" y1={y(maximo * f)} y2={y(maximo * f)} stroke="currentColor" opacity={0.12} strokeDasharray="3 5" />
            <text x="111" y={y(maximo * f) + 4} textAnchor="end" fill="currentColor" fontSize="11" opacity={0.75}>{formatar(maximo * f, unidade)}</text>
          </g>
        ))}
        <rect x={x(3)} y="18" width={x(8) - x(3) + 15} height="200" fill="var(--accent)" opacity={0.035} />
        <path d={caminho(historico, 0)} fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        <path d={caminho(previsao, 3)} fill="none" stroke="var(--accent)" strokeWidth="2.7" strokeDasharray="7 5" strokeLinecap="round" strokeLinejoin="round" />
        {historico.map((v, i) => <circle key={"h" + i} cx={x(i)} cy={y(v)} r="3.8" fill="currentColor" />)}
        {futuro.map((v, i) => <circle key={"f" + i} cx={x(i + 4)} cy={y(v)} r="4" fill="var(--accent)" />)}
        {ANOS.map((ano, i) => <text key={ano} x={x(i)} y="244" textAnchor="middle" fill="currentColor" fontSize="12" opacity={i === 3 || i === 4 || i === 8 ? 1 : 0.65}>{ano}</text>)}
        <line x1={x(3) + 46} x2={x(3) + 46} y1="17" y2="222" stroke="var(--accent)" strokeDasharray="2 5" opacity="0.55" />
      </svg>
      </div>
      <div className={s.legenda}><span><i className={s.pontoHistorico} />BDGD observada</span><span><i className={s.pontoCenario} />Simulação condicional</span></div>
      <p className={s.notaGrafico}>Eixo vertical a partir de zero. Valores de itens são arredondados apenas na exibição.</p>
    </div>
  );
}

export function PrevisoesExploratorias() {
  const [dados, setDados] = useState<Pacote | null>(null);
  const [erro, setErro] = useState("");
  const [dist, setDist] = useState("26");
  const [conceito, setConceito] = useState("consumidores");
  const [metodo, setMetodo] = useState<Metodo>("tendencia_linear");
  const [anoAlvo, setAnoAlvo] = useState(2030);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch("/data/previsoes/cenarios-exploratorios-2026-2030.json", { signal: ctrl.signal })
      .then((r) => { if (!r.ok) throw new Error("Arquivo de cenários indisponível."); return r.json(); })
      .then((d: Pacote) => {
        if (!Array.isArray(d.series) || d.previsaoValidada !== false || d.series.length === 0)
          throw new Error("Versão do conjunto de cenários incompatível.");
        setDados(d);
      })
      .catch((e: Error) => { if (e.name !== "AbortError") setErro(e.message); });
    return () => ctrl.abort();
  }, []);

  const empresas = useMemo(() => {
    if (!dados) return [];
    return [...new Map(dados.series.map((item) => [item[0], item[1]])).entries()]
      .sort((a, b) => String(a[1]).localeCompare(String(b[1]), "pt-BR"));
  }, [dados]);
  const porDist = useMemo(() => dados?.series.filter((item) => String(item[0]) === dist) ?? [], [dados, dist]);
  const conceitos = useMemo(() => [...porDist].sort((a, b) =>
    (NOMES[a[2]] ?? a[2]).localeCompare(NOMES[b[2]] ?? b[2], "pt-BR")), [porDist]);
  const serie = conceitos.find((item) => item[2] === conceito) ?? conceitos[0];
  const conceitoEfetivo = serie?.[2] ?? "";
  const bloqueioCoopera = dist === String(COOPERA_UCBT_2025.dist) && conceitoEfetivo === "consumidores";
  const futuros = serie && !bloqueioCoopera && (metodo === "persistencia"
    ? [0, 1, 2, 3, 4].map(() => serie[5][3]) : serie[6]);
  const valorAno = serie && futuros ? futuros[anoAlvo - 2026] : null;
  const erroModelo = serie && (metodo === "persistencia" ? serie[7][0] : serie[7][1]);
  const avisos = serie && futuros ? avaliarRiscosCenario(serie[5], futuros, serie[10], metodo) : [];
  const codigosAviso = avisos.map((a) => a.codigo).join("|");
  const csv = serie && futuros && dados
    ? toCSV(["ano", "valor", "classe", "metodo", "dist", "conceitoId", "unidade", "metrica",
      "status_homologacao", "publicacao_id", "verificacao_independente_zero", "versao_dados", "commit_origem", "blob_sha_origem", "avisos_estatisticos"],
      ANOS.map((ano, i) => [ano, i < 4 ? serie[5][i] : futuros[i - 4],
        i < 4 ? (serie[10][i] === "Z" ? "zero_tecnico" : "observado") : "simulacao_condicional",
        i < 4 ? "BDGD" : metodo, serie[0], serie[2], serie[4], serie[3],
        i < 4 ? serie[9][i] : "NAO_VALIDADA", i < 4 ? serie[8][i] : "",
        i < 4 && serie[10][i] === "Z" ? "pendente" : "nao_se_aplica", dados.versao, dados.commitOrigem, dados.blobShaOrigem,
        i < 4 ? "" : codigosAviso]))
    : "";

  return (
    <section className={s.section} aria-labelledby="exploracao-title">
      <div className={s.titulo}>
        <div>
          <div className="eyebrow">Base auditada · simulação exploratória</div>
          <h2 id="exploracao-title">Explorar cenários 2026–2030</h2>
          <p className="muted">Dados reais de 2022–2025; projeções condicionais, não previsões validadas de demanda ou investimento.</p>
        </div>
        <span className={s.status}>Sem validação preditiva</span>
      </div>
      {erro ? <p role="alert" className={s.erro}>{erro} Consulte o histórico na página Evolução.</p> : !dados ?
        <p role="status">Carregando as séries auditadas…</p> : (
          <>
            <div className={s.indicadores}>
              <div><strong>{NUM.format(dados.series.length)}</strong><span>Séries elegíveis</span></div>
              <div><strong>{NUM.format(empresas.length)}</strong><span>Distribuidoras</span></div>
              <div><strong>25</strong><span>Tipos de ativos</span></div>
              <div><strong>1</strong><span>Origem de backtest</span></div>
            </div>
            <div className={s.filtros}>
              <label>Distribuidora
                <select value={dist} onChange={(e) => { setDist(e.target.value); setConceito("consumidores"); }}>
                  {empresas.map(([codigo, nome]) => <option key={codigo} value={codigo}>{nome} · DIST {codigo}</option>)}
                </select>
              </label>
              <label>Ativo
                <select value={conceitoEfetivo} onChange={(e) => setConceito(e.target.value)}>
                  {conceitos.map((item) => <option key={item[2]} value={item[2]}>{NOMES[item[2]] ?? item[2]}</option>)}
                </select>
              </label>
              <label>Método
                <select value={metodo} onChange={(e) => setMetodo(e.target.value as Metodo)}>
                  <option value="tendencia_linear">Tendência linear</option>
                  <option value="persistencia">Persistência (estoque constante)</option>
                </select>
              </label>
              <label>Ano simulado
                <select value={anoAlvo} onChange={(e) => setAnoAlvo(Number(e.target.value))}>
                  {dados.anosSimulados.map((ano) => <option key={ano}>{ano}</option>)}
                </select>
              </label>
            </div>
            {bloqueioCoopera && <p role="status" data-testid="coopera-bloqueio-cenario"><b>Coopera 2025 — cenário de consumidores suspenso.</b> UCBT sem registros (0*) na publicação ANEEL; 225 AT de UCMT/UCAT são somente subtotal parcial. A extrapolação existente não é confiável. Uma estimativa KNN com variáveis externas e âncora histórica válida está em estudo, sem resultados numéricos publicados.</p>}
            {serie && futuros && valorAno !== null && (
              <>
                <div className={s.destaque} aria-live="polite" aria-atomic="true">
                  <div><span>Estoque observado em 2025</span><strong>{formatar(serie[5][3], serie[4])} <small>{serie[4]}</small></strong></div>
                  <div><span>Cenário condicional para {anoAlvo}</span><strong>{formatar(valorAno, serie[4])} <small>{serie[4]}</small></strong></div>
                  <div><span>Erro absoluto no teste de 2025</span><strong>{formatar(erroModelo ?? 0, serie[4])} <small>{serie[4]}</small></strong><em>Apenas 1 origem temporal de teste</em></div>
                </div>
                {avisos.length > 0 && (
                  <section className={s.alertas} aria-label="Limitações específicas da série selecionada">
                    <h3>Sinais que exigem cautela neste cenário</h3>
                    <ul>{avisos.map((alerta) => (
                      <li key={alerta.codigo} data-risco={alerta.codigo}>
                        <strong>{alerta.gravidade === "alta" ? "Atenção reforçada" : "Ressalva"}:</strong> {alerta.descricao}
                      </li>
                    ))}</ul>
                  </section>
                )}
                <Grafico historico={serie[5]} futuro={futuros} unidade={serie[4]} modelo={metodo} />
                <div className={s.duasColunas}>
                  <div>
                    <h3>Valores e natureza do dado</h3>
                    <div className={s.tabelaContainer} tabIndex={0} role="region" aria-label="Valores dos cenários — tabela rolável">
                      <table className={s.tabela}>
                        <thead><tr><th>Ano</th><th>Quantidade ou extensão</th><th>Classificação</th></tr></thead>
                        <tbody>{ANOS.map((ano, i) => (
                          <tr key={ano}><td>{ano}</td><td>{formatar(i < 4 ? serie[5][i] : futuros[i - 4], serie[4])} {serie[4]}</td>
                          <td>{i < 4 ? (serie[10][i] === "Z" ? "Zero técnico*" : "Observado") : "Simulação"}</td></tr>
                        ))}</tbody>
                      </table>
                    </div>
                    <a className={s.exportar} href={"data:text/csv;charset=utf-8," + encodeURIComponent("\uFEFF" + csv)}
                      download={"cenario_DIST_" + serie[0] + "_" + serie[2] + "_" + metodo + ".csv"}>
                      Exportar série selecionada (CSV)
                    </a>
                  </div>
                  <div>
                    <h3>Proveniência e limites</h3>
                    <p className={s.texto}>Os quatro valores históricos vêm de publicações oficiais BDGD. O cenário é extrapolação matemática, sem variáveis de demanda, CAPEX ou teste plurianual robusto.</p>
                    <ul className={s.fontes}>
                      {[2022, 2023, 2024, 2025].map((ano, i) => (
                        <li key={ano}>
                          <span>{ano} · {serie[9][i]?.replaceAll("_", " ") ?? "Estado não informado"}</span>
                          {serie[8][i] ? <a href={"https://www.arcgis.com/home/item.html?id=" + serie[8][i]} target="_blank" rel="noopener noreferrer">Publicação ANEEL</a> : <span>Fonte não informada</span>}
                        </li>
                      ))}
                    </ul>
                    <div className={s.alerta}>A comparação usa o perímetro original da distribuidora. Séries com rupturas ou sucessões não reconciliadas foram excluídas; os resultados não representam totais nacionais completos.</div>
                  </div>
                </div>
                <p className={s.rodape}>* Zero técnico: a classificação é consistente com o agregado processado, mas a comprovação independente de cada entidade vazia no GDB ainda precisa ser concluída.</p>
                <p className={s.rodape}>Origem: contrato nacional BDGD 1.0.0, PR #4, commit {dados.commitOrigem}. Identificadores das publicações preservados. Não há previsão estatisticamente validada nem intervalo probabilístico de confiança.</p>
              </>
            )}
          </>
        )}
    </section>
  );
}
