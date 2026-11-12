import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  acumulado, anualCompleto, anualDeMeses, comparar, completoDist, faixasDeExtensao, fmtInd, fmtMetrica, frasesComparacao, histograma, linhasNacionais, mediaPonderada,
  paresSemelhantes, percentilDe, perfilPorQuartil, ranking, razaoLimite, resumo, situacao, valorComparavel, variacao, type Linha,
} from "@/lib/confiabilidade/calculo";
import { COR_ND, DIV, QUEBRAS_REG, SEQ, classeDe, corDe, legenda, quebrasQuantis } from "@/lib/confiabilidade/escala";
import { escreverLado, lerLado } from "@/lib/confiabilidade/estado";
import type { BlocoAno, DistDoc, Indice, MetricaDef, NacionalAno } from "@/lib/confiabilidade/tipos";

const PRODUTO = join(__dirname, "..", "public", "data", "confiabilidade");
const real = existsSync(join(PRODUTO, "indice.json"));
const ler = <T,>(p: string): T => JSON.parse(readFileSync(join(PRODUTO, p), "utf8")) as T;

const bloco = (dec: number | null, ld: number | null, infra: Record<string, number | null> | null = null): BlocoAno => ({
  dec, fec: dec === null ? null : dec / 2, ld, lf: ld === null ? null : ld / 2, nuc: 1000, nuc_dez: 1000, meses_dec: 12, meses_fec: 12,
  m: { dec: Array(12).fill(dec === null ? null : dec / 12), fec: Array(12).fill(null), nuc: Array(12).fill(1000) },
  comp: { dec: { ip: null, ind: null, xp: null, xn: null, exp: null }, fec: { ip: null, ind: null, xp: null, xn: null, exp: null } },
  estado: "OBSERVADO_OFICIAL", infra, rec: null, alertas: [],
});
const linha = (dist: number, c: number, dec: number | null, infra: Record<string, number | null>): Linha => ({ dist, c, n: `C${c}`, dec, fec: dec, ld: 10, lf: 5, nuc: 1000, infra });

describe("regras de continuidade", () => {
  it("anual é a soma dos meses apurados; ausência não vira zero", () => {
    expect(anualDeMeses([1, 2, null, 3])).toEqual({ v: 6, n: 3 });
    expect(anualDeMeses([null, null])).toEqual({ v: null, n: 0 });
  });
  it("acumulado para no primeiro mês ausente", () => {
    expect(acumulado([1, 2, null, 4])).toEqual([1, 3, null, null]);
  });
  it("agregado é ponderado por consumidores, nunca média simples", () => {
    const r = mediaPonderada([{ v: 10, w: 9000 }, { v: 40, w: 1000 }, { v: null, w: 500 }, { v: 5, w: 0 }]);
    expect(r.v).toBeCloseTo(13, 9);
    expect(r).toMatchObject({ n: 2, fora: 2 });
  });
  it("razão e situação perante o limite", () => {
    expect(razaoLimite(12, 10)).toBeCloseTo(1.2);
    expect(razaoLimite(12, 0)).toBeNull();
    expect(razaoLimite(null, 10)).toBeNull();
    expect(situacao(10, 10)).toBe("dentro");
    expect(situacao(10.01, 10)).toBe("acima");
    expect(situacao(5, null)).toBe("nd");
    expect(variacao(12, 10)).toEqual({ abs: 2, rel: 0.2 });
    expect(variacao(12, null)).toBeNull();
  });
});

