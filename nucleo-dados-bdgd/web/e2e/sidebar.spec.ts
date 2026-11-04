import { expect, test, type Page } from "@playwright/test";

const side = (page: Page) => page.locator('aside[aria-label="Navegação principal"]');
const toggle = (page: Page) => side(page).getByRole("button", { name: /(?:Recolher|Expandir) navegação/ });
async function dimensions(page: Page) {
  return side(page).evaluate((el) => {
    const r = el.getBoundingClientRect();
    const main = el.nextElementSibling!.getBoundingClientRect();
    const button = el.querySelector('button[aria-expanded]')!.getBoundingClientRect();
    return { width: r.width, mainX: main.x, buttonY: button.y, buttonBottom: button.bottom,
      viewportHeight: innerHeight, overflow: document.documentElement.scrollWidth - innerWidth };
  });
}
async function width(page: Page, value: number) {
  await expect.poll(async () => (await dimensions(page)).width).toBe(value);
  await expect.poll(async () => (await dimensions(page)).mainX).toBe(value);
  expect((await dimensions(page)).overflow).toBeLessThanOrEqual(1);
}

test("barra lateral: dimensões reais, teclado, navegação e persistência", async ({ page }, info) => {
  await page.goto("/metodologia/");
  await expect(toggle(page)).toBeVisible();
  await width(page, 244);
  await toggle(page).focus();
  await page.keyboard.press("Enter");
  await expect(toggle(page)).toHaveAttribute("aria-expanded", "false");
  await info.attach("recolhida.json", { body: JSON.stringify(await dimensions(page)), contentType: "application/json" });
  await width(page, 68);
  await expect(toggle(page)).toBeFocused();
  await expect(side(page).getByRole("link", { name: "Matriz nacional", exact: true })).toHaveAttribute("title", "Matriz nacional");
  await side(page).getByRole("link", { name: "Matriz nacional", exact: true }).focus();
  await expect(page.getByRole("tooltip")).toHaveText("Matriz nacional");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("tooltip")).toHaveCount(0);
  await side(page).getByRole("link", { name: "Matriz nacional", exact: true }).click();
  await expect(page.getByTestId("matriz-tabela")).toBeVisible();
  await width(page, 68);
  await page.reload();
  await width(page, 68);
  await page.getByTestId("theme-toggle").click();
  await width(page, 68);
  await toggle(page).focus();
  await page.keyboard.press("Space");
  await width(page, 244);
  await expect(toggle(page)).toHaveAttribute("aria-expanded", "true");
  await page.reload();
  await width(page, 244);
});

test("barra lateral: alterna com leitura e escrita de localStorage bloqueadas", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "localStorage", { get() { throw new DOMException("bloqueado", "SecurityError"); } });
  });
  await page.goto("/metodologia/");
  await width(page, 244);
  await toggle(page).click();
  await width(page, 68);
  await side(page).getByRole("link", { name: "Matriz nacional", exact: true }).click();
  await expect(page.getByTestId("matriz-tabela")).toBeVisible();
  await width(page, 68);
  await toggle(page).click();
  await width(page, 244);
});

test("barra lateral: botão alcançável em janela de pouca altura", async ({ page }, info) => {
  await page.setViewportSize({ width: 1024, height: 400 });
  await page.goto("/metodologia/");
  await expect(toggle(page)).toBeVisible();
  await info.attach("janela-baixa.json", { body: JSON.stringify(await dimensions(page)), contentType: "application/json" });
  await page.screenshot({ path: info.outputPath("janela-baixa.png") });
  expect((await dimensions(page)).buttonBottom).toBeLessThanOrEqual(400);
  await toggle(page).click();
  await width(page, 68);
  await page.screenshot({ path: info.outputPath("recolhida-janela-baixa.png") });
  const link = side(page).getByRole("link", { name: "Previsões", exact: true });
  await link.focus();
  const r = (await link.boundingBox())!;
  expect(r.y).toBeGreaterThanOrEqual(0);
  expect(r.y + r.height).toBeLessThanOrEqual((await toggle(page).boundingBox())!.y);
  await toggle(page).click();
  await width(page, 244);
});
