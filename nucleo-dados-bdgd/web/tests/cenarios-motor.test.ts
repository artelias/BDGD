import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { CENARIOS, parseCenarios, somaGrupo, variacoes, type ProdutoCenarios } from "@/lib/cenarios-motor";

const erro = (elegivel: boolean) => ({ wape: 0.01, mae: 1, rmse: 1, vies: 0, mdape: 0.01, n: 3, wape_h1: 0.01, wape_h2: 0.02, estabilidade: 0, cagr: 0.02, elegivel, motivo: elegivel ? null : "X" });
function produto(): ProdutoCenarios {
  return {
    schema_version: "cenarios-motor-1", base: 2025, horizonte: [2026, 2027], origens_backtest: [2023, 2024], parametros: {},
    modelos: { persistencia: { nome: "P", familia: "b", complexidade: 0, formula: "" }, deriva: { nome: "D", familia: "b", complexidade: 1, formula: "" } },
    variaveis: [], empresas: { "1": "A", "2": "B" }, fontes_sha256: {}, intervalos: null, previsao_validada: false,
    metricas: [{
      conceito: "x", ativo: "X", familia: "F", metrica: "quantidade", unidade: "itens", estado: "dois_cenarios", experimental: false,
      cenarios: { conservador: "persistencia", moderado: "deriva", agressivo: null }, justificativas: { conservador: "", moderado: "", agressivo: "Indisponível" },
      modelos: { persistencia: erro(true), deriva: erro(true) }, diagnostico_painel: {},
      series: {
        "1": { hist: [[2024, 9], [2025, 10]], conservador: [10, 10], moderado: [11, 12], agressivo: null, erro_moderado: 0.01 },
        "2": { hist: [[2024, 4], [2025, 5]], conservador: [5, 5], moderado: null, agressivo: null, erro_moderado: null },
      },
    }],
  };
}

describe("produto de cenários do motor", () => {
  it("aceita produto coerente e recusa alegações indevidas", () => {
    expect(parseCenarios(produto()).metricas).toHaveLength(1);
    expect(() => parseCenarios({ ...produto(), previsao_validada: true })).toThrow();
    expect(() => parseCenarios({ ...produto(), intervalos: [] })).toThrow();
  });
  it("recusa cenário apontando para modelo inelegível e trajetória sem modelo", () => {
    const p = produto(); p.metricas[0].modelos.deriva = erro(false);
    expect(() => parseCenarios(p)).toThrow(/inelegível/);
    const q = produto(); q.metricas[0].series["1"].agressivo = [1, 2];
    expect(() => parseCenarios(q)).toThrow(/sem modelo/);
    const r = produto(); r.metricas[0].series["1"].moderado = [-1, 2];
    expect(() => parseCenarios(r)).toThrow(/inválida/);
  });
  it("soma de grupo só com todas as trajetórias; nunca completa faltantes", () => {
    const m = produto().metricas[0];
    expect(somaGrupo(m, ["1", "2"], "conservador", 2).traj).toEqual([15, 15]);
    const mod = somaGrupo(m, ["1", "2"], "moderado", 2);
    expect(mod.traj).toBeNull();
    expect(mod.faltantes).toEqual(["2"]);
    expect(mod.hist?.get(2025)).toBe(15);
  });
  it("variações absoluta e percentual contra o ano-base", () => {
    expect(variacoes(10, [11, 12])).toEqual([{ valor: 11, abs: 1, pct: 10.000000000000009 }, { valor: 12, abs: 2, pct: 19.999999999999996 }]);
    expect(variacoes(10, null)).toBeNull();
  });
  it("o produto publicado é válido e coerente com seus cenários", () => {
    const p = parseCenarios(JSON.parse(readFileSync("public/data/previsoes/cenarios-motor.json", "utf8")));
    expect(p.metricas.length).toBeGreaterThanOrEqual(25);
    for (const m of p.metricas) {
      const g = (c: (typeof CENARIOS)[number]) => m.cenarios[c] ? m.modelos[m.cenarios[c]!].cagr! : null;
      if (g("conservador") !== null) expect(g("conservador")!).toBeLessThan(g("moderado")!);
      if (g("agressivo") !== null) expect(g("agressivo")!).toBeGreaterThan(g("moderado")!);
      if (m.conceito === "consumidores") expect(m.series["5370"]?.moderado ?? null).toBeNull();
    }
  });
});
