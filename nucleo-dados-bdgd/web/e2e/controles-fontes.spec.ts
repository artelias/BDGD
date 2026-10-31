import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

type Cube = { dims: string[]; entidades: string[]; rows: (number | null)[][] };
type Concept = { medidas: string[]; valores: Record<string, string[]>; cubos: Record<string, Cube> };
type Menu = { id: string; conceito?: string; filtro?: Record<string, string[]>; excluir?: Record<string, string[]> };
const catalog = JSON.parse(readFileSync("public/data/2025-12-31/index.json", "utf8")).conceitos;
const source = (name: string): Concept => JSON.parse(readFileSync(`public/data/2025-12-31/conceitos/${name}.json`, "utf8"));

// Oráculo independente: seleciona linhas do cubo público e soma a coluna física,
// sem importar agregar(), escolherCubo() ou componentes usados pela interface.
function total(cd: Concept, dim: string, code: string, item: Menu) {
  const required = [dim, ...Object.keys(item.filtro ?? {}), ...Object.keys(item.excluir ?? {})];
  const candidates = Object.entries(cd.cubos).filter(([, c]) => required.every((key) => c.dims.includes(key)));
  candidates.sort(([a, ca], [b, cb]) => Number(b === "principal") - Number(a === "principal") || cb.entidades.length - ca.entidades.length || ca.rows.length - cb.rows.length);
  const cube = candidates[0][1];
  const rows = cube.rows.filter((r) => r[0] === 6600);
  if (!rows.length) return null;
  const pos = cube.dims.length + 1;
  const selected = rows.filter((r) => {
    const value = (key: string) => cd.valores[key][r[cube.dims.indexOf(key) + 1]!];
    return value(dim) === code && Object.entries(item.filtro ?? {}).every(([k, allowed]) => allowed.includes(value(k))) &&
      Object.entries(item.excluir ?? {}).every(([k, excluded]) => !excluded.includes(value(k)));
  });
  if (selected.some((r) => r[pos] === null)) return null;
  return selected.reduce((sum, r) => sum + Math.max(0, r[pos]!), 0);
}
const formatted = (n: number | null, measure: string) => n == null ? "N/D" : n.toLocaleString("pt-BR", measure === "extensao_km" && n < 100
  ? { minimumFractionDigits: 1, maximumFractionDigits: 1 } : { maximumFractionDigits: 0 }) + (measure === "extensao_km" ? " km" : "");

for (const item of catalog.menu.flatMap((group: { itens: Menu[] }) => group.itens) as Menu[]) {
  if (!item.conceito) continue;
  const concept = item.conceito;
  const cd = source(concept);
  const category = catalog.conceitos[concept].categoria;
  const cardDim = item.filtro?.[category]?.length ? (cd.cubos.principal.dims.includes("a1") ? "a1" : null) : category;
  const dims = [...new Set(Object.values(cd.cubos).flatMap((c) => c.dims))].filter((dim) => dim !== cardDim && !item.filtro?.[dim]);
  for (const dim of dims) test(`fonte original: Explorar ${item.id}, filtro ${dim}, duas opções e limpeza`, async ({ page }, info) => {
    await page.goto(`/explorar/?ativo=${item.id}&escopo=dists&dists=6600`);
    await expect(page.getByTestId("valor-recorte")).toBeVisible();
    if (await page.getByTestId("mais-caracteristicas").count()) await page.getByTestId("mais-caracteristicas").click();
    const filter = page.getByTestId(`filtro-${dim}`);
    const required = [dim, ...Object.keys(item.filtro ?? {}), ...Object.keys(item.excluir ?? {})];
    if (!Object.values(cd.cubos).some((c) => required.every((key) => c.dims.includes(key)))) {
      await expect(filter).toBeDisabled();
      return;
    }
    await expect(filter).toBeEnabled();
    const evidence = [];
    for (const optionIndex of [0, 1]) {
      await filter.click();
      const dialog = page.getByRole("dialog").last();
      const options = dialog.getByRole("group").getByRole("button");
      const count = await options.count();
      if (optionIndex >= count) break; // fonte com um único valor: não inventa segunda categoria
      const label = await options.nth(optionIndex).innerText();
      await options.nth(optionIndex).click();
      await page.keyboard.press("Escape");
      await expect.poll(() => new URL(page.url()).searchParams.get("f")).toContain(`${dim}:`);
      const f = new URL(page.url()).searchParams.get("f")!;
      const code = f.split(";").find((v) => v.startsWith(`${dim}:`))!.slice(dim.length + 1);
      const expected = total(cd, dim, code, item);
      await expect(page.getByTestId("valor-recorte")).toHaveText(formatted(expected, cd.medidas[0]));
      evidence.push({ concept, dim, label, code, expected, medida: cd.medidas[0], source: `conceitos/${concept}.json` });
      await page.reload();
      await expect(page.getByTestId("valor-recorte")).toHaveText(formatted(expected, cd.medidas[0]));
      await page.getByTestId("chips-recorte").getByRole("button", { name: "Limpar", exact: true }).click();
      await expect.poll(() => new URL(page.url()).searchParams.has("f")).toBe(false);
      if (await page.getByTestId("mais-caracteristicas").count()) await page.getByTestId("mais-caracteristicas").click();
    }
    expect(evidence.length).toBeGreaterThan(0);
    await info.attach("fonte-controle.json", { body: JSON.stringify(evidence), contentType: "application/json" });
  });
}

