import { expect, test } from "@playwright/test";

test.describe("Núcleo de Dados da BDGD — 2025-12-31", () => {
  test("pacote publicado é somente 2025-12-31", async ({ request }) => {
    const r = await request.get("/data/2025-12-31/index.json");
    expect(r.ok()).toBeTruthy();
    const j = await r.json();
    expect(j.release.data_base).toBe("2025-12-31");
    const cols = JSON.stringify(Object.keys(j.distribuidoras[0])) + JSON.stringify(j.fatos.cols);
    expect(cols).not.toMatch(/(^|[^_])cod_id"/i);
  });

  test("panorama: mapa ARAT, KPIs e seleção de distribuidora", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Panorama Brasil" })).toBeVisible();
    await expect(page.getByTestId("map-ready")).toHaveAttribute("data-ready", "true", { timeout: 60_000 });
    await expect(page.locator("canvas.maplibregl-canvas")).toBeVisible();
    await expect(page.getByTestId("kpi-ssdmt")).not.toContainText("N/D");
    await page.getByTestId("panel-search").fill("CEA");
    await page.getByTestId("dist-31").click();
    await expect(page).toHaveURL(/dist=31/);
    await expect(page.getByTestId("dist-title")).toHaveText(/CEA Equatorial/);
    await page.getByTestId("panel-back").click();
    await expect(page).not.toHaveURL(/dist=/);
  });

  test("panorama: legenda de grupo filtra o recorte", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Energisa", exact: true }).first().click();
    await expect(page).toHaveURL(/grupo=energisa/);
    await expect(page.getByRole("heading", { name: "Energisa", level: 2 })).toBeVisible();
  });

  test("matriz: busca, ordenação e exportação CSV", async ({ page }) => {
    await page.goto("/matriz/");
    const table = page.getByTestId("matriz-tabela");
    await expect(table).toBeVisible();
    await page.getByTestId("matriz-busca").fill("Energisa");
    await expect(table.locator("tbody tr")).not.toHaveCount(0);
    for (const row of await table.locator("tbody tr").all()) {
      const t = await row.innerText();
      if (!t.startsWith("Total")) expect(t).toMatch(/Energisa/);
    }
    await table.getByRole("button", { name: /SSDMT/ }).click();
    await expect(page).toHaveURL(/ordem=SSDMT/);
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("matriz-csv").click()]);
    expect(dl.suggestedFilename()).toMatch(/^bdgd_2025-12-31_matriz_.*\.csv$/);
  });

  test("comparador: troca A/B e exporta", async ({ page }) => {
    await page.goto("/comparar/?a=grupo:energisa&b=grupo:equatorial");
    await expect(page.getByTestId("comparar-tabela")).toBeVisible();
    await page.getByTestId("trocar").click();
    await expect(page).toHaveURL(/a=grupo(%3A|:)equatorial/);
    await expect(page).toHaveURL(/b=grupo(%3A|:)energisa/);
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("comparar-csv").click()]);
    expect(dl.suggestedFilename()).toContain("2025-12-31_comparacao");
  });

  test("entidades e DDA: facetas em cascata e combinação indisponível", async ({ page }) => {
    await page.goto("/explorar/?ent=UCBT");
    await expect(page.getByTestId("ent-title")).toHaveText(/Baixa Tensão/);
    await page.getByTestId("attr-ARE_LOC").click();
    await expect(page.getByTestId("chart-categorias")).toBeVisible();
    await page.locator("table tbody tr").first().click();
    await expect(page).toHaveURL(/c1=/);
    await expect(page.getByTestId("attr2-CLAS_SUB")).toHaveAttribute("aria-disabled", "false");
    await expect(page.getByTestId("attr2-TEN_FORN")).toHaveAttribute("aria-disabled", "true");
    await page.getByTestId("attr2-CLAS_SUB").click();
    await expect(page).toHaveURL(/a2=CLAS_SUB/);
  });

  test("tema persiste após recarregar", async ({ page }) => {
    await page.goto("/metodologia/");
    const html = page.locator("html");
    await page.getByTestId("theme-toggle").click(); // sistema -> claro
    await page.getByTestId("theme-toggle").click(); // claro -> escuro
    await expect(html).toHaveAttribute("data-theme", "dark");
    await page.reload();
    await expect(html).toHaveAttribute("data-theme", "dark");
  });

  test("busca global por teclado abre a distribuidora", async ({ page }) => {
    await page.goto("/matriz/");
    await expect(page.getByTestId("matriz-tabela")).toBeVisible();
    await page.keyboard.press("Control+k");
    await page.getByTestId("search-input").fill("Energisa AC");
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/\?dist=26/);
  });

  test("celular: barra de abas e folha do mapa @mobile", async ({ page }) => {
    await page.goto("/");
    const tabs = page.getByRole("navigation", { name: "Navegação" });
    await expect(tabs).toBeVisible();
    await tabs.getByRole("link", { name: "Matriz" }).click();
    await expect(page).toHaveURL(/\/matriz\//);
    await expect(page.getByTestId("matriz-tabela")).toBeVisible();
  });
});
