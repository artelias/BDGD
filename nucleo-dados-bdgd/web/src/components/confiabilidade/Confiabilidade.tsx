"use client";
import { DataError, LoadingBlock } from "@/components/ui/Feedback";
import { Segmented } from "@/components/ui/Segmented";
import { useIndice } from "@/lib/confiabilidade/dados";
import { useEstadoConf, type Aba } from "@/lib/confiabilidade/estado";
import p from "@/components/pages/pages.module.css";
import { Benchmarking } from "./Benchmarking";
import { Comparador } from "./Comparador";
import { Fatores } from "./Fatores";
import { MetodologiaConf } from "./MetodologiaConf";
import { VisaoMapa } from "./VisaoMapa";
import s from "./conf.module.css";

const ANOS_VAZIO: number[] = [];
const ABAS: Array<{ value: Aba; label: string }> = [
  { value: "mapa", label: "Mapa e conjuntos" }, { value: "comparar", label: "Comparar A × B" }, { value: "benchmarking", label: "Benchmarking" },
  { value: "fatores", label: "Fatores associados" }, { value: "metodologia", label: "Metodologia" },
];

export function Confiabilidade() {
  const indice = useIndice();
  const e = useEstadoConf(indice.dados?.anos ?? ANOS_VAZIO);
  return (
    <>
      <header className={`${p.head} rise`}>
        <div className="eyebrow">DEC e FEC oficiais da ANEEL · infraestrutura da BDGD 2022–2025 · por conjunto elétrico</div>
        <h1 className="display" style={{ marginTop: 8 }}>Inteligência de Confiabilidade Elétrica</h1>
        <p className="lede">Compare DEC/FEC e investigue como a infraestrutura elétrica se relaciona com a qualidade do fornecimento. Os indicadores de continuidade são os publicados pela ANEEL; a infraestrutura por conjunto é calculada da BDGD e ainda é exploratória.</p>
      </header>
      {indice.carregando ? <LoadingBlock label="Carregando os indicadores de continuidade" /> : indice.erro || !indice.dados ? <DataError error={indice.erro ?? "índice ausente"} /> : indice.dados.demonstrativo ? (
        <DataError error="O pacote de confiabilidade carregado é demonstrativo (sintético) e não pode ser exibido no portal." />
      ) : <>
        <div className={s.tabs}><Segmented label="Seção da Confiabilidade" value={e.aba} onChange={(v) => e.set({ aba: v === "mapa" ? null : v }, true)} options={ABAS} /></div>
        {e.aba === "mapa" && <VisaoMapa indice={indice.dados} e={e} />}
        {e.aba === "comparar" && <Comparador indice={indice.dados} e={e} />}
        {e.aba === "benchmarking" && <Benchmarking indice={indice.dados} e={e} />}
        {e.aba === "fatores" && <Fatores indice={indice.dados} e={e} />}
        {e.aba === "metodologia" && <MetodologiaConf indice={indice.dados} />}
      </>}
    </>
  );
}
