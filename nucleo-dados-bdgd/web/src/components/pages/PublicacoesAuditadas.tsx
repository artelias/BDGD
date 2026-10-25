"use client";

import { useEffect, useMemo, useState } from "react";
import s from "./publicacoes-auditadas.module.css";
import { ParesDivergentes } from "./ParesDivergentes";

type Linha = [
  ano: number, dist: number, empresa: string, itemId: string, uso: string,
  dataBaseGdb: string, dataBaseTitulo: string, versao: string, decisao: string,
  recomendacao: string, intervalo: string,
];
interface Auditoria {
  versao: string;
  sourceCommit: string;
  total: number;
  resumo: Record<string, number>;
  items: Linha[];
  publicacoesNaoLocalizadas: Array<[ano: number, dist: number, empresa: string]>;
  publicacoesNaoLocalizadasCelulas: number;
}
type Filtro = "restritas" | "divergentes" | "competencia" | "em_uso" | "todas";
const TOTAL_ESPERADO = 414;
const PENDENTE = "par_divergente_pendente";
const EXCLUIDAS = new Set(["excluido_competencia", "par_item_excluido_competencia"]);
const LABEL: Record<string, string> = {
  par_divergente_pendente: "Duas versões divergentes — decisão pendente",
  excluido_competencia: "Excluído: competência incompatível",
  par_item_excluido_competencia: "Versão do par excluída por competência",
  par_competencia_unica_valida_em_uso: "Versão única em uso (ver ressalvas)",
  em_uso_na_serie: "Em uso na série",
  pacote_2025: "Pacote 2025",
};
const fmt = (v: number) => new Intl.NumberFormat("pt-BR").format(v);

