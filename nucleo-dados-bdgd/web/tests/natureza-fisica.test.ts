import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { describe, expect, it } from "vitest";
import { exportarCsv, naturezaMetrica, parseCenarios, type MetricaCenario, type ProdutoCenarios } from "@/lib/cenarios-motor";
import { parseResumoMotor } from "@/lib/motor-universal";
import { arredondarContagem, casasDe, ehContagem, exigirContagemInteira, formatarFisico, naturezaDe, valorPublico } from "@/lib/natureza-fisica";

const erro = { wape: 0.01, mae: 1, rmse: 1, vies: 0, mdape: 0.01, n: 3, wape_h1: 0.01, wape_h2: 0.02, estabilidade: 0, cagr: 0.02, elegivel: true, motivo: null };
function produto(unidade: string, metrica: string, traj: number[]): ProdutoCenarios {
  return {
    schema_version: "cenarios-motor-1", base: 2025, horizonte: [2026, 2027], origens_backtest: [2023, 2024], parametros: {},
    modelos: { persistencia: { nome: "P", familia: "b", complexidade: 0, formula: "" } }, variaveis: [], empresas: { "1": "A" }, fontes_sha256: {},
    intervalos: null, previsao_validada: false,
    metricas: [{
      conceito: "x", ativo: "X", familia: "F", metrica, unidade, estado: "somente_moderado", experimental: false,
      cenarios: { conservador: null, moderado: "persistencia", agressivo: null }, justificativas: { conservador: "", moderado: "", agressivo: "" },
      modelos: { persistencia: erro }, diagnostico_painel: {},
      series: { "1": { hist: [[2024, 9], [2025, 10]], conservador: null, moderado: traj, agressivo: null, erro_moderado: 0.01 } },
    }],
  };
}

describe("natureza física das métricas", () => {
  it("classifica unidades e recusa unidade desconhecida", () => {
    expect([naturezaDe("itens"), naturezaDe("clientes"), naturezaDe("km"), naturezaDe("kVA"), naturezaDe("MWh"), naturezaDe("%")])
      .toEqual(["discrete_count", "discrete_count", "continuous_length", "continuous_capacity", "continuous_energy", "ratio"]);
    expect(() => naturezaDe("furlongs")).toThrow(/natureza física/);
    expect(ehContagem(naturezaDe("itens"))).toBe(true); expect(ehContagem(naturezaDe("km"))).toBe(false);
  });

  it("arredonda contagens com empate declarado (meio para cima) e recusa negativos", () => {
    expect([0.5, 1.5, 2.5, 3.5].map(arredondarContagem)).toEqual([1, 2, 3, 4]);
    expect(arredondarContagem(0.49999999999999994)).toBe(0);
    expect(arredondarContagem(1e15 + 0.5)).toBe(1e15 + 1);
    for (const ruim of [-0.1, NaN, Infinity]) expect(() => arredondarContagem(ruim)).toThrow();
  });

  it("valorPublico: inteiro para contagem, inalterado para as demais naturezas", () => {
    expect(valorPublico(2.5, "discrete_count")).toBe(3);
    for (const n of ["continuous_length", "continuous_capacity", "continuous_energy", "ratio"] as const) expect(valorPublico(20705.206181, n)).toBe(20705.206181);
  });

  it("exigirContagemInteira recusa fração e negativo", () => {
    expect(exigirContagemInteira(7, "t")).toBe(7);
    for (const ruim of [7.5, -1, NaN]) expect(() => exigirContagemInteira(ruim, "t")).toThrow(/fracionária/);
  });

  it("exibição: contagem sem casas decimais; extensão e potência com decimais", () => {
    expect(formatarFisico(92010.762, "discrete_count")).toBe("92.011");
    expect(formatarFisico(92010.5, "discrete_count")).toBe("92.011");
    expect(formatarFisico(20705.206, "continuous_length")).toBe("20.705,2");
    expect(formatarFisico(null, "discrete_count")).toBe("N/D");
    expect([casasDe("discrete_count"), casasDe("continuous_capacity"), casasDe("ratio")]).toEqual([0, 1, 3]);
  });
});

