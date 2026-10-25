// Motor de cubos por conceito (R3) com fixtures SINTÉTICAS (não são dados BDGD).
import { describe, expect, it } from "vitest";
import { agregar, dimsCompativeis, distribuicao, escolherCubo, escreverRecorte, foraDoCubo, juntar, lerRecorte, participacao, rotulo } from "@/lib/cubo";
import type { ConceitoData } from "@/lib/types";

// transformadores: tipo (565, 570), fases (ABC, A), area (UB, NU); municipio só num cubo próprio
const cd: ConceitoData = {
  id: "transformadores", medidas: ["quantidade", "potencia_kva"],
  valores: { tipo: ["565", "570"], fases: ["ABC", "A"], area: ["UB", "NU"], municipio: ["1", "2"] },
  rotulos: { tipo: { "565": "Transformador de distribuição (TUC 565)", "570": "Transformador de força (TUC 570)" }, fases: { ABC: "Trifásico", A: "Monofásico" }, area: { UB: "Urbano", NU: "Não urbano" } },
  a1PorTuc: { "565": { "01": "Aéreo" } },
  cubos: {
    principal: { dims: ["tipo", "fases", "area"], entidades: ["EQTRMT"], rows: [
      // dist, tipo, fases, area, quantidade, potencia
      [1, 0, 0, 0, 100, 1000], [1, 0, 1, 1, 50, 250], [1, 1, 0, 0, 2, 20000],
      [2, 0, 0, 0, 300, 3000], [2, 0, 1, 0, 10, null],
      [3, 0, 0, 1, 40, 400], [3, 1, 0, 0, 1, 10000],
    ] },
    municipio: { dims: ["municipio", "tipo"], entidades: ["EQTRMT"], rows: [
      [1, 0, 0, 150, null], [1, 1, 1, 2, null], [2, 0, 0, 310, null], [3, 1, 0, 40, null], [3, 1, 1, 1, null],
    ] },
  },
};
const br = new Set([1, 2, 3]);

describe("escolha de cubo", () => {
  it("usa o cubo que contém todas as dimensões filtradas", () => {
    expect(escolherCubo(cd, ["tipo", "area"])).toBe("principal");
    expect(escolherCubo(cd, ["municipio"])).toBe("municipio");
    expect(escolherCubo(cd, ["municipio", "fases"])).toBeNull();
  });
  it("prefere o principal mesmo quando outro cubo tem menos linhas (mesmo total garantido)", () => {
    expect(escolherCubo(cd, ["tipo"])).toBe("principal");
    expect(foraDoCubo(cd, "municipio")).toEqual([]);
  });
  it("dimensões compatíveis com o recorte atual", () => {
    expect([...dimsCompativeis(cd, { filtro: { municipio: ["1"] } })].sort()).toEqual(["municipio", "tipo"]);
    expect(dimsCompativeis(cd, { filtro: { fases: ["ABC"] } }).has("municipio")).toBe(false);
  });
});

describe("agregação exata", () => {
  it("soma linhas do cubo; filtros combinam por E entre dimensões e OU dentro da dimensão", () => {
    expect(agregar(cd, { filtro: { tipo: ["565"] } }, "quantidade", br)!.v).toBe(500);
    expect(agregar(cd, { filtro: { tipo: ["565"], fases: ["ABC"] } }, "quantidade", br)!.v).toBe(440);
    expect(agregar(cd, { filtro: { area: ["UB", "NU"] } }, "quantidade", br)!.v).toBe(503);
  });
  it("cubo municipal soma o mesmo total do principal", () => {
    expect(agregar(cd, { filtro: {} }, "quantidade", br, "municipio")!.v).toBe(agregar(cd, { filtro: {} }, "quantidade", br, "principal")!.v);
  });
  it("exclusão de categorias", () => {
    expect(agregar(cd, { filtro: {}, excluir: { tipo: ["565"] } }, "quantidade", br)!.v).toBe(3);
  });
  it("potência N/D numa DIST tira a DIST inteira da soma (nunca parcial)", () => {
    const a = agregar(cd, { filtro: { tipo: ["565"] } }, "potencia_kva", br)!;
    expect(a.nd).toBe(1); expect(a.n).toBe(2); expect(a.v).toBe(1000 + 250 + 400);
  });
  it("DIST presente sem linhas no recorte vale zero, não N/D", () => {
    const a = agregar(cd, { filtro: { tipo: ["570"] } }, "quantidade", new Set([2]))!;
    expect(a.v).toBe(0); expect(a.n).toBe(1); expect(a.nd).toBe(0);
  });
  it("combinação sem cubo é indisponível, não estimada", () => {
    expect(agregar(cd, { filtro: { municipio: ["1"], fases: ["A"] } }, "quantidade", br)).toBeNull();
  });
});

describe("distribuição por categoria", () => {
  it("categorias somam o total do recorte", () => {
    const d = distribuicao(cd, "tipo", { filtro: {} }, "quantidade", br)!;
    expect(d.categorias.map((c) => [c.code, c.v])).toEqual([["565", 500], ["570", 3]]);
  });
  it("A1 é descrito pelo TUC fixado", () => {
    expect(rotulo(cd, "a1", "01", { filtro: { tipo: ["565"] } })).toBe("Aéreo");
    expect(rotulo(cd, "a1", "01", { filtro: {} })).toBe("01");
  });
});

describe("participação dupla (denominadores homogêneos)", () => {
  it("categoria dentro do escopo e escopo dentro do Brasil", () => {
    const base = { filtro: {} }, rec = { filtro: { tipo: ["570"] } };
    const p = participacao(cd, base, rec, "quantidade", new Set([1]), br);
    expect(p.valor).toBe(2); expect(p.totalEscopo).toBe(152); expect(p.brasil).toBe(3);
    expect(p.noEscopo).toBeCloseTo(2 / 152); expect(p.doBrasil).toBeCloseTo(2 / 3);
  });
  it("N/D na medida torna a participação indisponível com motivo", () => {
    const p = participacao(cd, { filtro: {} }, { filtro: { tipo: ["565"] } }, "potencia_kva", new Set([2]), br);
    expect(p.noEscopo).toBeNull(); expect(p.motivo).toMatch(/sem valor homologado/);
  });
});

describe("recorte na URL", () => {
  it("ida e volta", () => {
    const f = { tipo: ["565", "570"], area: ["UB"] };
    expect(lerRecorte(escreverRecorte(f))).toEqual(f);
  });
  it("junção de recortes intersecta valores da mesma dimensão", () => {
    expect(juntar({ filtro: { tipo: ["565", "570"] } }, { filtro: { tipo: ["565"] } }).filtro.tipo).toEqual(["565"]);
  });
});

describe("medida que não se aplica (-1)", () => {
  const cd2: ConceitoData = { id: "t", medidas: ["quantidade", "potencia_kva"], valores: { tipo: ["565", "575"] }, rotulos: {},
    cubos: { principal: { dims: ["tipo"], entidades: ["EQTRMT", "EQTRM"], rows: [[1, 0, 10, 100], [1, 1, 5, -1], [2, 1, 3, -1]] } } };
  it("não soma nem vira N/D", () => {
    const a = agregar(cd2, { filtro: {} }, "potencia_kva", null)!;
    expect(a.v).toBe(100); expect(a.nd).toBe(0); expect(a.n).toBe(1);
    expect(agregar(cd2, { filtro: {} }, "quantidade", null)!.v).toBe(18);
    expect(distribuicao(cd2, "tipo", { filtro: {} }, "potencia_kva", null)!.categorias.map((c) => c.code)).toEqual(["565"]);
  });
});
