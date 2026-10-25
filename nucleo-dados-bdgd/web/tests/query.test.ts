// Testes da semântica de consulta com fixtures SINTÉTICAS (não são dados BDGD).
import { describe, expect, it } from "vitest";
import { Dataset } from "@/lib/dataset";
import { availableCodes, combinableWith, distribution, facetValue } from "@/lib/facets";
import { diff, fmt, fmtCompact, fmtPct, fmtUnit, toCSV } from "@/lib/format";
import type { FacetData, IndexData } from "@/lib/types";

const idx: IndexData = {
  release: { schema_version: "1.1.0", release_id: "teste", data_base: "2025-12-31", status: "parcial", generated_at: "2026-10-23T00:00:00Z", dda_version: "t",
    quality: { status: "em_validacao", source_reconciliation: true }, cobertura: { distribuidoras_historicas_consideradas: 4, com_gdb_2025: 3, processadas: 3, quarentena: [], em_processamento: [], sem_publicacao_2025: ["9"] },
    regras: {}, licenca: "", autoria: "", privacidade: "" },
  distribuidoras: [
    { dist: 1, sigla: "A_Um", nome: "A Um", grupo: "g1", grupo_status: "verificado", area_km2: 10, ufs: ["SP"], fonte: "https://x", sha256: "a".repeat(64), versao: "V11", alertas: {} },
    { dist: 2, sigla: "B_Dois", nome: "B Dois", grupo: "g1", grupo_status: "verificado", area_km2: 20, ufs: ["RJ"], fonte: "https://x", sha256: "b".repeat(64), versao: "V11", alertas: {} },
    { dist: 3, sigla: "C_Tres", nome: "C Tres", grupo: "nao_confirmado", grupo_status: "nao_confirmado", area_km2: 5, ufs: [], fonte: "https://x", sha256: "c".repeat(64), versao: "V11", alertas: {} },
  ],
  grupos: [{ id: "g1", nome: "Grupo Um", controlador: "X", fontes: ["https://x"], tipo_fonte: "t", consultado_em: "2026-10-23", observacao: "" }],
  entidades: [
    { id: "UCBT", nome: "UC BT", familia: "Consumidores", metrica: "quantidade", unidade: "itens", regra: "", ativo: true, naoSomarCom: null },
    { id: "UCMT", nome: "UC MT", familia: "Consumidores", metrica: "quantidade", unidade: "itens", regra: "", ativo: true, naoSomarCom: null },
    { id: "SSDMT", nome: "Rede MT", familia: "Rede", metrica: "extensao_km", unidade: "km", regra: "", ativo: true, naoSomarCom: null },
  ],
  fatos: { cols: [], rows: [
    [1, "UCBT", 100, 110, 100, null, null, "a", ""], [1, "UCMT", 5, 5, 5, null, null, "a", ""], [1, "SSDMT", 40, 40, 40, 12.5, null, "a", ""],
    [2, "UCBT", null, 80, 70, null, null, "l", "quantidade N/D"], [2, "UCMT", 3, 3, 3, null, null, "a", ""], [2, "SSDMT", 10, 10, 10, 3.25, null, "a", ""],
    [3, "UCBT", 20, 20, 20, null, null, "a", ""], [3, "SSDMT", 0, 0, 0, 0, null, "a", ""],
  ] },
  complementares: { uc_uniao_distinta: { "1": { "UC*": [104, "l", "sobreposicao=1"] }, "2": { "UC*": [72, "a", ""] }, "3": { "UC*": [20, "a", ""] } } },
  cobertura: [], filtrosIndisponiveis: [], homologacao: [],
};
const ds = new Dataset(idx);

describe("fato-base e agregação entre DISTs", () => {
  it("entidade ausente no GDB é N/D (null), nunca zero", () => {
    expect(ds.cell(3, "UCMT", "quantidade")).toBeNull();
    const a = ds.aggregate([3], "UCMT", "quantidade");
    expect(a.v).toBeNull(); expect(a.ausentes).toBe(1);
  });
  it("zero auditado continua zero", () => { expect(ds.aggregate([3], "SSDMT", "extensao_km").v).toBe(0); });
  it("soma parcial declara N/D e cobertura", () => {
    const a = ds.aggregate([1, 2, 3], "UCBT", "quantidade");
    expect(a.v).toBe(120); expect(a.n).toBe(2); expect(a.nd).toBe(1); expect(a.partial).toBe(true);
  });
  it("grupo soma apenas vínculos verificados", () => {
    expect(ds.scopeDists({ tipo: "grupo", id: "g1" })).toEqual([1, 2]);
    expect(ds.aggregate(ds.scopeDists({ tipo: "grupo", id: "g1" }), "SSDMT", "extensao_km").v).toBe(15.75);
  });
  it("consumidores usam a união por DIST e ignoram DIST com UC não validada", () => {
    const c = ds.consumidores([1, 2, 3]);
    expect(c.v).toBe(124); // DIST 2 tem UCBT N/D
    expect(c.nd).toBe(1);
  });
});

