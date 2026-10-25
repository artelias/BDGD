// Radar · Benchmark com fixtures SINTÉTICAS (não são dados BDGD).
import { describe, expect, it } from "vitest";
import { eixosRadar, lider } from "@/lib/benchmark";
import type { Indicador } from "@/lib/catalogo";
import { Dataset } from "@/lib/dataset";
import { ndDetalhe, ndFrase } from "@/lib/kpis";
import type { Distribuidora, IndexData } from "@/lib/types";

const dist = (dist: number, grupo: string, verificado = true): Distribuidora => ({
  dist, sigla: `D_${dist}`, nome: `D ${dist}`, grupo, grupo_status: verificado ? "verificado" : "nao_confirmado", area_km2: 1, ufs: [], fonte: "https://x", sha256: "a".repeat(64), versao: "V11", alertas: {},
});
const idx: IndexData = {
  release: { schema_version: "1.1.0", release_id: "teste", data_base: "2025-12-31", status: "homologado", generated_at: "2026-10-23T00:00:00Z", dda_version: "t",
    quality: { status: "aprovado", source_reconciliation: true }, cobertura: { distribuidoras_historicas_consideradas: 5, com_gdb_2025: 5, processadas: 5, quarentena: [], em_processamento: [], sem_publicacao_2025: [] },
    regras: {}, licenca: "", autoria: "", privacidade: "" },
  distribuidoras: [dist(1, "g1"), dist(2, "g1"), dist(3, "g2"), dist(4, "g2"), dist(5, "nao_confirmado", false)],
  grupos: [
    { id: "g1", nome: "Grupo Um", controlador: "X", fontes: ["https://x"], tipo_fonte: "t", consultado_em: "2026-10-23", observacao: "" },
    { id: "g2", nome: "Grupo Dois", controlador: "Y", fontes: ["https://x"], tipo_fonte: "t", consultado_em: "2026-10-23", observacao: "" },
  ],
  entidades: [
    { id: "UNTRMT", nome: "Transformadores", familia: "Transformação", metrica: "quantidade", unidade: "itens", regra: "", ativo: true, naoSomarCom: "EQTRMT" },
    { id: "SSDMT", nome: "Rede MT", familia: "Rede", metrica: "extensao_km", unidade: "km", regra: "", ativo: true, naoSomarCom: null },
  ],
  fatos: { cols: [], rows: [
    [1, "UNTRMT", 1200, 1200, 1200, null, null, "a", ""], [2, "UNTRMT", 300, 300, 300, null, null, "a", ""],
    [3, "UNTRMT", 1000, 1000, 1000, null, null, "a", ""], [4, "UNTRMT", 1000, 1000, 1000, null, null, "a", ""], [5, "UNTRMT", 500, 500, 500, null, null, "a", ""],
    [1, "SSDMT", 10, 10, 10, null, null, "b", "COMP nulo"], [2, "SSDMT", 10, 10, 10, null, null, "b", "COMP nulo"],
    [3, "SSDMT", 10, 10, 10, 50, null, "a", ""], [4, "SSDMT", 10, 10, 10, 0, null, "a", ""],
  ] },
  complementares: {}, cobertura: [], filtrosIndisponiveis: [], homologacao: [],
};
const ds = new Dataset(idx);
const ind = (id: string, ent: string, metric: Indicador["metric"]): Indicador => ({ id, nome: id, resumo: "", explicacao: "", tecnico: "", ent, metric, conceito: "x" });
const TR = ind("tr", "UNTRMT", "quantidade");
const REDE = ind("rede", "SSDMT", "extensao_km");
const g1 = ds.scopeDists({ tipo: "grupo", id: "g1" });

