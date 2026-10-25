import { expect, test } from "@playwright/test";

test.describe("Riscos exploratórios — dados BDGD sem imputação", () => {
  test("registra quando o zero de 2030 resulta de truncar uma tendência negativa", async ({ page }) => {
    await page.goto("/previsoes/");
    const painel = page.getByRole("region", { name: "Explorar cenários 2026–2030" });
    await painel.getByRole("combobox", { name: "Distribuidora" }).selectOption("87");
    await painel.getByRole("combobox", { name: "Ativo" }).selectOption("bancos_capacitores");
    await painel.getByRole("combobox", { name: "Método" }).selectOption("tendencia_linear");

    const aviso = painel.locator('[data-risco="TENDENCIA_TRUNCADA_NO_ZERO"]');
    await expect(aviso).toContainText("artifício matemático");
    await expect(painel.locator('[data-risco="REDUCAO_SUPERIOR_A_70_PCT"]')).toBeVisible();

    const [arquivo] = await Promise.all([
      page.waitForEvent("download"),
      painel.getByRole("link", { name: "Exportar série selecionada (CSV)" }).click(),
    ]);
    const chunks: Buffer[] = [];
    for await (const chunk of await arquivo.createReadStream()) chunks.push(Buffer.from(chunk));
    const csv = Buffer.concat(chunks).toString("utf8");
    expect(csv).toContain("publicacao_id,avisos_estatisticos");
    expect(csv).toContain("2030,0,simulacao_condicional");
    expect(csv).toContain("TENDENCIA_TRUNCADA_NO_ZERO");
  });

  test("não exporta quatro zeros de origem como observações positivas comprovadas", async ({ page }) => {
    await page.goto("/previsoes/");
    const painel = page.getByRole("region", { name: "Explorar cenários 2026–2030" });
    await painel.getByRole("combobox", { name: "Distribuidora" }).selectOption("39");
    await painel.getByRole("combobox", { name: "Ativo" }).selectOption("reatores");
    await expect(painel.locator('[data-risco="HISTORICO_QUATRO_ZEROS_TECNICOS"]')).toBeVisible();
    await expect(painel).toContainText("Zero técnico*");
    const [arquivo] = await Promise.all([
      page.waitForEvent("download"),
      painel.getByRole("link", { name: "Exportar série selecionada (CSV)" }).click(),
    ]);
    const chunks: Buffer[] = [];
    for await (const chunk of await arquivo.createReadStream()) chunks.push(Buffer.from(chunk));
    const csv = Buffer.concat(chunks).toString("utf8");
    expect(csv).toContain("2025,0,zero_verificado_pendente");
    expect(csv).toContain("2022,0,zero_verificado_pendente");
    expect(csv).toContain("status_homologacao").toBe(false); // apenas a coluna estável homologacao_origem
    expect(csv).toContain("homologacao_origem,publicacao_id");
  });

  test("@mobile riscos continuam acessíveis e a página não ganha rolagem horizontal", async ({ page }) => {
    await page.goto("/previsoes/");
    const painel = page.getByRole("region", { name: "Explorar cenários 2026–2030" });
    await painel.getByRole("combobox", { name: "Distribuidora" }).selectOption("39");
    await painel.getByRole("combobox", { name: "Ativo" }).selectOption("reatores");
    await expect(painel.locator('[data-risco="HISTORICO_QUATRO_ZEROS_TECNICOS"]')).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
