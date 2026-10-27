/** Ressalva de publicação; NÃO é uma imputação ou alteração da BDGD. */
export const COOPERA_UCBT_2025 = {
  dist: 5370,
  ano: 2025,
  entidade: "UCBT",
  referencia: "2025-12-31",
  nomeArquivo: "Coopera_5370_2025-12-31_V11_20260822-0914.gdb.zip",
  arcgisItemId: "5d0f7ea5db5d48aeb365998fabaa9db7",
  registrosUcbt: 0,
  ucmtAt: 224,
  ucatAt: 1,
  subtotalAtObservado: 225,
  rotuloUcbt: "0*",
  rotuloSubtotal: "225*",
  estado: "AUSENCIA_CADASTRAL_NA_PUBLICACAO",
} as const;

/** Ausência de entidade na fonte não comprova estoque físico zero. */
export function totalComCoberturaBt(
  ucbtAt: number | null,
  ucmtAt: number,
  ucatAt: number,
): number | null {
  return ucbtAt === null ? null : ucbtAt + ucmtAt + ucatAt;
}

/** Preserva o subtotal observado, explicitamente incompleto. */
export function observacaoCoopera2025() {
  return {
    valorNaFonte: COOPERA_UCBT_2025.rotuloUcbt,
    subtotalObservado: COOPERA_UCBT_2025.subtotalAtObservado,
    totalConsumidores: totalComCoberturaBt(null, COOPERA_UCBT_2025.ucmtAt, COOPERA_UCBT_2025.ucatAt),
    elegivelTreino: false,
    texto: "0* = nenhum registro UCBT na publicação ANEEL de 2025; não significa zero consumidores físicos. O subtotal de 225 AT cobre apenas UCMT (224) e UCAT (1); o total BT+MT+AT é N/D. Possível falha cadastral da fonte, ainda não confirmada.",
  };
}
