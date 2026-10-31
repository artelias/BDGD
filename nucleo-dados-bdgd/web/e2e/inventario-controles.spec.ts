import { test, expect, type Page } from "@playwright/test";

// Inventário de observação. O coletor não aprova controles: a matriz cruza
// os nomes observados com ações e asserções executadas em outros testes.
async function controles(page: Page, state: string) {
  return page.locator('a[href],button,select,input,summary,tr[data-dist],[role="radio"],[role="option"],[role="button"],tr[tabindex="0"],canvas.maplibregl-canvas').evaluateAll((els, state) => {
    return els.filter((e) => e.checkVisibility() && e.getBoundingClientRect().width > 0).map((e) => {
      const text = (node: Element) => (node.textContent ?? "").trim().replace(/\s+/g, " ");
      const label = e.closest("label")?.firstChild?.textContent?.trim();
      const name = e.getAttribute("aria-label") || (e.tagName === "SELECT" ? label : null) || e.getAttribute("title") || e.getAttribute("placeholder") || text(e) || e.getAttribute("data-testid");
      const section = e.closest('section,nav,aside,[role="dialog"],[role="toolbar"],footer,header');
      const labelled = section?.getAttribute("aria-labelledby");
      return { state, component: section?.getAttribute("aria-label") || (labelled && document.getElementById(labelled)?.textContent) || section?.getAttribute("data-testid") || section?.tagName || "Página",
        control: name?.slice(0, 180) ?? "sem nome", id: e.getAttribute("data-testid"), role: e.getAttribute("role") || e.tagName.toLowerCase(), disabled: e.matches(':disabled,[aria-disabled="true"]') };
    });
  }, state);
}

const states = [
  ["/", "kpi-uc"], ["/?dist=6600", "dist-title"], ["/explorar/?ativo=transformadores&c=565&tec=EQTRMT", "valor-recorte"], ["/explorar/?ativo=conjuntos&escopo=dists&dists=31", "inv-tabela"],
  ["/matriz/", "matriz-tabela"], ["/comparar/", "comparar-tabela"], ["/comparar/?ativo=transformadores&aba=radar", "radar-tabela"], ["/comparar/?aba=graficos", "chart-comparacao"],
  ["/evolucao/?ativo=consumidores&escopo=dists&dists=6600,5370", "evo-tabela"], ["/previsoes/", "cenarios-motor"], ["/metodologia/", "metodologia-por-empresa"], ["/auditoria-publicacoes/", "auditoria-publicacoes"],
];
for (const [route, ready] of states) test(`inventário observado ${route}`, async ({ page }, info) => {
  await page.goto(route);
  await expect(page.getByTestId(ready)).toBeVisible();
  const rows = await controles(page, route);
  const extra = page.getByTestId("mais-caracteristicas");
  if (await extra.isVisible()) { await extra.click(); rows.push(...await controles(page, route + " · mais características")); }
  if (route === "/matriz/") {
    await page.getByTestId("filtro-col-trafo_dist").click();
    await expect(page.getByTestId("col-filtro-area")).toBeVisible();
    rows.push(...await controles(page, route + " · filtro de coluna"));
  }
  for (const summary of await page.locator("details:not([open]) > summary:visible").all()) {
    await summary.click();
    await expect(summary.locator("..")).toHaveAttribute("open", "");
  }
  if (route === "/previsoes/") await expect(page.getByRole("combobox", { name: "Família do motor", exact: true })).toBeVisible();
  rows.push(...await controles(page, route + " · detalhes"));
  await info.attach("controles-observados.json", { body: JSON.stringify(rows), contentType: "application/json" });
});
