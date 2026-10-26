import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";
const catalog = JSON.parse(readFileSync("../etl/bdgd2025/config/conceitos_2025.json", "utf8"));

test("motor universal: carga sob demanda, catálogo inteiro, diagnóstico e exportação", async ({ page }) => {
  let requests = 0;
  page.on("request", (r) => { if (r.url().includes("motor-universal-resumo")) requests++; });
  await page.goto("/previsoes/");
  await expect(page.getByRole("heading", { name: "Explorar cenários 2026–2030" })).toBeVisible();
  expect(requests).toBe(0);
  await page.getByText("Explorar experimentos do motor universal", { exact: true }).click();
  await expect(page.getByTestId("motor-universal-cobertura")).toContainText(`${catalog.ativos.length} ativos catalogados`);
  const section = page.getByTestId("motor-universal");
  await expect(section.getByRole("combobox", { name: "Ativo do motor", exact: true }).locator("option")).toHaveCount(catalog.ativos.length);
  await section.getByRole("combobox", { name: "Ativo do motor", exact: true }).selectOption("consumidores");
  await section.getByRole("combobox", { name: "Distribuidora do motor", exact: true }).selectOption("26");
  await expect(section).toContainText("Simulação condicional para 2030");
  await expect(section).toContainText("0 previsões homologadas");
  const [dl] = await Promise.all([page.waitForEvent("download"), section.getByRole("link", { name: "Exportar diagnóstico e seleção (JSON)" }).click()]);
  const text = Buffer.concat(await (await dl.createReadStream()).toArray()).toString("utf8");
  const data = JSON.parse(text);
  expect(data.previsao_validada).toBe(false); expect(data.intervalos).toBeNull();
  expect(data.serie.DIST).toBe("26"); expect(data.source_sha256).toHaveLength(64);
  await section.getByRole("combobox", { name: "Ativo do motor", exact: true }).selectOption("trafo_dist");
  await section.getByRole("combobox", { name: "Métrica do motor", exact: true }).selectOption("potencia_kva");
  await expect(section.getByTestId("motor-universal-vazio")).toContainText("Nenhum valor foi preenchido");
});

test("@iphone motor universal: categorias, filtros, dados ausentes e acessibilidade", async ({ page }, info) => {
  await page.goto("/previsoes/");
  await page.getByText("Explorar experimentos do motor universal", { exact: true }).click();
  const section = page.getByTestId("motor-universal");
  await expect(section.getByTestId("motor-universal-cobertura")).toBeVisible();
  await section.getByRole("combobox", { name: "Ativo do motor", exact: true }).selectOption("rede_mt");
  await expect(section.getByRole("combobox", { name: "Métrica do motor", exact: true })).toHaveValue("extensao_km");
  await section.getByRole("combobox", { name: "Família do motor", exact: true }).selectOption("Clientes");
  await expect(section.getByRole("combobox", { name: "Ativo do motor", exact: true }).locator("option")).toHaveCount(catalog.ativos.filter((a: { familia: string }) => a.familia === "Clientes").length);
  await section.getByRole("combobox", { name: "Distribuidora do motor", exact: true }).selectOption("26");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
  await page.screenshot({ path: info.outputPath("motor-universal-iphone.png"), scale: "css" });
  await info.attach("motor universal no iPhone", { path: info.outputPath("motor-universal-iphone.png"), contentType: "image/png" });
  const axe = await new AxeBuilder({ page }).include('[data-testid="motor-universal"]').withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(axe.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? "")).map((v) => v.id)).toEqual([]);
});

test("motor universal: falha de contrato mostra erro em vez de números", async ({ page }) => {
  await page.route("**/motor-universal-resumo.json.gz", (route) => route.fulfill({ json: { previsao_validada: true } }));
  await page.goto("/previsoes/");
  await page.getByText("Explorar experimentos do motor universal", { exact: true }).click();
  await expect(page.getByTestId("motor-universal").getByRole("alert")).toContainText("Contrato do motor universal inválido");
  await expect(page.getByTestId("motor-universal").getByRole("combobox")).toHaveCount(0);
});


test("motor universal: denominadores e potência sem histórico ficam explícitos no desktop", async ({ page }, info) => {
  await page.goto("/previsoes/");
  await page.getByText("Explorar experimentos do motor universal", { exact: true }).click();
  const section = page.getByTestId("motor-universal");
  await expect(section.getByTestId("motor-universal-universo")).toContainText("3.306 combinações esperadas");
  await expect(section.getByTestId("motor-universal-universo")).toContainText("456 combinações sem histórico");
  await section.getByText("Cobertura por métrica", { exact: true }).click();
  const region = section.getByRole("region", { name: "Cobertura das métricas do motor", exact: true });
  await expect(region.getByRole("row")).toHaveCount(4);
  await expect(region.getByRole("row").filter({ hasText: "potencia_kva" })).toContainText("456");
  await region.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath("motor-universal-cobertura-desktop.png"), scale: "css" });
  await info.attach("cobertura desktop", { path: info.outputPath("motor-universal-cobertura-desktop.png"), contentType: "image/png" });
});

test("@iphone motor universal: tabela de cobertura acessível sem alargar a página", async ({ page }, info) => {
  await page.goto("/previsoes/");
  await page.getByText("Explorar experimentos do motor universal", { exact: true }).click();
  const section = page.getByTestId("motor-universal");
  await expect(section.getByTestId("motor-universal-universo")).toContainText("1.305 bloqueadas");
  await section.getByText("Cobertura por métrica", { exact: true }).click();
  const region = section.getByRole("region", { name: "Cobertura das métricas do motor", exact: true });
  await region.focus(); await page.keyboard.press("ArrowRight");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
  const axe = await new AxeBuilder({ page }).include('[data-testid="motor-universal"]').withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(axe.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? "")).map((v) => v.id)).toEqual([]);
  await page.screenshot({ path: info.outputPath("motor-universal-cobertura-iphone.png"), scale: "css" });
  await info.attach("cobertura iPhone emulado", { path: info.outputPath("motor-universal-cobertura-iphone.png"), contentType: "image/png" });
});
