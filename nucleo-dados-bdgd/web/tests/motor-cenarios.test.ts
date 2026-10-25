import { describe, expect, it } from "vitest";
import { gerarCenarioExploratorio } from "../src/lib/motor-cenarios";
import type { SerieFisica } from "../src/lib/previsoes-contrato";
const serie = (ano: number, valor: number): SerieFisica => ({
  ano, valor, dist: 6600, conceitoId: "rede_mt", metrica: "extensao", unidade: "km",
  perimetroId: "fixo", regraVersao: "v1", estado: "observado", fonte: "BDGD",
  dataBase: `${ano}-12-31`, cobertura: 1, perimetroBridgeId: null,
});
describe("motor exploratorio", () => {
  it("ajusta também o intercepto OLS na série real EAC/alimentadores", () => {
    const r = gerarCenarioExploratorio([88, 111, 120, 123].map((v, i) => serie(2022 + i, v)), 2030, "tendencia_linear");
    expect(r.pontos[0].valor).toBeCloseTo(139);
    expect(r.pontos[4].valor).toBeCloseTo(184.6);
    expect(r.backtest.maeModelo).toBeCloseTo(46 / 3);
    expect(r.backtest.maePersistencia).toBe(3);
  });
  it("produz cenarios identificados sem afirmar validacao", () => {
    const r = gerarCenarioExploratorio([serie(2022, 100), serie(2023, 110), serie(2024, 120), serie(2025, 130)], 2027, "tendencia_linear");
    expect(r.diagnostico.elegivel).toBe(true);
    expect(r.pontos.map((p) => [p.ano, p.valor, p.modo])).toEqual([
      [2026, 140, "simulacao_condicional"], [2027, 150, "simulacao_condicional"],
    ]);
    expect(r.backtest.origens).toBe(1);
    expect(r.backtest.maeModelo).toBe(0);
    expect(r.backtest.maePersistencia).toBe(10);
  });
  it("bloqueia N/D mesmo quando traz valor zero", () => {
    const r = gerarCenarioExploratorio([serie(2024, 10), { ...serie(2025, 0), estado: "ausente" }]);
    expect(r.pontos).toEqual([]);
    expect(r.diagnostico.motivos).toContain("OBSERVACAO_NAO_ELEGIVEL");
  });
  it("bloqueia lacuna temporal, cobertura parcial e ponte pendente", () => {
    const r = gerarCenarioExploratorio([serie(2022, 10), { ...serie(2024, 20), cobertura: 0.8, perimetroBridgeId: "EBO" }]);
    expect(r.diagnostico.motivos).toEqual(expect.arrayContaining(["LACUNA_TEMPORAL", "COBERTURA_INCOMPLETA", "PONTE_SOCietARIA_NAO_HOMOLOGADA"]));
    expect(r.pontos).toHaveLength(0);
  });
  it("rejeita misturar ativos e anos duplicados", () => {
    const r = gerarCenarioExploratorio([serie(2025, 10), { ...serie(2025, 12), conceitoId: "rede_bt" }]);
    expect(r.diagnostico.motivos).toEqual(expect.arrayContaining(["SERIES_INCOMPATIVEIS", "ANO_DUPLICADO"]));
  });
  it("nao cria cenario sem historico", () => {
    expect(gerarCenarioExploratorio([]).pontos).toEqual([]);
    expect(gerarCenarioExploratorio([serie(2025, 10)]).diagnostico.elegivel).toBe(false);
  });
});
