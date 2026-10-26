import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const paginas = [
  ["/", "Panorama Brasil"], ["/explorar/", "Explorar ativos"], ["/matriz/", "Matriz Nacional"],
  ["/comparar/", "Comparador"], ["/evolucao/", "Evolução histórica"],
  ["/previsoes/", "Motor de Expansão Elétrica"], ["/metodologia/", "Metodologia e qualidade"],
] as const;
const conteudo = (p: Page) => p.getByRole("main");

test("QA: busca global encontra os cenários e abre Previsões", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("open-search").click();
  await page.getByTestId("search-input").fill("cenários");
  await page.getByRole("option", { name: /Previsões/ }).click();
  await expect(page.getByRole("heading", { name: "Motor de Expansão Elétrica" })).toBeVisible();
});

test("QA: busca de UCAT mantém a entidade técnica solicitada", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("open-search").click();
  await page.getByTestId("search-input").fill("UCAT");
  await page.getByRole("option").first().click();
  await expect(page).toHaveURL(/tec=UCAT/);
  await expect(page.getByTestId("tec-entidade")).toContainText("Consumidores de alta tensão");
});

test("QA: busca global anuncia seleção e retém/restaura foco", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("open-search").click();
  const input = page.getByTestId("search-input");
  await input.fill("matriz");
  await page.keyboard.press("ArrowDown");
  await expect(input).toHaveAttribute("aria-activedescendant", /cmd-option-/);
  await page.keyboard.press("Tab");
  expect(await page.getByRole("dialog", { name: "Busca global" }).evaluate((d) => d.contains(document.activeElement))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Busca global" })).toHaveCount(0);
  await expect(page.getByTestId("open-search")).toBeFocused();
});

test("QA: marca cabe na lateral e estados atuais são explicados", async ({ page }) => {
  await page.goto("/metodologia/");
  await expect(page.getByText("Regra UC v3", { exact: true })).toBeVisible();
  await expect(page.getByText(/99 de 99 distribuidoras/)).toHaveCount(0);
  const dentro = await page.locator('aside[aria-label="Navegação principal"]').evaluate((side) => {
    const brand = side.querySelector('a[aria-label*="início"]')!;
    return brand.getBoundingClientRect().right <= side.getBoundingClientRect().right;
  });
  expect(dentro).toBe(true);
});

test("@iphone QA: Mais fecha com Escape, restaura foco e fecha no item atual", async ({ page }) => {
  await page.goto("/previsoes/");
  const mais = page.getByRole("button", { name: "Mais", exact: true });
  await mais.click();
  const dialog = page.getByRole("dialog", { name: "Mais opções" });
  await expect(dialog).toHaveAttribute("aria-modal", "true");
  await dialog.getByRole("button", { name: "Fechar", exact: true }).focus();
  await page.keyboard.press("Tab");
  expect(await dialog.evaluate((d) => d.contains(document.activeElement))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(mais).toBeFocused();
  await mais.click();
  await dialog.getByRole("link", { name: /^Previsões/ }).click();
  await expect(dialog).toHaveCount(0);
});

test("@iphone QA: modo avançado acessível sem códigos na URL", async ({ page }) => {
  await page.goto("/explorar/?ativo=consumidores");
  await page.getByTestId("modo-avancado-mobile").click();
  await page.getByTestId("abrir-tecnico").click();
  await expect(page.getByTestId("visao-tecnica")).toBeVisible();
});

test("@iphone QA: navegação pelas sete páginas, busca vazia e retorno", async ({ page }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Navegação", exact: true });
  for (const [link, heading] of [["Matriz", "Matriz Nacional"], ["Comparar", "Comparador"], ["Explorar", "Explorar ativos"], ["Panorama", "Panorama Brasil"]]) {
    await nav.getByRole("link", { name: link, exact: true }).click();
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
  }
  for (const [link, heading] of [["Evolução histórica", "Evolução histórica"], ["Metodologia e qualidade", "Metodologia e qualidade"], ["Previsões", "Motor de Expansão Elétrica"]]) {
    await nav.getByRole("button", { name: "Mais", exact: true }).click();
    await page.getByRole("dialog", { name: "Mais opções" }).getByRole("link", { name: new RegExp("^" + link) }).click();
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
  }
  await page.getByTestId("open-search").click();
  await page.getByTestId("search-input").fill("zzzz-sem-resultado-qa");
  await expect(page.getByText(/Nada encontrado para/)).toBeVisible();
  await expect(page.getByRole("option")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("open-search")).toBeFocused();
});

test("@iphone QA: TUC, potência, categorias e CSV do recorte", async ({ page }) => {
  await page.goto("/explorar/?ativo=transformadores&escopo=grupo:energisa");
  await page.getByTestId("cartao-565").click();
  await expect(page).toHaveURL(/c=565/);
  await expect(page.getByTestId("tabela-categorias")).toBeVisible();
  await page.getByTestId("cartao-570").click();
  await expect(page).toHaveURL(/c=570/);
  await page.getByRole("radio", { name: "Potência", exact: true }).click();
  await expect(page.getByTestId("valor-recorte")).toContainText("kVA");
  const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("explorar-csv").click()]);
  const csv = Buffer.concat(await (await dl.createReadStream()).toArray()).toString("utf8");
  expect(csv).toContain("potencia_kva,kVA");
  expect(csv).toContain("570");
  await test.info().attach("exportacao-tuc-570.csv", { body: csv, contentType: "text/csv" });
});

