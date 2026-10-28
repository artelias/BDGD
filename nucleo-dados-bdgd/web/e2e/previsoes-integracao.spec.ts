import { expect, test } from "@playwright/test";

test("Evolução prioriza a série física; inventário técnico permanece em página própria", async ({ page }) => {
  await page.goto("/evolucao/?ativo=consumidores");
  await expect(page.getByTestId("evo-tabela")).toBeVisible();
  await expect(page.getByTestId("evo-cards")).toBeVisible();
  await expect(page.getByTestId("auditoria-publicacoes")).toHaveCount(0);
  await expect(page.getByTestId("evo-ressalvas")).toHaveCount(0);
  await page.goto("/auditoria-publicacoes/");
  await expect(page.getByTestId("auditoria-publicacoes")).toContainText("414");
});

test("Previsões apresenta resultados exploratórios antes das ressalvas longas", async ({ page }) => {
  await page.goto("/previsoes/");
  await expect(page.getByRole("heading", { name: "Explorar cenários 2026–2030" })).toBeVisible();
  await expect(page.getByText("1.555", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Explorar cenários 2026–2030" }).getByRole("combobox", { name: "Distribuidora" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Explorar cenários 2026–2030" }).getByRole("combobox", { name: "Ativo" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Explorar cenários 2026–2030" }).getByRole("combobox", { name: "Método" })).toBeVisible();
  await page.getByRole("region", { name: "Explorar cenários 2026–2030" }).getByRole("combobox", { name: "Método" }).selectOption("persistencia");
  await expect(page.getByRole("img", { name: /simulação condicional 2026 a 2030 pelo método persistência/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Exportar série selecionada/ })).toHaveAttribute("download", /cenario_DIST_/);
  await expect(page.getByText("Entenda a diferença entre simulação e previsão validada")).toBeVisible();
});

test("@mobile Previsões mantém formulário e gráficos acessíveis sem rolagem horizontal da página", async ({ page }) => {
  await page.goto("/previsoes/");
  await expect(page.getByRole("heading", { name: "Explorar cenários 2026–2030" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Explorar cenários 2026–2030" }).getByRole("combobox", { name: "Distribuidora", exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Explorar cenários 2026–2030" }).getByRole("combobox", { name: "Ano simulado" })).toBeVisible();
  const sobra = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(sobra).toBeLessThanOrEqual(1);
});
