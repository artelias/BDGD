import { describe, expect, it } from "vitest";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const ARQUIVO = resolve(process.cwd(), "public/data/previsoes/cenarios-exploratorios-2026-2030.json");
const CONTRATO = resolve(process.cwd(), "../output-historico/contrato-integracao/serie_fisica_nacional.csv");
const dados = JSON.parse(readFileSync(ARQUIVO, "utf8"));

function tendencia(v: number[], alvo: number): number {
  const n = v.length;
  const mx = (n - 1) / 2;
  const my = v.reduce((a, b) => a + b, 0) / n;
  const slope = v.reduce((s, y, i) => s + (i - mx) * (y - my), 0) /
    v.reduce((s, _y, i) => s + (i - mx) ** 2, 0);
  return Math.max(0, my + slope * (alvo - mx));
}

describe("dados de cenários exploratórios — contrato nacional", () => {
  it("preserva a classificação não validada, universo conhecido e fonte versionada", () => {
    expect(dados.previsaoValidada).toBe(false);
    expect(dados.numeroOrigensBacktest).toBe(1);
    expect(dados.series).toHaveLength(1792);
    expect(new Set(dados.series.map((s: unknown[]) => s[0])).size).toBe(81);
    expect(new Set(dados.series.map((s: unknown[]) => s[2])).size).toBe(25);
    expect(dados.anosObservados).toEqual([2022, 2023, 2024, 2025]);
    expect(dados.anosSimulados).toEqual([2026, 2027, 2028, 2029, 2030]);
  });

  it("contém apenas séries numéricas, de perímetro único, com erros reproduzíveis", () => {
    for (const s of dados.series) {
      const historico: number[] = s[5];
      const linear: number[] = s[6];
      const erros: number[] = s[7];
      expect(historico).toHaveLength(4);
      expect(linear).toHaveLength(5);
      expect(s[8]).toHaveLength(4);
      expect(s[9]).toHaveLength(4);
      expect(s[10]).toHaveLength(4);
      expect(s[10].every((estado: string) => estado === "O" || estado === "Z")).toBe(true);
      expect([...historico, ...linear, ...erros].every((v) => Number.isFinite(v) && v >= 0)).toBe(true);
      for (let i = 0; i < 4; i++) {
        if (s[10][i] === "Z") expect(historico[i]).toBe(0);
        expect(s[8][i]).toMatch(/^[0-9a-f]{32}$/i);
      }
      expect(erros[0]).toBeCloseTo(Math.abs(historico[2] - historico[3]), 8);
      expect(erros[1]).toBeCloseTo(Math.abs(tendencia(historico.slice(0, 3), 3) - historico[3]), 8);
      linear.forEach((valor, i) => expect(valor).toBeCloseTo(tendencia(historico, i + 4), 7));
    }
  });

  it("usa o mesmo blob da origem quando o contrato nacional está no checkout", () => {
    if (!existsSync(CONTRATO)) return;
    const b = readFileSync(CONTRATO);
    const sha = createHash("sha1").update("blob " + b.length + "\0").update(b).digest("hex");
    expect(dados.blobShaOrigem).toBe(sha);
  });

  it("reproduz o placar do backtest de 2025 sem escolher um vencedor único", () => {
    let tendenciaVence = 0, persistenciaVence = 0, empates = 0;
    for (const s of dados.series) {
      const [persist, linear] = s[7];
      if (linear < persist - 1e-9) tendenciaVence++;
      else if (persist < linear - 1e-9) persistenciaVence++;
      else empates++;
    }
    expect([tendenciaVence, persistenciaVence, empates]).toEqual([832, 497, 463]);
  });
});
