import { expect, test } from "@playwright/test";

/** Riscos da tendência exploratória (truncamento no zero, quatro zeros técnicos) eram exibidos pelo painel "Explorar cenários
 *  2026–2030", retirado no PR #21. A lógica continua coberta no Vitest (tests/risco-cenarios.test.ts) e o produto exploratório
 *  continua publicado. Aqui se verifica que o painel principal não reintroduz esses riscos: nenhuma trajetória truncada no zero e
 *  nenhuma série fabricada a partir de zeros técnicos. */
test.describe("Riscos exploratórios — dados BDGD sem imputação", () => {
  test("nenhuma trajetória publicada chega a zero por truncamento; a queda forte de bancos (DIST 87) aparece como valor positivo", async ({ page, request }) => {
    const dados = await (await request.get("/data/previsoes/cenarios-motor.json")).json();
    for (const m of dados.metricas) for (const s of Object.values(m.series) as Record<string, number[] | null>[])
      for (const c of ["conservador", "moderado", "agressivo"]) for (const v of s[c] ?? []) expect(v, `${m.conceito}/${c}`).toBeGreaterThan(0);
    await page.goto("/previsoes/");
    await expect(page.getByRole("region", { name: "Explorar cenários 2026–2030" })).toHaveCount(0);
    const painel = page.getByTestId("cenarios-motor");
    await painel.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("bancos_capacitores");
    await painel.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).selectOption("dist:87");
    const s87 = dados.metricas.find((x: { conceito: string }) => x.conceito === "bancos_capacitores").series["87"];
    await expect(painel.getByRole("region", { name: "Tabela anual de histórico e cenários" }).getByRole("row", { name: /^2030/ })).toContainText(String(s87.moderado[4]));
    await expect(painel.locator("[data-risco]")).toHaveCount(0);
  });

  test("não fabrica série a partir de quatro zeros técnicos: reatores da DIST 39 não são oferecidos como previsão", async ({ page, request }) => {
    const dados = await (await request.get("/data/previsoes/cenarios-motor.json")).json();
    const m = dados.metricas.find((x: { conceito: string }) => x.conceito === "reatores");
    expect(m.series["39"]).toBeUndefined();
    await page.goto("/previsoes/");
    const painel = page.getByTestId("cenarios-motor");
    await painel.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("reatores");
    await expect(painel.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).locator('option[value="dist:39"]')).toHaveCount(0);
  });

  test("@mobile o painel de cenários continua acessível e a página não ganha rolagem horizontal", async ({ page }) => {
    await page.goto("/previsoes/");
    const painel = page.getByTestId("cenarios-motor");
    await painel.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("reatores");
    await expect(painel.getByTestId("cenarios-completude")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
