import { expect, test, type Locator, type Page } from "@playwright/test";

/** Correções finais da RC 1.0, no produto servido: completude coerente dos cenários (cards, gráfico, tabela, CSV),
 *  contagens sempre inteiras e lateral sem informação técnica. O mapa × tema tem spec própria (mapa-tema.spec.ts). */

const csvDe = async (link: Locator) => decodeURIComponent((await link.getAttribute("href"))!.split(",").slice(1).join(","));
const vis = (page: Page, id: string) => page.getByTestId(id).filter({ visible: true });

test.describe("cenários do produto público: completude coerente em cards, gráfico, tabela e CSV", () => {
  test("Transformadores de distribuição (quantidade): só o Moderado, declarado como previsão parcial com motivo", async ({ page, request }) => {
    const dados = await (await request.get("/data/previsoes/cenarios-motor.json")).json();
    const m = dados.metricas.find((x: { conceito: string; metrica: string }) => x.conceito === "trafo_dist" && x.metrica === "quantidade");
    await page.goto("/previsoes/");
    const sec = page.getByTestId("cenarios-motor");
    await sec.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("trafo_dist");
    await sec.getByRole("combobox", { name: "Métrica", exact: true }).selectOption("quantidade");
    await sec.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).selectOption("dist:7019");
    const comp = sec.getByTestId("cenarios-completude");
    await expect(comp).toHaveAttribute("data-completude", "PARCIAL");
    await expect(comp).toHaveAttribute("data-publicados", "moderado");
    await expect(comp).toContainText("Previsão parcial");
    await expect(comp).toContainText("1 de 3 cenários publicados (Moderado)");
    await expect(comp).toContainText("Conservador não publicado");
    await expect(comp).toContainText("Agressivo não publicado");
    const radios = sec.getByRole("radiogroup", { name: "Cenário" }).getByRole("radio");
    await expect(radios.nth(0)).toBeDisabled(); await expect(radios.nth(2)).toBeDisabled(); await expect(radios.nth(1)).toBeEnabled();
    await expect(radios.nth(0)).toContainText("Não publicado neste recorte");
    await expect(sec.getByText(/Comparar os \d cenários publicados/)).toHaveCount(0);     // nada a comparar com um cenário só
    const tabela = sec.getByRole("region", { name: "Tabela anual de histórico e cenários" });
    await expect(tabela.locator("thead th")).toHaveText(["Ano", "Natureza", "Moderado", /^Variação vs 2025/]);
    await expect(tabela.locator("caption")).toContainText("Previsão parcial · 1 de 3 cenários publicados");
    await expect(tabela.getByText("Indisponível")).toHaveCount(0);
    const v2030 = m.series["7019"].moderado[4].toLocaleString("pt-BR", { maximumFractionDigits: 0 });
    await expect(tabela.getByRole("row", { name: /^2030/ })).toContainText(v2030);
    await expect(sec.getByTestId("cenarios-grafico")).toHaveAttribute("aria-label", /Previsão parcial/);
    const csv = await csvDe(sec.getByRole("link", { name: "Exportar série e cenários (CSV)" }));
    const [cab, ...linhas] = csv.trim().split("\n");
    expect(cab).toBe(`ano,natureza,observado,conservador_nao_publicado,moderado_${m.cenarios.moderado},agressivo_nao_publicado,completude_cenarios,cenarios_publicados`);
    for (const l of linhas) expect(l.endsWith(",PARCIAL,moderado")).toBe(true);
    for (const l of linhas.filter((x) => x.includes("simulacao_condicional"))) { const v = l.split(","); expect([v[3], v[5]]).toEqual(["", ""]); expect(v[4]).toMatch(/^\d+$/); }
  });

  test("série com os três cenários aparece COMPLETA, com as três colunas e o CSV igual ao produto", async ({ page, request }) => {
    const dados = await (await request.get("/data/previsoes/cenarios-motor.json")).json();
    const m = dados.metricas.find((x: { conceito: string; metrica: string }) => x.conceito === "rede_mt" && x.metrica === "extensao_km");
    await page.goto("/previsoes/");
    const sec = page.getByTestId("cenarios-motor");
    await sec.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("rede_mt");
    await sec.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).selectOption("dist:7019");
    await expect(sec.getByTestId("cenarios-completude")).toHaveAttribute("data-completude", "COMPLETA");
    const tabela = sec.getByRole("region", { name: "Tabela anual de histórico e cenários" });
    await expect(tabela.locator("thead th")).toHaveText(["Ano", "Natureza", "Conservador", "Moderado", "Agressivo", /^Variação/]);
    const csv = await csvDe(sec.getByRole("link", { name: "Exportar série e cenários (CSV)" }));
    const l2030 = csv.split("\n").find((l) => l.startsWith("2030,"))!.split(",");
    expect(l2030.slice(3, 6).map(Number)).toEqual(["conservador", "moderado", "agressivo"].map((c) => m.series["7019"][c][4]));
  });

  test("extremo sem Moderado não é exibido: série bloqueada como cenários incompletos, sem números de projeção", async ({ page }) => {
    await page.goto("/previsoes/");
    const sec = page.getByTestId("cenarios-motor");
    await sec.getByRole("combobox", { name: "Ativo", exact: true }).selectOption("chaves");
    await sec.getByRole("combobox", { name: "Distribuidora ou grupo", exact: true }).selectOption("dist:6072");
    await expect(sec.getByTestId("cenarios-completude")).toHaveAttribute("data-completude", "SEM_PREVISAO");
    await expect(sec.getByTestId("cenarios-vazio")).toContainText("Cenários incompletos: previsão não publicada");
    await expect(sec.getByTestId("cenarios-completude")).toContainText("um extremo nunca é publicado sozinho");
    await expect(sec.getByRole("region", { name: "Tabela anual de histórico e cenários" })).toHaveCount(0);
    for (const r of await sec.getByRole("radiogroup", { name: "Cenário" }).getByRole("radio").all()) await expect(r).toBeDisabled();
  });
});

