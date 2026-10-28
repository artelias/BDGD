"use client";

import { useEffect, useState } from "react";
import s from "./publicacoes-auditadas.module.css";

interface Par {
  ano: number; dist: number; empresa: string; risco: string;
  impactoMaxPct: number; ativosComDiferenca: number;
  itemA: string; itemB: string; versaoA: string; versaoB: string;
  recomendacaoTecnica: string; decisao: string; ativosDiferentes: string[];
}
interface Pacote { quantidade: number; selecionadaAutomaticamente: boolean; pares: Par[] }
const link = (itemId: string) => "https://www.arcgis.com/home/item.html?id=" + itemId;

export function ParesDivergentes() {
  const [dados, setDados] = useState<Pacote | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  useEffect(() => {
    const ctrl = new AbortController();
    fetch("/data/historico/pares-divergentes.json", { signal: ctrl.signal })
      .then((res) => { if (!res.ok) throw new Error("HTTP " + res.status); return res.json(); })
      .then((r: Pacote) => {
        if (!Array.isArray(r.pares) || r.pares.length !== 13 ||
            r.quantidade !== 13 || r.selecionadaAutomaticamente !== true)
          throw new Error("Relação de republicações divergentes incompatível.");
        setDados(r);
      })
      .catch((e: Error) => { if (e.name !== "AbortError") setErro(e.message); });
    return () => ctrl.abort();
  }, []);

  return (
    <details className={s.pares} data-testid="pares-publicacoes">
      <summary>Analisar individualmente os 13 pares de republicações divergentes</summary>
      <p className={s.rodape}>São seis pares sem mudança nas quantidades dos 25 conceitos e sete com diferença em algum total. Mesmo sem diferença nos 25 totais, os atributos e vínculos podem divergir. A versão mais recente válida foi selecionada por critério técnico-editorial documentado; a anterior segue disponível. Não implica homologação regulatória.</p>
      {erro ? <p role="alert">{erro}</p> : !dados ? <p role="status">Carregando comparações técnicas…</p> :
        <div className={s.scroll} tabIndex={0} role="region" aria-label="Comparação dos 13 pares de versões oficiais">
          <table className={s.tabela}>
            <thead><tr><th>Ano</th><th>Distribuidora</th><th>Diferenças de totais</th><th>Versões oficiais</th><th>Parecer técnico</th></tr></thead>
            <tbody>{dados.pares.map((r) => (
              <tr key={r.ano + "-" + r.dist}>
                <td className={s.ano}>{r.ano}</td>
                <td><b>{r.empresa}</b><span className={s.sub}>DIST {r.dist}</span></td>
                <td><strong>{r.ativosComDiferenca} de 25 conceitos</strong>
                  {r.ativosDiferentes.length > 0 &&
                    <span className={s.sub}>{r.ativosDiferentes.join(", ")}</span>}
                  <span className={s.sub}>Impacto nacional máximo estimado no inventário: {r.impactoMaxPct.toLocaleString("pt-BR", { maximumFractionDigits: 5 })}%</span>
                </td>
                <td>
                  <a href={link(r.itemA)} target="_blank" rel="noopener noreferrer">Versão A: {r.versaoA}</a>
                  <span className={s.sub}><a href={link(r.itemB)} target="_blank" rel="noopener noreferrer">Versão B (selecionada): {r.versaoB}</a></span>
                </td>
                <td><b>Versão mais recente selecionada com ressalva</b>
                  <span className={s.sub}>{r.recomendacaoTecnica}</span>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      }
    </details>
  );
}