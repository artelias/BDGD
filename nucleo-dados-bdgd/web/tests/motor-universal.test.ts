import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { exportarExperimentoMotor, parseResumoMotor } from "../src/lib/motor-universal";
const raw = () => JSON.parse(gunzipSync(readFileSync("public/data/previsoes/motor-universal-resumo.json.gz")).toString("utf8"));
describe("Motor universal — contrato e publicação", () => {
  it("descobre os ativos e métricas pelo catálogo, sem lista de TUCs fixa", () => {
    const data = parseResumoMotor(raw());
    const catalog = JSON.parse(readFileSync("../etl/bdgd2025/config/conceitos_2025.json", "utf8"));
    expect([...new Set(data.objetivos.map((t) => t.objetivo_id))].sort()).toEqual(catalog.ativos.map((t: { id: string }) => t.id).sort());
    expect(data.objetivos.some((t) => t.metrica === "potencia_kva")).toBe(true);
    expect(data.objetivos.find((t) => t.objetivo_id === "rede_mt" && t.padrao)?.unidade).toBe("km");
  });
  it("recusa contratos desconhecidos, sintéticos ou alegação de validação automática", () => {
    for (const mutation of [{ schema_version: "outro" }, { sintetico: true }, { previsao_validada: true }])
      expect(() => parseResumoMotor({ ...raw(), ...mutation })).toThrow();
  });
  it("recusa objetivo duplicado, unidade incompatível e projeção negativa", () => {
    const data = raw(); data.objetivos.push(data.objetivos[0]);
    expect(() => parseResumoMotor(data)).toThrow();
    const unit = raw(); unit.series[0].unidade = "MWh";
    expect(() => parseResumoMotor(unit)).toThrow();
    const value = raw(); value.series.find((s: { modelos: unknown[] }) => s.modelos.length).modelos[0].futuro[0] = -1;
    expect(() => parseResumoMotor(value)).toThrow();
  });
  it("mantém N/D e zeros técnicos, sem fabricar potência ausente", () => {
    const data = parseResumoMotor(raw());
    expect(data.series.some((s) => s.historico.some((h) => h.valor === null))).toBe(true);
    expect(data.series.some((s) => s.historico.some((h) => h.estado === "zero_tecnico"))).toBe(true);
    expect(data.series.some((s) => s.historico.some((h) => h.estado === "zero_verificado"))).toBe(false);
    expect(data.objetivos.filter((t) => t.metrica === "potencia_kva").every((t) => t.series === 0)).toBe(true);
  });
  it("exporta estado, versões, corte e diagnóstico, sem intervalo inventado", () => {
    const data = parseResumoMotor(raw());
    const serie = data.series.find((s) => s.modelos.length)!;
    const exported = JSON.parse(exportarExperimentoMotor(data, serie, serie.modelos[0]));
    expect(exported.previsao_validada).toBe(false);
    expect(exported.natureza).toBe("simulacao_condicional");
    expect(exported.intervalos).toBeNull();
    expect(exported.source_sha256).toHaveLength(64);
    expect(exported.code_version).toHaveLength(64);
    expect(exported.serie.historico).toEqual(serie.historico);
  });
});
