import { expect, test, type Page } from "@playwright/test";

// Regressão do defeito P2: o <Suspense> no layout raiz fazia o prerender emitir o shell como segmento adiado e a hidratação deixava
// a cópia oculta da página em <div hidden id="S:0">, duplicando ids e landmarks. Aqui o DOM é conferido, não os seletores dos testes.
const PAGINAS = ["/", "/explorar/", "/matriz/", "/comparar/", "/evolucao/", "/previsoes/", "/metodologia/"];

async function auditar(page: Page, rota: string) {
  const erros: string[] = [];
  page.on("pageerror", (e) => erros.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error") erros.push(m.text()); });
  await page.goto(rota);
  await expect(page.locator("#conteudo")).toHaveCount(1);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2500);        // o defeito aparecia segundos depois da carga, no reveal agendado do React
  const dom = await page.evaluate(() => {
    const cont: Record<string, number> = {};
    for (const e of document.querySelectorAll("[id]")) cont[e.id] = (cont[e.id] ?? 0) + 1;
    return {
      duplicados: Object.entries(cont).filter(([, n]) => n > 1).map(([k]) => k),
      s0: !!document.getElementById("S:0"), templates: document.querySelectorAll('template[id^="B:"]').length,
      ocultos: [...document.querySelectorAll("body > div[hidden]")].filter((d) => d.querySelector("main,aside,h1,#conteudo")).length,
      landmarks: ["aside", "h1", "#conteudo"].map((s) => document.querySelectorAll(s).length),
    };
  });
  expect.soft(dom.duplicados, `ids duplicados em ${rota}`).toEqual([]);
  expect.soft(dom.s0, `cópia oculta S:0 em ${rota}`).toBe(false);
  expect.soft(dom.templates, `template B: retido em ${rota}`).toBe(0);
  expect.soft(dom.ocultos, `página oculta retida em ${rota}`).toBe(0);
  expect.soft(dom.landmarks[2], `#conteudo em ${rota}`).toBe(1);
  expect.soft(dom.landmarks[1], `um único h1 em ${rota}`).toBeLessThanOrEqual(1);
  const relevantes = erros.filter((e) => !/favicon|maplibre|Failed to load resource.*(png|pbf)|preload/i.test(e));
  expect.soft(relevantes, `erros no console em ${rota}`).toEqual([]);
}

for (const rota of PAGINAS) {
  test(`hidratação: ${rota} sem ids duplicados nem cópia oculta, sem erros no console`, async ({ page }) => { await auditar(page, rota); });
  test(`hidratação @mobile: ${rota} sem ids duplicados nem cópia oculta`, async ({ page }) => { await auditar(page, rota); });
}

test("hidratação: parâmetros da URL, filtros, tema e lateral sobrevivem à navegação entre páginas", async ({ page }) => {
  await page.goto("/matriz/?ativos=consumidores&ufs=PB");
  await expect(page.getByTestId("matriz-tabela")).toBeVisible();
  const antes = await page.evaluate(() => location.search);
  await page.getByRole("link", { name: "Comparador" }).first().click();
  await expect(page).toHaveURL(/\/comparar\//);
  await page.goBack();
  await expect(page).toHaveURL(/\/matriz\/\?ativos=consumidores&ufs=PB/);
  expect(await page.evaluate(() => location.search)).toBe(antes);
  await expect(page.locator("#conteudo")).toHaveCount(1);
  const lateral = page.locator('aside[aria-label="Navegação principal"]');
  await expect(lateral).toHaveCount(1);
  const botao = lateral.getByRole("button", { name: /(?:Recolher|Expandir) navegação/ });
  const larg = async () => lateral.evaluate((e) => e.getBoundingClientRect().width);
  const w0 = await larg(); await botao.click(); await expect.poll(larg).not.toBe(w0);
  await page.getByRole("button", { name: /tema|claro|escuro/i }).first().click();
  await expect(page.locator("#conteudo")).toHaveCount(1);
  for (const r of PAGINAS) { await page.goto(r); await expect(page.locator("#conteudo")).toHaveCount(1); await expect(page.locator("aside")).toHaveCount(1); }
});
