// Matriz de homologação aplicada à Evolução — fixtures SINTÉTICAS (não são dados BDGD).
import { describe, expect, it } from "vitest";
import { serieDist, serieSoma, type CelulaSerie } from "@/lib/evolucao";
import { aplicarMatriz, coberturaAtivo, indexarHom, indiceHom, naturezaVariacoes, pontosHom, serieBrasil, seriePainel, sinaisNoEscopo, type Homologacao, type PontoHom } from "@/lib/homologacao";

const anos = [2022, 2023, 2024, 2025];
const h: Homologacao = {
  versao: "t", fonte: "t", fontes: {}, estados: { H: "", T: "", R: "", P: "", B: "", N: "" },
  motivos: ["ok", "par divergente", "outra competência", "ressalva", "nao somar", "anomalia", "nao total"],
  celulas: { x: [
    [1, 2022, "T", 0, 0], [1, 2023, "P", 1, 0], [1, 2024, "R", 3, 2], [1, 2025, "H", 0, 0],
    [2, 2022, "B", 2, 0], [2, 2023, "T", 0, 0], [2, 2024, "T", 0, 0], [2, 2025, "P", 5, 0],
    [3, 2022, "R", 4, 4], [3, 2023, "N", 0, 0], [3, 2024, "N", 0, 0], [3, 2025, "N", 0, 0],
  ] },
  brasil: { x: [[2022, null, "B", 1, 1, [2], 6], [2023, null, "B", 1, 1, [1], 6], [2024, 30, "R", 2, 0, [], 3], [2025, 40, "R", 1, 1, [2], 3]] },
  painel: { x: { universo: [], valores: [] } },
  proveniencia: {}, sinais: { "1|x|2023|2024": ["mudanca_cadastral", "HIPOTESE", "recadastro", 1], "2|x|2023|2024": ["expansao_fisica", "EXPLICACAO_PLAUSIVEL", "obras", 2] },
  pares: {}, pontes: [], absorcao_epb: {}, sem_tuc: {},
};
// todas as células validadas na série de origem; a matriz decide o que é publicável
const serie: CelulaSerie[] = [
  [1, 2022, 10, "v", 0], [1, 2023, 11, "v", 0], [1, 2024, 12, "v", 0], [1, 2025, 13, "v", 0],
  [2, 2022, 20, "d", 0], [2, 2023, 18, "v", 0], [2, 2024, 18, "v", 0], [2, 2025, 0, "v", 0],
  [3, 2022, 5, "v", 0], [3, 2023, null, "s", 0], [3, 2024, null, "s", 0], [3, 2025, null, "s", 0],
];
const ih = indiceHom(h, "x");
const idx = indexarHom(aplicarMatriz(serie, ih));

describe("matriz de homologação na Evolução", () => {
  it("célula pendente, bloqueada ou sem dado vira N/D (nunca zero), mesmo validada na série", () => {
    const d1 = serieDist(idx, 1, anos, "A").pontos.map((p) => p.v);
    expect(d1).toEqual([10, null, 12, 13]);                       // 2023 pendente de decisão
    const d2 = serieDist(idx, 2, anos, "B").pontos;
    expect(d2.map((p) => p.v)).toEqual([null, 18, 18, null]);     // 2025 pendente: o zero da série não aparece
    expect(d2[3].estado).toBe("x");
    expect(d2[0].estado).toBe("d");                               // outra competência continua identificada
  });
  it("estado, motivo e flags chegam aos pontos", () => {
    const p = pontosHom(serieDist(idx, 1, anos, "A"), h, ih, 1).pontos as PontoHom[];
    expect(p.map((x) => x.pub)).toEqual(["T", "P", "R", "H"]);
    expect(p[1].motivo).toBe("par divergente");
    expect(p[2].flags).toBe(2);
  });
  it("soma de grupo não inclui pendentes (ano fica sem valor) nem predecessora 'não somar'", () => {
    const g = serieSoma(idx, [1, 2, 3], anos, "g", "G").pontos.map((p) => p.v);
    expect(g[0]).toBeNull();                                      // DIST 2 bloqueada em 2022: sem soma parcial
    expect(g[1]).toBeNull();                                      // DIST 1 pendente em 2023
    expect(g[2]).toBe(30);
    const so13 = serieSoma(idx, [1, 3], anos, "g", "G").pontos[0].v;
    expect(so13).toBe(10);                                        // DIST 3 (não somar) fica fora, sem bloquear
  });
  it("Brasil 2022–2023 nunca aparece como total nacional; anos elegíveis vêm da matriz", () => {
    const br = serieBrasil(h, "x", anos).pontos as PontoHom[];
    expect(br.map((p) => p.v)).toEqual([null, null, 30, 40]);
    expect(br[0].estado).toBe("g");
    expect(br[0].motivo).toBe("nao total");
  });
  it("painel vazio não gera série", () => { expect(seriePainel(h, "x", anos)).toBeNull(); });
  it("cobertura conta estados por ano", () => {
    const c = coberturaAtivo(h, "x", anos);
    expect(c[0]).toMatchObject({ T: 1, B: 1, R: 1, publicaveis: 2 });
    expect(coberturaAtivo(h, "x", anos, [3])[1].N).toBe(1);
  });
  it("natureza distingue mudança cadastral de expansão física", () => {
    expect(naturezaVariacoes(h, 1, "x", anos)[1]).toMatchObject({ ano: 2024, natureza: "mudanca_cadastral", confianca: "HIPOTESE" });
    expect(naturezaVariacoes(h, 1, "x", anos)[0].natureza).toBeNull();
    expect(sinaisNoEscopo(h, [1, 2], "x", anos)[1]).toMatchObject({ total: 2, contagem: { mudanca_cadastral: 1, expansao_fisica: 1 } });
  });
});
