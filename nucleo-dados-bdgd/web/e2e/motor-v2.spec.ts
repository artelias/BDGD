import { expect, test, type Page } from "@playwright/test";

// Build de homologação (NEXT_PUBLIC_MOTOR_V2=homologacao): confere a interface do Motor V2 contra o produto servido.
const sec = (page: Page) => page.getByTestId("motor-v2");
const fmt = (v: number | null, conta: boolean) => v == null ? "N/D" : v.toLocaleString("pt-BR", { maximumFractionDigits: conta ? 0 : 1 });
async function semRolagemHorizontal(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
}
async function dist(page: Page, d: number) {
  const r = await page.request.get(`/data/motor-v2/distribuidoras/${d}.json`);
  expect(r.ok()).toBe(true);
  return r.json();
}

test("motor v2: série de uma distribuidora confere com o produto, cenários, CSV e estado", async ({ page }) => {
  await page.goto("/previsoes/");
  await expect(sec(page)).toBeVisible();
  const s = sec(page);
  await s.getByLabel("Distribuidora ou grupo do Motor V2").selectOption("dist:6600");
  await s.getByLabel("Ativo e métrica do Motor V2").selectOption("trafo_forca|potencia_kva");
  const j = await dist(page, 6600);
  const serie = j.series.find((x: { objetivo: string; metrica: string }) => x.objetivo === "trafo_forca" && x.metrica === "potencia_kva");
  await expect(s.getByTestId("motor-v2-estado")).toContainText(/Projetada/);
  const tabela = s.getByTestId("motor-v2-tabela");
  for (const [i, ano] of [2026, 2027, 2028, 2029, 2030].entries()) {
    const linha = tabela.locator("tr", { has: page.locator(`th:text-is("${ano}")`) });
    await expect(linha.locator("td").nth(1)).toHaveText(fmt(serie.cenarios.Conservador[i], false));
    await expect(linha.locator("td").nth(2)).toHaveText(fmt(serie.cenarios.Moderado[i], false));
    await expect(linha.locator("td").nth(3)).toHaveText(fmt(serie.cenarios.Agressivo[i], false));
  }
  await s.getByRole("radio", { name: /Agressivo/ }).click();
  await expect(s.getByRole("radio", { name: /Agressivo/ })).toHaveAttribute("aria-checked", "true");
  await expect(s.getByTestId("motor-v2-grafico")).toBeVisible();
  const href = await s.getByTestId("motor-v2-csv").getAttribute("href");
  const csv = decodeURIComponent(href!.split(",").slice(1).join(","));
  expect(csv.trim().split("\n")).toHaveLength(1 + serie.historico.length + 15);
  expect(csv).toContain("experimental_nao_homologado");
  await expect(s.getByTestId("motor-v2-modelo")).toContainText(/Não homologado/);
  await expect(s.getByTestId("motor-v2-cobertura")).toContainText(/PARCIAL/);
  await semRolagemHorizontal(page);
});

test("motor v2: sucessão sem números, grupo PARCIAL e potência de reguladores não somada", async ({ page }) => {
  await page.goto("/previsoes/");
  const s = sec(page);
  await expect(s).toBeVisible();
  await s.getByLabel("Distribuidora ou grupo do Motor V2").selectOption("dist:6611");
  await s.getByLabel("Ativo e métrica do Motor V2").selectOption("consumidores|quantidade");
  await expect(s.getByTestId("motor-v2-estado")).toContainText("Sucessão societária");
  await expect(s.getByTestId("motor-v2-tabela").locator("td", { hasText: /^\d/ })).toHaveCount(1);   // só o histórico 2022 observado
  await s.getByLabel("Distribuidora ou grupo do Motor V2").selectOption("grupo:energisa");
  await expect(s.getByTestId("motor-v2-grupo-rotulo")).toContainText(/Total/);
  await s.getByLabel("Ativo e métrica do Motor V2").selectOption("reguladores|potencia_kva");
  await expect(s.getByTestId("motor-v2-nao-somavel")).toBeVisible();
  await semRolagemHorizontal(page);
});

test("motor v2: metodologia por empresa mostra modelo, equação e coeficientes verificados", async ({ page }) => {
  await page.goto("/metodologia/#motor-v2");
  const m = page.getByTestId("metodologia-motor-v2-auditoria");
  await expect(m).toBeVisible();
  await m.getByLabel("Distribuidora da metodologia do Motor V2").selectOption("11825");
  await m.getByLabel("Ativo e métrica da metodologia do Motor V2").selectOption("trafo_medida|quantidade");
  const ficha = page.getByTestId("metodologia-motor-v2-ficha");
  await expect(ficha).toContainText("ols:comparaveis");
  await expect(ficha).toContainText(/recuperados por reajuste/);
  await expect(ficha).toContainText(/Não homologado/);
  await m.getByLabel("Ativo e métrica da metodologia do Motor V2").selectOption("trafo_medida|potencia_kva");
  await expect(ficha).toContainText(/Não aplicável/);
});

const PAGINAS = ["/", "/explorar/", "/matriz/", "/comparar/", "/evolucao/", "/previsoes/", "/metodologia/"];
for (const w of [1440, 1024, 901, 900, 768, 390, 320]) {
  test(`layout em ${w}px: sete páginas sem rolagem horizontal; lateral recolhe com largura real ou navegação inferior`, async ({ page }) => {
    test.setTimeout(240_000);
    await page.setViewportSize({ width: w, height: 860 });
    for (const p of PAGINAS) {
      await page.goto(p);
      await expect(page.locator("main, [role=main]").first()).toBeVisible();
      await page.waitForLoadState("networkidle");
      await semRolagemHorizontal(page);
    }
    const lateral = page.locator('aside[aria-label="Navegação principal"]');
    if (w >= 901) {
      const medir = () => lateral.evaluate((el) => [el.getBoundingClientRect().width, el.nextElementSibling!.getBoundingClientRect().x]);
      const botao = lateral.getByRole("button", { name: /(?:Recolher|Expandir) navegação/ });
      if ((await botao.getAttribute("aria-expanded")) === "false") await botao.click();
      await expect.poll(medir).toEqual([244, 244]);
      await botao.click();
      await expect.poll(medir).toEqual([68, 68]);
      await semRolagemHorizontal(page);
      await botao.click();
      await expect.poll(medir).toEqual([244, 244]);
    } else {
      await expect(lateral).toBeHidden();
      await expect(page.getByRole("navigation", { name: "Navegação", exact: true })).toBeVisible();
    }
  });
}
