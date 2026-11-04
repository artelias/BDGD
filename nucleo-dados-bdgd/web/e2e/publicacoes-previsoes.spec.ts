import { expect, test } from "@playwright/test";

test.describe("Publicações auditadas — histórico 2022–2025", () => {
  test("quarentena antiga foi substituída pelo inventário real e filtros distinguem bloqueios", async ({ page }) => {
    await page.goto("/auditoria-publicacoes/");
    const auditoria = page.getByTestId("auditoria-publicacoes");
    await expect(auditoria.getByRole("heading", { name: "Publicações avaliadas, versões selecionadas e restrições" })).toBeVisible();
    await expect(auditoria).toContainText("414");
    await expect(auditoria).toContainText("26");
    await expect(auditoria).toContainText("14");
    await expect(auditoria.getByRole("row")).toHaveCount(28); // 13 versões anteriores + 14 exclusões + cabeçalho
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
    await expect(auditoria).toContainText("Versão anterior preservada");

    await auditoria.getByRole("combobox", { name: "Situação" }).selectOption("competencia");
    await expect(auditoria.getByRole("row")).toHaveCount(15);
    await auditoria.getByRole("combobox", { name: "Ano" }).selectOption("2022");
    await expect(auditoria.getByRole("row")).toHaveCount(7); // 6 excluídos em 2022
    await auditoria.getByRole("combobox", { name: "Ano" }).selectOption("2023");
    await expect(auditoria.getByRole("row")).toHaveCount(9); // 8 excluídos em 2023
  });

  test("publicação oficial, motivo e estado em uso com ressalva permanecem rastreáveis", async ({ page }) => {
    await page.goto("/auditoria-publicacoes/");
    const auditoria = page.getByTestId("auditoria-publicacoes");
    await auditoria.getByRole("combobox", { name: "Situação" }).selectOption("todas");
    await auditoria.getByRole("combobox", { name: "Ano" }).selectOption("2023");
    await auditoria.getByRole("searchbox", { name: "Distribuidora, DIST ou item oficial" }).fill("Coprel");
    const linhas = auditoria.getByRole("region", { name: "Publicações e justificativas — tabela rolável" }).locator("tbody tr");
    await expect(linhas).toHaveCount(2);
    await expect(auditoria).toContainText("Versão única em uso (ver ressalvas)");
    await expect(auditoria).toContainText("BASE inconsistente");
    await expect(linhas.first().locator('a[href^="https://www.arcgis.com/home/item.html?id="]')).toBeVisible();
  });

  test("@mobile inventário acessível sem rolagem horizontal da página", async ({ page }) => {
    await page.goto("/auditoria-publicacoes/");
    const auditoria = page.getByTestId("auditoria-publicacoes");
    await expect(auditoria.getByRole("row")).toHaveCount(28);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
});

test.describe("Previsões — cenários reais, não previsões validadas", () => {
  // painel principal (o exploratório foi retirado no PR #21): mesmo valor no gráfico, na tabela e no CSV, com a fonte do produto
  test("filtros, gráfico, histórico e CSV têm o mesmo valor e fonte", async ({ page, request }) => {
    const dados = await (await request.get("/data/previsoes/cenarios-motor.json")).json();
    const s26 = dados.metricas.find((x: { conceito: string; metrica: string }) => x.conceito === "alimentadores" && x.metrica === "quantidade").series["26"];
    await page.goto("/previsoes/");
    const painel = page.getByTestId("cenarios-motor");
    await painel.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("alimentadores");
    await painel.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).selectOption("dist:26");
    const tabela = painel.getByRole("region", { name: "Tabela anual de histórico e cenários" });
    await expect(tabela.getByRole("row", { name: /^2025/ })).toContainText("123");
    await expect(tabela.getByRole("row", { name: /^2030/ })).toContainText(String(s26.moderado[4]));
    await expect(painel.getByTestId("cenarios-grafico")).toBeVisible();
    const href = await painel.getByRole("link", { name: "Exportar série e cenários (CSV)" }).getAttribute("href");
    const csv = decodeURIComponent(href!.split(",").slice(1).join(","));
    expect(csv).toContain("2025,observado,123,");
    // contagem: o CSV exporta o inteiro publicado, o mesmo da tabela, nunca uma tendência bruta
    const l2030 = csv.split(/\r?\n/).find((l) => l.startsWith("2030,"))!.split(",");
    expect(Number(l2030[4])).toBe(s26.moderado[4]);
    expect(l2030[4]).toMatch(/^\d+$/);
    await expect(painel).toContainText("sem validação científica independente");
    await expect(page.getByRole("region", { name: "Explorar cenários 2026–2030" })).toHaveCount(0);
  });

  test("@mobile visão mostra cenários sem esconder controles e não estoura a largura", async ({ page }) => {
    await page.goto("/previsoes/");
    const painel = page.getByTestId("cenarios-motor");
    await expect(painel.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true })).toBeVisible();
    await expect(painel.getByRole("combobox", { name: "Ativo", exact: true })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
