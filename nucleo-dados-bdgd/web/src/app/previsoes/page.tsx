import { Patrimonio } from "@/components/pages/Patrimonio";
import type { Metadata } from "next";
import Link from "next/link";
import { PrevisoesExploratorias } from "@/components/pages/PrevisoesExploratorias";
import { MotorUniversal } from "@/components/pages/MotorUniversal";
import { CenariosMotor } from "@/components/pages/CenariosMotor";
import { Activity, ArrowUpRight, ChartSpline, CircleHelp, Database, GitBranch, Layers3, Wallet } from "lucide-react";

export const metadata: Metadata = { title: "Previsões | Expansão elétrica" };

const perspectivas = [
  {
    titulo: "Crescimento de ativos",
    subtitulo: "Estoque físico e movimentação patrimonial",
    descricao: "Transformadores de distribuição (TUC 565), transformadores de força (TUC 570), medidores, proteção e estruturas. Instalações e equipamentos não são somados em duplicidade.",
    icone: Layers3,
    medidas: "Unidades · kVA · entradas e baixas",
  },
  {
    titulo: "Crescimento da infraestrutura",
    subtitulo: "Capacidade e extensão do sistema",
    descricao: "Redes de baixa, média e alta tensão, alimentadores, subestações e capacidade instalada, respeitando a unidade física e a cobertura territorial.",
    icone: Activity,
    medidas: "km · MVA · circuitos · subestações",
  },
  {
    titulo: "Expansão por conectividade",
    subtitulo: "Demanda, reserva e topologia",
    descricao: "Relações verificáveis entre unidades consumidoras, alimentadores, transformadores e trechos de rede. O aumento de consumidores não implica automaticamente novos equipamentos.",
    icone: GitBranch,
    medidas: "UC · demanda · carregamento · reserva",
  },
] as const;

const entregas = [
  { nome: "Históricos 2022–2024", detalhe: "Extração, validação técnica e auditoria das bases por competência e distribuidora. Homologação humana dos anos anteriores pendente.", situacao: "Auditoria concluída" },
  { nome: "Perímetros comparáveis", detalhe: "EMR/ENF tratada contra dupla contagem; ponte EPB/EBO ainda depende de decisão humana.", situacao: "Parcialmente reconciliado" },
  { nome: "Variáveis elétricas e econômicas", detalhe: "Demanda, capacidade, topologia, PIB regional, indústria, juros e custos, conforme disponibilidade histórica.", situacao: "Contrato definido" },
  { nome: "Validação dos modelos", detalhe: "Backtest com origens 2023 e 2024 (horizontes de 1 e 2 anos), mesmos pontos para todos os modelos; 2028–2030 sem verificação retrospectiva.", situacao: "Executado" },
  { nome: "Cenários 2026–2030", detalhe: "Conservador, Moderado e Agressivo por métrica, quando sustentados pelo erro observado; sem intervalos probabilísticos nem homologação preditiva.", situacao: "Simulação condicional" },
] as const;