describe("escala do mapa", () => {
  it("quantis só com valores presentes e classes monotônicas", () => {
    const q = quebrasQuantis([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, null, NaN], 5);
    expect(q).toEqual([3, 5, 7, 9]);
    expect(classeDe(1, q)).toBe(0);
    expect(classeDe(9, q)).toBe(4);
    expect(classeDe(null, q)).toBeNull();
  });
  it("maior valor = pior: escuro no tema claro e claro no escuro; N/D tem cor própria", () => {
    const q = [3, 5, 7, 9];
    expect(corDe(100, q, "absoluto", "light")).toBe(SEQ.light[4]);
    expect(corDe(0, q, "absoluto", "light")).toBe(SEQ.light[0]);
    expect(corDe(100, q, "absoluto", "dark")).toBe(SEQ.dark[4]);
    expect(corDe(null, q, "absoluto", "dark")).toBe(COR_ND.dark);
  });
  it("modo regulatório usa classes fixas de apurado ÷ limite com centro neutro", () => {
    expect(corDe(1.0, [], "regulatorio", "light")).toBe(DIV.light[3]);
    expect(corDe(2.0, [], "regulatorio", "light")).toBe(DIV.light[6]);
    expect(corDe(0.3, [], "regulatorio", "light")).toBe(DIV.light[0]);
    expect(legenda([], "regulatorio", "light", String)).toHaveLength(QUEBRAS_REG.length + 1);
    expect(legenda([3, 5], "absoluto", "light", String).map((x) => x.rotulo)).toEqual(["menos de 3", "3 a 5", "5 ou mais"]);
  });
});

describe("comparação e pares", () => {
  const metricas: MetricaDef[] = [
    { id: "uc", nome: "Consumidores", unidade: "UC", tipo: "contagem", grupo: "C", definicao: "" },
    { id: "pct_uc_rural", nome: "Consumidores em área não urbana", unidade: "%", tipo: "pct", grupo: "T", definicao: "" },
    { id: "km_mt_por_mil_uc", nome: "Rede MT por mil consumidores", unidade: "km", tipo: "razao", grupo: "R", definicao: "" },
  ];
  it("diferenças com ausência preservada; % sem diferença relativa", () => {
    const r = comparar({ uc: 100, pct_uc_rural: 0.5, km_mt_por_mil_uc: null }, { uc: 50, pct_uc_rural: 0.25, km_mt_por_mil_uc: 3 }, metricas);
    expect(r[0]).toMatchObject({ dif: 50, rel: 1 });
    expect(r[1].rel).toBeNull();
    expect(r[1].dif).toBeCloseTo(0.25);
    expect(r[2]).toMatchObject({ a: null, dif: null, rel: null });
  });
  it("frases descrevem, nunca explicam (sem 'porque', 'causa' ou 'devido')", () => {
    const f = frasesComparacao({ nomeA: "A1", nomeB: "B1", ind: "dec", a: bloco(30, 18, { km_mt_por_mil_uc: 40 }), b: bloco(10, 20, { km_mt_por_mil_uc: 10 }), metricas, medianaParesA: 12, medianaParesB: null, distancia: 3 });
    expect(f.join(" ")).toMatch(/O DEC de A1 \(30\) é maior que o de B1 \(10\)/);
    expect(f.join(" ")).toMatch(/67% acima/);
    expect(f.join(" ")).toMatch(/Rede MT por mil consumidores|rede MT por mil consumidores/);
    expect(f.join(" ").toLowerCase()).not.toMatch(/porque|causa|devido/);
  });
  it("sem DEC num dos lados, não compara continuidade", () => {
    const f = frasesComparacao({ nomeA: "A", nomeB: "B", ind: "dec", a: bloco(null, 10), b: bloco(5, 10), metricas });
    expect(f[0]).toMatch(/não é possível/);
  });
  it("pares exigem 3 critérios e excluem o próprio conjunto", () => {
    const base = (i: number) => ({ uc: 1000 + i, uc_por_km2: 10 + i, pct_uc_rural: 0.2 + i / 1000, km_mt_por_mil_uc: 5 + i / 10, mwh_por_uc: 2 });
    const u = Array.from({ length: 30 }, (_, i) => linha(1, i, i, base(i)));
    const r = paresSemelhantes(u[10], u, 5);
    expect(r.pares).toHaveLength(5);
    expect(r.pares.every((p) => p.linha.c !== 10)).toBe(true);
    expect(r.pares[0].distancia).toBeLessThanOrEqual(r.pares[4].distancia);
    expect(paresSemelhantes(linha(1, 99, 1, { uc: 5 }), u).pares).toHaveLength(0);
  });
  it("ranking ignora N/D e ordena pela pior continuidade", () => {
    const u = [linha(1, 1, 5, {}), linha(1, 2, null, {}), linha(1, 3, 20, {})];
    expect(ranking(u, null, "dec", "piores").map((x) => x.linha.c)).toEqual([3, 1]);
    expect(ranking(u, null, "dec", "acima_limite")[0].valor).toBeCloseTo(2);
  });
  it("perfil por quartil só com amostra suficiente", () => {
    expect(perfilPorQuartil([linha(1, 1, 1, { a: 1 })], "dec", ["a"]).cortes).toBeNull();
    const u = Array.from({ length: 40 }, (_, i) => linha(1, i, i, { a: i * 2 }));
    const p = perfilPorQuartil(u, "dec", ["a"]);
    expect(p.linhas[0].melhores! < p.linhas[0].piores!).toBe(true);
    expect(p.linhas[0].contraste).toBeGreaterThan(0);
  });
});