describe("produtos públicos respeitam o contrato", () => {
  it("parseCenarios recusa contagem fracionária e aceita decimais em extensão e potência", () => {
    expect(() => parseCenarios(produto("itens", "quantidade", [11, 12.4]))).toThrow(/fracionária/);
    expect(() => parseCenarios(produto("itens", "quantidade", [11, 12]))).not.toThrow();
    expect(() => parseCenarios(produto("km", "extensao_km", [11.25, 12.5]))).not.toThrow();
    expect(() => parseCenarios(produto("kVA", "potencia_kva", [1100.5, 1200.25]))).not.toThrow();
  });

  it("natureza da métrica: declarada ou derivada da unidade", () => {
    const base = { unidade: "itens", metrica: "quantidade" } as Pick<MetricaCenario, "natureza" | "unidade" | "metrica">;
    expect(naturezaMetrica(base)).toBe("discrete_count");
    expect(naturezaMetrica({ ...base, natureza: "continuous_length" })).toBe("continuous_length");
    expect(naturezaMetrica({ unidade: "", metrica: "potencia_kva" })).toBe("continuous_capacity");
  });

  it("exportação CSV: contagens inteiras e extensões com decimais", () => {
    const c = parseCenarios(produto("itens", "quantidade", [11, 12]));
    expect(exportarCsv(c, c.metricas[0], "1")).toContain("2026,simulacao_condicional,,11,");
    const k = parseCenarios(produto("km", "extensao_km", [11.25, 12.5]));
    expect(exportarCsv(k, k.metricas[0], "1")).toContain(",11.25,");
  });

  it("cenarios-motor.json publicado: nenhuma contagem fracionária e decimais preservados", () => {
    const p = parseCenarios(JSON.parse(readFileSync("public/data/previsoes/cenarios-motor.json", "utf8")));
    let contagens = 0, decimais = 0;
    for (const m of p.metricas) {
      const n = naturezaMetrica(m);
      for (const s of Object.values(m.series)) for (const c of ["conservador", "moderado", "agressivo"] as const) for (const v of s[c] ?? []) {
        if (ehContagem(n)) { contagens++; expect(Number.isInteger(v)).toBe(true); }
        else if (!Number.isInteger(v)) decimais++;
      }
    }
    expect(contagens).toBeGreaterThan(10000); expect(decimais).toBeGreaterThan(1000);
  });

  it("resumo do motor universal publicado: projeções de contagem são inteiras", () => {
    const r = parseResumoMotor(JSON.parse(gunzipSync(readFileSync("public/data/previsoes/motor-universal-resumo.json.gz")).toString("utf8")));
    let n = 0;
    for (const s of r.series) if (ehContagem(naturezaDe(s.unidade))) for (const m of s.modelos) for (const v of m.futuro) { n++; expect(Number.isInteger(v)).toBe(true); }
    expect(n).toBeGreaterThan(20000);
  });

  it("parseResumoMotor recusa projeção fracionária de contagem", () => {
    const r = JSON.parse(gunzipSync(readFileSync("public/data/previsoes/motor-universal-resumo.json.gz")).toString("utf8"));
    const s = r.series.find((x: { unidade: string; modelos: { futuro: number[] }[] }) => x.unidade === "itens" && x.modelos.some((m) => m.futuro.length));
    s.modelos.find((m: { futuro: number[] }) => m.futuro.length).futuro[0] += 0.5;
    expect(() => parseResumoMotor(r)).toThrow(/fracionária/);
  });

  it("cenarios exploratórios publicados: tendência de contagens inteira; extensão e potência com decimais", () => {
    const d = JSON.parse(readFileSync("public/data/previsoes/cenarios-exploratorios-2026-2030.json", "utf8"));
    let contagens = 0, decimais = 0;
    for (const s of d.series) for (const v of s[6]) {
      if (ehContagem(naturezaDe(s[4]))) { contagens++; expect(Number.isInteger(v)).toBe(true); }
      else if (!Number.isInteger(v)) decimais++;
    }
    expect(contagens).toBeGreaterThan(5000); expect(decimais).toBeGreaterThan(100);
  });
});
