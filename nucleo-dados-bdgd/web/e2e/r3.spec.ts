import { expect, test, type Page } from "@playwright/test";

const num = (s: string) => Number(s.replace(/[^\d,]/g, "").replace(",", "."));
async function valor(page: Page) { return num(await page.getByTestId("valor-recorte").innerText()); }

test.describe("R3 — Explorar ativos por conceito", () => {
  test("clicar no conceito abre a visão consolidada, sem escolher tabela, com TUC descobertos", async ({ page }) => {
    await page.goto("/explorar/");
    await page.getByTestId("menu-transformadores").click();
    await expect(page.getByTestId("conceito-titulo")).toHaveText("Transformadores");
    await expect(page.getByTestId("cartao-565")).toContainText("distribuição");
    await expect(page.getByTestId("cartao-570")).toContainText("força");
    await expect(page.getByTestId("cartao-575")).toContainText("medida");
    await expect(page.getByTestId("onde-instalados")).toContainText("não são somadas");
    await expect(page.getByTestId("tabela-categorias")).toBeVisible();
  });

  test("cartão TUC 570 e potência: quantidade e potência em medidas separadas", async ({ page }) => {
    await page.goto("/explorar/?ativo=transformadores");
    await page.getByTestId("cartao-570").click();
    await expect(page).toHaveURL(/c=570/);
    const q = await valor(page);
    expect(q).toBeGreaterThan(1000);
    await page.getByRole("radio", { name: "Potência", exact: true }).click();
    await expect(page.getByTestId("valor-recorte")).toContainText("kVA");
  });

  test("participação dupla com denominadores distintos (grupo)", async ({ page }) => {
    await page.goto("/explorar/?ativo=religadores&escopo=grupo:energisa&f=area:NU");
    const pe = num(await page.getByTestId("part-escopo").innerText());
    const pb = num(await page.getByTestId("part-brasil").innerText());
    expect(pe).toBeGreaterThan(0); expect(pe).toBeLessThanOrEqual(100);
    expect(pb).toBeGreaterThan(0); expect(pb).toBeLessThan(100);
    expect(pe).not.toBe(pb);
  });

  test("mesmo recorte: valor do Explorar = soma dos totais por distribuidora do grupo", async ({ page }) => {
    await page.goto("/explorar/?ativo=chaves&escopo=grupo:cemig");
    const g = await valor(page);
    await page.goto("/explorar/?ativo=chaves&escopo=dists&dists=4950");
    expect(await valor(page)).toBe(g);
  });

  test("todos os conceitos do menu abrem", async ({ page }) => {
    await page.goto("/explorar/");
    await expect(page.getByTestId("menu-consumidores")).toBeVisible();
    const itens = await page.locator('[data-testid^="menu-"]').evaluateAll((els) => els.map((e) => e.getAttribute("data-testid")!).filter((x) => x !== "menu-mobile"));
    expect(itens.length).toBeGreaterThan(18);
    for (const id of itens) {
      await page.getByTestId(id).click();
      await expect(page.getByTestId("conceito-titulo")).toBeVisible();
      await expect(page.getByText("Conceito indisponível")).toHaveCount(0);
    }
  });

  test("inventário: subestação com ativos associados e CSV", async ({ page }) => {
    await page.goto("/explorar/?ativo=subestacoes&escopo=dists&dists=31");
    await expect(page.getByTestId("inv-tabela")).toBeVisible();
    await page.getByTestId("inv-tabela").locator("tbody tr").first().click();
    await expect(page.getByTestId("inv-detalhe")).toContainText("Alimentadores");
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("inv-csv").click()]);
    expect(dl.suggestedFilename()).toBe("bdgd_2025-12-31_inventario_sub_31.csv");
  });

  test("filtro sem cubo conjunto fica indisponível (município + fases)", async ({ page }) => {
    await page.goto("/explorar/?ativo=consumidores&f=municipio:3550308");
    await expect(page.getByTestId("valor-recorte")).not.toHaveText("N/D");
    await page.getByTestId("mais-caracteristicas").click().catch(() => {});
    await expect(page.locator('[data-testid="filtro-fases"]')).toHaveCount(1);
    const pe = await page.locator('[data-testid="filtro-fases"]').evaluate((el) => getComputedStyle(el.parentElement!).pointerEvents);
    expect(pe).toBe("none");
  });

  test("visão técnica por entidade preserva os cubos DDA do R2 (modo avançado)", async ({ page }) => {
    await page.goto("/explorar/?ativo=consumidores");
    await page.getByTestId("modo-avancado").click();
    await page.getByTestId("abrir-tecnico").click();
    await expect(page.getByTestId("visao-tecnica")).toBeVisible();
    await page.getByTestId("attr-ARE_LOC").click();
    await expect(page.getByTestId("chart-categorias").last()).toBeVisible();
  });

  test("CSV do Explorar traz recorte, unidade e fonte", async ({ page }) => {
    await page.goto("/explorar/?ativo=redes&escopo=grupo:equatorial");
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("explorar-csv").click()]);
    const txt = Buffer.concat(await (await dl.createReadStream()).toArray()).toString("utf-8");
    expect(txt.split(/\r?\n/)[0]).toContain("data_base,versao,ativo,escopo,distribuidoras,recorte,dimensao,codigo,categoria,medida,unidade,valor");
    expect(txt).toContain("extensao_km,km");
  });
});
