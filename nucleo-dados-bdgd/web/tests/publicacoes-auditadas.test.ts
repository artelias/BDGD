import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const dir = resolve(process.cwd(), "public/data/historico");
const audit = JSON.parse(readFileSync(resolve(dir, "publicacoes-auditadas.json"), "utf-8"));
const selecionadas = JSON.parse(readFileSync(resolve(dir, "politica-republicacoes.json"), "utf-8"));
const serie = JSON.parse(readFileSync(resolve(dir, "serie.json"), "utf-8"));
const estados = JSON.parse(readFileSync(resolve(dir, "estados-contrato.json"), "utf-8"));
const matriz = JSON.parse(readFileSync(resolve(dir, "homologacao.json"), "utf-8"));
const usa = (s: string) => audit.items.filter((p: unknown[]) => p[4] === s);
const bloqueados = ["excluido_competencia", "par_item_excluido_competencia"];

describe("republicações históricas 2022–2023 — seleção sem homologação", () => {
  it("preserva 414 itens oficiais, 14 exclusões por competência e 11 ausências", () => {
    expect(audit.total).toBe(414);
    expect(audit.items).toHaveLength(414);
    expect(new Set(audit.items.map((p: unknown[]) => p[3])).size).toBe(414);
    expect(bloqueados.flatMap(usa)).toHaveLength(14);
    expect(audit.publicacoesNaoLocalizadas).toHaveLength(11);
    expect(audit.publicacoesNaoLocalizadasCelulas).toBe(275);
  });
  it("escolhe somente a versão mais recente entre os 13 pares e preserva anteriores", () => {
    expect(selecionadas.total_pares).toBe(13);
    expect(usa("em_uso_na_serie")).toHaveLength(286);
    expect(usa("versao_anterior_preservada")).toHaveLength(13);
    expect(usa("par_divergente_pendente")).toHaveLength(0);
    expect(usa("pacote_2025")).toHaveLength(99);
    expect(usa("par_competencia_unica_valida_em_uso")).toHaveLength(2);
    for (const p of selecionadas.pares) {
      expect(p.selecionada.versao).toMatch(/^V11_\d{8}-\d{4}$/);
      expect(p.selecionada.versao.localeCompare(p.anterior.versao)).toBeGreaterThan(0);
      const items = audit.items.filter((r: unknown[]) => r[0] === p.ano && r[1] === p.dist);
      expect(items.find((r: unknown[]) => r[3] === p.selecionada.item_id)?.[4]).toBe("em_uso_na_serie");
      expect(items.find((r: unknown[]) => r[3] === p.anterior.item_id)?.[4]).toBe("versao_anterior_preservada");
      expect(matriz.pares[`${p.dist}|${p.ano}`].selecionada).toBe(p.selecionada.item_id);
    }
  });
  it("reconstitui dados auditados sem transformar ausência em zero", () => {
    const v = serie.original.trafo_dist.find((r: unknown[]) => r[0] === 6600 && r[1] === 2023);
    expect(v).toEqual([6600, 2023, 70540, "v", 0]);
    const estado = estados.celulas.trafo_dist.find((r: unknown[]) => r[0] === 6600 && r[1] === 2023);
    expect(estado[2]).toBe("observado");
    const situacao = matriz.celulas.trafo_dist.find((r: unknown[]) => r[0] === 6600 && r[1] === 2023);
    expect(situacao[2]).toBe("R");
    expect(matriz.brasil.trafo_dist.find((r: unknown[]) => r[0] === 2023)[1]).toBeNull();
    expect(serie.cobertura.find((r: {ano:number}) => r.ano === 2023).pendentes).toBe(0);
    for(const p of selecionadas.pares){
      for(const [ativo, rows] of Object.entries(serie.original) as Array<[string, unknown[][]]>){
        const cell=rows.find(r=>r[0]===p.dist && r[1]===p.ano);
        const estado=estados.celulas[ativo].find((r: unknown[])=>r[0]===p.dist && r[1]===p.ano);
        expect(cell).toBeDefined();
        if(estado[2]==="observado" || estado[2]==="zero_verificado"){expect(cell?.[2]).not.toBeNull();expect(cell?.[3]).toBe("v");}
        else if(estado[2]==="ausente"){expect(cell?.[2]).toBeNull();}
        else throw new Error("estado inesperado no par selecionado");
      }
    }
  });
});
