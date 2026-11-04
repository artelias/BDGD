import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const paginas = ["/", "/explorar/", "/matriz/", "/comparar/", "/evolucao/", "/previsoes/", "/metodologia/"];
const pronto = (p: Page, rota: string) => rota === "/" ? p.getByTestId("kpi-uc") : rota === "/explorar/" ? p.getByTestId("conceito-titulo")
  : rota === "/matriz/" ? p.getByTestId("matriz-tabela") : rota === "/comparar/" ? p.getByTestId("comparar-tabela")
    : rota === "/evolucao/" ? p.getByTestId("evo-tabela") : rota === "/previsoes/" ? p.getByTestId("cenarios-motor").getByRole("combobox", { name: "Ativo", exact: true }) : p.locator("#regras");

for (const width of [1440, 1024, 901, 900, 768, 390, 320]) for (const theme of ["light", "dark"] as const) {
  test(`homologação responsiva ${width}px ${theme}: sete páginas e breakpoint`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 800 });
    await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
    const erros: string[] = [];
    page.on("pageerror", (e) => erros.push(e.message));
    const medidas = [];
    for (const rota of paginas) {
      await page.goto(rota);
      await expect(pronto(page, rota)).toBeVisible();
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      const side = page.locator('aside[aria-label="Navegação principal"]');
      if (width > 900) {
        await expect(side).toBeVisible();
        expect((await side.boundingBox())!.width).toBe(244);
        await side.getByRole("button", { name: "Recolher navegação" }).click();
        await expect.poll(async () => (await side.boundingBox())!.width).toBe(68);
        await side.getByRole("button", { name: "Expandir navegação" }).click();
        await expect.poll(async () => (await side.boundingBox())!.width).toBe(244);
      } else {
        await expect(side).toBeHidden();
        await expect(page.getByRole("navigation", { name: "Navegação", exact: true })).toBeVisible();
      }
      const box = await page.getByRole("main").boundingBox();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
      expect(overflow, `${rota} em ${width}px`).toBeLessThanOrEqual(1);
      expect(box!.x).toBe(width > 900 ? 244 : 0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width + 1);
      medidas.push({ rota, width, theme, overflow, main: box });
    }
    expect(erros).toEqual([]);
    await info.attach("dimensoes.json", { body: JSON.stringify(medidas), contentType: "application/json" });
  });
}

function csv(text: string): string[][] {
  const rows: string[][] = []; let row: string[] = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') { if (quoted && text[i + 1] === '"') { field += c; i++; } else quoted = !quoted; }
    else if (c === "," && !quoted) { row.push(field); field = ""; }
    else if (c === "\n" && !quoted) { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
    else field += c;
  }
  if (field || row.length) { row.push(field.replace(/\r$/, "")); rows.push(row); }
  return rows;
}

test("Evolução: 12 observações de EPB, Coopera e Enel SP confrontadas ao contrato nacional", async ({ page }) => {
  const records = csv(readFileSync("../output-historico/contrato-integracao/serie_fisica_nacional.csv", "utf8"));
  const header = records.shift()!;
  const col = (name: string) => header.indexOf(name);
  for (const dist of ["6600", "5370", "390"]) {
    const expected = records.filter((r) => r[col("dist")] === dist && r[col("conceitoId")] === "consumidores");
    expect(expected).toHaveLength(4);
    await page.goto(`/evolucao/?escopo=dists&dists=${dist}&ativo=consumidores`);
    const cells = page.getByTestId("evo-tabela").locator("tbody tr").first().locator("td");
    for (const r of expected) {
      const value = r[col("valor")];
      await expect(cells.nth(Number(r[col("ano")]) - 2022)).toContainText(value === "" ? "N/D" : Number(value).toLocaleString("pt-BR"));
    }
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("evo-csv").click()]);
    const exported = csv(Buffer.concat(await (await dl.createReadStream()).toArray()).toString("utf8"));
    const keys = exported.shift()!;
    for (const r of expected) {
      const year = r[col("ano")];
      const entry = exported.find((row) => row[keys.indexOf("ano")] === year);
      expect(entry).toBeDefined();
      const value = r[col("valor")];
      expect(entry![keys.indexOf("valor")]).toBe(value === "" ? "" : String(Number(value)));
    }
  }
});

