import { describe, expect, it } from "vitest";
import { simularContratoNacional, type LinhaContratoNacional } from "../src/lib/contrato-nacional-adapter";
const linha = (ano: number, valor: number): LinhaContratoNacional => ({
  ano, valor, dist: 6600, conceitoId: "transformadores", metrica: "quantidade",
  unidade: "itens", perimetroId: "publicacao_original", regraVersao: "v1",
  estado: "observado", cobertura: 1, fonte: "ANEEL", dataBase: `${ano}-12-31`,
  perimetroBridgeId: "", fonte_homologada: false, status_homologacao: "COMPLETO_TECNICO",
  ruptura_desde_ano_anterior: false, nao_somar_em_agregados: false,
});
describe("adaptador contrato nacional", () => {
  it("aceita exploracao tecnica sem homologar a fonte", () => {
    const r = simularContratoNacional([linha(2022, 10), linha(2023, 12), linha(2024, 14), linha(2025, 16)], 2026);
    expect(r.pontos[0].valor).toBe(16);
    expect(r.fontesHomologadas).toBe(false);
    expect(r.publicavelComoPrevisao).toBe(false);
  });
  it("bloqueia ruptura temporal", () => {
    const r = simularContratoNacional([linha(2024, 10), { ...linha(2025, 12), ruptura_desde_ano_anterior: "true" }]);
    expect(r.pontos).toHaveLength(0);
    expect(r.bloqueiosContrato).toContain("RUPTURA_TEMPORAL");
  });
  it("bloqueia predecessora ja incorporada", () => {
    const r = simularContratoNacional([linha(2024, 10), { ...linha(2025, 12), nao_somar_em_agregados: true }]);
    expect(r.pontos).toHaveLength(0);
    expect(r.bloqueiosContrato).toContain("NAO_SOMAR_EM_AGREGADOS");
  });
  it("nao transforma valor vazio em zero", () => {
    const r = simularContratoNacional([linha(2024, 10), { ...linha(2025, 0), valor: "", estado: "ausente" }]);
    expect(r.pontos).toHaveLength(0);
    expect(r.diagnostico.motivos).toContain("OBSERVACAO_NAO_ELEGIVEL");
  });
});