describe("apuração parcial (regressão da auditoria de 12/11/2026)", () => {
  it("valor com menos de 12 meses é exibido, mas não é comparado ao limite anual", () => {
    const b = { ...bloco(12, 10), meses_fec: 11 };
    expect(anualCompleto(b, "dec")).toBe(true);
    expect(anualCompleto(b, "fec")).toBe(false);
    expect(valorComparavel(b, "fec")).toBeNull();
    expect(situacao(valorComparavel(b, "fec"), b.lf)).toBe("nd");
    expect(valorComparavel(b, "dec")).toBe(12);
  });
  it("tabela nacional: indicador parcial vira N/D só nas comparações; arquivo sem meses continua igual", () => {
    const t: NacionalAno = { ano: 2025, campos: ["dist", "c", "n", "dec", "fec", "ld", "lf", "nuc", "meses_dec", "meses_fec", "uc"],
      linhas: [[1, 10, "A", 5, 3, 8, 6, 100, 12, 11, 100], [1, 11, "B", 9, 4, 8, 6, 100, 12, 12, 100]] };
    const [a, b] = linhasNacionais(t);
    expect([a.dec, a.fec, a.parcial]).toEqual([5, null, ["fec"]]);
    expect([b.fec, b.parcial, b.infra]).toEqual([4, [], { uc: 100 }]);
    expect(ranking([a, b], null, "fec", "melhores").map((x) => x.linha.c)).toEqual([11]);
    expect(ranking([a, b], null, "fec", "acima_limite").map((x) => x.linha.c)).toEqual([11]);
    const antigo = linhasNacionais({ ano: 2025, campos: ["dist", "c", "n", "dec", "fec", "ld", "lf", "nuc"], linhas: [[1, 10, "A", 5, 3, 8, 6, 100]] })[0];
    expect([antigo.fec, antigo.parcial]).toEqual([3, []]);
  });
  it("comparador não compara valor parcial e diz o motivo", () => {
    const f = frasesComparacao({ nomeA: "A", nomeB: "B", ind: "fec", a: { ...bloco(12, 10), meses_fec: 11 }, b: bloco(4, 10), metricas: [], medianaParesA: 1 }).join(" ");
    expect(f).toMatch(/A tem apuração parcial de FEC no ano/);
    expect(f).not.toMatch(/é maior que|O FEC de A|A está/);
    expect(f).toMatch(/B está .* limite regulatório de FEC/);
  });
  it("agregado da distribuidora sem 12 meses não entra nas quebras", () => {
    expect(completoDist({ dec: 1, fec: 1, completo: false, completo_dec: true, completo_fec: false, nuc: 1, conjuntos: 1, acima_dec: 0, acima_fec: 0, com_infra: 1, estado: "DERIVADO_EXPLORATORIO", regra: "" }, "fec")).toBe(false);
    expect(completoDist({ dec: 1, fec: 1, completo: true, nuc: 1, conjuntos: 1, acima_dec: 0, acima_fec: 0, com_infra: 1, estado: "DERIVADO_EXPLORATORIO", regra: "" }, "dec")).toBe(true);
  });
});

