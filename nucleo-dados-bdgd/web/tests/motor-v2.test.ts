import { execFileSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  CENARIOS_V2, ESTADOS_PROJETADOS, SCHEMA_MOTOR_V2, csvSerieV2, motorV2Habilitado, projetada, somaGrupo, validarDist, validarIndice,
  type DistV2, type SerieV2,
} from "../src/lib/motor-v2";

const raiz = resolve(__dirname, "../data-motor-v2");
const indice = validarIndice(JSON.parse(readFileSync(join(raiz, "indice.json"), "utf8")));
const arquivos = readdirSync(join(raiz, "dist")).filter((f) => f.endsWith(".json"));
const dists: DistV2[] = arquivos.map((f) => validarDist(JSON.parse(readFileSync(join(raiz, "dist", f), "utf8"))));
const ESTADOS = ["PROJETADA_EXPERIMENTAL", "PROJETADA_BASELINE", "SEM_ANCORA_2025", "HISTORICO_INSUFICIENTE", "DADO_NAO_HOMOLOGADO",
  "SEM_PUBLICACAO", "SUCESSAO_SOCIETARIA", "NAO_APLICAVEL", "SEM_SEMANTICA_FISICA_HOMOGENEA", "BLOQUEIO_TECNICO"];

describe("produto do Motor V2 (data-motor-v2, homologação)", () => {
  it("cobre o universo do contrato: 114 DIST, catálogo inteiro, todo registro com estado documentado", () => {
    expect(indice.schema).toBe(SCHEMA_MOTOR_V2);
    expect(indice.status_publicacao).toMatch(/NAO_PUBLICAVEL_EM_PRODUCAO/);
    expect(dists).toHaveLength(114);
    expect(indice.resumo.universo.objetivos_metricas_catalogo).toBe(29);
    expect(indice.resumo.cobertura_processamento.fracao).toBe(1);
    expect(indice.resumo.bloqueio_tecnico).toBe(0);
    const n = indice.objetivos.length;
    for (const d of dists) {
      expect(d.series).toHaveLength(n);
      for (const s of d.series) {
        expect(ESTADOS).toContain(s.estado);
        expect(s.motivo.length > 0 || projetada(s)).toBe(true);
      }
    }
  });

  it("toda série projetada tem exatamente 15 valores, não negativos, inteiros nas contagens e ordenados entre cenários", () => {
    let n = 0;
    for (const d of dists) for (const s of d.series.filter(projetada)) {
      n += 1;
      for (const c of CENARIOS_V2) expect(s.cenarios![c]).toHaveLength(5);
      for (let i = 0; i < 5; i += 1) {
        const [c0, m0, a0] = CENARIOS_V2.map((c) => s.cenarios![c][i]!);
        expect(c0).toBeLessThanOrEqual(m0 + 1e-6);
        expect(m0).toBeLessThanOrEqual(a0 + 1e-6);
      }
      expect(s.modelo?.homologado).toBe(false);
    }
    expect(n).toBe(indice.resumo.cobertura_previsao.com_15_valores);
  });

  it("série sem projeção nunca traz números; ausência histórica fica null, nunca zero inventado", () => {
    for (const d of dists) for (const s of d.series) {
      if (!projetada(s)) { expect(s.cenarios).toBeNull(); expect(s.modelo).toBeNull(); }
      for (const [, v, est] of s.historico) if (v === 0) expect(est).toMatch(/zero_verificado|observado|extraido|utilizavel/);
    }
  });

  it("Consumidores contém UCBT em toda célula com as duas séries ancoradas em 2025", () => {
    let celulas = 0;
    for (const d of dists) {
      const c = d.series.find((s) => s.objetivo === "consumidores");
      const u = d.series.find((s) => s.objetivo === "ucbt");
      if (!c?.cenarios || !u?.cenarios || c.ancora !== 2025 || u.ancora !== 2025) continue;
      for (const k of CENARIOS_V2) c.cenarios[k].forEach((v, i) => { celulas += 1; expect(v!).toBeGreaterThanOrEqual(u.cenarios![k][i]!); });
    }
    expect(celulas).toBeGreaterThan(1000);
  });

  it("incorporadas e códigos de sucessão não aparecem como empresa ativa", () => {
    for (const dist of [6611, 6612, 70, 397]) {
      const d = dists.find((x) => x.dist === dist)!;
      expect(d.series.every((s) => s.estado === "SUCESSAO_SOCIETARIA")).toBe(true);
    }
  });

  it("totais nacionais: PARCIAL quando falta DIST aplicável; potência de reguladores sem total", () => {
    const reg = indice.objetivos.find((o) => o.objetivo === "reguladores" && o.metrica === "potencia_kva")!;
    expect(reg.total_2030).toBeNull();
    expect(indice.objetivos.find((o) => o.objetivo === "trafo_medida" && o.metrica === "potencia_kva")!.estados.NAO_APLICAVEL).toBeGreaterThan(0);
    for (const o of indice.objetivos.filter((x) => x.total_2030)) {
      const faltam = (o.estados.SEM_ANCORA_2025 ?? 0) + (o.estados.DADO_NAO_HOMOLOGADO ?? 0) + (o.estados.HISTORICO_INSUFICIENTE ?? 0) + (o.estados.SEM_PUBLICACAO ?? 0);
      if (faltam) expect(o.rotulo_total).toBe("PARCIAL");
    }
  });

  it("não expõe identificador individual nem credencial; arquivos pequenos para carga sob demanda", () => {
    for (const f of ["indice.json", ...arquivos.map((a) => `dist/${a}`)]) {
      const t = readFileSync(join(raiz, f), "utf8");
      expect(t).not.toMatch(/COD_ID|PAC_1|\bCPF\b|password|token|secret|BEGIN [A-Z ]*KEY/i);
      expect(statSync(join(raiz, f)).size).toBeLessThan(200_000);
    }
  });
});

