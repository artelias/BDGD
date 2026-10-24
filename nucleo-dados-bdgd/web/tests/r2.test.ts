// Matriz e participação dupla com fixtures SINTÉTICAS (não são dados BDGD).
import { describe, expect, it } from "vitest";
import { Dataset } from "@/lib/dataset";
import { aplicavel, csvRecorte, filtraDists } from "@/lib/matriz";
import { participacao } from "@/lib/participacao";
import type { Distribuidora, FacetData, IndexData } from "@/lib/types";

const dist = (dist: number, grupo: string, ufs: string[]): Distribuidora => ({
  dist, sigla: `D_${dist}`, nome: `D ${dist}`, grupo, grupo_status: grupo === "x" ? "nao_confirmado" : "verificado", area_km2: 1, ufs, fonte: "https://x", sha256: "a".repeat(64), versao: "V11", alertas: {},
});
const idx: IndexData = {
  release: { schema_version: "1.1.0", release_id: "r-teste", data_base: "2025-12-31", status: "homologado", generated_at: "", dda_version: "t", quality: { status: "aprovado", source_reconciliation: true },
    cobertura: { distribuidoras_historicas_consideradas: 3, com_gdb_2025: 3, processadas: 3, quarentena: [], em_processamento: [], sem_publicacao_2025: [] }, regras: {}, licenca: "", autoria: "", privacidade: "" },
  distribuidoras: [dist(1, "g", ["SP"]), dist(2, "g", ["RJ", "SP"]), dist(3, "x", ["SC"])],
  grupos: [{ id: "g", nome: "G", controlador: "", fontes: [""], tipo_fonte: "", consultado_em: "", observacao: "" }],
  entidades: [
    { id: "SSDMT", nome: "Rede MT", familia: "Rede", metrica: "extensao_km", unidade: "km", regra: "SUM(COMP)/1000", ativo: true, naoSomarCom: null },
    { id: "UCBT", nome: "UC BT", familia: "Consumidores", metrica: "quantidade", unidade: "itens", regra: "", ativo: true, naoSomarCom: null },
  ],
  fatos: { cols: [], rows: [[1, "SSDMT", 5, 5, 5, 10, null, "a", ""], [2, "SSDMT", 5, 5, 5, 20, null, "a", ""], [1, "UCBT", 7, 7, 7, null, null, "a", ""]] },
  complementares: {}, cobertura: [], filtrosIndisponiveis: [], homologacao: [],
};
const ds = new Dataset(idx);

describe("matriz R2", () => {
  it("Extensão só se aplica a tipos com comprimento; Quantidade a todos", () => {
    expect(aplicavel(ds, ds.entidade("SSDMT")!, "extensao_km")).toBe(true);
    expect(aplicavel(ds, ds.entidade("UCBT")!, "extensao_km")).toBe(false);
    expect(aplicavel(ds, ds.entidade("UCBT")!, "quantidade")).toBe(true);
  });
  it("filtro por UF seleciona distribuidoras com área na UF", () => {
    expect(filtraDists(ds, { grupo: "todos", dists: [], ufs: ["SP"] }).map((d) => d.dist)).toEqual([1, 2]);
    expect(filtraDists(ds, { grupo: "nao_confirmado", dists: [], ufs: [] }).map((d) => d.dist)).toEqual([3]);
  });
  it("CSV do recorte traz versão, regra, cobertura e entidade ausente explícita", () => {
    const csv = csvRecorte(ds, filtraDists(ds, { grupo: "todos", dists: [], ufs: [] }), [ds.entidade("SSDMT")!], "principal").split("\n");
    expect(csv[0]).toBe("data_base,versao,dist,sigla,grupo_economico,grupo_status,entidade,tipo_de_ativo,metrica,unidade,valor,status,motivo,regra,cobertura_recorte");
    expect(csv[1]).toContain("r-teste"); expect(csv[1]).toContain("2/3 distribuidoras com valor");
    expect(csv[3]).toContain("entidade_ausente");
  });
});

const fd = (rows: FacetData["rows"][string], rollup = true): FacetData => ({
  entidade: "EQTRMT", descricoes: {}, atributos: {}, motivos: {},
  facets: [{ id: "EQTRMT.TUC", dims: ["TUC"], metricas: { quantidade: { unidade: "itens", rollup, disjunta: rollup, cobertura: "completa", status: "a" } } }],
  rows: { "EQTRMT.TUC": rows },
});
const rows: FacetData["rows"][string] = [
  [1, ["565"], { quantidade: 30 }, { quantidade: "a" }], [1, ["570"], { quantidade: 10 }, { quantidade: "a" }],
  [2, ["565"], { quantidade: 60 }, { quantidade: "a" }], [3, ["565"], { quantidade: 10 }, { quantidade: "a" }],
];

describe("participação dupla", () => {
  it("categoria no recorte e recorte no Brasil, mesmo cubo", () => {
    const p = participacao(fd(rows), { TUC: "565" }, "TUC", "quantidade", new Set([1]), new Set([1, 2, 3]), 1, 3);
    expect(p.noEscopo).toBeCloseTo(0.75); // 30 / 40
    expect(p.doBrasil).toBeCloseTo(0.3); // 30 / 100
  });
  it("cobertura parcial do cubo torna N/D com motivo", () => {
    const p = participacao(fd(rows.filter((r) => r[0] !== 3)), { TUC: "565" }, "TUC", "quantidade", new Set([1]), new Set([1, 2, 3]), 1, 3);
    expect(p.noEscopo).toBeCloseTo(0.75);
    expect(p.doBrasil).toBeNull(); expect(p.motivoBrasil).toMatch(/2 de 3/);
  });
  it("categorias sobrepostas não geram proporção", () => {
    const p = participacao(fd(rows, false), { TUC: "565" }, "TUC", "quantidade", new Set([1]), new Set([1, 2, 3]), 1, 3);
    expect(p.noEscopo).toBeNull(); expect(p.doBrasil).toBeNull();
  });
});
