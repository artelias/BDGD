import type { Metadata } from "next";
import { ChartSpline } from "lucide-react";

export const metadata: Metadata = { title: "Previsões" };

const ETAPAS = [
  ["Histórico 2022–2024", "Extração das BDGDs de 31/12/2022, 2023 e 2024 com o mesmo rigor de validação da competência 2025."],
  ["Sucessões e perímetros", "Mapeamento de incorporações e transferências (por exemplo, Energisa Borborema → Energisa Paraíba) para séries comparáveis ao perímetro de 2025, sem dupla contagem."],
  ["Séries harmonizadas", "Uma série original por distribuidora e uma série analítica no perímetro 2025, com regras de comparabilidade por entidade e métrica."],
  ["Modelagem (futuro)", "Somente depois de inspecionar o histórico: baselines, validação temporal e intervalos de incerteza. Nenhum modelo foi treinado."],
];

export default function Page() {
  return (
    <div style={{ maxWidth: 760 }}>
      <div className="eyebrow">Roteiro · sem resultados calculados</div>
      <h1 className="display" style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 14 }}><ChartSpline size={34} strokeWidth={1.6} color="var(--accent)" aria-hidden /> Previsões</h1>
      <p className="lede" style={{ marginTop: 10 }}>
        Este módulo está em planejamento. O portal publica exclusivamente dados da BDGD de 31/12/2025; nenhuma previsão, tendência ou série histórica é exibida aqui, e os dados de 2022–2024 não entram no painel 2025.
      </p>
      <ol style={{ listStyle: "none", padding: 0, margin: "28px 0 0", display: "grid", gap: 0 }}>
        {ETAPAS.map(([t, d], i) => (
          <li key={t} style={{ display: "grid", gridTemplateColumns: "36px 1fr", gap: 14, padding: "16px 0", borderTop: "1px solid var(--hairline)" }}>
            <span className="num" style={{ fontFamily: "var(--font-display)", fontSize: "1.25rem", fontWeight: 650, color: "var(--text-3)" }}>{String(i + 1).padStart(2, "0")}</span>
            <span><span style={{ fontWeight: 620 }}>{t}</span><br /><span className="muted" style={{ fontSize: "0.9375rem" }}>{d}</span></span>
          </li>
        ))}
      </ol>
    </div>
  );
}
