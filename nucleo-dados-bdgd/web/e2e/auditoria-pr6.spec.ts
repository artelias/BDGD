import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

type Serie = [number, string, string, string, string, number[], number[], number[], string[], string[], string[]];
const painel = (page: import("@playwright/test").Page) => page.getByRole("region", { name: "Explorar cenários 2026–2030" });

async function baixar(link: import("@playwright/test").Locator, page: import("@playwright/test").Page) {
  const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString("utf8").replace(/^\uFEFF/, "");
}

test("auditoria: filtros de todas as distribuidoras com série, dois métodos e cinco horizontes", async ({ page, request }) => {
  const dados = await (await request.get("/data/previsoes/cenarios-exploratorios-2026-2030.json")).json();
  const series: Serie[] = dados.series;
  await page.goto("/previsoes/");
  const p = painel(page);
  const dist = p.getByRole("combobox", { name: "Distribuidora" });
  const ativo = p.getByRole("combobox", { name: "Ativo" });
  await expect(dist.locator("option")).toHaveCount(new Set(series.map((s) => s[0])).size); // 81 após a seleção das 13 republicações
  for (const codigo of new Set(series.map((s) => s[0]))) {
    await dist.selectOption(String(codigo));
    await expect(ativo.locator("option")).toHaveCount(series.filter((s) => s[0] === codigo).length + (codigo === 5370 ? 1 : 0));
    if (codigo === 5370) await expect(ativo.locator('option[value="consumidores"]')).toHaveCount(1); // ausente permanece selecionável e bloqueado
    expect(await ativo.inputValue()).not.toBe("");
  }
  await dist.selectOption("26");
  await ativo.selectOption("alimentadores");
  const linha = series.find((s) => s[0] === 26 && s[2] === "alimentadores")!;
  for (const metodo of ["persistencia", "tendencia_linear"]) {
    await p.getByRole("combobox", { name: "Método" }).selectOption(metodo);
    for (const ano of [2026, 2027, 2028, 2029, 2030]) {
      await p.getByRole("combobox", { name: "Ano simulado" }).selectOption(String(ano));
      await expect(p).toContainText(`Cenário condicional para ${ano}`);
      const esperado = (metodo === "persistencia" ? linha[5][3] : linha[6][ano - 2026]).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
      await expect(p.locator('[aria-live="polite"]')).toContainText(`${esperado} itens`);
    }
  }
});

test("auditoria: CSV conserva zeros técnicos, homologação e fonte nos dois métodos", async ({ page, request }) => {
  const dados = await (await request.get("/data/previsoes/cenarios-exploratorios-2026-2030.json")).json();
  const serie: Serie = dados.series.find((s: Serie) => s[10].includes("Z"));
  await page.goto("/previsoes/");
  const p = painel(page);
  await p.getByRole("combobox", { name: "Distribuidora" }).selectOption(String(serie[0]));
  await p.getByRole("combobox", { name: "Ativo" }).selectOption(serie[2]);
  for (const metodo of ["persistencia", "tendencia_linear"]) {
    await p.getByRole("combobox", { name: "Método" }).selectOption(metodo);
    const csv = await baixar(p.getByRole("link", { name: "Exportar série selecionada (CSV)" }), page);
    const [header, ...linhas] = csv.trim().split(/\r?\n/).map((l) => l.split(","));
    expect(linhas).toHaveLength(9);
    expect(header).toContain("publicacao_id");
    expect(header).toContain("status_homologacao");
    linhas.forEach((r, i) => {
      expect(Number(r[1])).toBeCloseTo(i < 4 ? serie[5][i] : metodo === "persistencia" ? serie[5][3] : serie[6][i - 4], 7);
      expect(r[2]).toBe(i < 4 ? serie[10][i] === "Z" ? "zero_tecnico" : "observado" : "simulacao_condicional");
      if (i < 4) expect(r[header.indexOf("publicacao_id")]).toBe(serie[8][i]);
      if (i < 4 && serie[10][i] === "Z") expect(r[header.indexOf("verificacao_independente_zero")]).toBe("pendente");
    });
  }
});

