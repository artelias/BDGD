import { expect, test } from "@playwright/test";

test("Comparador: seletores de grupo A e B nao encobrem filtros nem tabela", async ({ page }) => {
  await page.goto("/comparar/?a=grupo:energisa&b=grupo:equatorial");
  for (const lado of ["a", "b"]) {
    await page.getByTestId(`picker-${lado}`).click();
    const menu = page.getByTestId(`picker-${lado}-menu`);
    await expect(menu).toBeVisible();
    const card = page.getByTestId(`lado-${lado}`);
    const filtros = page.getByRole("toolbar", { name: "Ativo e recorte" });
    const menuBox = await menu.boundingBox();
    const cardBox = await card.boundingBox();
    const filtrosBox = await filtros.boundingBox();
    expect(menuBox).not.toBeNull();
    expect(cardBox).not.toBeNull();
    expect(filtrosBox).not.toBeNull();
    expect(menuBox!.y + menuBox!.height).toBeLessThanOrEqual(cardBox!.y + cardBox!.height + 2);
    expect(cardBox!.y + cardBox!.height).toBeLessThanOrEqual(filtrosBox!.y + 2);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
    await page.keyboard.press("Escape");
    await expect(menu).toHaveCount(0);
  }
});

test("Evolucao: graficos e valores sem inventario de publicacoes nem cartoes de validacao", async ({ page }) => {
  await page.goto("/evolucao/?ativo=trafo_dist");
  await expect(page.getByTestId("evo-tabela")).toBeVisible();
  await expect(page.getByTestId("anos")).toHaveCount(0);
  await expect(page.getByTestId("auditoria-publicacoes")).toHaveCount(0);
  await expect(page.getByTestId("evo-cards")).toBeVisible();
});
