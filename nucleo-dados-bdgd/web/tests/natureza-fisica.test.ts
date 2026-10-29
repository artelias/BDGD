import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { describe, expect, it } from "vitest";
import { exportarCsv, naturezaMetrica, parseCenarios, type MetricaCenario, type ProdutoCenarios } from "@/lib/cenarios-motor";
import { parseResumoMotor } from "@/lib/motor-universal";
import { arredondarContagem, casasDe, ehContagem, exigirCoerencia, exigirContagemInteira, formatarFisico, naturezaDe, valorPublico } from "@/lib/natureza-fisica";

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

  it("valorPublico não arredonda na borda: contagem fracionária é erro, as demais naturezas passam inalteradas", () => {
    expect(valorPublico(3, "discrete_count")).toBe(3);
    for (const ruim of [2.5, 0.2, -1, NaN]) expect(() => valorPublico(ruim, "discrete_count")).toThrow(/fracionária/);
    for (const n of ["continuous_length", "continuous_capacity", "continuous_energy", "ratio"] as const) expect(valorPublico(20705.206181, n)).toBe(20705.206181);
  });

  it("exigirContagemInteira recusa fração e negativo", () => {
    expect(exigirContagemInteira(7, "t")).toBe(7);
    for (const ruim of [7.5, -1, NaN]) expect(() => exigirContagemInteira(ruim, "t")).toThrow(/fracionária/);
  });

  it("exibição: contagem inteira sem casas decimais, fração é erro (nunca arredondada); extensão e potência com decimais", () => {
    expect(formatarFisico(92011, "discrete_count")).toBe("92.011");
    for (const ruim of [92010.762, 92010.5]) expect(() => formatarFisico(ruim, "discrete_count")).toThrow(/fracionária/);
    expect(formatarFisico(20705.206, "continuous_length")).toBe("20.705,2");
    expect(formatarFisico(745664.5, "continuous_capacity")).toBe("745.664,5");
    expect(formatarFisico(null, "discrete_count")).toBe("N/D");
    expect([casasDe("discrete_count"), casasDe("continuous_capacity"), casasDe("ratio")]).toEqual([0, 1, 3]);
  });

  it("coerência natureza × unidade × métrica: qualquer divergência é erro, nada é corrigido", () => {
    expect(exigirCoerencia({ natureza: "discrete_count", unidade: "itens", metrica: "quantidade" }, "t")).toBe("discrete_count");
    expect(exigirCoerencia({ unidade: "kVA", metrica: "potencia_kva" }, "t")).toBe("continuous_capacity");
    expect(exigirCoerencia({ unidade: "", metrica: "extensao_km" }, "t")).toBe("continuous_length");
    expect(() => exigirCoerencia({ natureza: "continuous_length", unidade: "itens", metrica: "quantidade" }, "t")).toThrow(/incompatível com a unidade/);
    expect(() => exigirCoerencia({ natureza: "discrete_count", unidade: "kVA", metrica: "potencia_kva" }, "t")).toThrow(/incompatível/);
    expect(() => exigirCoerencia({ natureza: "discrete_count", unidade: "km", metrica: "extensao_km" }, "t")).toThrow(/incompatível/);
    expect(() => exigirCoerencia({ unidade: "itens", metrica: "extensao_km" }, "t")).toThrow(/incompatível com a métrica/);
    expect(() => exigirCoerencia({ unidade: "MVA", metrica: "potencia_kva" }, "t")).toThrow(/Unidade MVA incompatível/);   // a métrica é em kVA: sem conversão silenciosa
    expect(() => exigirCoerencia({ unidade: "km", metrica: "potencia_kva" }, "t")).toThrow();
    expect(() => exigirCoerencia({ natureza: "inventada", unidade: "itens", metrica: "quantidade" }, "t")).toThrow(/inválida/);
    expect(() => exigirCoerencia({ unidade: "furlongs", metrica: "quantidade" }, "t")).toThrow(/natureza física/);
    expect(() => exigirCoerencia({ metrica: "algo_novo" }, "t")).toThrow(/não determinável/);
  });
});

describe("produtos públicos respeitam o contrato", () => {
  it("parseCenarios recusa contagem fracionária e aceita decimais em extensão e potência", () => {
    expect(() => parseCenarios(produto("itens", "quantidade", [11, 12.4]))).toThrow(/fracionária/);
    expect(() => parseCenarios(produto("itens", "quantidade", [11, 12]))).not.toThrow();
    expect(() => parseCenarios(produto("km", "extensao_km", [11.25, 12.5]))).not.toThrow();
    expect(() => parseCenarios(produto("kVA", "potencia_kva", [1100.5, 1200.25]))).not.toThrow();
  });

  it("parseCenarios recusa natureza incompatível com a unidade ou a métrica", () => {
    const comNatureza = (natureza: string, unidade: string, metrica: string, traj: number[]) => {
      const p = produto(unidade, metrica, traj); (p.metricas[0] as { natureza?: string }).natureza = natureza; return p;
    };
    expect(() => parseCenarios(comNatureza("continuous_length", "itens", "quantidade", [11, 12]))).toThrow(/incompatível/);
    expect(() => parseCenarios(comNatureza("discrete_count", "km", "extensao_km", [11, 12]))).toThrow(/incompatível/);
    expect(() => parseCenarios(comNatureza("discrete_count", "kVA", "potencia_kva", [1100, 1200]))).toThrow(/incompatível/);
    expect(() => parseCenarios(comNatureza("continuous_capacity", "kVA", "extensao_km", [1100.5, 1200.5]))).toThrow(/incompatível/);
    expect(() => parseCenarios(comNatureza("discrete_count", "itens", "quantidade", [11, 12]))).not.toThrow();
    // a fração não é "corrigida" quando a natureza declarada é contagem
    expect(() => parseCenarios(comNatureza("discrete_count", "itens", "quantidade", [11, 12.5]))).toThrow(/fracionária/);
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

  it("parseResumoMotor recusa natureza ou unidade incompatível com a métrica", () => {
    const base = () => JSON.parse(gunzipSync(readFileSync("public/data/previsoes/motor-universal-resumo.json.gz")).toString("utf8"));
    const r1 = base(); r1.series.find((x: { unidade: string }) => x.unidade === "itens").natureza_fisica = "continuous_length";
    expect(() => parseResumoMotor(r1)).toThrow(/incompatível/);
    const r2 = base(); const o = r2.objetivos.find((x: { unidade: string; metrica: string }) => x.metrica === "extensao_km"); o.unidade = "itens";
    expect(() => parseResumoMotor(r2)).toThrow();
    expect(() => parseResumoMotor(base())).not.toThrow();
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