export function PublicacoesAuditadas() {
  const [data, setData] = useState<Auditoria | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ano, setAno] = useState("todos");
  const [filtro, setFiltro] = useState<Filtro>("restritas");
  const [busca, setBusca] = useState("");
  useEffect(() => {
    const ctrl = new AbortController();
    fetch("/data/historico/publicacoes-auditadas.json", { signal: ctrl.signal })
      .then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then((d: Auditoria) => {
        if (!Array.isArray(d.items) || d.items.length !== TOTAL_ESPERADO || d.total !== TOTAL_ESPERADO ||
          d.publicacoesNaoLocalizadas?.length !== 11 || d.publicacoesNaoLocalizadasCelulas !== 275)
          throw new Error("Inventário de publicações incompleto ou incompatível.");
        setData(d);
      })
      .catch((err: Error) => { if (err.name !== "AbortError") setErro(err.message); });
    return () => ctrl.abort();
  }, []);
  const restritas = (data?.resumo[PENDENTE] ?? 0) +
    (data?.resumo.excluido_competencia ?? 0) +
    (data?.resumo.par_item_excluido_competencia ?? 0);
  const linhas = useMemo(() => {
    if (!data) return [];
    const term = busca.trim().toLocaleLowerCase("pt-BR");
    return data.items.filter((r) => {
      const status = r[4];
      if (ano !== "todos" && String(r[0]) !== ano) return false;
      if (filtro === "restritas" && !(status === PENDENTE || EXCLUIDAS.has(status))) return false;
      if (filtro === "divergentes" && status !== PENDENTE) return false;
      if (filtro === "competencia" && !EXCLUIDAS.has(status)) return false;
      if (filtro === "em_uso" && (status === PENDENTE || EXCLUIDAS.has(status))) return false;
      return !term || [r[1], r[2], r[3], r[7]].some((v) =>
        String(v).toLocaleLowerCase("pt-BR").includes(term));
    }).sort((a, b) => b[0] - a[0] || a[2].localeCompare(b[2], "pt-BR") || a[3].localeCompare(b[3]));
  }, [data, ano, filtro, busca]);

  return (
    <section className={s.section} aria-labelledby="publicacoes-auditadas-title" data-testid="auditoria-publicacoes">
      <div className={s.head}>
        <div>
          <div className="eyebrow">Rastreabilidade · inventário de arquivos</div>
          <h2 id="publicacoes-auditadas-title">Publicações avaliadas e motivos de bloqueio</h2>
          <p>O antigo termo “em quarentena” não descrevia corretamente a situação atual. Agora cada publicação tem uma classificação verificável e link para o item oficial.</p>
        </div>
      </div>
      {!data ? (erro ? <p role="alert">Falha ao carregar inventário: {erro}.</p> :
        <p role="status">Carregando inventário auditado das publicações…</p>) : (
        <>
          <div className={s.kpis} aria-label="Resumo do inventário">
            <div><strong>{fmt(data.total)}</strong><span>Publicações examinadas</span></div>
            <div><strong>{fmt(data.resumo[PENDENTE] ?? 0)}</strong><span>Arquivos em 13 pares divergentes</span></div>
            <div><strong>{fmt((data.resumo.excluido_competencia ?? 0) + (data.resumo.par_item_excluido_competencia ?? 0))}</strong><span>Excluídos por competência</span></div>
            <div><strong>{fmt(data.total - restritas)}</strong><span>Em uso no histórico ou pacote 2025</span></div>
          </div>
          <div className={s.explicacao}>
            <p><b>Arquivos excluídos:</b> a data-base não corresponde ao ano requerido. A exclusão técnica já foi aplicada; não é tarefa de processamento pendente.</p>
            <p><b>Republicações divergentes:</b> há duas versões oficiais conflitantes para 13 combinações distribuidora–ano. Sem uma escolha formalmente justificada, os indicadores afetados continuam N/D.</p>
            <p><b>Em uso com ressalva:</b> duas publicações são a única versão utilizável entre pares de competências, incluindo a Coprel 2023, cuja BASE precisa de decisão humana. O uso não significa homologação automática.</p>
          </div>
          <div className={s.filtros}>
            <label>Ano
              <select value={ano} onChange={(e) => setAno(e.target.value)}>
                <option value="todos">Todos os anos</option>
                {[2022, 2023, 2024, 2025].map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </label>
            <label>Situação
              <select value={filtro} onChange={(e) => setFiltro(e.target.value as Filtro)}>
                <option value="restritas">Excluídas ou com decisão pendente</option>
                <option value="divergentes">Republicações divergentes</option>
                <option value="competencia">Excluídas por competência</option>
                <option value="em_uso">Em uso (incluindo ressalvas)</option>
                <option value="todas">Todas as publicações</option>
              </select>
            </label>
            <label>Distribuidora, DIST ou item oficial
              <input type="search" value={busca} onChange={(e) => setBusca(e.target.value)}
                placeholder="Pesquisar empresa, DIST ou ID do arquivo" />
            </label>
          </div>
          <p className={s.contagem} aria-live="polite">{fmt(linhas.length)} publicação(ões) correspondentes aos filtros.</p>
          {linhas.length === 0 ? <p className={s.vazio}>Nenhuma publicação corresponde aos filtros. Isso não equivale a zero ativos.</p> : (
            <div className={s.scroll} tabIndex={0} role="region" aria-label="Publicações e justificativas — tabela rolável">
              <table className={s.tabela}>
                <thead><tr><th>Ano</th><th>Distribuidora</th><th>Situação do arquivo</th><th>DATA_BASE</th><th>Fonte e versão</th></tr></thead>
                <tbody>{linhas.map((r) => (
                  <tr key={r[3]} data-status={r[4]}>
                    <td className={s.ano}>{r[0]}</td>
                    <td><b>{r[2]}</b><span className={s.sub}>DIST {r[1]}</span></td>
                    <td><strong className={s.estado} data-uso={r[4]}>{LABEL[r[4]] ?? r[4]}</strong>
                      {(r[4] === PENDENTE || r[4] === "par_competencia_unica_valida_em_uso") &&
                        <span className={s.sub}>{r[9]}</span>}
                    </td>
                    <td><span className={s.sub}>GDB: {r[5] || "não identificado"}</span><span className={s.sub}>Catálogo: {r[6] || "não informado"}</span></td>
                    <td><a href={"https://www.arcgis.com/home/item.html?id=" + r[3]} target="_blank" rel="noopener noreferrer">
                      Abrir publicação ANEEL</a><span className={s.sub}>{r[7]}</span><span className={s.hash}>{r[3]}</span></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          <details className={s.pares} data-testid="publicacoes-inexistentes">
            <summary>11 publicações não localizadas no catálogo oficial — não são arquivos em quarentena</summary>
            <p className={s.rodape}>A busca pelo catálogo oficial não encontrou publicações para essas combinações distribuidora/ano, afetando {fmt(data.publicacoesNaoLocalizadasCelulas)} células de ativos. Não há arquivo local para corrigir. É necessário que a ANEEL ou a distribuidora disponibilize ou identifique a publicação adequada.</p>
            <div className={s.scroll} tabIndex={0} role="region" aria-label="Publicações não localizadas no catálogo ANEEL">
              <table className={s.tabela}>
                <thead><tr><th>Ano</th><th>Distribuidora</th><th>Situação</th></tr></thead>
                <tbody>{data.publicacoesNaoLocalizadas.map(([ano, dist, empresa]) => (
                  <tr key={ano + "-" + dist}>
                    <td className={s.ano}>{ano}</td>
                    <td><b>{empresa}</b><span className={s.sub}>DIST {dist}</span></td>
                    <td>Publicação oficial não localizada; 25 conceitos ficam N/D para essa combinação.</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </details>
          <ParesDivergentes />
          <p className={s.rodape}>Fonte: matriz de conformidade BDGD Ordinária, commit {data.sourceCommit}, auditoria concluída em 25/10/2026. Nenhuma versão pendente foi escolhida automaticamente. Publicações não localizadas no catálogo e ativos não aplicáveis são controlados separadamente no contrato.</p>
        </>
      )}
    </section>
  );
}
