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
    // regressão: o contêiner do mapa precisa ocupar o palco (ordem de CSS em produção)
    expect(await page.locator("canvas.maplibregl-canvas").evaluate((c) => c.clientHeight)).toBeGreaterThan(400);
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
    await table.getByRole("button", { name: /^Rede de média tensão/ }).click();
    await expect(page).toHaveURL(/ordem=rede_mt/);
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

  test("R2 panorama: clicar de novo desmarca, Ver Brasil limpa e ranking expande", async ({ page }) => {
    await page.goto("/?dist=31");
    await expect(page.getByTestId("dist-title")).toHaveText(/CEA Equatorial/);
    const bar = page.getByRole("button", { name: /CEA Equatorial/ }).last();
    await page.getByTestId("ranking-toggle").click();
    await expect(page.getByTestId("ranking-status")).toContainText("Mostrando 99 de 99");
    await page.getByTestId("ranking-list").getByRole("button", { name: /CEA Equatorial/ }).click();
    await expect(page).not.toHaveURL(/dist=/);
    await page.getByTestId("ranking-toggle").click();
    await expect(page.getByTestId("ranking-status")).toContainText("Mostrando 12 de 99");
    void bar;
    await page.goto("/?grupo=energisa&dist=26");
    await expect(page.getByTestId("ver-brasil")).toBeVisible();
    await page.getByTestId("ver-brasil").click();
    await expect(page).not.toHaveURL(/dist=|grupo=/);
  });

  test("R2 panorama: KPIs sem transbordo, explicação e N/D justificado", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("kpi-uc")).toBeVisible();
    const over = await page.locator('[data-testid^="kpi-"]').evaluateAll((els) => els.map((e) => e.parentElement!).filter((k) => k.scrollWidth > k.clientWidth + 1).length);
    expect(over).toBe(0);
    await page.getByTestId("explain-ssdmt").click();
    await expect(page.getByRole("dialog", { name: /Rede de média tensão/ })).toBeVisible();
    await page.getByRole("button", { name: "Ver cálculo técnico" }).click();
    await expect(page.getByRole("dialog", { name: /Rede de média tensão/ })).toContainText("COMP");
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("nd-uc")).toContainText(/distribuidoras? sem valor homologado/);
    await page.getByTestId("nd-uc-why").click();
    await expect(page.getByRole("dialog").last()).toContainText("DIST");
    await page.getByTestId("kpi-picker").click();
    await page.getByRole("button", { name: "Redes", exact: true }).click();
    await expect(page.getByTestId("kpi-ramlig")).toBeVisible();
  });

  test("R2 rodapé: autoria e contato", async ({ page }) => {
    await page.goto("/metodologia/");
    await expect(page.getByTestId("autoria")).toContainText("Desenvolvido por Arthur Henrique Elias de Lima");
    await expect(page.getByTestId("contato")).toHaveAttribute("href", "mailto:Arthur.henrique.elias@gmail.com");
    await expect(page.locator("footer")).not.toContainText("Projeto independente");
    await expect(page.locator("footer")).toContainText("ANEEL — BDGD (Dados Abertos)");
    await expect(page.locator("#dicionario")).toBeAttached();
  });

  test("R2 comparador: barras espelhadas e radar com benchmark acima de 100%", async ({ page }) => {
    await page.goto("/comparar/?a=grupo:energisa&b=grupo:equatorial&grafico=valores&ref=bench_dists");
    await expect(page.getByTestId("chart-espelhado")).toBeVisible();
    await expect(page.getByTestId("radar-tabela")).toBeVisible();
    const pcts = await page.locator('[data-testid^="radar-pct-"]').allInnerTexts();
    expect(pcts.some((x) => parseFloat(x.replace(".", "").replace(",", ".")) > 100)).toBeTruthy();
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("radar-csv").click()]);
    expect(dl.suggestedFilename()).toContain("radar");
  });

  test("R2 evolução: histórico em preparação sem números de ativos", async ({ page }) => {
    await page.goto("/evolucao/");
    await expect(page.getByTestId("historico-preparacao")).toBeVisible();
    await expect(page.getByTestId("historico-progresso")).toContainText("31/12/2022");
  });

  test("R2 mapa: clique fora das áreas volta ao Brasil", async ({ page }) => {
    await page.goto("/?dist=5697"); // Celesc: litoral de SC, canto inferior direito do quadro é oceano
    await expect(page.getByTestId("map-ready")).toHaveAttribute("data-ready", "true", { timeout: 60_000 });
    await expect(page.getByTestId("dist-title")).toBeVisible();
    await page.waitForTimeout(1500);
    const box = (await page.locator("canvas.maplibregl-canvas").boundingBox())!;
    await page.mouse.click(box.x + box.width - 60, box.y + box.height - 40); // oceano, canto inferior direito
    await expect(page).not.toHaveURL(/dist=/);
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