const facets: FacetData = {
  entidade: "UCBT",
  facets: [
    { id: "UCBT.ARE_LOC", dims: ["ARE_LOC"], metricas: { quantidade_registros: { unidade: "itens", rollup: true, disjunta: true, cobertura: "completa", status: "a" }, quantidade: { unidade: "itens", rollup: false, disjunta: false, cobertura: "completa", status: "l" } } },
    { id: "UCBT.FAS_CON", dims: ["FAS_CON"], metricas: { quantidade_registros: { unidade: "itens", rollup: true, disjunta: true, cobertura: "completa", status: "a" } } },
    { id: "UCBT.CLAS_SUB", dims: ["CLAS_SUB"], metricas: { quantidade_registros: { unidade: "itens", rollup: true, disjunta: true, cobertura: "completa", status: "a" } } },
    { id: "UCBT.ARE_LOC+FAS_CON", dims: ["ARE_LOC", "FAS_CON"], metricas: { quantidade_registros: { unidade: "itens", rollup: true, disjunta: true, cobertura: "completa", status: "a" } } },
  ],
  descricoes: { ARE_LOC: { UB: "Urbano", NU: "Não urbano" }, FAS_CON: { A: "Monofásico" } },
  atributos: {},
  rows: {
    "UCBT.ARE_LOC": [[1, ["UB"], { quantidade_registros: 80, quantidade: 75 }, { quantidade_registros: "a", quantidade: "l" }], [1, ["NU"], { quantidade_registros: 30, quantidade: 28 }, { quantidade_registros: "a", quantidade: "l" }],
      [2, ["UB"], { quantidade_registros: 80, quantidade: null }, { quantidade_registros: "a", quantidade: "b" }]],
    "UCBT.FAS_CON": [[1, ["A"], { quantidade_registros: 110 }, { quantidade_registros: "a" }]],
    "UCBT.CLAS_SUB": [[1, ["RE1"], { quantidade_registros: 110 }, { quantidade_registros: "a" }]],
    "UCBT.ARE_LOC+FAS_CON": [[1, ["UB", "A"], { quantidade_registros: 80 }, { quantidade_registros: "a" }], [1, ["NU", "A"], { quantidade_registros: 30 }, { quantidade_registros: "a" }]],
  },
  motivos: { "2|quantidade": "quantidade N/D (regra UC v2)" },
};

describe("facetas DDA", () => {
  it("usa o cubo com exatamente as dimensões filtradas", () => {
    const r = facetValue(facets, { ARE_LOC: "UB", FAS_CON: "A" }, "quantidade_registros", new Set([1]));
    expect(r.status).toBe("ok"); expect(r.facet?.id).toBe("UCBT.ARE_LOC+FAS_CON"); expect(r.v).toBe(80);
  });
  it("sem cubo conjunto: combinação não suportada (nunca multiplica marginais)", () => {
    const r = facetValue(facets, { ARE_LOC: "UB", CLAS_SUB: "RE1" }, "quantidade_registros", new Set([1]));
    expect(r.status).toBe("combinacao_nao_suportada"); expect(r.v).toBeNull();
  });
  it("DIST bloqueado sai da soma e é contado como N/D", () => {
    const r = facetValue(facets, { ARE_LOC: "UB" }, "quantidade", new Set([1, 2]));
    expect(r.v).toBe(75); expect(r.n).toBe(1); expect(r.nd).toBe(1); expect(r.motivos[0]).toContain("regra UC v2");
  });
  it("distribuição não aditiva é sinalizada", () => {
    expect(distribution(facets, "ARE_LOC", "quantidade", new Set([1])).additive).toBe(false);
    expect(distribution(facets, "ARE_LOC", "quantidade_registros", new Set([1])).additive).toBe(true);
  });
  it("cascata: atributos combináveis e códigos disponíveis", () => {
    expect(combinableWith(facets, "ARE_LOC")).toEqual(["FAS_CON"]);
    expect(availableCodes(facets, "FAS_CON", new Set([1]), { ARE_LOC: "NU" })).toEqual(["A"]);
  });
  it("código sem descrição não ganha rótulo inventado", () => {
    const d = distribution(facets, "CLAS_SUB", "quantidade_registros", new Set([1]));
    expect(d.categories[0].label).toContain("sem descrição");
  });
});

describe("formatação e comparação", () => {
  it("N/D para nulo", () => { expect(fmt(null)).toBe("N/D"); expect(fmtCompact(undefined)).toBe("N/D"); });
  it("potência grande exibida em MVA com unidade explícita", () => { expect(fmtUnit(161165000, "potencia_kva")).toEqual({ value: "161.165", unit: "MVA" }); });
  it("Δ% indefinido quando B = 0 ou N/D", () => {
    expect(diff(10, 0)).toEqual({ abs: 10, rel: null });
    expect(diff(null, 5)).toEqual({ abs: null, rel: null });
    expect(fmtPct(diff(15, 10).rel)).toBe("+50,0%");
  });
  it("CSV RFC 4180 com vazio para N/D", () => {
    expect(toCSV(["a", "b"], [["x,y", null]])).toBe('a,b\n"x,y",\n');
  });
});

describe("cobertura do cubo e rótulos", () => {
  it("informa quantos DISTs do escopo o cubo cobre", () => {
    expect(distribution(facets, "ARE_LOC", "quantidade_registros", new Set([1, 2, 3])).covered).toBe(2);
    expect(distribution(facets, "FAS_CON", "quantidade_registros", new Set([1, 2, 3]), { ARE_LOC: "UB" }).covered).toBe(1);
  });
});