test.describe("Motor V2 (homologação): previsão parcial explícita e contagem nacional", () => {
  test("série com extremo bloqueado: faixa PARCIAL, card desativado, tabela só com os publicados e CSV com a completude", async ({ page, request }) => {
    const d = await (await request.get("/data/motor-v2/distribuidoras/5697.json")).json();
    const s = d.series.find((x: { objetivo: string; metrica: string }) => x.objetivo === "medidores" && x.metrica === "quantidade");
    expect(s.completude_cenarios).toMatchObject({ estado: "PARCIAL", publicados: ["Conservador", "Moderado"] });
    await page.goto("/previsoes/");
    const sec = vis(page, "motor-v2");
    await sec.getByLabel("Distribuidora ou grupo do Motor V2").selectOption("dist:5697");
    await sec.getByLabel("Ativo e métrica do Motor V2").selectOption("medidores|quantidade");
    const comp = sec.getByTestId("motor-v2-completude");
    await expect(comp).toHaveAttribute("data-completude", "PARCIAL");
    await expect(comp).toContainText("2 de 3 cenários publicados (Conservador, Moderado)");
    await expect(comp).toContainText("Agressivo não publicado");
    await expect(sec.getByRole("radio", { name: /Agressivo/ })).toBeDisabled();
    await sec.getByRole("radio", { name: /Conservador/ }).click();
    await expect(sec.getByRole("radio", { name: /Conservador/ })).toHaveAttribute("aria-checked", "true");
    const tabela = sec.getByTestId("motor-v2-tabela");
    await expect(tabela).toHaveAttribute("data-completude", "PARCIAL");
    await expect(tabela.locator("thead th")).toHaveText(["Ano", "Natureza", "Conservador", "Moderado"]);
    const linha = tabela.locator("tr", { has: page.locator('th:text-is("2030")') });
    await expect(linha.locator("td").nth(1)).toHaveText(s.cenarios.Conservador[4].toLocaleString("pt-BR"));
    await expect(linha.locator("td").nth(2)).toHaveText(s.cenarios.Moderado[4].toLocaleString("pt-BR"));
    await expect(sec.getByTestId("motor-v2-grafico")).toHaveAttribute("aria-label", /Previsão parcial/);
    const csv = await csvDe(sec.getByTestId("motor-v2-csv"));
    const linhas = csv.trim().split("\n").slice(1).map((l) => l.split(";"));
    for (const l of linhas) expect(l[6]).toBe("PARCIAL");
    for (const l of linhas.filter((x) => x[9] === "Agressivo")) { expect(l[10]).toBe(""); expect(l[12]).toBe("BLOQUEADO"); }
    for (const l of linhas.filter((x) => x[8] === "projecao" && x[10] !== "")) expect(l[10]).toMatch(/^\d+$/);
  });

  test("cobertura nacional mostra quantas séries têm três cenários, quantas são parciais e quantas bloqueadas", async ({ page, request }) => {
    const ix = await (await request.get("/data/motor-v2/indice.json")).json();
    const o = ix.objetivos.find((x: { objetivo: string; metrica: string }) => x.objetivo === "consumidores" && x.metrica === "quantidade");
    await page.goto("/previsoes/");
    const c = vis(page, "motor-v2-completude-nacional");
    await expect(c).toContainText(`${o.completude_cenarios.COMPLETA} com os três cenários`);
    await expect(c).toContainText(`${o.completude_cenarios.PARCIAL} parciais`);
  });
});