test("filtros incompatíveis não podem ser ativados pelo teclado; Escape devolve foco", async ({ page }) => {
  await page.goto("/explorar/?ativo=consumidores&f=municipio:3550308");
  await expect(page.getByTestId("filtro-fases")).toBeDisabled();
  await page.goto("/matriz/?ativos=consumidores&cf=consumidores~municipio:3550308");
  await page.getByTestId("filtro-col-consumidores").click();
  await expect(page.getByTestId("col-filtro-fases")).toBeDisabled();
  await page.keyboard.press("Escape");
  await page.getByTestId("matriz-dists").click();
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("matriz-dists")).toBeFocused();
  await page.goto("/comparar/?ativo=consumidores&f=municipio:3550308");
  await expect(page.getByTestId("cmp-filtro-fases")).toBeDisabled();
});

test("metodologia: menus, empresa, métrica, cenário e valores correspondem ao produto", async ({ page }) => {
  const data = await (await page.request.get("/data/previsoes/cenarios-motor.json")).json();
  await page.goto("/metodologia/");
  const toc = page.getByRole("navigation", { name: "Seções", exact: true });
  const links = toc.getByRole("link");
  for (let i = 0; i < await links.count(); i++) {
    const href = (await links.nth(i).getAttribute("href"))!;
    await links.nth(i).click();
    await expect(page).toHaveURL(new RegExp(`${href}$`));
    await expect(page.locator(href)).toBeInViewport();
  }
  const section = page.getByTestId("metodologia-por-empresa");
  for (const id of ["6600", "5370", "390"]) {
    // DIST 390 (Enel SP) só se consta do contrato; não substitui silenciosamente.
    expect(data.empresas[id]).toBeTruthy();
    await section.getByLabel("Selecionar distribuidora da metodologia").selectOption(id);
    for (const metric of ["consumidores|quantidade", "rede_mt|extensao_km", "trafo_dist|potencia_kva"]) {
      await section.getByLabel("Selecionar ativo e métrica da metodologia").selectOption(metric);
      const [asset, measure] = metric.split("|");
      const m = data.metricas.find((x: { conceito: string; metrica: string }) => x.conceito === asset && x.metrica === measure);
      for (const scenario of ["conservador", "moderado", "agressivo"]) {
        await section.getByLabel("Selecionar cenário da metodologia").selectOption(scenario);
        if (m.cenarios[scenario]) await expect(section.getByRole("heading", { name: `Função aplicada — ${data.modelos[m.cenarios[scenario]].nome}` })).toBeVisible();
        else await expect(section.getByRole("status")).toContainText("Não há modelo elegível");
      }
      const table = section.getByRole("region", { name: "Histórico e projeções individuais" });
      const series = m.series[id];
      for (const year of [2022, 2023, 2024, 2025, 2030]) {
        const row = table.getByRole("row", { name: new RegExp(`^${year}`) });
        const val = year < 2026 ? series?.hist.find((x: number[]) => x[0] === year)?.[1] : series?.moderado?.[4];
        await expect(row.locator("td").nth(year < 2026 ? 0 : 2)).toHaveText(val == null ? "N/D" : val.toLocaleString("pt-BR", { maximumFractionDigits: m.unidade === "itens" ? 0 : 2 }));
      }
    }
  }
});