test("@iphone QA: matriz sem resultados não exporta um total vazio", async ({ page }) => {
  await page.goto("/matriz/");
  await expect(page.getByTestId("matriz-tabela")).toBeVisible();
  await page.getByTestId("matriz-busca").fill("zzzz-sem-resultado-qa");
  await expect(page.getByRole("status").filter({ hasText: "Nada no recorte" })).toBeVisible();
  await expect(page.getByTestId("matriz-tabela")).toHaveCount(0);
  await expect(page.getByTestId("matriz-csv")).toBeDisabled();
  await page.getByRole("button", { name: "Limpar", exact: true }).click();
  await expect(page.getByTestId("matriz-tabela")).toBeVisible();
  await expect(page.getByTestId("matriz-csv")).toBeEnabled();
});

test("@iphone QA: cenários permitem filtros e exportam a seleção no celular", async ({ page }) => {
  await page.goto("/previsoes/");
  const section = page.getByRole("region", { name: "Explorar cenários 2026–2030" });
  await section.getByRole("combobox", { name: "Método", exact: true }).selectOption("persistencia");
  await section.getByRole("combobox", { name: "Ano simulado", exact: true }).selectOption("2030");
  await expect(section.getByText("Cenário condicional para 2030")).toBeVisible();
  await expect(section.getByRole("region", { name: "Valores dos cenários — tabela rolável", exact: true }).locator("tbody tr")).toHaveCount(9);
  const [dl] = await Promise.all([page.waitForEvent("download"), section.getByRole("link", { name: "Exportar série selecionada (CSV)" }).click()]);
  expect(dl.suggestedFilename()).toContain("persistencia.csv");
  const csv = Buffer.concat(await (await dl.createReadStream()).toArray()).toString("utf8");
  expect(csv).toContain("2030");
  expect(csv).toMatch(/simulacao_condicional/);
  await test.info().attach("exportacao-cenario.csv", { body: csv, contentType: "text/csv" });
});

test("@iphone QA: folha de navegação cabe em paisagem e isola o foco", async ({ page }) => {
  await page.setViewportSize({ width: 568, height: 320 });
  await page.goto("/metodologia/");
  await page.getByRole("button", { name: "Mais", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Mais opções" });
  await dialog.getByRole("button", { name: "Fechar", exact: true }).scrollIntoViewIfNeeded();
  const box = (await dialog.boundingBox())!;
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(320);
  await expect(page.locator("body")).toHaveCSS("overflow", "hidden");
  const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(axe.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? "")).map((v) => v.id)).toEqual([]);
  await dialog.getByRole("button", { name: "Fechar", exact: true }).click();
  await expect(page.locator("body")).not.toHaveCSS("overflow", "hidden");
});

for (const dispositivo of ["desktop", "iphone"] as const) {
  for (const tema of ["light", "dark"] as const) {
    for (const [rota, titulo] of paginas) {
      test(`${dispositivo === "iphone" ? "@iphone " : ""}QA visual ${dispositivo} ${tema} ${rota}`, async ({ page }, info) => {
        await page.emulateMedia({ colorScheme: tema, reducedMotion: "reduce" });
        const erros: string[] = [], falhas: string[] = [];
        page.on("pageerror", (e) => erros.push(e.message));
        page.on("response", (r) => { if (r.url().includes("/data/") && r.status() >= 400) falhas.push(`${r.status()} ${r.url()}`); });
        const inicio = Date.now();
        await page.goto(rota);
        await expect(conteudo(page).getByRole("heading", { name: titulo, exact: true })).toBeVisible();
        // Espera pelo dado efetivo da página; h1 sozinho não comprova a carga.
        const alvo = rota === "/" ? page.getByTestId("kpi-uc") : rota === "/explorar/" ? page.getByTestId("conceito-titulo")
          : rota === "/matriz/" ? page.getByTestId("matriz-tabela") : rota === "/comparar/" ? page.getByTestId("comparar-tabela")
          : rota === "/evolucao/" ? page.getByTestId("evo-tabela") : rota === "/previsoes/" ? page.getByRole("region", { name: "Explorar cenários 2026–2030" }).getByRole("combobox", { name: "Ativo", exact: true })
          : page.locator("#regras");
        await expect(alvo).toBeVisible();
        const cargaMs = Date.now() - inicio;
        expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
        await page.screenshot({ path: info.outputPath("inicio.png"), scale: "css" });
        await info.attach("início", { path: info.outputPath("inicio.png"), contentType: "image/png" });
        await alvo.scrollIntoViewIfNeeded();
        await page.screenshot({ path: info.outputPath("dados.png"), scale: "css" });
        await info.attach("dados efetivos", { path: info.outputPath("dados.png"), contentType: "image/png" });
        const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).exclude(".maplibregl-canvas").analyze();
        const graves = axe.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""));
        await info.attach("navegacao.json", { body: JSON.stringify({ rota, dispositivo, tema, cargaMs, erros, falhas, axe: axe.violations }, null, 2), contentType: "application/json" });
        expect(graves.map((v) => v.id)).toEqual([]);
        expect(erros).toEqual([]); expect(falhas).toEqual([]);
      });
    }
  }
}