describe("regras da interface do Motor V2", () => {
  const serie = (over: Partial<SerieV2>): SerieV2 => ({
    objetivo: "postes", metrica: "quantidade", nome: "Postes", familia: "Estruturas", unidade: "itens", natureza: "discrete_count", variante: null,
    estado: "PROJETADA_BASELINE", classe: null, motivo: "", fonte: "nivel_B", historico: [[2024, 10, "observado"], [2025, 11, "observado"]], ancora: 2025,
    horizonte_real: "1..5", valor_ancora: 11, entra_em_totais: true, modelo: null, erros: null, baselines: null, melhor_baseline_medido: null, ganho_vs_melhor_baseline: null,
    cenarios: { Conservador: [11, 11, 11, 11, 11], Moderado: [12, 13, 14, 15, 16], Agressivo: [13, 15, 17, 19, 21] }, cenarios_meta: null, ...over,
  });

  it("portão fechado por padrão e aberto só com NEXT_PUBLIC_MOTOR_V2=homologacao", () => {
    expect(motorV2Habilitado(undefined)).toBe(false);
    expect(motorV2Habilitado("")).toBe(false);
    expect(motorV2Habilitado("producao")).toBe(false);
    expect(motorV2Habilitado("homologacao")).toBe(true);
  });

  it("soma de grupo: completa só com todas as DIST; ausente nunca vira zero", () => {
    const a = { dist: 1, empresa: "A", serie: serie({}) };
    const b = { dist: 2, empresa: "B", serie: serie({ estado: "SEM_ANCORA_2025", entra_em_totais: false, ancora: 2023 }) };
    expect(somaGrupo([a, { ...a, dist: 3, empresa: "C" }], "Moderado")).toMatchObject({ rotulo: "COMPLETO", incluidas: 2, total: [24, 26, 28, 30, 32] });
    const p = somaGrupo([a, b, { dist: 4, empresa: "D", serie: undefined }], "Moderado");
    expect(p.rotulo).toBe("PARCIAL");
    expect(p.faltam).toEqual(["B", "D"]);
    expect(p.total).toEqual([12, 13, 14, 15, 16]);
    expect(somaGrupo([{ dist: 9, empresa: "Z", serie: undefined }], "Moderado").total).toBeNull();
    const reg = serie({ objetivo: "reguladores", metrica: "potencia_kva", unidade: "kVA", natureza: "continuous_power" });
    expect(somaGrupo([{ dist: 1, empresa: "A", serie: reg }], "Moderado").rotulo).toBe("NAO_SOMAVEL");
  });

  it("histórico com ano ausente não é somado como zero no grupo", () => {
    const a = { dist: 1, empresa: "A", serie: serie({ historico: [[2024, null, "ausente"], [2025, 11, "observado"]] }) };
    const g = somaGrupo([a, { dist: 2, empresa: "B", serie: serie({}) }], "Moderado");
    expect(g.hist.has(2024)).toBe(false);
    expect(g.hist.get(2025)).toBe(22);
  });

  it("CSV respeita o recorte e deixa N/D vazio", () => {
    const csv = csvSerieV2({ dist: 1, empresa: "A; B" }, serie({ historico: [[2024, null, "ausente:PUBLICACAO_NAO_LOCALIZADA"], [2025, 11, "observado"]] }));
    const linhas = csv.trim().split("\n");
    expect(linhas).toHaveLength(1 + 2 + 15);
    expect(linhas[1]).toContain(';2024;observado;;;ausente:PUBLICACAO_NAO_LOCALIZADA;');
    expect(linhas[1]).toContain('"A; B"');
    expect(csv).toContain("experimental_nao_homologado");
  });

  it("valida contra contrato: contagem fracionária ou série sem projeção com valores é rejeitada", () => {
    const d = (s: SerieV2): DistV2 => ({ schema: SCHEMA_MOTOR_V2, dist: 1, empresa: "A", grupo: null, series: [s] });
    expect(() => validarDist(d(serie({ cenarios: { Conservador: [1.5, 1, 1, 1, 1], Moderado: [1, 1, 1, 1, 1], Agressivo: [1, 1, 1, 1, 1] } })))).toThrow(/fracionária/);
    expect(() => validarDist(d(serie({ estado: "NAO_APLICAVEL" })))).toThrow(/sem projeção/);
    expect(ESTADOS_PROJETADOS).toHaveLength(3);
  });
});