export default function Page() {
  return (
    <div style={{ maxWidth: 1180, margin: "0 auto", paddingBottom: 80 }}>
      <header style={{ maxWidth: 900, marginBottom: 18 }}>
        <div className="eyebrow">Estoque físico · dados nacionais BDGD</div>
        <h1 className="display" style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          <ChartSpline size={34} strokeWidth={1.6} color="var(--accent)" aria-hidden="true" />
          Motor de Expansão Elétrica
        </h1>
        <p className="lede" style={{ marginTop: 12 }}>
          Compare, por ativo e métrica física, os cenários Conservador, Moderado e Agressivo de 2026 a 2030, gerados por modelos
          executados e validados retrospectivamente sobre 2022–2025. Resultados simulados não representam investimentos previstos ou obras necessárias.
        </p>
      </header>

      <CenariosMotor />
      <PrevisoesExploratorias />
      <MotorUniversal />
      <Patrimonio />

      <details style={{ border: "1px solid var(--hairline)", borderRadius: 12, padding: "13px 16px", marginBottom: 26 }}>
        <summary style={{ cursor: "pointer", fontSize: ".88rem", fontWeight: 630 }}>
          Entenda a diferença entre simulação e previsão validada
        </summary>
        <p className="muted" style={{ margin: "12px 0 0", lineHeight: 1.6, fontSize: ".87rem" }}>
          Os cenários extrapolam o estoque histórico observado de 2022 a 2025. Como há apenas duas origens temporais
          de backtest e os anos anteriores não estão integralmente homologados, o modelo ainda não oferece previsões
          estatisticamente validadas, necessidade técnica de expansão, CAPEX ou intervalos probabilísticos.
        </p>
      </details>

      <section aria-labelledby="perspectivas-title" style={{ marginBottom: 36 }}>
        <div className="eyebrow">Três perspectivas complementares</div>
        <h2 id="perspectivas-title" style={{ fontSize: "1.45rem", fontWeight: 690, margin: "8px 0 18px" }}>O que o motor irá analisar</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 280px), 1fr))", gap: 14 }}>
          {perspectivas.map(({ titulo, subtitulo, descricao, icone: Icon, medidas }) => (
            <article key={titulo} style={{ border: "1px solid var(--hairline)", borderRadius: 16, padding: 22, minWidth: 0 }}>
              <Icon size={25} color="var(--accent)" strokeWidth={1.7} aria-hidden="true" />
              <h3 style={{ fontSize: "1.12rem", fontWeight: 680, margin: "14px 0 5px" }}>{titulo}</h3>
              <p style={{ fontSize: ".9rem", fontWeight: 600, margin: "0 0 12px" }}>{subtitulo}</p>
              <p className="muted" style={{ lineHeight: 1.6, fontSize: ".91rem", marginBottom: 16 }}>{descricao}</p>
              <p className="muted" style={{ fontSize: ".8rem", borderTop: "1px solid var(--hairline)", paddingTop: 12, margin: 0 }}>{medidas}</p>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="saidas-title" style={{ marginBottom: 36 }}>
        <div className="eyebrow">Saídas diferentes, não intercambiáveis</div>
        <h2 id="saidas-title" style={{ fontSize: "1.45rem", fontWeight: 690, margin: "8px 0 18px" }}>Três resultados do modelo</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 240px), 1fr))", gap: 14 }}>
          {[
            { nome: "Necessidade técnica", explicacao: "O reforço ou expansão requerido por demanda, reserva, confiabilidade e topologia.", icon: CircleHelp },
            { nome: "Estoque provável", explicacao: "A variação de ativos físicos após novas instalações, substituições e baixas.", icon: Database },
            { nome: "Investimento associado", explicacao: "CAPEX condicionado a custos, cronograma, restrições e ambiente regulatório.", icon: Wallet },
          ].map(({ nome, explicacao, icon: Icon }) => (
            <article key={nome} style={{ padding: 20, border: "1px solid var(--hairline)", borderRadius: 14 }}>
              <Icon size={22} color="var(--accent)" aria-hidden="true" />
              <h3 style={{ fontWeight: 650, margin: "12px 0 7px" }}>{nome}</h3>
              <p className="muted" style={{ fontSize: ".9rem", lineHeight: 1.6, margin: 0 }}>{explicacao}</p>
              <p style={{ margin: "16px 0 0", fontSize: ".82rem", fontWeight: 600 }}>Resultado: N/D — não estimado</p>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="etapas-title" style={{ marginBottom: 30 }}>
        <div className="eyebrow">Rastreabilidade</div>
        <h2 id="etapas-title" style={{ fontSize: "1.45rem", fontWeight: 690, margin: "8px 0 16px" }}>Condições para publicar resultados</h2>
        <div style={{ borderTop: "1px solid var(--hairline)" }}>
          {entregas.map((etapa, i) => (
            <div key={etapa.nome} style={{ display: "grid", gridTemplateColumns: "36px minmax(0,1fr)", gap: 12, padding: "16px 0", borderBottom: "1px solid var(--hairline)" }}>
              <span className="muted" style={{ fontVariantNumeric: "tabular-nums" }}>{String(i + 1).padStart(2, "0")}</span>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
                <div style={{ flex: "1 1 250px" }}>
                  <h3 style={{ fontWeight: 650, margin: "0 0 5px" }}>{etapa.nome}</h3>
                  <p className="muted" style={{ fontSize: ".9rem", lineHeight: 1.55, margin: 0 }}>{etapa.detalhe}</p>
                </div>
                <span className="muted" style={{ fontSize: ".8rem", border: "1px solid var(--hairline)", borderRadius: 100, padding: "5px 10px", whiteSpace: "nowrap" }}>{etapa.situacao}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer style={{ borderTop: "1px solid var(--hairline)", paddingTop: 18, display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
        <p className="muted" style={{ fontSize: ".85rem", flex: "1 1 280px", margin: 0 }}>
          Histórico e cenários condicionais aparecem separadamente. Não há previsão estatisticamente validada publicada; nenhum valor é inferido de exemplos ilustrativos.
        </p>
        <Link href="/" style={{ display: "inline-flex", alignItems: "center", gap: 6, fontWeight: 600, fontSize: ".88rem" }}>
          Explorar dados observados <ArrowUpRight size={16} aria-hidden="true" />
        </Link>
      </footer>
    </div>
  );
}
