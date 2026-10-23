import type { Metadata } from "next";
import { History } from "lucide-react";
import Link from "next/link";
import status from "@/data/historico_status.json";

export const metadata: Metadata = { title: "Evolução histórica" };

const REGRAS = [
  ["Só dados homologados", "Um ano entra na série quando todas as distribuidoras elegíveis daquela data-base forem processadas, reconciliadas com o arquivo de origem e aprovadas."],
  ["Mesma regra em todos os anos", "Contagens, extensões e potências seguem as regras de 2025. Campo que mudou de significado entre versões do Manual fica fora da série."],
  ["Sucessões de distribuidoras", "Incorporações (por exemplo, Energisa Borborema → Energisa Paraíba) são aplicadas para comparar no perímetro de 2025, sem contar a mesma rede duas vezes."],
  ["Sem projeções", "A página mostra apenas o que foi publicado pela ANEEL. Nenhuma tendência ou previsão é calculada."],
];

export default function Page() {
  const pronta = status.anos.every((a) => a.homologadas > 0 && a.homologadas === a.elegiveis);
  return (
    <div style={{ maxWidth: 880 }}>
      <div className="eyebrow">2022 · 2023 · 2024 · 2025</div>
      <h1 className="display" style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 14 }}><History size={34} strokeWidth={1.6} color="var(--accent)" aria-hidden /> Evolução histórica</h1>
      {!pronta && (
        <>
          <p className="lede" style={{ marginTop: 10 }} data-testid="historico-preparacao">
            <b>Histórico em preparação.</b> Ainda não há série homologada e comparável de 2022 a 2025, por isso nenhum número de ativos é exibido aqui. O painel continua mostrando apenas a data-base 31/12/2025.
          </p>
          <section aria-labelledby="prog-title" style={{ marginTop: 28 }}>
            <h2 className="title" id="prog-title" style={{ fontSize: "1.25rem" }}>Andamento do processamento</h2>
            <p className="caption" style={{ marginTop: 4 }}>Contagens de execução do ETL histórico em {status.gerado_em.split("-").reverse().join("/")}; {status.estado}. Não são valores de ativos.</p>
            <div style={{ overflowX: "auto", marginTop: 12 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--fs-label)", fontVariantNumeric: "tabular-nums" }} data-testid="historico-progresso">
                <caption className="sr-only">Andamento do processamento histórico por data-base</caption>
                <thead>
                  <tr style={{ color: "var(--text-3)", fontSize: "var(--fs-caption)" }}>
                    {["Data-base", "Elegíveis", "Processadas", "Em quarentena", "Falhas de reconciliação", "Homologadas"].map((h, i) => <th key={h} scope="col" style={{ textAlign: i ? "right" : "left", padding: "8px 10px", borderBottom: "1px solid var(--hairline-strong)", fontWeight: 560 }}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {status.anos.map((a) => (
                    <tr key={a.ano}>
                      <th scope="row" style={{ textAlign: "left", padding: "10px", borderBottom: "1px solid var(--hairline)", fontWeight: 600 }}>31/12/{a.ano}</th>
                      {[a.elegiveis, a.processadas, a.quarentena, a.reconciliacao_falhas, a.homologadas].map((v, i) => <td key={i} style={{ textAlign: "right", padding: "10px", borderBottom: "1px solid var(--hairline)" }}>{v}</td>)}
                    </tr>
                  ))}
                  <tr>
                    <th scope="row" style={{ textAlign: "left", padding: "10px", fontWeight: 600 }}>31/12/2025</th>
                    <td colSpan={5} style={{ textAlign: "right", padding: "10px", color: "var(--text-2)" }}>publicado no painel · <Link href="/metodologia/#qualidade" style={{ color: "var(--accent)", textDecoration: "underline", textUnderlineOffset: 3 }}>ver qualidade</Link></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
      <section aria-labelledby="regras-title" style={{ marginTop: 32 }}>
        <h2 className="title" id="regras-title" style={{ fontSize: "1.25rem" }}>Como a série será montada</h2>
        <ol style={{ listStyle: "none", padding: 0, margin: "12px 0 0", display: "grid" }}>
          {REGRAS.map(([t, d], i) => (
            <li key={t} style={{ display: "grid", gridTemplateColumns: "36px 1fr", gap: 14, padding: "14px 0", borderTop: "1px solid var(--hairline)" }}>
              <span className="num" style={{ fontFamily: "var(--font-display)", fontSize: "1.125rem", fontWeight: 650, color: "var(--text-3)" }}>{String(i + 1).padStart(2, "0")}</span>
              <span><span style={{ fontWeight: 620 }}>{t}</span><br /><span className="muted" style={{ fontSize: "0.9375rem" }}>{d}</span></span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
