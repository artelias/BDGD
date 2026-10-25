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

test.describe("R3 — Matriz Nacional por ativo", () => {
  test("sem controles globais de medida; colunas por ativo com unidade própria", async ({ page }) => {
    await page.goto("/matriz/");
    await expect(page.getByRole("heading", { name: "Matriz Nacional" })).toBeVisible();
    await expect(page.getByRole("radiogroup", { name: "Medida" })).toHaveCount(0);
    const t = page.getByTestId("matriz-tabela");
    await expect(t.getByRole("button", { name: /^Transformadores de distribuição/ })).toBeVisible();
    await expect(t.getByRole("button", { name: /^Área de atuação/ })).toHaveCount(0);
  });

  test("filtro dentro da coluna = mesmo recorte do Explorar", async ({ page }) => {
    await page.goto("/matriz/?ativos=religadores&cf=religadores~area:NU&dists=4950");
    await expect(page.getByTestId("total-religadores")).not.toHaveText(/N\/D/);
    const m = num(await page.getByTestId("total-religadores").innerText());
    await page.goto("/explorar/?ativo=religadores&escopo=dists&dists=4950&f=area:NU");
    expect(await valor(page)).toBe(m);
  });

  test("filtro pela interface marca a coluna e aparece nos chips; CSV traz recorte", async ({ page }) => {
    await page.goto("/matriz/?ativos=trafo_dist,consumidores");
    await page.getByTestId("filtro-col-trafo_dist").click();
    await page.getByTestId("col-filtro-area").click();
    await page.getByRole("button", { name: /Urbano/ }).first().click();
    await expect.poll(() => decodeURIComponent(page.url())).toContain("cf=trafo_dist~area:");
    await expect(page.getByTestId("matriz-chips")).toContainText("Transformadores de distribuição");
    await page.keyboard.press("Escape");
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("matriz-csv").click()]);
    const txt = Buffer.concat(await (await dl.createReadStream()).toArray()).toString("utf-8");
    expect(txt.split(/\r?\n/)[0].replace(/^﻿/, "")).toBe("data_base,versao,dist,sigla,grupo_economico,grupo_status,ativo,nome_ativo,medida,unidade,recorte,valor,status,motivo,regra");
    expect(txt).toContain("area:");
  });

  test("medida alternativa por coluna (potência)", async ({ page }) => {
    await page.goto("/matriz/?ativos=trafo_dist&cm=trafo_dist~potencia_kva");
    await expect(page.getByTestId("matriz-tabela")).toContainText("kVA");
  });
});

test.describe("R3 — Comparador com abas e filtros compartilhados", () => {
  test("três abas alternativas; só a selecionada é renderizada", async ({ page }) => {
    await page.goto("/comparar/");
    await expect(page.getByTestId("comparar-tabela")).toBeVisible();
    await expect(page.getByTestId("radar")).toHaveCount(0);
    await page.getByRole("radio", { name: "Gráficos" }).click();
    await expect(page.getByTestId("chart-comparacao")).toBeVisible();
    await expect(page.getByTestId("comparar-tabela")).toHaveCount(0);
    await page.getByRole("radio", { name: "Valores A × B" }).click();
    await expect(page.getByTestId("chart-espelhado")).toBeVisible();
    await page.getByRole("radio", { name: "Radar" }).click();
    await expect(page.getByTestId("radar-tabela")).toBeVisible();
    await expect(page).toHaveURL(/aba=radar/);
  });

  test("o mesmo recorte vale para A e B: A = valor do Explorar no grupo", async ({ page }) => {
    await page.goto("/comparar/?a=grupo:energisa&b=grupo:equatorial&ativo=religadores&f=area:NU");
    const linhaTotal = page.getByTestId("comparar-tabela").locator("tbody tr").first();
    const a = num(await linhaTotal.locator("td").nth(2).innerText());
    await page.goto("/explorar/?ativo=religadores&escopo=grupo:energisa&f=area:NU");
    expect(await valor(page)).toBe(a);
  });

  test("benchmark recalculado após o filtro (acima de 100% permitido)", async ({ page }) => {
    await page.goto("/comparar/?a=grupo:energisa&b=grupo:equatorial&ativo=transformadores&f=area:NU&aba=radar&ref=bench_dists");
    await expect(page.getByTestId("radar-tabela")).toBeVisible();
    const sem = await page.locator('[data-testid^="radar-pct-"]').allInnerTexts();
    await page.goto("/comparar/?a=grupo:energisa&b=grupo:equatorial&ativo=transformadores&aba=radar&ref=bench_dists");
    const com = await page.locator('[data-testid^="radar-pct-"]').allInnerTexts();
    expect(sem.join()).not.toBe(com.join());
    expect(sem.some((x) => num(x) > 100)).toBeTruthy();
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("radar-csv").click()]);
    expect(dl.suggestedFilename()).toContain("radar");
  });
});

test.describe("R3 — Evolução histórica 2022–2025", () => {
  test("três modos de escopo, situação por ano e nenhum ano preenchido artificialmente", async ({ page }) => {
    await page.goto("/evolucao/");
    await expect(page.getByTestId("anos")).toContainText("31/12/2022");
    await expect(page.getByTestId("anos")).toContainText("homologado");
    for (const m of ["Brasil", "Grupo", "Distribuidoras"]) await expect(page.getByRole("radio", { name: m, exact: true }).first()).toBeVisible();
    await expect(page.getByTestId("evo-tabela")).toBeVisible();
    // células de anos não validados aparecem como N/D, nunca como zero
    const cells = await page.getByTestId("evo-tabela").locator("tbody td").allInnerTexts();
    expect(cells.some((c) => c.trim() === "0")).toBeFalsy();
  });

  test("multi-distribuidoras: uma linha por distribuidora e CSV com estado de cada ano", async ({ page }) => {
    await page.goto("/evolucao/?escopo=dists&dists=26,31&ativo=consumidores");
    await expect(page.getByTestId("evo-tabela").locator("tbody tr")).toHaveCount(2);
    await expect(page.getByTestId("chart-linhas")).toBeVisible();
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("evo-csv").click()]);
    const txt = Buffer.concat(await (await dl.createReadStream()).toArray()).toString("utf-8");
    expect(txt).toContain("estado");
    expect(txt).toMatch(/validado|em andamento|sem publicação/);
  });

  test("grupo usa composição de 2025 e mapa de calor como alternativa", async ({ page }) => {
    await page.goto("/evolucao/?escopo=grupo:energisa&ativo=rede_mt&layout=calor");
    await expect(page.getByTestId("evo-tabela")).toContainText("composição de 2025");
    await page.getByRole("radio", { name: "Perímetro de 2025" }).click();
    await expect(page.getByTestId("sucessoes")).toContainText("Energisa Borborema");
  });
});
