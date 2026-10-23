import { describe, expect, it } from "vitest";
import { Dataset } from "@/lib/dataset";
import { panoramaIndicador, PANORAMA_IDS, panoramaValue } from "@/lib/panorama-r3";
import type { IndexData } from "@/lib/types";

const dados = (): IndexData => ({
  release: { schema_version: "1.1", release_id: "r", data_base: "2025-12-31", status: "homologado", generated_at: "", dda_version: "",
    quality: { status: "aprovado", source_reconciliation: true }, cobertura: { distribuidoras_historicas_consideradas: 2, com_gdb_2025: 2, processadas: 2, quarentena: [], em_processamento: [], sem_publicacao_2025: [] }, regras: {}, licenca: "", autoria: "", privacidade: "" },
  distribuidoras: [1, 2].map((dist) => ({ dist, sigla: "D" + dist, nome: "D", grupo: "g", grupo_status: "verificado" as const, area_km2: null, ufs: [], fonte: "", sha256: "", versao: "", alertas: {} })),
  grupos: [], entidades: [],
  fatos: { cols: [], rows: [
    [1, "EQTRMT", 12, 12, 12, null, null, "a", ""], [1, "EQTRAT", 4, 4, 4, null, null, "a", ""],
    [2, "EQTRMT", 8, 8, 8, null, null, "a", ""], [2, "EQTRAT", 3, 3, 3, null, null, "a", ""],
    [1, "SSDMT", 1, 1, 1, 20, null, "a", ""], [2, "SSDMT", 1, 1, 1, 30, null, "a", ""],
  ] },
  vinculosTuc: { cols: [], destinos: {}, rows: [
    [1, "EQTRMT", "565", 10, 10, 10, 9], [1, "EQTRMT", "570", 2, 2, 2, 2],
    [1, "EQTRAT", "570", 4, 4, 4, 4],
    [2, "EQTRMT", "565", 7, 7, 7, 7], [2, "EQTRMT", "000", 1, 1, 1, 1],
    [2, "EQTRAT", "570", 3, 3, 3, 3],
  ] },
  complementares: {}, cobertura: [], filtrosIndisponiveis: [], homologacao: [],
});
const item = (id: string) => { const k = panoramaIndicador(id); if (!k) throw new Error(id); return k; };
describe("Panorama R3: semântica", () => {
  it("tem 10 conceitos executivos sem instalação duplicada", () => {
    expect(PANORAMA_IDS).toHaveLength(10);
    expect(PANORAMA_IDS).toContain("trdist565");
    expect(PANORAMA_IDS).toContain("trforca570");
    expect(PANORAMA_IDS).not.toContain("untrmt");
  });
  it("TUC 565 não soma instalações nem TUC 000", () => {
    expect(panoramaValue(new Dataset(dados()), item("trdist565"), [1, 2]).v).toBe(17);
  });
  it("TUC 570 inclui equipamentos MT e AT sem somar UN*", () => {
    expect(panoramaValue(new Dataset(dados()), item("trforca570"), [1, 2]).v).toBe(9);
  });
  it("inventário TUC incompleto bloqueia valor nacional", () => {
    const raw = dados(); raw.vinculosTuc!.rows.pop();
    const a = panoramaValue(new Dataset(raw), item("trforca570"), [1, 2]);
    expect(a.v).toBeNull(); expect(a.nd).toBe(1);
    expect(panoramaValue(new Dataset(raw), item("trforca570"), [1]).v).toBe(6);
  });
  it("ausência de cubo é N/D, nunca zero", () => {
    const raw = dados(); delete raw.vinculosTuc;
    expect(panoramaValue(new Dataset(raw), item("trdist565"), [1]).v).toBeNull();
  });
  it("rede utiliza km e denominador completo", () => {
    expect(panoramaValue(new Dataset(dados()), item("ssdmt"), [1, 2]).v).toBe(50);
    expect(item("ssdmt").metric).toBe("extensao_km");
  });
  it("ausência de uma DIST não vira total nacional parcial", () => {
    const raw = dados();
    raw.fatos.rows = raw.fatos.rows.filter((r) => !(r[0] === 2 && r[1] === "SSDMT"));
    const a = panoramaValue(new Dataset(raw), item("ssdmt"), [1, 2]);
    expect(a.v).toBeNull(); expect(a.ausentes).toBe(1);
  });
  it("UC em conflito não exibe soma parcial como Brasil", () => {
    const raw = dados();
    raw.complementares.uc_uniao_distinta = { "1": { "UC*": [120, "a", ""] }, "2": { "UC*": [null, "b", "conflito de ativação"] } };
    expect(panoramaValue(new Dataset(raw), item("uc"), [1, 2]).v).toBeNull();
    expect(panoramaValue(new Dataset(raw), item("uc"), [1]).v).toBe(120);
  });
  it("zero verdadeiro permanece zero quando cobertura está íntegra", () => {
    const raw = dados(); raw.vinculosTuc!.rows = raw.vinculosTuc!.rows.filter((r) => r[2] !== "565");
    raw.fatos.rows = raw.fatos.rows.map((r) => r[1] === "EQTRMT" ? [r[0], r[1], r[0] === 1 ? 2 : 1, r[3], r[4], r[5], r[6], r[7], r[8]] : r);
    expect(panoramaValue(new Dataset(raw), item("trdist565"), [1, 2]).v).toBe(0);
  });
});
