import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const audit = JSON.parse(readFileSync(resolve(process.cwd(), "public/data/historico/publicacoes-auditadas.json"), "utf-8"));
const usa = (s: string) => audit.items.filter((p: unknown[]) => p[4] === s);
const statusBloqueados = ["excluido_competencia", "par_item_excluido_competencia"];

describe("inventário individual de publicações — 25/10/2026", () => {
  it("conserva o universo e os IDs únicos das 414 publicações da auditoria", () => {
    expect(audit.total).toBe(414);
    expect(audit.items).toHaveLength(414);
    expect(new Set(audit.items.map((p: unknown[]) => p[3])).size).toBe(414);
    expect(audit.sourceCommit).toBe("8e2eab8");
    expect(audit.items.every((p: unknown[]) => String(p[3]).match(/^[0-9a-f]{32}$/i))).toBe(true);
  });

  it("distingue 14 exclusões técnicas, 26 itens em 13 pares e 374 versões em uso", () => {
    expect(usa("par_divergente_pendente")).toHaveLength(26);
    expect(statusBloqueados.flatMap((s) => usa(s))).toHaveLength(14);
    expect(usa("em_uso_na_serie")).toHaveLength(273);
    expect(usa("pacote_2025")).toHaveLength(99);
    expect(usa("par_competencia_unica_valida_em_uso")).toHaveLength(2);
    expect(audit.items.filter((p: unknown[]) => [2022, 2023, 2024, 2025].includes(p[0]))).toHaveLength(414);
  });

  it("exclusões por competência são sustentadas pelo DAT_FNL incompatível, não zeros", () => {
    for (const p of statusBloqueados.flatMap((s) => usa(s))) {
      expect(p[5]).toMatch(/^\d{2}\/\d{2}\/\d{4}$/);
      // Exclui inclusive 30/11/2022 de uma base que deveria ser 31/12/2022.
      expect(p[5]).not.toBe("31/12/" + p[0]);
    }
    expect(statusBloqueados.flatMap((s) => usa(s)).filter((p: unknown[]) => p[0] === 2022)).toHaveLength(6);
    expect(statusBloqueados.flatMap((s) => usa(s)).filter((p: unknown[]) => p[0] === 2023)).toHaveLength(8);
  });

  it("conflitos são dois itens oficiais por par, sem publicação escolhida", () => {
    const pares = new Map<string, unknown[][]>();
    for (const p of usa("par_divergente_pendente")) {
      const chave = p[0] + "|" + p[1];
      pares.set(chave, [...(pares.get(chave) ?? []), p]);
    }
    expect(pares.size).toBe(13);
    expect([...pares.values()].every((arr) => arr.length === 2)).toBe(true);
  });

  it("separa 11 publicações ausentes do catálogo de 14 arquivos excluídos", () => {
    expect(audit.publicacoesNaoLocalizadas).toHaveLength(11);
    expect(audit.publicacoesNaoLocalizadasCelulas).toBe(275);
    expect(new Set(audit.publicacoesNaoLocalizadas.map((p: unknown[]) => p[0] + "|" + p[1])).size).toBe(11);
    const inexistentes = new Set(audit.publicacoesNaoLocalizadas.map((p: unknown[]) => p[0] + "|" + p[1]));
    expect(audit.items.filter((p: unknown[]) => inexistentes.has(p[0] + "|" + p[1]))).toHaveLength(0);
  });

  it("a base publicada não rotula uma versão divergente como 'em uso'", () => {
    const distAnoPendente = new Set(usa("par_divergente_pendente").map((p: unknown[]) => p[0] + "|" + p[1]));
    expect(audit.items.filter((p: unknown[]) =>
      distAnoPendente.has(p[0] + "|" + p[1]) && p[4] !== "par_divergente_pendente")).toHaveLength(0);
  });
});
