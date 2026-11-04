import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";


async function baixar(link: import("@playwright/test").Locator, page: import("@playwright/test").Page) {
  const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString("utf8").replace(/^\uFEFF/, "");
}

// PR #21: o painel exploratório "Explorar cenários 2026–2030" foi retirado; a experiência pública de cenários é o painel principal
// "Cenários de expansão por métrica física". As auditorias abaixo valem para ele, sobre o produto publicado cenarios-motor.json.
const principal = (page: import("@playwright/test").Page) => page.getByTestId("cenarios-motor");
type Produto = { metricas: { conceito: string; metrica: string; series: Record<string, { hist: [number, number][]; conservador: number[] | null; moderado: number[] | null; agressivo: number[] | null }> }[] };

test("auditoria: painel principal oferece todas as distribuidoras com série e mostra o 2030 publicado de cada cenário", async ({ page, request }) => {
  const dados = (await (await request.get("/data/previsoes/cenarios-motor.json")).json()) as Produto;
  const m = dados.metricas.find((x) => x.conceito === "alimentadores" && x.metrica === "quantidade")!;
  await page.goto("/previsoes/");
  await expect(page.getByRole("region", { name: "Explorar cenários 2026–2030" })).toHaveCount(0);   // painel retirado (PR #21)
  const p = principal(page);
  await p.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("alimentadores");
  const dist = p.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true });
  await expect(dist.locator('optgroup[label="Distribuidoras"] option')).toHaveCount(Object.keys(m.series).length);
  const codigos = Object.keys(m.series).filter((d) => m.series[d].moderado);
  for (const d of [codigos[0], codigos[Math.floor(codigos.length / 2)], codigos[codigos.length - 1]]) {
    await dist.selectOption(`dist:${d}`);
    const linha = p.getByRole("region", { name: "Tabela anual de histórico e cenários" }).getByRole("row", { name: /^2030/ });
    for (const c of ["conservador", "moderado", "agressivo"] as const) {
      const v = m.series[d][c];
      if (v) await expect(linha).toContainText(v[4].toLocaleString("pt-BR", { maximumFractionDigits: 0 }));
    }
  }
});

test("auditoria: CSV do painel principal reproduz histórico, cenários publicados e completude do produto", async ({ page, request }) => {
  const dados = (await (await request.get("/data/previsoes/cenarios-motor.json")).json()) as Produto;
  const m = dados.metricas.find((x) => x.conceito === "rede_bt" && x.metrica === "extensao_km")!;
  const d = Object.keys(m.series).find((x) => m.series[x].moderado && m.series[x].hist.length === 4)!;
  await page.goto("/previsoes/");
  const p = principal(page);
  await p.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("rede_bt");
  await p.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).selectOption(`dist:${d}`);
  const csv = await baixar(p.getByRole("link", { name: "Exportar série e cenários (CSV)" }), page);
  const [cab, ...linhas] = csv.trim().split(/\r?\n/).map((l) => l.split(","));
  expect(linhas).toHaveLength(9);
  expect(cab).toContain("completude_cenarios");
  const s = m.series[d];
  s.hist.forEach(([ano, v], i) => { expect(Number(linhas[i][0])).toBe(ano); expect(Number(linhas[i][2])).toBeCloseTo(v, 6); expect(linhas[i][1]).toBe("observado"); });
  (["conservador", "moderado", "agressivo"] as const).forEach((c, k) => {
    for (let i = 0; i < 5; i += 1) {
      const v = linhas[4 + i][3 + k];
      if (s[c]) expect(Number(v)).toBeCloseTo(s[c]![i], 6); else expect(v).toBe("");
    }
  });
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

test("auditoria: gráfico do painel principal não corta rótulos de grandes estoques", async ({ page, request }) => {
  const dados = (await (await request.get("/data/previsoes/cenarios-motor.json")).json()) as Produto;
  const m = dados.metricas.find((x) => x.conceito === "consumidores" && x.metrica === "quantidade")!;
  const maior = Object.entries(m.series).filter(([, x]) => x.moderado).sort((a, b) => b[1].moderado![4] - a[1].moderado![4])[0][0];
  await page.goto("/previsoes/");
  const p = principal(page);
  await p.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("consumidores");
  await p.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).selectOption(`dist:${maior}`);
  const grafico = p.getByTestId("cenarios-grafico");
  await expect.poll(async () => grafico.locator("svg text").count()).toBeGreaterThan(0);
  // ECharts posiciona os textos por transform: a verificação usa a geometria na tela (cada rótulo dentro da caixa do gráfico)
  const fora = await grafico.evaluate((el) => {
    const c = el.getBoundingClientRect();
    return [...el.querySelectorAll("svg text")].map((t) => ({ texto: t.textContent, r: t.getBoundingClientRect() }))
      .filter(({ r }) => r.width > 0 && (r.left < c.left - 1 || r.right > c.right + 1)).map(({ texto }) => texto);
  });
  expect(fora).toEqual([]);
});

test("auditoria: falha do arquivo de cenários é explícita e não produz zero", async ({ page }) => {
  await page.route("**/data/previsoes/cenarios-motor.json", (r) => r.fulfill({ status: 503, body: "Indisponível" }));
  await page.goto("/previsoes/");
  await expect(principal(page).getByRole("alert")).toContainText("Não foi possível carregar os cenários do motor");
  await expect(principal(page).getByRole("button", { name: "Tentar novamente" })).toBeVisible();
  await expect(principal(page).getByRole("link", { name: /Exportar série/ })).toHaveCount(0);
  await expect(principal(page).getByRole("region", { name: "Tabela anual de histórico e cenários" })).toHaveCount(0);
});

for (const tema of ["light", "dark"] as const) {
  test(`@mobile auditoria visual e teclado: 320, 390 e 768 px, tema ${tema}`, async ({ page }, testInfo) => {
    await page.emulateMedia({ colorScheme: tema, reducedMotion: "reduce" });
    const erros: string[] = [];
    page.on("pageerror", (e) => erros.push(e.message));
    for (const largura of [320, 390, 768]) {
      await page.setViewportSize({ width: largura, height: 844 });
      await page.goto("/previsoes/");
      await expect(principal(page).getByRole("radiogroup", { name: "Cenário" })).toBeVisible();
      await expect(page.getByRole("region", { name: "Explorar cenários 2026–2030" })).toHaveCount(0);
      await expect(page.getByRole("heading", { name: "Motor de Expansão Elétrica", exact: true })).toHaveCount(1);
      expect(await page.getByRole("main").count()).toBe(1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
      if (largura === 390) await page.screenshot({ path: testInfo.outputPath(`viewport-${tema}-390.png`), scale: "css" });
      const tabela = principal(page).getByRole("region", { name: "Tabela anual de histórico e cenários" });
      await tabela.focus();
      await expect(tabela).toBeFocused();
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
