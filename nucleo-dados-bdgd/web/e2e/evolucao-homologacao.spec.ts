import { expect, test } from "@playwright/test";

// Fase 5A: matriz de homologação aplicada à Evolução (dados reais do pacote publicado)
const linha = (page: import("@playwright/test").Page, nome: RegExp | string) => page.getByTestId("evo-tabela").locator("tbody tr").filter({ has: page.getByRole("rowheader", { name: nome }) });

test.describe("Evolução — homologação assistida", () => {
  test("Brasil fica N/D em todos os anos com lacunas; painel balanceado identificado", async ({ page }) => {
    await page.goto("/evolucao/?ativo=consumidores");
    const br = linha(page, /^Brasil/);
    await expect(br.locator("td").nth(3)).toBeVisible();
    const cel = await br.locator("td").allInnerTexts();
    expect(cel[0]).toContain("N/D"); expect(cel[1]).toContain("N/D");
    expect(cel[2]).toContain("N/D"); expect(cel[3]).toContain("N/D");
    await expect(page.getByTestId("evo-tabela")).toContainText(/Painel balanceado \(\d+ distribuidoras\)/);
    await expect(page.getByTestId("anos")).toHaveCount(0);
    await expect(page.getByTestId("auditoria-publicacoes")).toHaveCount(0);
    await expect(page.getByTestId("evo-tabela")).toBeVisible();
  });

  test("republicação mais recente conserva o valor observado em 2023 sem inventário na tela", async ({ page }) => {
    await page.goto("/evolucao/?escopo=dists&dists=5381&ativo=consumidores");
    const tr = page.getByTestId("evo-tabela").locator("tbody tr").first();
    await expect(tr.locator("td").nth(1)).toContainText("6.894");
    await expect(page.getByTestId("auditoria-publicacoes")).toHaveCount(0);
    await expect(page.getByTestId("evo-pendencias")).toHaveCount(0);
  });

  test("anomalia comprovada na fonte não publica o valor (Coopera 2025 sem UCBT)", async ({ page }) => {
    await page.goto("/evolucao/?escopo=dists&dists=5370&ativo=consumidores");
    const tr = page.getByTestId("evo-tabela").locator("tbody tr").first();
    await expect(tr.locator("td").nth(3)).toBeVisible();
    const cel = await tr.locator("td").allInnerTexts();
    expect(cel[3]).toContain("N/D");
    expect(cel[3]).not.toContain("225");
  });

  test("proveniência rastreia até a publicação ANEEL com intervalo da base e SHA-256", async ({ page }) => {
    await page.goto("/evolucao/?escopo=dists&dists=26&ativo=rede_mt");
    const prov = page.getByTestId("evo-proveniencia");
    await expect(prov).toContainText("01/01/2024–31/12/2024");
    await expect(prov.locator('a[href^="https://www.arcgis.com/home/item.html?id="]').first()).toBeVisible();
    await expect(page.getByTestId("evo-tuc")).toContainText("Recortes por TUC");
  });

  test("natureza das variações distingue mudança cadastral de expansão física", async ({ page }) => {
    await page.goto("/evolucao/?escopo=dists&dists=385&ativo=rede_at");
    await expect(page.getByTestId("evo-variacoes")).toContainText("mudança cadastral");
    await page.goto("/evolucao/?escopo=dists&dists=4950&ativo=chaves");
    await expect(page.getByTestId("evo-variacoes")).toContainText("mudança de classificação");
  });

  test("família filtra os ativos e unidades são respeitadas", async ({ page }) => {
    await page.goto("/evolucao/?ativo=rede_mt");
    await expect(page.getByTestId("evo-familia")).toBeVisible();
    await expect(page.getByTestId("evo-cards")).toContainText("km");
    await page.goto("/evolucao/?ativo=postes");
    await expect(page.getByTestId("evo-cards")).not.toContainText(" km ");
  });

  test("sucessões: ENF não é somada e a ponte EPB ← EBO aparece como pendente com evidência", async ({ page }) => {
    await page.goto("/evolucao/?visao=perimetro&ativo=consumidores");
    await expect(page.getByTestId("sucessoes")).toContainText("já contida na sucessora");
    await expect(page.getByTestId("sucessoes")).toContainText("absorção provável, aguardando decisão");
  });

  test("@mobile página responsiva sem rolagem horizontal da página", async ({ page }) => {
    await page.goto("/evolucao/?escopo=dists&dists=26,31&ativo=consumidores");
    await expect(page.getByTestId("evo-tabela")).toBeVisible();
    const sobra = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(sobra).toBeLessThanOrEqual(1);
  });
});