test("Motor V2: total nacional mostra o Moderado; extremos rotulados como soma de extremos individuais, com alerta em geradores", async ({ page, request }) => {
  const ix = await (await request.get("/data/motor-v2/indice.json")).json();
  const o = ix.objetivos.find((x: { objetivo: string; metrica: string }) => x.objetivo === "geradores" && x.metrica === "quantidade");
  expect(o.agregado_extremos.agressivo_acima_do_observado).toBe(true);
  await page.goto("/previsoes/");
  const sec = vis(page, "motor-v2");
  await sec.getByLabel("Ativo e métrica do Motor V2").selectOption("geradores|quantidade");
  const ag = sec.getByTestId("motor-v2-agregado-extremos");
  await expect(ag).toHaveAttribute("data-alerta", "true");
  await expect(ag).toContainText("Soma dos extremos individuais (não é cenário nacional)");
  await expect(ag).toContainText(o.total_2030.Agressivo.toLocaleString("pt-BR"));
  await expect(sec.getByTestId("motor-v2-agregado-alerta")).toContainText("supera o maior crescimento nacional observado");
  await expect(sec.getByTestId("motor-v2-cobertura")).toContainText(`Moderado ${o.total_2030.Moderado.toLocaleString("pt-BR")}`);
});

test.describe("contagens físicas sempre inteiras na interface", () => {
  test("Evolução de uma contagem pequena (1 → 2 subestações): eixo e tabela sem decimais", async ({ page }) => {
    await page.goto("/evolucao/?escopo=dists&dists=95&ativo=subestacoes");
    const serie = page.getByRole("region", { name: "Série temporal" }).or(page.locator('section[aria-label="Série temporal"]')).first();
    await expect(serie.locator("svg").first()).toBeVisible();
    await expect.poll(async () => (await serie.locator("svg text").allTextContents()).filter((t) => /^\d+$/.test(t.trim())).length).toBeGreaterThan(0);
    const textos = await serie.locator("svg text").allTextContents();
    expect(textos.filter((t) => /^\d+,\d+$/.test(t.trim()))).toEqual([]);                 // nenhuma marca 1,2 · 1,5 · 12,5
    const tabela = await page.getByRole("region", { name: "Tabela da série" }).innerText();
    expect(tabela).not.toMatch(/\b\d+,\d+\s*(itens)?\b(?!\s*%)/);
  });

  test("Explorar e Panorama: contagens de destaque sem notação compacta fracionária (\"12,5 mil\")", async ({ page }) => {
    for (const p of ["/", "/explorar/?item=consumidores"]) {
      await page.goto(p);
      await page.waitForLoadState("networkidle");
      const txt = await page.locator("main").filter({ visible: true }).first().innerText();
      expect(txt, p).not.toMatch(/\d+,\d+\s*(mil|mi)\b(?!\s*(km|kVA|MVA))/);
    }
  });
});

test.describe("lateral sem informação técnica", () => {
  for (const [tag, nome] of [["", "desktop"], [" @mobile", "mobile"]] as const) {
    test(`navegação principal sem data-base, GDBs processados nem publicações não localizadas — ${nome}${tag}`, async ({ page }) => {
      for (const p of ["/", "/previsoes/", "/metodologia/"]) {
        await page.goto(p);
        const lateral = page.locator('aside[aria-label="Navegação principal"]');
        await expect(lateral).toHaveCount(1);
        const t = await lateral.evaluate((el) => el.textContent ?? "");
        expect(t).not.toMatch(/Data-base|GDBs processados|não localizadas|31\/12\/2025/);
        expect(t).toContain("Desenvolvido por");
      }
      if (tag) {
        await page.getByRole("button", { name: "Mais", exact: true }).click();
        await expect(page.getByRole("dialog", { name: "Mais opções" })).not.toContainText(/GDBs processados|não localizadas/);
      }
    });
  }

  test("a informação de auditoria continua disponível em Metodologia e qualidade", async ({ page }) => {
    await page.goto("/metodologia/");
    await expect(vis(page, "metodologia-gdbs")).toContainText(/\d+ GDBs processados · \d+ publicações 2025 não localizadas/);
  });
});
