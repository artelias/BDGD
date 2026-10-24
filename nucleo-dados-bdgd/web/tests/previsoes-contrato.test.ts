import { describe, expect, it } from "vitest";
import { previsaoPublicavel, valorObservado, type ResultadoPrevisao, type SerieFisica } from "../src/lib/previsoes-contrato";

const valido = (): ResultadoPrevisao => ({
  modo: "previsao_validada", perspectiva: "ativos", resultado: "estoque_fisico",
  dist: 6600, conceitoId: "transformadores", metrica: "quantidade", unidade: "un",
  anoOrigem: 2025, anoAlvo: 2026, perimetroId: "EPB-reconciliado",
  valor: 100, limiteInferior: 90, limiteSuperior: 110,
  modeloId: "modelo-v1", modeloEstado: "validado", versaoDados: "v1",
  evidenciaValidacao: {
    protocoloId: "backtest-v1", versaoCodigo: "sha256:abc", dataCorteTreino: "2025-12-31",
    numeroObservacoes: 8, numeroOrigensTeste: 3, baselineId: "naive",
    metricaErro: "mae", erroModelo: 5, erroBaseline: 7,
    coberturaHistorica: 1, fontesHomologadas: true, perimetroReconciliado: true,
  },
});

describe("contrato de publicação de previsões", () => {
  it("aceita apenas uma previsão com evidências completas", () => {
    expect(previsaoPublicavel(valido())).toBe(true);
  });
  it.each(["historico", "simulacao_condicional"] as const)("rejeita modo %s", (modo) => {
    expect(previsaoPublicavel({ ...valido(), modo })).toBe(false);
  });
  it("rejeita modelo não validado e sem evidência", () => {
    expect(previsaoPublicavel({ ...valido(), modeloEstado: "exploratorio" })).toBe(false);
    expect(previsaoPublicavel({ ...valido(), evidenciaValidacao: undefined })).toBe(false);
  });
  it("rejeita horizontes inválidos, não finitos e limites inconsistentes", () => {
    expect(previsaoPublicavel({ ...valido(), anoAlvo: 2025 })).toBe(false);
    expect(previsaoPublicavel({ ...valido(), valor: Number.NaN })).toBe(false);
    expect(previsaoPublicavel({ ...valido(), limiteInferior: 101 })).toBe(false);
    expect(previsaoPublicavel({ ...valido(), limiteSuperior: 99 })).toBe(false);
    expect(previsaoPublicavel({ ...valido(), limiteInferior: -1 })).toBe(false);
    expect(previsaoPublicavel({ ...valido(), valor: -1, limiteInferior: null, limiteSuperior: null })).toBe(false);
  });
  it("rejeita validação sem baseline superior, amostra ou cobertura", () => {
    const ev = valido().evidenciaValidacao!;
    expect(previsaoPublicavel({ ...valido(), evidenciaValidacao: { ...ev, erroModelo: 7 } })).toBe(false);
    expect(previsaoPublicavel({ ...valido(), evidenciaValidacao: { ...ev, numeroObservacoes: 4 } })).toBe(false);
    expect(previsaoPublicavel({ ...valido(), evidenciaValidacao: { ...ev, numeroOrigensTeste: 1 } })).toBe(false);
    expect(previsaoPublicavel({ ...valido(), evidenciaValidacao: { ...ev, coberturaHistorica: 0.99 } })).toBe(false);
    expect(previsaoPublicavel({ ...valido(), evidenciaValidacao: { ...ev, fontesHomologadas: false } })).toBe(false);
    expect(previsaoPublicavel({ ...valido(), evidenciaValidacao: { ...ev, perimetroReconciliado: false } })).toBe(false);
  });
});

const serie = (): SerieFisica => ({
  dist: 6600, ano: 2025, perimetroId: "EPB", conceitoId: "transformadores",
  metrica: "quantidade", unidade: "un", regraVersao: "v1",
  estado: "observado", valor: 10, fonte: "BDGD", dataBase: "2025-12-31",
  cobertura: 1, perimetroBridgeId: null,
});

describe("estado de observação", () => {
  it("mantém valor observado e zero explicitamente verificado", () => {
    expect(valorObservado(serie())).toBe(10);
    expect(valorObservado({ ...serie(), estado: "zero_verificado", valor: 0 })).toBe(0);
  });
  it.each(["ausente", "nao_homologado", "nao_aplicavel", "ruptura"] as const)("não converte %s em zero", (estado) => {
    expect(valorObservado({ ...serie(), estado, valor: 0 })).toBeNull();
  });
  it("rejeita zero não verificado e valores não finitos", () => {
    expect(valorObservado({ ...serie(), estado: "zero_verificado", valor: 2 })).toBeNull();
    expect(valorObservado({ ...serie(), valor: Number.POSITIVE_INFINITY })).toBeNull();
  });
});
