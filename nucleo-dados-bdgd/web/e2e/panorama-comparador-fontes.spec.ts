import { expect, test } from "@playwright/test";

type Dist = { dist: number; sigla: string; grupo: string; grupo_status: string };
type Group = { id: string; nome: string };
type Value = [number, number | null, string];

test("Panorama: cada grupo da legenda filtra o ranking pelos vínculos verificados", async ({ page }) => {
  const raw = await (await page.request.get("/data/2025-12-31/index.json")).json();
  const legend = page.getByRole("group", { name: "Grupos econômicos (filtra o mapa)" });
  const values = new Map((raw.ativosTotais.consumidores.quantidade as Value[]).map(([dist, v]) => [dist, v]));
  await page.goto("/");
  await page.getByTestId("kpi-uc").click();
  const rank = page.getByTestId("ranking-list").getByRole("button");
  for (const group of raw.grupos as Group[]) {
    await legend.getByRole("button", { name: group.nome, exact: true }).click();
    const members = (raw.distribuidoras as Dist[]).filter((d) => d.grupo === group.id && d.grupo_status === "verificado");
    await expect(page.getByRole("heading", { name: group.nome, exact: true, level: 2 })).toBeVisible();
    await expect(rank).toHaveCount(Math.min(12, members.length));
    if (members.length) {
      const leader = members.sort((a, b) => (values.get(b.dist) ?? -1) - (values.get(a.dist) ?? -1))[0];
      await expect(rank.first()).toContainText(leader.sigla.replaceAll("_", " "));
    }
  }
  await page.getByTestId("ver-brasil").click();
  await expect(page.getByRole("heading", { name: /Brasil · cobertura parcial/ })).toBeVisible();
  await page.getByTestId("panel-search").fill("dist-sem-resultado-qa");
  await expect(page.locator('button[data-testid^="dist-"]')).toHaveCount(0);
  await page.getByRole("button", { name: "Limpar busca", exact: true }).click();
  await page.getByTestId("panel-search").fill("6600");
  await page.getByTestId("dist-6600").click();
  await expect(page.getByTestId("dist-title")).toContainText("Energisa");
  const expected = values.get(6600)!;
  await expect(page.getByText(expected.toLocaleString("pt-BR"), { exact: true }).first()).toBeVisible();
});

test("Comparador: valores A, B e diferença trocam de lado com o contrato e o link copia o recorte", async ({ page, context }) => {
  const raw = await (await page.request.get("/data/2025-12-31/index.json")).json();
  const values = new Map((raw.ativosTotais.consumidores.quantidade as Value[]).map(([dist, v]) => [dist, v]));
  const row = page.getByTestId("comparar-tabela").getByRole("row").filter({ has: page.getByRole("cell", { name: "Unidades consumidoras", exact: true }) });
  await page.goto("/comparar/?a=dist:6600&b=dist:390");
  for (const [a, b] of [[6600, 390], [390, 6600]]) {
    if (a === 390) await page.getByTestId("trocar").click();
    await expect(row.getByRole("cell").nth(2)).toHaveText(values.get(a)!.toLocaleString("pt-BR"));
    await expect(row.getByRole("cell").nth(3)).toHaveText(values.get(b)!.toLocaleString("pt-BR"));
    await expect(row.getByRole("cell").nth(4)).toHaveText((values.get(a)! - values.get(b)!).toLocaleString("pt-BR"));
  }
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.getByRole("button", { name: "Link", exact: true }).click();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(page.url());
  await page.reload();
  await expect(row.getByRole("cell").nth(2)).toHaveText(values.get(390)!.toLocaleString("pt-BR"));
});
