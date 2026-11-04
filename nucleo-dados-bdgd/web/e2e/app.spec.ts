import { expect, test } from "@playwright/test";

test.describe("Núcleo de Dados da BDGD — 2025-12-31", () => {
  test("pacote publicado é somente 2025-12-31", async ({ request }) => {
    const r = await request.get("/data/2025-12-31/index.json");
    expect(r.ok()).toBeTruthy();
    const j = await r.json();
    expect(j.release.data_base).toBe("2025-12-31");
    const cols = JSON.stringify(Object.keys(j.distribuidoras[0])) + JSON.stringify(j.fatos.cols);
    expect(cols).not.toMatch(/(^|[^_])cod_id"/i);
  });

  test("panorama: mapa ARAT, KPIs e seleção de distribuidora", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Panorama Brasil" })).toBeVisible();
    await expect(page.getByTestId("map-ready")).toHaveAttribute("data-ready", "true", { timeout: 60_000 });
    await expect(page.locator("canvas.maplibregl-canvas")).toBeVisible();
    // regressão: o contêiner do mapa precisa ocupar o palco (ordem de CSS em produção)
    expect(await page.locator("canvas.maplibregl-canvas").evaluate((c) => c.clientHeight)).toBeGreaterThan(400);
    await expect(page.getByTestId("kpi-ssdmt").locator("..")).not.toContainText("Subtotal observado");
    await expect(page.getByRole("heading", { name: /Brasil · cobertura parcial/ })).toBeVisible();
    await page.getByTestId("panel-search").fill("CEA");
    await page.getByTestId("dist-31").click();
    await expect(page).toHaveURL(/dist=31/);
    await expect(page.getByTestId("dist-title")).toHaveText(/CEA Equatorial/);
    await page.getByTestId("panel-back").click();
    await expect(page).not.toHaveURL(/dist=/);
  });

  test("panorama: legenda de grupo filtra o recorte", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Energisa", exact: true }).first().click();
    await expect(page).toHaveURL(/grupo=energisa/);
    await expect(page.getByRole("heading", { name: "Energisa", level: 2 })).toBeVisible();
  });

  test("matriz: recorte por coluna aplicado e exportado sem alterar os dados", async ({ page }) => {
    await page.goto("/matriz/?ativos=trafo_dist,consumidores");
    const table = page.getByTestId("matriz-tabela");
    await expect(table).toBeVisible();
    await page.getByTestId("filtro-col-trafo_dist").click();
    await page.getByTestId("col-filtro-area").click();
    await page.getByRole("button", { name: /Urbano/ }).first().click();
    await expect.poll(() => decodeURIComponent(page.url())).toContain("cf=trafo_dist~area:");
    await expect(page.getByTestId("matriz-chips")).toContainText("Transformadores de distribuição");
    await page.keyboard.press("Escape");
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("matriz-csv").click()]);
    expect(dl.suggestedFilename()).toMatch(/\.csv$/);
  });
  test("comparador: troca A/B e exporta", async ({ page }) => {
    await page.goto("/comparar/?a=grupo:energisa&b=grupo:equatorial");
    await expect(page.getByTestId("comparar-tabela")).toBeVisible();
    await page.getByTestId("trocar").click();
    await expect(page).toHaveURL(/a=grupo(%3A|:)equatorial/);
    await expect(page).toHaveURL(/b=grupo(%3A|:)energisa/);
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("comparar-csv").click()]);
    expect(dl.suggestedFilename()).toContain("2025-12-31_comparacao");
  });

  test("comparador: seletor de grupo expande sem sobrepor os filtros", async ({ page }) => {
    await page.goto("/comparar/?a=grupo:energisa&b=grupo:equatorial");
    await page.getByTestId("picker-a").click();
    const lista = page.getByRole("listbox", { name: "Grupo econômico verificado" }).first();
    await expect(lista).toBeVisible();
    const menu = await lista.boundingBox();
    const filtros = await page.getByRole("toolbar", { name: "Ativo e recorte" }).boundingBox();
    expect(menu).not.toBeNull();
    expect(filtros).not.toBeNull();
    expect(menu!.y + menu!.height).toBeLessThanOrEqual(filtros!.y + 2);
    await lista.getByRole("option", { name: /Neoenergia/ }).click();
    await expect(page).toHaveURL(/a=grupo(%3A|:)neoenergia/);
  });

  test("entidades e DDA: modo técnico preserva facetas de UCBT", async ({ page }) => {
    await page.goto("/explorar/?ativo=consumidores");
    await expect(page.getByTestId("conceito-titulo")).toHaveText("Consumidores");
    await page.getByTestId("modo-avancado").click();
    await page.getByTestId("abrir-tecnico").click();
    await expect(page.getByTestId("visao-tecnica")).toBeVisible();
    await page.getByTestId("attr-ARE_LOC").click();
    await expect(page.getByTestId("chart-categorias").last()).toBeVisible();
  });
  test("R2 panorama: clicar de novo desmarca, Ver Brasil limpa e ranking expande", async ({ page }) => {
    await page.goto("/?dist=31");
    await expect(page.getByTestId("dist-title")).toHaveText(/CEA Equatorial/);
    const bar = page.getByRole("button", { name: /CEA Equatorial/ }).last();
    await page.getByTestId("ranking-toggle").click();
    await expect(page.getByTestId("ranking-status")).toContainText("Mostrando 99 de 99");
    await page.getByTestId("ranking-list").getByRole("button", { name: /CEA Equatorial/ }).click();
    await expect(page).not.toHaveURL(/dist=/);
    await page.getByTestId("ranking-toggle").click();
    await expect(page.getByTestId("ranking-status")).toContainText("Mostrando 12 de 99");
    void bar;
    await page.goto("/?grupo=energisa&dist=26");
    await expect(page.getByTestId("ver-brasil")).toBeVisible();
    await page.getByTestId("ver-brasil").click();
    await expect(page).not.toHaveURL(/dist=|grupo=/);
  });

  test("R3 panorama: dez KPIs, cálculo explicado e total nacional não parcial", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("kpi-uc")).toBeVisible();
    const over = await page.locator('[data-testid^="kpi-"]').evaluateAll((els) => els.map((e) => e.parentElement!).filter((k) => k.scrollWidth > k.clientWidth + 1).length);
    expect(over).toBe(0);
    await page.getByTestId("explain-ssdmt").click();
    await expect(page.getByRole("dialog", { name: /Rede de média tensão/ })).toBeVisible();
    await page.getByRole("button", { name: "Ver cálculo técnico" }).click();
    await expect(page.getByRole("dialog", { name: /Rede de média tensão/ })).toContainText("COMP");
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="kpi-uc"]').locator("..")).not.toContainText("Subtotal observado");
    await expect(page.locator('button[data-testid^="kpi-"]:not([data-testid="kpi-picker"])')).toHaveCount(10);
    await expect(page.getByTestId("kpi-trdist565")).toBeVisible();
    await expect(page.getByTestId("kpi-trforca570")).toBeVisible();
    await page.getByTestId("kpi-picker").click();
    await page.getByRole("button", { name: "Redes", exact: true }).click();
    await expect(page.getByTestId("kpi-ssdat")).toBeVisible();
  });

  test("R2 rodapé: autoria e contato", async ({ page }) => {
    await page.goto("/metodologia/");
    await expect(page.getByTestId("autoria")).toContainText("Desenvolvido por Arthur Henrique Elias de Lima");
    await expect(page.getByTestId("contato")).toHaveAttribute("href", "mailto:Arthur.henrique.elias@gmail.com");
    await expect(page.locator("footer")).not.toContainText("Projeto independente");
    await expect(page.locator("footer")).toContainText("ANEEL — BDGD (Dados Abertos)");
    await expect(page.locator("#dicionario")).toBeAttached();
  });

  test("R3 matriz: medida kVA disponível somente para transformadores", async ({ page }) => {
    await page.goto("/matriz/?ativos=trafo_dist&cm=trafo_dist~potencia_kva");
    const table = page.getByTestId("matriz-tabela");
    await expect(table).toBeVisible();
    await expect(table).toContainText("kVA");
    await expect(page.getByRole("radiogroup", { name: "Medida" })).toHaveCount(0);
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("matriz-csv").click()]);
    const stream = await dl.createReadStream();
    const chunks: Buffer[] = [];
    for await (const chunk of stream) chunks.push(Buffer.from(chunk));
    const head = Buffer.concat(chunks).toString("utf8").split(/\r?\n/)[0].replace(/^\uFEFF/, "");
    expect(head).toContain("medida,unidade,recorte,valor,status,motivo,regra");
  });
  test("R3 comparador: barras espelhadas e radar exibidos em abas específicas", async ({ page }) => {
    await page.goto("/comparar/?a=grupo:energisa&b=grupo:equatorial&ativo=transformadores&ref=bench_dists");
    await expect(page.getByTestId("comparar-tabela")).toBeVisible();
    await page.getByRole("radio", { name: "Gráficos" }).click();
    await page.getByRole("radio", { name: "Valores A × B" }).click();
    await expect(page.getByTestId("chart-espelhado")).toBeVisible();
    await page.getByRole("radio", { name: "Radar" }).click();
    await expect(page.getByTestId("radar-tabela")).toBeVisible();
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("radar-csv").click()]);
    expect(dl.suggestedFilename()).toContain("radar");
  });
  test("R3 explorar: TUC 565 filtra transformadores mantendo visões e dimensões", async ({ page }) => {
    await page.goto("/explorar/?ativo=transformadores&escopo=grupo:energisa");
    await expect(page.getByTestId("conceito-titulo")).toHaveText("Transformadores");
    await page.getByTestId("cartao-565").click();
    await expect(page).toHaveURL(/c=565/);
    await expect(page.getByTestId("onde-instalados")).toContainText("não são somadas");
    await expect(page.getByTestId("tabela-categorias")).toBeVisible();
  });
  test("Evolução 2022–2025 exibe histórico real e rastreabilidade", async ({ page }) => {
    await page.goto("/evolucao/?ativo=consumidores");
    await expect(page.getByTestId("evo-tabela")).toBeVisible();
    await expect(page.getByTestId("evo-cards")).toBeVisible();
    await expect(page.getByTestId("evo-tabela")).toContainText("2025");
    await expect(page.getByText("Histórico em preparação.")).toHaveCount(0);
  });

  test("R2 mapa: clique fora das áreas volta ao Brasil", async ({ page }) => {
    await page.goto("/?dist=5697"); // Celesc: litoral de SC, canto inferior direito do quadro é oceano
    await expect(page.getByTestId("map-ready")).toHaveAttribute("data-ready", "true", { timeout: 60_000 });
    await expect(page.getByTestId("dist-title")).toBeVisible();
    await page.waitForTimeout(1500);
    const box = (await page.locator("canvas.maplibregl-canvas").boundingBox())!;
    // Locator.click rola o canvas até o ponto ficar visível; mouse.click usava coordenada fora do viewport.
    await page.locator("canvas.maplibregl-canvas").click({ position: { x: box.width - 60, y: box.height - 40 } }); // oceano
    await expect(page).not.toHaveURL(/dist=/);
  });

  test("tema claro/escuro alterna a cada clique e persiste após navegação e recarga", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/metodologia/");
    await page.evaluate(() => localStorage.setItem("nucleo-bdgd-tema", "system"));
    await page.reload();
    const html = page.locator("html");
    const button = page.getByTestId("theme-toggle");
    await expect(html).toHaveAttribute("data-theme", "light");

    await button.click(); // sistema claro -> escuro, não sistema -> claro
    await expect(html).toHaveAttribute("data-theme", "dark");
    await expect(button).toHaveAttribute("aria-pressed", "true");
    await expect.poll(() => page.evaluate(() => localStorage.getItem("nucleo-bdgd-tema"))).toBe("dark");

    await button.click(); // escuro -> claro, sem estado intermediário
    await expect(html).toHaveAttribute("data-theme", "light");
    await expect(button).toHaveAttribute("aria-pressed", "false");

    await button.click(); // claro -> escuro novamente
    await expect(html).toHaveAttribute("data-theme", "dark");
    await page.reload();
    await expect(html).toHaveAttribute("data-theme", "dark");
    await page.goto("/matriz/");
    await expect(html).toHaveAttribute("data-theme", "dark");
  });

  test("tema alterna na sessão mesmo sem permissão de escrita no storage", async ({ page }) => {
    await page.addInitScript(() => {
      const original = Storage.prototype.setItem;
      Storage.prototype.setItem = function (key: string, value: string) {
        if (key === "nucleo-bdgd-tema") throw new Error("storage indisponível");
        return original.call(this, key, value);
      };
    });
    await page.goto("/metodologia/");
    const html = page.locator("html");
    const button = page.getByTestId("theme-toggle");
    const initial = await html.getAttribute("data-theme");
    const next = initial === "dark" ? "light" : "dark";
    await button.click();
    await expect(html).toHaveAttribute("data-theme", next);
    await button.click();
    await expect(html).toHaveAttribute("data-theme", initial === "dark" ? "dark" : "light");
  });

  test("busca global por teclado abre a distribuidora", async ({ page }) => {
    await page.goto("/matriz/");
    await expect(page.getByTestId("matriz-tabela")).toBeVisible();
    await page.keyboard.press("Control+k");
    await page.getByTestId("search-input").fill("Energisa AC");
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/\?dist=26/);
  });

  test("celular: barra de abas e folha do mapa @mobile", async ({ page }) => {
    await page.goto("/");
    const tabs = page.getByRole("navigation", { name: "Navegação" });
    await expect(tabs).toBeVisible();
    await tabs.getByRole("link", { name: "Matriz" }).click();
    await expect(page).toHaveURL(/\/matriz\//);
    await expect(page.getByTestId("matriz-tabela")).toBeVisible();
  });
});