test("auditoria: Brasil incompleto permanece N/D na tela e no CSV histórico", async ({ page }) => {
  await page.goto("/evolucao/?ativo=consumidores");
  const tabela = page.getByTestId("evo-tabela");
  const brasil = tabela.locator("tbody tr").filter({ has: page.getByRole("rowheader", { name: /^Brasil/ }) });
  await expect(brasil).toBeVisible();
  for (let i = 0; i < 4; i++) await expect(brasil.locator("td").nth(i)).toContainText("N/D");
  const csv = await baixar(page.getByTestId("evo-csv"), page);
  const linhas = csv.split(/\r?\n/).filter((l) => l.startsWith("Brasil"));
  expect(linhas).toHaveLength(4);
  for (const l of linhas) expect(l.split(",")[5]).toBe("");
  await expect(tabela).toContainText("Painel balanceado");
});

test("auditoria: EAC/UCAT zero documentado e navegação preserva a distribuidora", async ({ page }) => {
  await page.goto("/?dist=26");
  await expect(page.getByTestId("kpi-uc").locator("..")).toContainText("295.861");
  const linha = page.locator('a[href*="ent=UCAT"]').locator("..");
  await expect(linha).toContainText("Zero no agregado processado");
  await expect(linha).toContainText("verificação independente pendente");
  await linha.getByRole("link").first().click();
  await expect(page).toHaveURL(/dists=26/);
  await expect(page).toHaveURL(/tec=UCAT/);
  await expect(page.getByRole("heading", { name: "Explorar ativos" })).toBeVisible();
  await expect(page.getByTestId("tec-entidade")).toContainText("Consumidores de alta tensão");
});

test("auditoria: gráfico não corta rótulos de grandes estoques", async ({ page, request }) => {
  const dados = await (await request.get("/data/previsoes/cenarios-exploratorios-2026-2030.json")).json();
  const maior: Serie = [...dados.series].sort((a: Serie, b: Serie) => Math.max(...b[6]) - Math.max(...a[6]))[0];
  await page.goto("/previsoes/");
  const p = painel(page);
  await p.getByRole("combobox", { name: "Distribuidora" }).selectOption(String(maior[0]));
  await p.getByRole("combobox", { name: "Ativo" }).selectOption(maior[2]);
  const textos = await p.locator("svg text").evaluateAll((nodes) => nodes.map((node) => ({ texto: node.textContent, x: (node as SVGGraphicsElement).getBBox().x })));
  expect(textos.filter((t) => t.x < 0)).toEqual([]);
});

test("auditoria: falha do arquivo de cenários é explícita e não produz zero", async ({ page }) => {
  await page.route("**/data/previsoes/cenarios-exploratorios-2026-2030.json", (r) => r.fulfill({ status: 503, body: "Indisponível" }));
  await page.goto("/previsoes/");
  await expect(painel(page).getByRole("alert")).toContainText("Arquivo de cenários indisponível");
  await expect(painel(page).getByRole("link", { name: /Exportar série/ })).toHaveCount(0);
});

for (const tema of ["light", "dark"] as const) {
  test(`@mobile auditoria visual e teclado: 320, 390 e 768 px, tema ${tema}`, async ({ page }, testInfo) => {
    await page.emulateMedia({ colorScheme: tema, reducedMotion: "reduce" });
    const erros: string[] = [];
    page.on("pageerror", (e) => erros.push(e.message));
    for (const largura of [320, 390, 768]) {
      await page.setViewportSize({ width: largura, height: 844 });
      await page.goto("/previsoes/");
      await expect(painel(page)).toContainText("1.792");
      await expect(page.getByRole("heading", { name: "Motor de Expansão Elétrica", exact: true })).toHaveCount(1);
      expect(await page.getByRole("main").count()).toBe(1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
      if (largura === 390) await page.screenshot({ path: testInfo.outputPath(`viewport-${tema}-390.png`), scale: "css" });
      const grafico = page.getByRole("region", { name: "Gráfico rolável dos cenários" });
      await grafico.focus();
      await expect(grafico).toBeFocused();
      await page.keyboard.press("End");
      await page.screenshot({ path: testInfo.outputPath(`previsoes-${tema}-${largura}.png`), fullPage: true, scale: "css" });
    }
    const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    await testInfo.attach(`axe-${tema}.json`, { body: JSON.stringify(axe.violations, null, 2), contentType: "application/json" });
    expect(axe.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? "")).map((v) => v.id)).toEqual([]);
    expect(erros).toEqual([]);
  });
}

test("auditoria: retorno de Previsões abre o Panorama", async ({ page }) => {
  await page.goto("/previsoes/");
  await page.getByRole("link", { name: "Explorar dados observados" }).click();
  await expect(page.getByRole("heading", { name: "Panorama Brasil" })).toBeVisible();
});
