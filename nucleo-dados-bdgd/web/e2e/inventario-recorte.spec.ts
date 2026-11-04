import { expect, test } from "@playwright/test";

test("inventário: busca, detalhe e CSV preservam o recorte e os nulos da subestação", async ({ page }) => {
  const { sub } = await (await page.request.get("/data/2025-12-31/inventario/31.json")).json();
  const fonte = sub.rows.find((r: (string | number | null)[]) => r[0] === "APR");
  expect(fonte[sub.cols.indexOf("alimentadores")]).toBeNull();
  await page.goto("/explorar/?ativo=subestacoes&escopo=dists&dists=31");
  await page.getByTestId("inv-busca").fill(fonte[sub.cols.indexOf("nome")]);
  const linha = page.getByTestId("inv-tabela").locator("tbody tr");
  await expect(linha).toHaveCount(1);
  await expect(linha.locator("td").nth(1)).toHaveText("N/D");
  await linha.press("Enter");
  await expect(page.getByTestId("inv-detalhe").getByText("Alimentadores", { exact: true }).locator("..")).toContainText("N/D");
  const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("inv-csv").click()]);
  const records = Buffer.concat(await (await dl.createReadStream()).toArray()).toString("utf8").trim().split(/\r?\n/);
  expect(records).toHaveLength(2);
  const field = (name: string) => records[1].split(",")[records[0].split(",").indexOf(name)];
  expect(field("codigo")).toBe("APR");
  expect(field("alimentadores")).toBe("");
  expect(Number(field("consumidores"))).toBe(fonte[sub.cols.indexOf("consumidores")]);
  await page.getByTestId("inv-busca").fill("sem-resultado-qa");
  await expect(linha).toHaveCount(0);
  await expect(page.getByTestId("inv-csv")).toBeDisabled();
  await page.getByTestId("inventario").getByRole("button", { name: "Limpar", exact: true }).click();
  await expect(linha).toHaveCount(Math.min(400, sub.rows.length));
});