describe("formatação e utilidades", () => {
  it("contagem não inteira é sinalizada, ausência é N/D", () => {
    expect(fmtMetrica(1234, { tipo: "contagem" })).toBe("1.234");
    expect(fmtMetrica(1.5, { tipo: "contagem" })).toBe("valor inválido");
    expect(fmtMetrica(null, { tipo: "razao" })).toBe("N/D");
    expect(fmtMetrica(0, { tipo: "contagem" })).toBe("0");
    expect(fmtInd(null)).toBe("N/D");
  });
  it("percentil, resumo, histograma e faixas", () => {
    expect(percentilDe(5, [1, 5, 10, null])).toBeCloseTo(2 / 3);
    expect(resumo([null, 1, 3])).toMatchObject({ n: 2, mediana: 2 });
    expect(histograma([1, 1, 1])).toEqual([{ de: 1, ate: 1, n: 3 }]);
    expect(faixasDeExtensao([5, 20, 50, null, 0], [10, 40]).map((f) => f.n)).toEqual([1, 1, 1]);
  });
  it("lado A/B na URL", () => {
    expect(lerLado("6600-16849")).toEqual({ dist: 6600, conj: 16849 });
    expect(lerLado("x-1")).toBeNull();
    expect(escreverLado({ dist: 26, conj: 1 })).toBe("26-1");
  });
});

describe.skipIf(!real)("produto publicado (dados reais)", () => {
  const indice = real ? ler<Indice>("indice.json") : (null as unknown as Indice);
  it("índice real, não demonstrativo, contrato e anos 2022–2025", () => {
    expect(indice.demonstrativo).toBe(false);
    expect(indice.contrato).toBe("confiabilidade-1");
    expect(indice.anos).toEqual([2022, 2023, 2024, 2025]);
    expect(indice.distribuidoras.length).toBeGreaterThan(90);
  });
  it("EPB (6600): conjuntos únicos, contagens inteiras, só anos permitidos", () => {
    const d = ler<DistDoc>("distribuidoras/6600.json");
    const ids = d.conjuntos.map((c) => c.c);
    expect(new Set(ids).size).toBe(ids.length);
    const contagens = new Set(indice.metricas.filter((m) => m.tipo === "contagem").map((m) => m.id));
    for (const c of d.conjuntos) for (const [a, b] of Object.entries(c.a)) {
      expect([2022, 2023, 2024, 2025]).toContain(Number(a));
      for (const [k, v] of Object.entries(b.infra ?? {})) if (contagens.has(k) && v !== null) expect(Number.isInteger(v)).toBe(true);
    }
    const trafos = d.conjuntos.reduce((s, c) => s + (c.a["2025"]?.infra?.trafos ?? 0), 0);
    expect(trafos).toBe(74625);
  });
  it("nenhum conjunto pertence a duas distribuidoras no mesmo ano (tabela nacional)", () => {
    const t = ler<NacionalAno>("nacional/2025.json");
    const l = linhasNacionais(t);
    const k = new Set(l.map((x) => `${x.c}`));
    expect(k.size).toBe(l.length);
  });
  it("Elektro 2025: FEC sem junho na ANEEL fica fora de rankings, quebras e limite; DEC continua comparável", () => {
    const l = linhasNacionais(ler<NacionalAno>("nacional/2025.json")).filter((x) => x.dist === 385);
    expect(l.length).toBe(130);
    expect(l.every((x) => x.fec === null && x.parcial?.includes("fec") && x.dec !== null)).toBe(true);
    const d = ler<DistDoc>("distribuidoras/385.json");
    expect(d.anual["2025"].completo_fec).toBe(false);
    expect(d.anual["2025"].acima_fec).toBe(0);
    const com2025 = d.conjuntos.filter((c) => c.a["2025"]);
    expect(com2025.length).toBe(130);
    for (const c of com2025) {
      const b = c.a["2025"];
      expect(b.meses_fec).toBe(11);
      expect(b.alertas).toContain("apuracao_parcial");
      expect(b.fec).not.toBeNull();   // o valor oficial dos 11 meses continua publicado
    }
  });
  it("geometria de cada distribuidora só tem conjuntos dela", () => {
    for (const f of readdirSync(join(PRODUTO, "geo")).slice(0, 25)) {
      const dist = Number(f.replace(".json", ""));
      const g = ler<GeoJSON.FeatureCollection>(`geo/${f}`);
      const d = ler<DistDoc>(`distribuidoras/${dist}.json`);
      const conj = new Set(d.conjuntos.map((c) => c.c));
      for (const ft of g.features) expect(conj.has(Number(ft.properties?.c))).toBe(true);
    }
  });
});