describe("portão de publicação (scripts/motor-v2-gate.mjs)", () => {
  const rodar = (env: Record<string, string>) => {
    const tmp = mkdtempSync(join(tmpdir(), "gate-"));
    mkdirSync(join(tmp, "scripts")); mkdirSync(join(tmp, "data-motor-v2")); mkdirSync(join(tmp, "public/data/motor-v2"), { recursive: true });
    cpSync(resolve(__dirname, "../scripts/motor-v2-gate.mjs"), join(tmp, "scripts/motor-v2-gate.mjs"));
    writeFileSync(join(tmp, "data-motor-v2/indice.json"), "{}");
    writeFileSync(join(tmp, "public/data/motor-v2/resto.json"), "{}");
    const base = { NODE_ENV: "test", PATH: process.env.PATH ?? "", SystemRoot: process.env.SystemRoot ?? "" };
    execFileSync(process.execPath, [join(tmp, "scripts/motor-v2-gate.mjs")], { env: { ...base, ...env } as NodeJS.ProcessEnv });
    const out = { indice: existsSync(join(tmp, "public/data/motor-v2/indice.json")), resto: existsSync(join(tmp, "public/data/motor-v2/resto.json")) };
    rmSync(tmp, { recursive: true, force: true });
    return out;
  };
  it("produção: remove o produto experimental de public/", () => { expect(rodar({})).toEqual({ indice: false, resto: false }); });
  it("produção na Vercel continua fechada", () => { expect(rodar({ VERCEL_ENV: "production" })).toEqual({ indice: false, resto: false }); });
  it("homologação e preview da Vercel copiam o produto", () => {
    expect(rodar({ NEXT_PUBLIC_MOTOR_V2: "homologacao" }).indice).toBe(true);
    expect(rodar({ VERCEL_ENV: "preview" }).indice).toBe(true);
  });
});
