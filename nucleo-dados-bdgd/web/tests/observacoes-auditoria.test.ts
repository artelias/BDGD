import { describe, expect, it } from "vitest";
import { COOPERA_UCBT_2025, observacaoCoopera2025, totalComCoberturaBt } from "@/lib/observacoes-auditoria";

describe("Coopera 2025: ausência cadastral não equivale a zero físico", () => {
  it("mantém UCBT sem registros como observação 0* e não como estoque validado", () => {
    expect(COOPERA_UCBT_2025.rotuloUcbt).toBe("0*");
    expect(COOPERA_UCBT_2025.registrosUcbt).toBe(0);
    expect(observacaoCoopera2025().elegivelTreino).toBe(false);
  });
  it("não forma total BT+MT+AT sem UCBT", () => {
    expect(totalComCoberturaBt(null, 224, 1)).toBeNull();
    expect(observacaoCoopera2025().subtotalObservado).toBe(225);
    expect(observacaoCoopera2025().totalConsumidores).toBeNull();
  });
  it("só aceita zero verdadeiro se observado independentemente", () => {
    expect(totalComCoberturaBt(0, 224, 1)).toBe(225);
    expect(totalComCoberturaBt(100, 224, 1)).toBe(325);
  });
});