describe("radar · benchmark (caso de aceite)", () => {
  it("A = 1500, MAX_g = 2000 → 75%", () => {
    const [e] = eixosRadar(ds, [TR], g1, "bench_grupos", [], "");
    expect(e.a.v).toBe(1500); expect(e.ref).toBe(2000); expect(e.pctA).toBeCloseTo(0.75); expect(e.pctRef).toBe(1);
    expect(e.lider?.nome).toBe("Grupo Dois");
  });
  it("A = 1500, MAX_d = 1200 → 125% (não truncado)", () => {
    const [e] = eixosRadar(ds, [TR], g1, "bench_dists", [], "");
    expect(e.ref).toBe(1200); expect(e.pctA).toBeCloseTo(1.25); expect(e.lider?.nome).toBe("D 1");
  });
  it("Brasil = soma de todas as distribuidoras, inclusive sem grupo verificado", () => {
    const [e] = eixosRadar(ds, [TR], g1, "brasil", [], "");
    expect(e.ref).toBe(4000); expect(e.pctA).toBeCloseTo(0.375);
  });
  it("lado B usa B como denominador comum", () => {
    const [e] = eixosRadar(ds, [TR], g1, "lado", ds.scopeDists({ tipo: "grupo", id: "g2" }), "Grupo Dois");
    expect(e.pctA).toBeCloseTo(0.75); expect(e.refLabel).toBe("Grupo Dois");
  });
  it("N/D remove o eixo, com motivo", () => {
    const [e] = eixosRadar(ds, [REDE], g1, "bench_grupos", [], "");
    expect(e.a.v).toBeNull(); expect(e.pctA).toBeNull(); expect(e.nd).toMatch(/A sem valor/);
  });
  it("referência zero não gera porcentagem", () => {
    const [e] = eixosRadar(ds, [REDE], [3], "lado", [4], "D 4");
    expect(e.ref).toBe(0); expect(e.pctA).toBeNull(); expect(e.nd).toMatch(/zero/);
  });
  it("líder de grupos ignora distribuidoras sem grupo verificado", () => {
    expect(lider(ds, TR, "grupos")?.v).toBe(2000);
    expect(lider(ds, TR, "dists")?.v).toBe(1200);
  });
});

describe("N/D explicado", () => {
  it("lista quem ficou sem valor e o motivo do pacote", () => {
    const nd = ndDetalhe(ds, REDE, [1, 2, 3]);
    expect(nd.map((x) => x.dist)).toEqual([1, 2]);
    expect(nd[0].motivo).toBe("COMP nulo");
  });
  it("frase singular e plural", () => {
    expect(ndFrase(1)).toBe("1 distribuidora sem valor homologado");
    expect(ndFrase(3)).toBe("3 distribuidoras sem valor homologado");
  });
});

describe("radar genérico por linha (R3, mesmo caso de aceite)", async () => {
  const { benchmarkLinhas, somar } = await import("@/lib/comparador");
  const linha = { id: "tr", nome: "tr", familia: "x", medida: "quantidade" as const, porDist: new Map<number, number | null>([[1, 1200], [2, 300], [3, 1000], [4, 1000], [5, 500]]) };
  it("A = 1500, MAX_g = 2000 → 75%; MAX_d = 1200 → 125%; Brasil = 37,5%", () => {
    expect(somar(linha, g1).v).toBe(1500);
    expect(benchmarkLinhas(ds, [linha], g1, "bench_grupos", [], "")[0].pctA).toBeCloseTo(0.75);
    expect(benchmarkLinhas(ds, [linha], g1, "bench_dists", [], "")[0].pctA).toBeCloseTo(1.25);
    expect(benchmarkLinhas(ds, [linha], g1, "brasil", [], "")[0].pctA).toBeCloseTo(0.375);
  });
  it("N/D numa DIST de A remove-a da soma e é contada", () => {
    const l2 = { ...linha, porDist: new Map<number, number | null>([[1, null], [2, 300]]) };
    const s = somar(l2, g1); expect(s.v).toBe(300); expect(s.nd).toBe(1);
  });
});
