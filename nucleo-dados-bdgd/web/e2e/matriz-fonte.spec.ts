import { expect, test } from "@playwright/test";

test("Matriz: aguarda a fonte filtrada para exportar e distingue falha de ausência", async ({ page }) => {
  let fail!: () => void;
  const pending = new Promise<void>((resolve) => { fail = resolve; });
  const source = "**/data/2025-12-31/conceitos/transformadores.json";
  await page.route(source, async (route) => { await pending; await route.abort("failed"); });
  const requested = page.waitForRequest(source);
  await page.goto("/matriz/?ativos=trafo_dist&cf=trafo_dist~area:UB", { waitUntil: "domcontentloaded" });
  await requested;
  const exp = page.getByTestId("matriz-csv");
  await expect(exp).toBeDisabled();
  fail();
  // o Next mantém um anunciador de rotas com role="alert": filtrar pelo texto do alerta da Matriz
  await expect(page.getByRole("alert").filter({ hasText: "Fonte do recorte indisponível" })).toBeVisible();
  await expect(exp).toBeDisabled();
  await page.unroute(source);
  await page.reload();
  await expect(page.getByTestId("total-trafo_dist")).not.toHaveText("N/D");
  await expect(exp).toBeEnabled();
  await expect(page.getByRole("alert").filter({ hasText: "Fonte do recorte indisponível" })).toHaveCount(0);
});
