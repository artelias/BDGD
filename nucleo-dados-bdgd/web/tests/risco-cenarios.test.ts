import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { avaliarRiscosCenario } from "../src/lib/risco-cenarios";

type Linha = [
  number, string, string, string, string,
  number[], number[], number[], string[], string[], string[],
];
const arquivo = resolve(process.cwd(), "public/data/previsoes/cenarios-exploratorios-2026-2030.json");
const pacote = JSON.parse(readFileSync(arquivo, "utf8")) as { series: Linha[] };
const possui = (h: number[], f: number[], estados: string[], codigo: string) =>
  avaliarRiscosCenario(h, f, estados, "tendencia_linear").some((a) => a.codigo === codigo);

describe("auditoria estatística dos cenários físicos", () => {
  it("não trata quatro zeros técnicos como prova de inexistência de ativo", () => {
    const a = avaliarRiscosCenario([0, 0, 0, 0], [0, 0, 0, 0, 0], ["Z", "Z", "Z", "Z"], "persistencia");
    expect(a.map((x) => x.codigo)).toContain("HISTORICO_QUATRO_ZEROS_TECNICOS");
    expect(a.map((x) => x.codigo)).toContain("ZERO_TECNICO_PENDENTE");
  });

  it("identifica quando um zero simulado foi introduzido por truncamento negativo", () => {
    const a = avaliarRiscosCenario([51, 51, 48, 20], [18.5, 8.9, 0, 0, 0], ["O", "O", "O", "O"], "tendencia_linear");
    expect(a.map((x) => x.codigo)).toContain("TENDENCIA_TRUNCADA_NO_ZERO");
    expect(a.map((x) => x.codigo)).toContain("REDUCAO_SUPERIOR_A_70_PCT");
  });

  it("não afirma truncamento no método de persistência", () => {
    const a = avaliarRiscosCenario([51, 51, 48, 20], [20, 20, 20, 20, 20], ["O", "O", "O", "O"], "persistencia");
    expect(a.map((x) => x.codigo)).not.toContain("TENDENCIA_TRUNCADA_NO_ZERO");
  });

  it("sinaliza duplicação e mudança para zero depois de valores positivos", () => {
    expect(possui([0, 0, 3, 3], [4, 5, 7, 8, 9], ["Z", "Z", "O", "O"],
      "EXPANSAO_SUPERIOR_A_100_PCT")).toBe(true);
    expect(possui([1, 1, 1, 0], [0, 0, 0, 0, 0], ["O", "O", "O", "Z"],
      "ZERO_2025_APOS_VALOR_POSITIVO")).toBe(true);
  });

  it("rejeita séries sem esquema temporal ou valores numéricos válidos", () => {
    expect(() => avaliarRiscosCenario([1, 2], [3, 4], ["O", "O"], "persistencia")).toThrow();
    expect(() => avaliarRiscosCenario([1, NaN, 3, 4], [3, 4, 5, 6, 7], ["O", "O", "O", "O"], "persistencia")).toThrow();
    expect(() => avaliarRiscosCenario([1, 2, 3, 4], [3, 4, 5, 6, 7], ["O", "X", "O", "O"], "persistencia")).toThrow();
  });

  it("audita os 1.555 casos reais e mantém alertas por série sem imputar dados", () => {
    const totais: Record<string, number> = {};
    for (const s of pacote.series) {
      const h = s[5], f = s[6], e = s[10];
      for (const a of avaliarRiscosCenario(h, f, e, "tendencia_linear")) {
        totais[a.codigo] = (totais[a.codigo] ?? 0) + 1;
      }
    }
    expect(pacote.series).toHaveLength(1555);
    expect(totais.ZERO_TECNICO_PENDENTE).toBe(205);
    expect(totais.HISTORICO_QUATRO_ZEROS_TECNICOS).toBe(190);
    expect(totais.ZERO_2025_APOS_VALOR_POSITIVO).toBe(4);
    expect(totais.TENDENCIA_TRUNCADA_NO_ZERO).toBe(11);
    expect(totais.EXPANSAO_SUPERIOR_A_100_PCT).toBe(65);
    expect(totais.REDUCAO_SUPERIOR_A_70_PCT).toBe(13);
  });
});
