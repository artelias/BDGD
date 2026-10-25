// Evolução 2022–2025 com fixtures SINTÉTICAS (não são dados BDGD).
import { describe, expect, it } from "vitest";
import { anoAno, anoCompleto, indexar, indice100, painelBalanceado, serieDist, serieSoma, STATUS_ANO, variacao, type CelulaSerie } from "@/lib/evolucao";

const anos = [2022, 2023, 2024, 2025];
const cel: CelulaSerie[] = [
  [1, 2022, 100, "v", 0], [1, 2023, 110, "v", 0], [1, 2024, 121, "v", 0], [1, 2025, 133.1, "v", 0],
  [2, 2022, 50, "v", 0], [2, 2023, null, "p", 0], [2, 2024, 60, "v", 0], [2, 2025, 70, "v", 0],
  [3, 2022, 0, "v", 0], [3, 2023, 10, "v", 0], [3, 2024, 20, "v", 0], [3, 2025, 30, "v", 0],
  [4, 2022, 1000, "v", 0], [4, 2023, 5000, "v", 1], [4, 2024, 5100, "v", 0], [4, 2025, 5200, "v", 0],
  // predecessora que deixou de publicar
  [9, 2022, 40, "v", 0], [9, 2023, null, "s", 0], [9, 2024, null, "s", 0], [9, 2025, null, "s", 0],
];
const idx = indexar(cel);

describe("séries observadas", () => {
  it("ano não processado fica sem valor (nunca zero, nunca interpolado)", () => {
    expect(serieDist(idx, 2, anos, "B").pontos.map((p) => p.v)).toEqual([50, null, 60, 70]);
  });
  it("soma só nos anos em que todas as DIST estão validadas", () => {
    expect(serieSoma(idx, [1, 2], anos, "g", "G").pontos.map((p) => p.v)).toEqual([150, null, 181, 203.1]);
  });
  it("DIST sem publicação bloqueia soma parcial; só não aplicabilidade explícita pode ser omitida", () => {
    expect(serieSoma(idx, [1, 9], anos, "g", "G").pontos.map((p) => p.v)).toEqual([140, null, null, null]);
    expect(serieSoma(idx, [1, 99], anos, "g", "G").pontos.every((p) => p.v === null)).toBe(true);
  });
  it("painel balanceado: só quem tem os quatro anos validados", () => {
    expect(painelBalanceado(idx, [1, 2, 3, 4, 9], anos)).toEqual([1, 3, 4]);
  });
});

describe("variações", () => {
  it("CAGR e variação acumulada", () => {
    const v = variacao(serieDist(idx, 1, anos, "A"));
    expect(v.abs).toBeCloseTo(33.1); expect(v.pct).toBeCloseTo(0.331); expect(v.cagr).toBeCloseTo(0.1);
  });
  it("base zero: percentual e CAGR indefinidos", () => {
    const v = variacao(serieDist(idx, 3, anos, "C"));
    expect(v.abs).toBe(30); expect(v.pct).toBeNull(); expect(v.cagr).toBeNull(); expect(v.motivo).toMatch(/base zero/);
  });
  it("quebra de classificação no intervalo bloqueia a variação (não é crescimento físico)", () => {
    const v = variacao(serieDist(idx, 4, anos, "D"));
    expect(v.pct).toBeNull(); expect(v.motivo).toMatch(/quebra/);
    expect(anoAno(serieDist(idx, 4, anos, "D"))[0].pct).toBeNull();
    expect(anoAno(serieDist(idx, 4, anos, "D"))[1].pct).toBeCloseTo(0.02);
  });
  it("índice base 100", () => {
    expect(indice100(serieDist(idx, 1, anos, "A")).pontos.map((p) => Math.round(p.v!))).toEqual([100, 110, 121, 133]);
  });
});

describe("status do ano", () => {
  it("completo técnico libera o agregado, mas não é rotulado como homologado", () => {
    expect(anoCompleto("homologado")).toBe(true);
    expect(anoCompleto("completo_tecnico")).toBe(true);
    expect(anoCompleto("parcial")).toBe(false);
    expect(anoCompleto("homologado_tecnico")).toBe(false);
    expect(anoCompleto(undefined)).toBe(false);
    expect(STATUS_ANO.completo_tecnico).not.toMatch(/homologado/);
  });
});
