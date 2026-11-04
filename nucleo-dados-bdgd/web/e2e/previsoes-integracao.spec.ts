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

test("Previsões apresenta o painel principal de cenários antes das ressalvas longas (painel exploratório retirado, PR #21)", async ({ page }) => {
  await page.goto("/previsoes/");
  const p = page.getByTestId("cenarios-motor");
  await expect(page.getByRole("heading", { name: "Cenários de expansão por métrica física" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Explorar cenários 2026–2030" })).toHaveCount(0);
  for (const nome of ["Família", "Ativo", "Métrica", "Distribuidora ou grupo"]) await expect(p.getByRole("combobox", { name: nome, exact: true })).toBeVisible();
  await expect(p.getByRole("radiogroup", { name: "Cenário" })).toBeVisible();
  await expect(p.getByTestId("cenarios-grafico")).toBeVisible();
  await expect(p.getByRole("link", { name: "Exportar série e cenários (CSV)" })).toHaveAttribute("download", /^cenarios_.*_DIST_\d+\.csv$/);
  const ressalva = page.getByText("Entenda a diferença entre simulação e previsão validada");
  await expect(ressalva).toBeVisible();
  // o painel de resultados vem antes da ressalva longa
  expect((await p.boundingBox())!.y).toBeLessThan((await ressalva.boundingBox())!.y);
});

test("@mobile Previsões mantém formulário e gráficos acessíveis sem rolagem horizontal da página", async ({ page }) => {
  await page.goto("/previsoes/");
  const p = page.getByTestId("cenarios-motor");
  await expect(page.getByRole("heading", { name: "Cenários de expansão por métrica física" })).toBeVisible();
  await expect(p.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true })).toBeVisible();
  await expect(p.getByRole("combobox", { name: "Ativo", exact: true })).toBeVisible();
  await expect(p.getByTestId("cenarios-grafico")).toBeVisible();
  const sobra = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(sobra).toBeLessThanOrEqual(1);
});
