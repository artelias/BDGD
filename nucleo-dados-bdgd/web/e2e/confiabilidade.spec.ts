import { expect, test, type Page } from "@playwright/test";

/** Fluxos reais do módulo de Confiabilidade com o produto publicado (EPB 6600 e Energisa AC 26). */
function semErros(page: Page) {
  const erros: string[] = [];
  page.on("pageerror", (e) => erros.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error") erros.push(m.text()); });
  return () => erros.filter((e) => !/favicon|Failed to load resource.*(png|pbf)|preload/i.test(e));
}

test.describe("Confiabilidade", () => {
  test("Brasil → EPB: mapa carrega conjuntos reais, lista e legenda", async ({ page }) => {
    const erros = semErros(page);
    await page.goto("/confiabilidade/");
    await expect(page.getByRole("heading", { level: 1, name: "Inteligência de Confiabilidade Elétrica" })).toBeVisible();
    await expect(page.getByTestId("conf-lista-dist")).toBeVisible();
    await expect(page.getByTestId("conf-total-conjuntos")).not.toHaveText("0");
    await page.goto("/confiabilidade/?dist=6600");
    await expect(page.getByTestId("conf-mapa-pronto")).toHaveAttribute("data-ready", "true");
    await expect(page.getByTestId("conf-mapa-pronto")).toHaveAttribute("data-conjuntos", "75");
    await expect(page.getByTestId("conf-lista-conj").locator("tbody tr")).toHaveCount(75);
    await expect(page.getByTestId("conf-legenda")).toContainText("DEC anual 2025");
    await expect(page.getByTestId("conf-dist-dec")).toContainText("9,40");
    expect(erros()).toEqual([]);
  });

  test("alternar DEC/FEC, ano, mês e cor regulatória atualiza legenda e URL", async ({ page }) => {
    await page.goto("/confiabilidade/?dist=6600");
    await expect(page.getByTestId("conf-lista-conj")).toBeVisible();
    await page.getByRole("radio", { name: "FEC" }).first().click();
    await expect(page).toHaveURL(/ind=fec/);
    await expect(page.getByTestId("conf-legenda")).toContainText("FEC");
    await page.getByRole("radio", { name: "% do limite" }).click();
    await expect(page).toHaveURL(/cor=limite/);
    await expect(page.getByTestId("conf-legenda")).toContainText("no limite");
    await page.goto("/confiabilidade/?dist=6600&ano=2023&mes=4");
    await expect(page.getByTestId("conf-legenda")).toContainText("abr/2023");
    await expect(page.getByRole("radio", { name: "% do limite" })).toBeDisabled();   // limites são anuais
  });

  test("selecionar conjunto abre a ficha técnica com dados físicos e reconstrução", async ({ page }) => {
    const erros = semErros(page);
    await page.goto("/confiabilidade/?dist=6600");
    await page.getByTestId("conf-lista-conj").getByText("Mataraca", { exact: true }).click();
    await expect(page).toHaveURL(/conj=16849/);
    const ficha = page.getByTestId("conf-ficha");
    await expect(ficha).toBeVisible();
    await expect(page.getByTestId("conf-ficha-nome")).toHaveText("Mataraca");
    await expect(page.getByTestId("conf-kpi-dec")).toContainText("30,06");
    await expect(page.getByTestId("conf-infra")).toContainText("Rede MT por mil consumidores");
    await expect(page.getByTestId("conf-reconstrucao")).toBeVisible();
    // DEC apurado = componentes internas; externas e expurgos não recebem parcela do indicador
    await expect(ficha.getByRole("row", { name: /Externa, não programada \(fora do DEC\).*não compõe/ })).toBeVisible();
    await expect(page.getByTestId("conf-alimentadores").locator("tbody tr")).not.toHaveCount(0);
    expect(erros()).toEqual([]);
  });

  test("comparador A × B entre empresas: tabela, frases sem causalidade e CSV", async ({ page }) => {
    await page.goto("/confiabilidade/?aba=comparar&a=6600-16849&b=26-12591");
    await expect(page.getByTestId("conf-comp-qualidade")).toContainText("30,06");
    await expect(page.getByTestId("conf-comp-qualidade")).toContainText("42,48");
    const frases = await page.getByTestId("conf-frases").innerText();
    expect(frases.toLowerCase()).not.toMatch(/porque|causa|devido/);
    await expect(page.getByTestId("conf-comp-infra")).toBeVisible();
    const download = page.waitForEvent("download");
    await page.getByTestId("conf-csv").click();
    expect((await download).suggestedFilename()).toMatch(/^confiabilidade_comparacao_6600-16849_x_26-12591_2025\.csv$/);
  });

  test("benchmarking: pares semelhantes, perfil e ranking com dados reais", async ({ page }) => {
    await page.goto("/confiabilidade/?aba=benchmarking&dist=6600&conj=16849");
    await expect(page.getByTestId("conf-bench-resumo")).toContainText("75");
    await expect(page.getByTestId("conf-pares").locator("tbody tr")).toHaveCount(21);
    await expect(page.getByTestId("conf-perfil").locator("tbody tr")).not.toHaveCount(0);
    await expect(page.getByTestId("conf-ranking").locator("tbody tr")).toHaveCount(15);
  });

  test("fatores associados e metodologia exibem resultados e limitações reais", async ({ page }) => {
    await page.goto("/confiabilidade/?aba=fatores");
    await expect(page.getByTestId("conf-hipoteses").locator("tbody tr")).not.toHaveCount(0);
    await expect(page.getByTestId("conf-associacoes")).toBeVisible();
    await expect(page.getByTestId("conf-fat-n")).not.toHaveText("0");
    await page.goto("/confiabilidade/?aba=metodologia");
    await expect(page.getByTestId("conf-metodologia")).toContainText("Σ DIC ÷ Cc");
  });

  test("mapa: hover mostra a dica, clique abre a ficha, zoom e volta ao Brasil", async ({ page }) => {
    const erros = semErros(page);
    await page.goto("/confiabilidade/?dist=26&ind=fec&mes=3");
    await expect(page.getByTestId("conf-mapa-pronto")).toHaveAttribute("data-ready", "true");
    await expect(page.getByTestId("conf-mapa-pronto")).toHaveAttribute("data-conjuntos", "15");
    await expect(page.getByTestId("conf-legenda")).toContainText("FEC de mar/2025");
    const canvas = page.locator("canvas.maplibregl-canvas");
    await canvas.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1200);   // enquadramento animado (800 ms)
    const caixa = (await canvas.boundingBox())!;
    // procura um ponto sobre um conjunto em uma grade do canvas
    let achou = false;
    for (let i = 3; i <= 7 && !achou; i++) for (let j = 3; j <= 7 && !achou; j++) {
      await page.mouse.move(caixa.x + (caixa.width * i) / 10, caixa.y + (caixa.height * j) / 10);
      achou = await page.getByRole("status").filter({ hasText: /conjunto \d+ · Energisa AC/ }).isVisible().catch(() => false);
      if (achou) { await page.mouse.down(); await page.mouse.up(); }
    }
    expect(achou).toBe(true);
    await expect(page).toHaveURL(/dist=26&.*conj=\d+/);
    await expect(page.getByTestId("conf-ficha")).toBeVisible();
    await page.getByRole("button", { name: "Zoom in" }).click();
    await page.getByRole("button", { name: "Brasil", exact: true }).click();
    await expect(page).not.toHaveURL(/dist=/);
    await expect(page.getByTestId("conf-lista-dist")).toBeVisible();
    expect(erros()).toEqual([]);
  });

  test("tema escuro e claro mudam o fundo do mapa sem recriá-lo", async ({ page }) => {
    await page.goto("/confiabilidade/?dist=26");
    const estado = page.getByTestId("conf-mapa-pronto");
    await expect(estado).toHaveAttribute("data-ready", "true");
    const antes = await estado.getAttribute("data-fundo");
    await page.getByTestId("theme-toggle").click();
    await expect.poll(async () => estado.getAttribute("data-fundo")).not.toBe(antes);
  });

  test("@mobile página utilizável no celular, sem rolagem horizontal", async ({ page }) => {
    await page.goto("/confiabilidade/?dist=6600");
    await expect(page.getByTestId("conf-lista-conj")).toBeVisible();
    const largura = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    expect(largura[0]).toBeLessThanOrEqual(largura[1] + 1);
    await page.getByTestId("conf-lista-conj").getByText("Mataraca", { exact: true }).click();
    await expect(page.getByTestId("conf-ficha")).toBeVisible();
  });
});
