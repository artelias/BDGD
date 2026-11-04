import { readdirSync, readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";

vi.setConfig({ testTimeout: 120_000 });   // leem todos os produtos publicados (milhares de séries)
import { CENARIOS, completudeGrupo, completudeSerie, exportarCsv, parseCenarios, type ProdutoCenarios } from "@/lib/cenarios-motor";
import { estadoCompletude } from "@/lib/completude";
import { fmt, fmtCompact, fmtEixo, fmtUnitCompact, VALOR_INVALIDO } from "@/lib/format";
import { CENARIOS_V2, completudeV2, csvSerieV2, validarDist, type DistV2, type IndiceV2 } from "@/lib/motor-v2";

/** Correções finais da RC 1.0: completude dos cenários (os dois produtos), contagens físicas sempre inteiras e formatação. */
const json = (p: string) => JSON.parse(readFileSync(p, "utf8"));
const produto = (): ProdutoCenarios => parseCenarios(json("public/data/previsoes/cenarios-motor.json"));
const V2 = "data-motor-v2";
const distsV2 = (): DistV2[] => readdirSync(`${V2}/distribuidoras`).map((f) => validarDist(json(`${V2}/distribuidoras/${f}`)));

describe("completude dos cenários — produto público (cenarios-motor.json)", () => {
  it("toda série é COMPLETA, PARCIAL (com Moderado) ou SEM_PREVISAO; nenhum extremo sem Moderado; todo ausente tem motivo", () => {
    const p = produto();
    const n = { COMPLETA: 0, PARCIAL: 0, SEM_PREVISAO: 0 };
    for (const m of p.metricas) for (const s of Object.values(m.series)) {
      const c = completudeSerie(m, s);
      n[c.estado] += 1;
      if (c.publicados.length) expect(c.publicados).toContain("moderado");
      expect(c.publicados.length + c.naoPublicados.length).toBe(3);
      for (const [, motivo] of c.naoPublicados) expect(motivo.length).toBeGreaterThan(10);
    }
    expect(n.COMPLETA + n.PARCIAL + n.SEM_PREVISAO).toBe(2202);
    expect(n.PARCIAL).toBeGreaterThan(0);
  });

  it("série sem trajetória de um cenário cujo modelo existe na métrica traz o motivo do gerador", () => {
    const p = produto();
    for (const m of p.metricas) for (const s of Object.values(m.series)) for (const c of CENARIOS)
      if (m.cenarios[c] && !s[c] && s.hist.length) expect(s.motivos?.[c], `${m.conceito}/${c}`).toMatch(/^[A-Z_]+$/);
  });

  it("recusa extremo publicado sem Moderado na série (estado inconsistente do exportador)", () => {
    const d = json("public/data/previsoes/cenarios-motor.json");
    const m = d.metricas.find((x: { estado: string }) => x.estado === "tres_cenarios");
    const [k, s] = Object.entries(m.series as Record<string, { moderado: number[] | null; agressivo: number[] | null }>).find(([, x]) => x.moderado && x.agressivo)!;
    m.series[k] = { ...s, moderado: null };
    expect(() => parseCenarios(d)).toThrow(/sem Moderado/);
  });

  it("CSV da série: só cenários publicados têm valores, colunas não publicadas declaradas e completude em toda linha", () => {
    const p = produto();
    let parciais = 0;
    for (const m of p.metricas) for (const [d, s] of Object.entries(m.series)) {
      const c = completudeSerie(m, s);
      const [cab, ...linhas] = exportarCsv(p, m, d).trim().split("\n");
      const col = cab.split(",");
      CENARIOS.forEach((x, i) => expect(col[3 + i]).toBe(c.publicados.includes(x) ? `${x}_${m.cenarios[x]}` : `${x}_nao_publicado`));
      for (const l of linhas) {
        const v = l.split(",");
        expect(v[6]).toBe(c.estado);
        expect(v[7]).toBe(c.publicados.join("|"));
        if (v[1] === "simulacao_condicional") CENARIOS.forEach((x, i) => expect(v[3 + i] !== "").toBe(c.publicados.includes(x)));
      }
      if (c.estado === "PARCIAL") parciais += 1;
    }
    expect(parciais).toBeGreaterThan(0);
  });

  it("grupo: um cenário só é publicado quando todas as distribuidoras o têm", () => {
    const p = produto();
    const m = p.metricas.find((x) => x.conceito === "alimentadores" && x.metrica === "quantidade")!;
    const completas = Object.keys(m.series).filter((d) => completudeSerie(m, m.series[d]).estado === "COMPLETA").slice(0, 3);
    const parcial = Object.keys(m.series).find((d) => completudeSerie(m, m.series[d]).estado === "PARCIAL")!;
    expect(completudeGrupo(m, completas).estado).toBe("COMPLETA");
    const g = completudeGrupo(m, [...completas, parcial]);
    expect(g.estado).toBe("PARCIAL");
    expect(g.naoPublicados.map(([c]) => c)).toEqual(CENARIOS.filter((c) => !m.series[parcial][c]));
  });

  it("estadoCompletude lança erro para extremo sem Moderado e classifica os demais", () => {
    expect(() => estadoCompletude(["a", "m", "g"], "m", ["a"])).toThrow(/sem o Moderado/);
    expect(estadoCompletude(["a", "m", "g"], "m", ["m"])).toBe("PARCIAL");
    expect(estadoCompletude(["a", "m", "g"], "m", ["a", "m", "g"])).toBe("COMPLETA");
    expect(estadoCompletude(["a", "m", "g"], "m", [])).toBe("SEM_PREVISAO");
  });
});

describe("completude dos cenários — Motor V2", () => {
  it("2.484 séries com os três cenários, 219 parciais e 4 bloqueadas; o índice soma o mesmo que as séries", () => {
    const ix = json(`${V2}/indice.json`) as IndiceV2;
    const n = { COMPLETA: 0, PARCIAL: 0, SEM_PREVISAO: 0 };
    const porObj: Record<string, typeof n> = {};
    for (const d of distsV2()) for (const s of d.series) {
      if (!s.cenarios && s.estado !== "BLOQUEIO_PLAUSIBILIDADE") continue;
      const c = completudeV2(s);
      n[c.estado] += 1;
      const k = `${s.objetivo}|${s.metrica}`;
      porObj[k] ??= { COMPLETA: 0, PARCIAL: 0, SEM_PREVISAO: 0 };
      porObj[k][c.estado] += 1;
      if (c.estado === "PARCIAL") for (const [x, motivo] of c.naoPublicados) { expect(s.cenarios_status![x]).toBe("BLOQUEADO"); expect(motivo).toBeTruthy(); }
    }
    expect(n).toEqual({ COMPLETA: 2484, PARCIAL: 219, SEM_PREVISAO: 4 });
    for (const o of ix.objetivos) expect(o.completude_cenarios, `${o.objetivo}|${o.metrica}`).toEqual(porObj[`${o.objetivo}|${o.metrica}`] ?? { COMPLETA: 0, PARCIAL: 0, SEM_PREVISAO: 0 });
  });

  it("validarDist recusa completude declarada que não corresponde aos cenários publicados", () => {
    const d = json(`${V2}/distribuidoras/6600.json`);
    const s = d.series.find((x: { completude_cenarios?: { estado: string } }) => x.completude_cenarios?.estado === "COMPLETA");
    s.completude_cenarios = { ...s.completude_cenarios, estado: "PARCIAL" };
    expect(() => validarDist(d)).toThrow(/Completude/);
  });

  it("CSV da série leva a completude em toda linha e o bloqueado sai sem valor", () => {
    for (const d of distsV2().slice(0, 30)) for (const s of d.series.filter((x) => x.cenarios)) {
      const linhas = csvSerieV2(d, s).trim().split("\n").slice(1).map((l) => l.split(";"));
      for (const l of linhas) expect(l[6]).toBe(s.completude_cenarios.estado);
      for (const l of linhas.filter((x) => x[8] === "projecao")) expect(l[10] === "").toBe(s.cenarios_status![l[9] as (typeof CENARIOS_V2)[number]] === "BLOQUEADO");
    }
  });
});

describe("contagens físicas publicadas são inteiras em todos os produtos", () => {
  const inteiro = (v: unknown, onde: string) => { if (typeof v === "number") expect(Number.isInteger(v), `${onde}: ${v}`).toBe(true); };

  it("fatos nacionais, inventário por distribuidora e cubos dos conceitos", () => {
    const ix = json("public/data/2025-12-31/index.json");
    const cols: string[] = ix.fatos.cols;
    for (const r of ix.fatos.rows) cols.forEach((c, i) => { if (c.startsWith("quantidade")) inteiro(r[i], `fatos ${c}`); });
    const contagem = (c: string) => !/_km$|_kva$|^chave$|^nome$|^ten_nom$/.test(c);
    for (const f of readdirSync("public/data/2025-12-31/inventario")) {
      const inv = json(`public/data/2025-12-31/inventario/${f}`);
      for (const t of Object.values(inv) as { cols: string[]; rows: unknown[][] }[])
        for (const r of t.rows) t.cols.forEach((c, i) => { if (contagem(c)) inteiro(r[i], `inventário ${f} ${c}`); });
    }
    for (const f of readdirSync("public/data/2025-12-31/conceitos")) {
      const cj = json(`public/data/2025-12-31/conceitos/${f}`);
      const q = (cj.medidas as string[]).indexOf("quantidade");
      if (q < 0) continue;
      for (const c of Object.values(cj.cubos) as { dims: string[]; rows: number[][] }[])
        for (const r of c.rows) inteiro(r[1 + c.dims.length + q], `cubo ${f}`);
    }
  }, 120_000);

  it("série histórica 2022–2025 (Evolução) e Motor V2 (histórico, cenários e totais nacionais)", () => {
    const h = json("public/data/historico/serie.json");
    for (const k of ["original", "perimetro"]) for (const [conc, rows] of Object.entries(h[k] as Record<string, unknown[][]>))
      if (!/^(ramais|rede_at|rede_bt|rede_mt)$/.test(conc)) for (const r of rows) inteiro(r[2], `${k}/${conc}`);
    let n = 0;
    for (const d of distsV2()) for (const s of d.series) if (s.natureza === "discrete_count") {
      for (const [, v] of s.historico) { inteiro(v, `V2 ${s.objetivo}`); n += 1; }
      for (const c of CENARIOS_V2) for (const v of s.cenarios?.[c] ?? []) { inteiro(v, `V2 ${s.objetivo}/${c}`); n += 1; }
    }
    expect(n).toBeGreaterThan(30000);
    for (const o of (json(`${V2}/indice.json`) as IndiceV2).objetivos) if (o.natureza === "discrete_count" && o.total_2030)
      for (const c of CENARIOS_V2) inteiro(o.total_2030[c], `total ${o.objetivo}`);
  });
});

describe("formatação: contagem nunca sai com decimais nem é arredondada em silêncio", () => {
  it("contagem inteira com separador; fração é valor inválido (erro de contrato), não 12,5", () => {
    expect(fmt(12, "quantidade")).toBe("12");
    expect(fmt(1234567, "quantidade")).toBe("1.234.567");
    const erro = console.error; console.error = () => {};
    try { expect(fmt(12.5, "quantidade")).toBe(VALOR_INVALIDO); } finally { console.error = erro; }
    expect(fmt(12.5, "extensao_km")).toBe("12,5");
    expect(fmt(null, "quantidade")).toBe("N/D");
  });

  it("contagem não usa notação compacta (\"12,5 mil\"); extensão e potência continuam compactas", () => {
    expect(fmtCompact(12500, "quantidade")).toBe("12.500");
    expect(fmtCompact(91234567, "quantidade")).toBe("91.234.567");
    expect(fmtUnitCompact(1250000, "quantidade").value).toBe("1.250.000");
    expect(fmtCompact(1234567, "extensao_km")).toMatch(/mi km$/);
    expect(fmtCompact(undefined, "quantidade")).toBe("N/D");
  });

  it("eixo de contagem: marca fracionária não é rotulada; inteira sai inteira", () => {
    expect(fmtEixo(12.5, "quantidade")).toBe("");
    expect(fmtEixo(13, "quantidade")).toBe("13");
    expect(fmtEixo(12.5, "extensao_km")).toBe("12,5 km");
  });
});
