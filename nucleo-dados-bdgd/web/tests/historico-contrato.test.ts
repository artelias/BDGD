import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { aplicarEstadosContrato, lacunasNacionais, pontosContrato, type EstadosContrato } from "@/lib/historico-contrato";
import { aplicarMatriz, indexarHom, indiceHom, serieBrasil, type Homologacao } from "@/lib/homologacao";
import { serieDist, serieSoma, type SerieData } from "@/lib/evolucao";
import { Dataset } from "@/lib/dataset";
import { PANORAMA_KPIS, panoramaValue } from "@/lib/panorama-r3";
import { benchmarkLinhas } from "@/lib/comparador";

const ler = (nome: string) => JSON.parse(readFileSync(`public/data/${nome}.json`, "utf8"));
const contrato: EstadosContrato = ler("historico/estados-contrato");
const hom: Homologacao = ler("historico/homologacao");
const sd: SerieData = ler("historico/serie");
const anos = [2022, 2023, 2024, 2025];

describe("contrato histórico efetivamente publicado", () => {
  it("preserva os cinco estados originais sem confundir ausência com não aplicabilidade", () => {
    const linhas = Object.values(contrato.celulas).flat();
    expect(linhas).toHaveLength(11400);
    const estados = Object.fromEntries([...new Set(linhas.map((c) => c[2]))].map((e) => [e, linhas.filter((c) => c[2] === e).length]));
    expect(estados).toEqual({"observado":7976,"nao_aplicavel":1739,"nao_homologado":329,"ausente":317,"zero_verificado":1039});
  });
  it("nenhum dos 100 agregados incompletos é exibido como total nacional", () => {
    for (const ativo of Object.keys(contrato.celulas)) {
      const br = serieBrasil(hom, ativo, anos, contrato);
      br.pontos.forEach((p) => { expect(lacunasNacionais(contrato, ativo, p.ano)).toBeGreaterThan(0); expect(p.v).toBeNull(); });
    }
  });
  it("ausência da Cemig GT em 2024 bloqueia um grupo; sucessão documentada é não aplicável", () => {
    const ativo = "alimentadores";
    const celulas = aplicarEstadosContrato(aplicarMatriz(sd.original[ativo], indiceHom(hom, ativo)), contrato, ativo);
    const idx = indexarHom(celulas);
    expect(serieSoma(idx, [26, 2904], anos, "grupo", "G").pontos[2].v).toBeNull();
    const dist = pontosContrato(serieDist(idx, 70, anos, "D"), contrato, ativo, 70);
    expect(dist.pontos[2]).toMatchObject({ v: null, estado: "nao_aplicavel" });
    expect(serieSoma(idx, [26, 70], anos, "grupo", "G").pontos[2].v).toBe(120);
  });
  it("EAC/UCAT preserva 0 registros, sem alegar homologação independente do zero", () => {
    const ds = new Dataset(ler("2025-12-31/index"));
    expect(ds.cell(26, "UCAT", "quantidade")).toMatchObject({ v: 0, status: "a" });
    expect(ds.cell(26, "UCAT", "quantidade_registros")?.v).toBe(0);
    expect(ds.cell(26, "UCAT", "quantidade_cod_id_distinto")?.v).toBe(0);
    expect(ds.cell(26, "ENTIDADE_INEXISTENTE", "quantidade")).toBeNull();
  });
  it("Panorama não transforma o universo das 99 processadas no total nacional", () => {
    const ds = new Dataset(ler("2025-12-31/index"));
    expect(ds.raw.release.cobertura.sem_publicacao_2025.length).toBeGreaterThan(0);
    for (const k of PANORAMA_KPIS) expect(panoramaValue(ds, k, ds.scopeDists({ tipo: "brasil" })).v).toBeNull();
    expect(panoramaValue(ds, PANORAMA_KPIS.find((k) => k.id === "alimentadores")!, [26]).v).toBe(123);
  });
  it("radar não usa o subtotal das distribuidoras processadas como denominador nacional", () => {
    const ds = new Dataset(ler("2025-12-31/index"));
    const linha = { id: "sub", nome: "Subestações", familia: "Infraestrutura", medida: "quantidade" as const,
      porDist: new Map(ds.dists.map((d) => [d.dist, ds.cell(d.dist, "SUB", "quantidade")?.v ?? null])) };
    const [eixo] = benchmarkLinhas(ds, [linha], [26], "brasil", [], "");
    expect(eixo.ref).toBeNull();
    expect(eixo.pctA).toBeNull();
  });
  it("consumidores do Panorama conferem com a definição vigente em todas as 99 distribuidoras", () => {
    const ds = new Dataset(ler("2025-12-31/index"));
    const kpi = PANORAMA_KPIS.find((k) => k.id === "uc")!;
    const indice = new Map(aplicarMatriz(sd.original.consumidores, indiceHom(hom, "consumidores")).filter((r) => r[1] === 2025).map((r) => [r[0], r[2]]));
    for (const d of ds.dists) expect(panoramaValue(ds, kpi, [d.dist]).v).toBe(indice.get(d.dist) ?? null);
    expect(panoramaValue(ds, kpi, [26]).v).toBe(295861);
    expect(panoramaValue(ds, kpi, [5370]).v).toBeNull();
  });
});
