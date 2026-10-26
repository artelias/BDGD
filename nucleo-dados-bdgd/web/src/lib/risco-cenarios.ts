/**
 * Alertas descritivos sobre cenários condicionais BDGD.
 * Não altera a observação, não escolhe publicações e não homologa nenhum modelo.
 * Um zero projetado por truncamento NÃO é zero verificado na fonte.
 */
export type CodigoRisco =
  | "ZERO_TECNICO_PENDENTE"
  | "HISTORICO_QUATRO_ZEROS_TECNICOS"
  | "ZERO_2025_APOS_VALOR_POSITIVO"
  | "TENDENCIA_TRUNCADA_NO_ZERO"
  | "EXPANSAO_SUPERIOR_A_100_PCT"
  | "REDUCAO_SUPERIOR_A_70_PCT";

export interface AlertaRisco {
  codigo: CodigoRisco;
  gravidade: "alta" | "atencao";
  descricao: string;
}
export type MetodoRisco = "persistencia" | "tendencia_linear";

const tolerancia = 1e-9;
function inclinacao(y: readonly number[]): number {
  const n = y.length;
  const mx = (n - 1) / 2;
  const my = y.reduce((s, v) => s + v, 0) / n;
  return y.reduce((s, v, i) => s + (i - mx) * (v - my), 0) /
    y.reduce((s, _v, i) => s + (i - mx) ** 2, 0);
}

export function avaliarRiscosCenario(
  historico: readonly number[],
  futuro: readonly number[],
  estados: readonly string[],
  metodo: MetodoRisco,
): AlertaRisco[] {
  if (historico.length !== 4 || futuro.length !== 5 || estados.length !== 4 ||
      historico.some((v) => !Number.isFinite(v) || v < 0) ||
      futuro.some((v) => !Number.isFinite(v) || v < 0) ||
      estados.some((s) => s !== "O" && s !== "Z")) {
    throw new Error("Série de riscos incompatível com o contrato 2022–2030");
  }
  const avisos: AlertaRisco[] = [];
  const adicionar = (codigo: CodigoRisco, gravidade: AlertaRisco["gravidade"], descricao: string) => {
    avisos.push({ codigo, gravidade, descricao });
  };
  if (estados.includes("Z")) {
    adicionar("ZERO_TECNICO_PENDENTE", "atencao",
      "Há zero(s) de origem classificados tecnicamente. Ainda é necessária a comprovação independente de cada entidade no GDB; não tratar como ausência estrutural do ativo.");
  }
  if (historico.every((v) => v === 0) && estados.every((s) => s === "Z")) {
    adicionar("HISTORICO_QUATRO_ZEROS_TECNICOS", "alta",
      "Todos os quatro anos são zeros técnicos. A projeção igual a zero repete a hipótese de origem; não prova inexistência do ativo.");
  }
  const ultimo = historico[3];
  if (ultimo === 0 && historico.slice(0, 3).some((v) => v > 0)) {
    adicionar("ZERO_2025_APOS_VALOR_POSITIVO", "alta",
      "O estoque passou de um valor positivo a zero em 2025: verificar a entidade vazia, mudança de cadastro ou descontinuidade antes de interpretar a queda.");
  }
  if (metodo === "tendencia_linear") {
    // O mesmo OLS com intercepto do motor corrigido pelo Codex:
    // y_hat(x) = media_y + inclinacao * (x - media_x); 2022 tem x=0.
    const slope = inclinacao(historico);
    const mediaY = historico.reduce((s, v) => s + v, 0) / historico.length;
    const mediaX = (historico.length - 1) / 2;
    if (ultimo > 0 && Array.from({ length: 5 }, (_, i) => mediaY + slope * (i + 4 - mediaX)).some((v) => v < -tolerancia)) {
      adicionar("TENDENCIA_TRUNCADA_NO_ZERO", "alta",
        "A extrapolação linear produziria valor negativo, que o algoritmo truncou em zero. Esse zero é artifício matemático, nunca zero observado.");
    }
    const ano2030 = futuro[4];
    if (ultimo > 0 && ano2030 >= 2 * ultimo - tolerancia) {
      adicionar("EXPANSAO_SUPERIOR_A_100_PCT", "atencao",
        "A extrapolação linear duplica ou mais o estoque de 2025 até 2030. É um sinal de sensibilidade a apenas quatro observações.");
    }
    if (ultimo > 0 && ano2030 <= 0.3 * ultimo + tolerancia) {
      adicionar("REDUCAO_SUPERIOR_A_70_PCT", "alta",
        "O cenário reduz o estoque a 30% ou menos do patamar de 2025 até 2030. Investigar mudanças cadastrais e de perímetro.");
    }
  }
  return avisos;
}