test("homologação matriz: filtros combinados, ordenação e CSV confrontados ao contrato", async ({ page }) => {
  const raw = await (await page.request.get("/data/2025-12-31/index.json")).json();
  type Dist = { dist: number; grupo: string; grupo_status: string; ufs: string[] };
  const dists: Dist[] = raw.distribuidoras;
  const valores = new Map<number, number | null>((raw.ativosTotais.consumidores.quantidade as [number, number | null][]).map(([id, v]) => [id, v]));
  const rows = page.getByTestId("matriz-tabela").locator("tr[data-dist]");
  const verify = async (ids: number[]) => {
    await expect(rows).toHaveCount(ids.length);
    expect((await rows.evaluateAll((els) => els.map((e) => Number(e.getAttribute("data-dist"))))).sort((a, b) => a - b)).toEqual([...ids].sort((a, b) => a - b));
    for (const id of ids) await expect(page.getByTestId("matriz-tabela").locator(`tr[data-dist="${id}"] td`).nth(1)).toHaveText(valores.get(id) == null ? "N/D" : valores.get(id)!.toLocaleString("pt-BR"));
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("matriz-csv").click()]);
    const records = csv(Buffer.concat(await (await dl.createReadStream()).toArray()).toString("utf8").replace(/^\uFEFF/, ""));
    const header = records.shift()!;
    expect(records).toHaveLength(ids.length);
    for (const r of records) {
      const id = Number(r[header.indexOf("dist")]);
      expect(ids).toContain(id);
      expect(r[header.indexOf("valor")]).toBe(valores.get(id) == null ? "" : String(valores.get(id)));
      expect(r[header.indexOf("medida")]).toBe("quantidade");
    }
  };
  await page.goto("/matriz/?ativos=consumidores");
  await verify(dists.map((d) => d.dist));
  await page.getByTestId("matriz-grupo").click();
  await page.getByRole("option", { name: /^Energisa/ }).click();
  const energisa = dists.filter((d) => d.grupo === "energisa" && d.grupo_status === "verificado");
  await verify(energisa.map((d) => d.dist));
  await page.getByTestId("matriz-ufs").click();
  await page.getByRole("dialog", { name: "UF", exact: true }).getByRole("button", { name: /^PB\s/ }).click();
  await page.keyboard.press("Escape");
  await verify(energisa.filter((d) => d.ufs.includes("PB")).map((d) => d.dist));
  await page.reload();
  await verify(energisa.filter((d) => d.ufs.includes("PB")).map((d) => d.dist));
  await page.getByRole("button", { name: "Limpar tudo", exact: true }).click();
  await page.getByTestId("matriz-ativos").click();
  const ativos = page.getByRole("dialog", { name: "Ativos", exact: true });
  await ativos.getByRole("textbox", { name: "Buscar em Ativos" }).fill("Unidades consumidoras");
  await ativos.getByRole("group", { name: "Opções de Ativos" }).getByRole("button").first().click();
  await ativos.getByRole("button", { name: "Salvar como favorito" }).click();
  expect(await page.evaluate(() => localStorage.getItem("bdgd.matriz.ativos.favoritos"))).toBe("consumidores");
  await page.keyboard.press("Escape");
  await page.getByTestId("matriz-dists").click();
  const empresas = page.getByRole("dialog", { name: "Distribuidoras", exact: true });
  for (const id of [6600, 5370]) await empresas.getByRole("button", { name: new RegExp(`DIST ${id}$`) }).click();
  await page.keyboard.press("Escape");
  await verify([6600, 5370]);
  await page.getByTestId("matriz-busca").fill("6600");
  await verify([6600]);
  await page.getByTestId("matriz-busca").fill("inexistente-qa");
  await expect(page.getByTestId("matriz-csv")).toBeDisabled();
  await expect(page.getByRole("status").filter({ hasText: "Nada no recorte" })).toBeVisible();
  await page.getByRole("button", { name: "Limpar", exact: true }).click();
  await verify([6600, 5370]);
  await page.getByRole("button", { name: "Transpor", exact: true }).click();
  await expect(page.getByTestId("matriz-transposta")).toContainText(valores.get(6600)!.toLocaleString("pt-BR"));
  await page.getByRole("button", { name: "Distribuidoras nas colunas", exact: true }).click();
  await page.getByTestId("matriz-dists").click();
  await empresas.getByRole("button", { name: "Limpar (todas)", exact: true }).click();
  await page.keyboard.press("Escape");
  const sort = page.getByTestId("matriz-tabela").locator("thead").getByRole("button", { name: /^Unidades consumidoras/ });
  for (const asc of [false, true]) {
    await sort.click();
    // a ordenação passa pela URL e re-renderiza depois do clique: esperar o estado em vez de ler a tabela de imediato
    await expect(sort.locator("xpath=ancestor::th[1]")).toHaveAttribute("aria-sort", asc ? "ascending" : "descending");
    await expect.poll(async () => {
      const ids = await rows.evaluateAll((els) => els.map((e) => Number(e.getAttribute("data-dist"))));
      const values = ids.map((id) => valores.get(id)).filter((v): v is number => v != null);
      return values.length > 1 && values.every((v, i) => i === 0 || (asc ? values[i - 1] <= v : values[i - 1] >= v));
    }).toBe(true);
  }
});
