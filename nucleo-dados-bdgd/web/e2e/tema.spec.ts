import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Locator, type Page } from "@playwright/test";

/** Botão claro/escuro: cada clique alterna o tema VISÍVEL (Claro ↔ Escuro); a preferência do sistema só define o estado inicial.
 *  A mesma suíte roda em desktop, Android (@mobile) e iPhone estreito (@iphone); no celular o botão fica na folha "Mais". */
const KEY = "nucleo-bdgd-tema";
const VARIANTES = [["", "desktop"], [" @mobile", "mobile"], [" @iphone", "iphone"]] as const;

/** Botão visível do tema; no celular, abre a folha "Mais" quando o botão do cabeçalho não está visível. */
async function botao(page: Page): Promise<Locator> {
  const visivel = page.getByTestId("theme-toggle").locator("visible=true").first();
  if (await visivel.count()) return visivel;
  await page.getByRole("button", { name: "Mais", exact: true }).click();
  const dentro = page.getByRole("dialog", { name: "Mais opções" }).getByTestId("theme-toggle");
  await expect(dentro).toBeVisible();
  return dentro;
}
const tema = (page: Page) => page.locator("html").getAttribute("data-theme");
const guardado = (page: Page) => page.evaluate((k) => localStorage.getItem(k), KEY);
const luminancia = (page: Page) => page.evaluate(() => {
  const m = getComputedStyle(document.body).backgroundColor.match(/[\d.]+/g)!.map(Number);
  const [r, g, b] = m.slice(0, 3).map((v) => { const c = v / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
});

for (const [tag, nome] of VARIANTES) {
  test.describe(`tema claro/escuro — ${nome}`, () => {
    test(`preferência inicial do sistema escuro vira o estado inicial, não um terceiro estágio${tag}`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: "dark" });
      await page.goto("/metodologia/");
      await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
      expect(await guardado(page)).toBeNull();                       // nada gravado até o primeiro clique
      const b = await botao(page);
      await expect(b).toHaveAttribute("aria-pressed", "true");
      await expect(b).toHaveAttribute("aria-label", "Modo escuro");
      await b.click();                                              // escuro → claro no primeiro clique
      await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
      await expect(b).toHaveAttribute("aria-pressed", "false");
      expect(await guardado(page)).toBe("light");
      await b.click();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
      expect(await guardado(page)).toBe("dark");                    // nunca "system" depois de um clique
    });

    test(`sistema claro: cada clique muda a aparência e a escolha persiste após recarga e navegação${tag}`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: "light" });
      await page.goto("/metodologia/");
      await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
      const b = await botao(page);
      await expect(b).toHaveAttribute("aria-pressed", "false");
      const claro = await luminancia(page);
      await b.click();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
      await expect.poll(() => luminancia(page)).toBeLessThan(claro);      // o body tem transição de cor: espera assentar
      await expect(b).toHaveAttribute("aria-pressed", "true");
      await page.reload();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
      await page.goto("/previsoes/");
      await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
      expect(await guardado(page)).toBe("dark");
      await page.emulateMedia({ colorScheme: "light" });             // escolha explícita vence a mudança do sistema
      await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    });

    test(`armazenamento bloqueado: alterna na sessão, sem persistir, em ambos os sentidos${tag}`, async ({ page }) => {
      await page.addInitScript((k) => {
        const original = Storage.prototype.setItem;
        Storage.prototype.setItem = function (key: string, value: string) {
          if (key === k) throw new DOMException("bloqueado", "SecurityError");
          return original.call(this, key, value);
        };
      }, KEY);
      await page.emulateMedia({ colorScheme: "dark" });
      await page.goto("/metodologia/");
      const b = await botao(page);
      await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
      await b.click();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
      await expect(b).toHaveAttribute("aria-pressed", "false");
      await b.click();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
      await b.click();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
      expect(await guardado(page)).toBeNull();                       // nada foi gravado
    });

    test(`sem erros de hidratação ao carregar, alternar e navegar${tag}`, async ({ page }) => {
      const problemas: string[] = [];
      page.on("console", (m) => { if ((m.type() === "error" || m.type() === "warning") && /hydrat|did not match|server rendered|text content/i.test(m.text())) problemas.push(m.text()); });
      page.on("pageerror", (e) => problemas.push(`pageerror: ${e.message}`));
      for (const esquema of ["dark", "light"] as const) {
        await page.emulateMedia({ colorScheme: esquema });
        await page.addInitScript((k) => { try { localStorage.removeItem(k); } catch { /* sem armazenamento */ } }, KEY);
        await page.goto("/");
        await page.waitForLoadState("networkidle");
        await (await botao(page)).click();
        await page.goto("/matriz/");
        await page.waitForLoadState("networkidle");
      }
      expect(problemas).toEqual([]);
    });
  });
}

test.describe("tema claro/escuro — desktop: tooltip, contraste e todas as páginas", () => {
  test("tooltip descreve o tema atual e a ação; rótulo acessível é fixo", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/metodologia/");
    const b = page.getByTestId("theme-toggle");
    await b.hover();
    await expect(page.getByRole("tooltip")).toContainText("Tema claro — ativar escuro");
    await b.click();
    await expect(page.getByRole("tooltip")).toContainText("Tema escuro — ativar claro");
    await expect(b).toHaveAttribute("aria-label", "Modo escuro");
  });

  for (const esquema of ["light", "dark"] as const) {
    test(`contraste do botão e da barra superior (${esquema}) — axe color-contrast`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: esquema, reducedMotion: "reduce" });
      await page.goto("/metodologia/");
      await page.getByTestId("theme-toggle").click();                // também após uma alternância
      await page.getByTestId("theme-toggle").click();
      await expect(page.locator("html")).toHaveAttribute("data-theme", esquema);
      const r = await new AxeBuilder({ page }).withRules(["color-contrast", "button-name", "aria-allowed-attr"]).include("header").analyze();
      expect(r.violations.map((v) => `${v.id}: ${v.nodes[0]?.target.join(" ")}`)).toEqual([]);
    });
  }

  for (const rota of ["/", "/matriz/", "/comparar/", "/explorar/", "/evolucao/", "/metodologia/", "/previsoes/"]) {
    test(`tema efetivo em ${rota}: escuro e claro mudam a página inteira`, async ({ page }) => {
      await page.goto(rota);
      await page.evaluate((k) => localStorage.setItem(k, "dark"), KEY);
      await page.reload();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
      await expect.poll(() => luminancia(page)).toBeLessThan(0.15);   // o body tem transição de cor: espera assentar
      await page.getByTestId("theme-toggle").click();
      await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
      await expect.poll(() => luminancia(page)).toBeGreaterThan(0.6);
      expect(await tema(page)).toBe("light");
    });
  }
});
