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
    await expect(page.getByTestId("ent-title")).toHaveText(/baixa tensão/i);
    await page.getByTestId("attr-ARE_LOC").click();
    await expect(page.getByTestId("chart-categorias")).toBeVisible();
    await page.locator("table tbody tr").first().click();
    await expect(page).toHaveURL(/c1=/);
    await expect(page.getByTestId("attr2-CLAS_SUB")).toHaveAttribute("aria-disabled", "false");
    await expect(page.getByTestId("attr2-TEN_FORN")).toHaveAttribute("aria-disabled", "true");
    await page.getByTestId("attr2-CLAS_SUB").click();
    await expect(page).toHaveURL(/a2=CLAS_SUB/);
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("explorar-csv").click()]);
    expect(dl.suggestedFilename()).toMatch(/^bdgd_2025-12-31_UCBT_CLAS_SUB_dado-ARE_LOC-/);
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

  test("R3 panorama: dez KPIs, cálculo explicado e total nacional não parcial", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("kpi-uc")).toBeVisible();
    const over = await page.locator('[data-testid^="kpi-"]').evaluateAll((els) => els.map((e) => e.parentElement!).filter((k) => k.scrollWidth > k.clientWidth + 1).length);
    expect(over).toBe(0);
    await page.getByTestId("explain-ssdmt").click();
    await expect(page.getByRole("dialog", { name: /Rede de média tensão/ })).toBeVisible();
    await page.getByRole("button", { name: "Ver cálculo técnico" }).click();
    await expect(page.getByRole("dialog", { name: /Rede de média tensão/ })).toContainText("COMP");
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="kpi-uc"]').locator("..")).toContainText("Total indisponível");
    await expect(page.locator('button[data-testid^="kpi-"]:not([data-testid="kpi-picker"])')).toHaveCount(10);
    await expect(page.getByTestId("kpi-trdist565")).toBeVisible();
    await expect(page.getByTestId("kpi-trforca570")).toBeVisible();
    await page.getByTestId("kpi-picker").click();
    await page.getByRole("button", { name: "Redes", exact: true }).click();
    await expect(page.getByTestId("kpi-ssdat")).toBeVisible();
  });

  test("R2 rodapé: autoria e contato", async ({ page }) => {
    await page.goto("/metodologia/");
    await expect(page.getByTestId("autoria")).toContainText("Desenvolvido por Arthur Henrique Elias de Lima");
    await expect(page.getByTestId("contato")).toHaveAttribute("href", "mailto:Arthur.henrique.elias@gmail.com");
    await expect(page.locator("footer")).not.toContainText("Projeto independente");
    await expect(page.locator("footer")).toContainText("ANEEL — BDGD (Dados Abertos)");
    await expect(page.locator("#dicionario")).toBeAttached();
  });

  test("R2 matriz: medida Extensão só com tipos aplicáveis, UF e chips", async ({ page }) => {
    await page.goto("/matriz/?metrica=extensao_km&ufs=SC");
    const table = page.getByTestId("matriz-tabela");
    await expect(table).toBeVisible();
    await expect(table.getByRole("button", { name: /SSDMT/ })).toBeVisible();
    await expect(table.getByRole("button", { name: /UCBT/ })).toHaveCount(0);
    await expect(page.getByTestId("matriz-chips")).toContainText("UF: SC");
    for (const row of (await table.locator("tbody tr").all()).slice(1)) expect(await row.innerText()).toMatch(/SC/);
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("matriz-csv").click()]);
    const csv = await (await dl.createReadStream()).toArray();
    expect(Buffer.concat(csv).toString("utf-8").split(/\r?\n/)[0]).toContain("data_base,versao,dist,sigla,grupo_economico,grupo_status,entidade,tipo_de_ativo,metrica,unidade,valor,status,motivo,regra,cobertura_recorte");
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

  test("R2 explorar: recorte TUC 565 e participação dupla", async ({ page }) => {
    await page.goto("/explorar/?ent=EQTRMT&escopo=grupo:energisa");
    await page.getByTestId("preset-tuc-EQTRMT-565").click();
    await expect(page).toHaveURL(/c1=565/);
    await expect(page.getByTestId("participacao")).toBeVisible();
    await expect(page.getByTestId("vinculos-tuc")).toContainText("instalações distintas");
    await expect(page.getByTestId("part-escopo")).toHaveText(/%|N\/D/);
    await expect(page.getByTestId("inventario-atributos")).toContainText("Filtrável agora");
  });

  test("Evolução 2022–2025 exibe histórico real e rastreabilidade", async ({ page }) => {
    await page.goto("/evolucao/?ativo=consumidores");
    await expect(page.getByTestId("evo-tabela")).toBeVisible();
    await expect(page.getByTestId("evo-cards")).toBeVisible();
    await expect(page.getByTestId("evo-tabela")).toContainText("2025");
    await expect(page.getByText("Histórico em preparação.")).toHaveCount(0);
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
