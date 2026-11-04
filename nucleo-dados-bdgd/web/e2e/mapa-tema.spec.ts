import { expect, test, type Page } from "@playwright/test";

/** Mapa do Panorama × tema claro/escuro, em 10 alternâncias seguidas.
 *  Defeito corrigido: o ThemeProvider gravava data-theme num useEffect do pai, que roda depois dos efeitos dos filhos; o mapa
 *  recoloria lendo as variáveis CSS do tema ANTERIOR (fundo e continente de um tema, áreas de atuação do outro).
 *  Confere o estado que o mapa pintou e os pixels realmente renderizados no canvas. */

// cores de base do mapa (globals.css: --map-water, --map-land, --map-land-br)
const BASE = {
  light: [[230, 232, 232], [247, 247, 244], [251, 251, 249]],
  dark: [[10, 11, 13], [20, 22, 25], [24, 26, 30]],
} as const;
type Tema = keyof typeof BASE;
const perto = (a: number[], b: readonly number[]) => a.every((v, i) => Math.abs(v - b[i]) <= 3);

async function botaoTema(page: Page) {
  const visivel = page.getByTestId("theme-toggle").locator("visible=true").first();
  if (await visivel.count()) return { botao: visivel, fechar: async () => {} };
  await page.getByRole("button", { name: "Mais", exact: true }).click();
  const folha = page.getByRole("dialog", { name: "Mais opções" });
  return { botao: folha.getByTestId("theme-toggle"), fechar: async () => { await folha.getByRole("button", { name: "Fechar" }).click(); await expect(folha).toBeHidden(); } };
}

/** Pixels do canvas do mapa (fora dos controles), classificados pelas cores de base de cada tema. */
async function pixelsDeBase(page: Page) {
  const canvas = page.locator(".maplibregl-canvas");
  const b = (await canvas.boundingBox())!;
  const png = await page.screenshot({ clip: b, animations: "disabled" });
  const amostra: number[][] = await page.evaluate(async ({ src, w, h }) => {
    const img = new Image(); img.src = `data:image/png;base64,${src}`; await img.decode();
    const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
    const ctx = c.getContext("2d")!; ctx.drawImage(img, 0, 0);
    const k = img.width / w, out: number[][] = [];
    for (let y = 70; y < h - 40; y += 24) for (let x = 8; x < w - 70; x += 24) out.push(Array.from(ctx.getImageData(Math.round(x * k), Math.round(y * k), 1, 1).data).slice(0, 3));
    return out;
  }, { src: png.toString("base64"), w: b.width, h: b.height });
  const conta = (t: Tema) => amostra.filter((p) => BASE[t].some((c) => perto(p, c))).length;
  return { light: conta("light"), dark: conta("dark") };
}

async function conferir(page: Page, tema: Tema) {
  await expect(page.locator("html")).toHaveAttribute("data-theme", tema);
  const agua = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--map-water").trim());
  const sonda = page.getByTestId("map-ready");
  await expect(sonda).toHaveAttribute("data-tema", tema);
  await expect(sonda).toHaveAttribute("data-fundo", agua);
  const outro: Tema = tema === "dark" ? "light" : "dark";
  await expect.poll(async () => { const p = await pixelsDeBase(page); return p[outro] === 0 && p[tema] > 0; }, { timeout: 10_000 }).toBe(true);
  await expect(page.locator(".maplibregl-canvas")).toHaveCount(1);          // nenhuma instância duplicada
  await expect(page.locator(".maplibregl-ctrl-zoom-in")).toHaveCount(1);    // controles preservados
  await expect(page.locator(".maplibregl-ctrl-zoom-in")).toBeVisible();
}

for (const [tag, nome] of [["", "desktop"], [" @mobile", "mobile"]] as const) {
  test(`mapa: 10 alternâncias de tema sem mistura de cores, sem instância duplicada e com controles — ${nome}${tag}`, async ({ page }) => {
    test.setTimeout(180_000);
    const erros: string[] = [];
    page.on("pageerror", (e) => erros.push(e.message));
    page.on("console", (m) => { if (m.type() === "error") erros.push(m.text()); });
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/");
    await expect(page.getByTestId("map-ready")).toHaveAttribute("data-ready", "true");
    let tema: Tema = "light";
    await conferir(page, tema);
    for (let i = 0; i < 10; i++) {
      const { botao, fechar } = await botaoTema(page);
      await botao.click();
      tema = tema === "dark" ? "light" : "dark";
      await fechar();
      await conferir(page, tema);
    }
    await page.reload();                                                    // o tema escolhido sobrevive à recarga e o mapa nasce nele
    await expect(page.getByTestId("map-ready")).toHaveAttribute("data-ready", "true");
    await conferir(page, tema);
    expect(erros).toEqual([]);
  });
}
