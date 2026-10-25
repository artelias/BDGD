import { expect, test } from "@playwright/test";

test.describe("Publicações auditadas — histórico 2022–2025", () => {
  test("quarentena antiga foi substituída pelo inventário real e filtros distinguem bloqueios", async ({ page }) => {
    await page.goto("/evolucao/?ativo=consumidores");
    const auditoria = page.getByTestId("auditoria-publicacoes");
    await expect(auditoria.getByRole("heading", { name: "Publicações avaliadas e motivos de bloqueio" })).toBeVisible();
    await expect(auditoria).toContainText("414");
    await expect(auditoria).toContainText("26");
    await expect(auditoria).toContainText("14");
    await expect(auditoria.getByRole("row")).toHaveCount(41); // 40 restritas + cabeçalho
    const pares = page.getByTestId("pares-publicacoes");
    await pares.locator("summary").click();
    await expect(pares.getByRole("row")).toHaveCount(14); // 13 pares + cabeçalho
    await expect(pares).toContainText("Cedrap");
    const inexistentes = page.getByTestId("publicacoes-inexistentes");
    await inexistentes.locator("summary").click();
    await expect(inexistentes.getByRole("row")).toHaveCount(12); // 11 DIST/ano + cabeçalho
    await expect(inexistentes).toContainText("275 células");
    await pares.locator("summary").click();
    await inexistentes.locator("summary").click();

    await auditoria.getByRole("combobox", { name: "Situação" }).selectOption("divergentes");
    await expect(auditoria.getByRole("row")).toHaveCount(27);
    await expect(auditoria).toContainText("Duas versões divergentes");

    await auditoria.getByRole("combobox", { name: "Situação" }).selectOption("competencia");
    await expect(auditoria.getByRole("row")).toHaveCount(15);
    await auditoria.getByRole("combobox", { name: "Ano" }).selectOption("2022");
    await expect(auditoria.getByRole("row")).toHaveCount(7); // 6 excluídos em 2022
    await auditoria.getByRole("combobox", { name: "Ano" }).selectOption("2023");
    await expect(auditoria.getByRole("row")).toHaveCount(9); // 8 excluídos em 2023
  });

  test("publicação oficial, motivo e estado em uso com ressalva permanecem rastreáveis", async ({ page }) => {
    await page.goto("/evolucao/");
    const auditoria = page.getByTestId("auditoria-publicacoes");
    await auditoria.getByRole("combobox", { name: "Situação" }).selectOption("todas");
    await auditoria.getByRole("combobox", { name: "Ano" }).selectOption("2023");
    await auditoria.getByRole("searchbox", { name: "Distribuidora, DIST ou item oficial" }).fill("Coprel");
    const linhas = auditoria.locator("tbody tr");
    await expect(linhas).toHaveCount(2);
    await expect(auditoria).toContainText("Versão única em uso (ver ressalvas)");
    await expect(auditoria).toContainText("BASE inconsistente");
    await expect(linhas.first().locator('a[href^="https://www.arcgis.com/home/item.html?id="]')).toBeVisible();
  });

  test("@mobile inventário acessível sem rolagem horizontal da página", async ({ page }) => {
    await page.goto("/evolucao/");
    const auditoria = page.getByTestId("auditoria-publicacoes");
    await expect(auditoria.getByRole("row")).toHaveCount(41);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
});

test.describe("Previsões — cenários reais, não previsões validadas", () => {
  test("filtros, gráfico, histórico e CSV têm o mesmo valor e fonte", async ({ page }) => {
    await page.goto("/previsoes/");
    const painel = page.getByRole("region", { name: "Explorar cenários 2026–2030" });
    await expect(painel).toContainText("1.555");
    await painel.getByRole("combobox", { name: "Ativo" }).selectOption("alimentadores");
    await painel.getByRole("combobox", { name: "Ano simulado" }).selectOption("2030");
    await expect(painel).toContainText("180 itens");
    await expect(painel).toContainText("123 itens");
    await expect(painel.getByRole("img", { name: /Evolução histórica 2022 a 2025/ })).toBeVisible();
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      painel.getByRole("link", { name: "Exportar série selecionada (CSV)" }).click(),
    ]);
    const stream = await download.createReadStream();
    const bufs: Buffer[] = [];
    for await (const chunk of stream) bufs.push(Buffer.from(chunk));
    const csv = Buffer.concat(bufs).toString("utf8");
    expect(csv).toContain("2025,123,observado");
    expect(csv).toContain("2030,180,simulacao_condicional");
    await expect(painel).toContainText("Não há previsão estatisticamente validada");
  });

  test("@mobile visão mostra cenários sem esconder controles e não estoura a largura", async ({ page }) => {
    await page.goto("/previsoes/");
    const painel = page.getByRole("region", { name: "Explorar cenários 2026–2030" });
    await expect(painel.getByRole("combobox", { name: "Distribuidora" })).toBeVisible();
    await expect(painel.getByRole("combobox", { name: "Ativo" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
