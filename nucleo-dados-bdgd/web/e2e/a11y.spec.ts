import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// WCAG 2.2 A/AA (axe-core) nas páginas principais, nos dois temas. O canvas do mapa fica fora (não é texto).
for (const theme of ["light", "dark"] as const) {
  for (const path of ["/", "/matriz/", "/comparar/?grafico=valores", "/explorar/?ativo=transformadores&c=570&escopo=grupo:energisa", "/explorar/?ativo=subestacoes&escopo=dists&dists=31", "/evolucao/", "/metodologia/"]) {
    test(`acessibilidade ${theme} ${path}`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(800);
      const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).exclude(".maplibregl-canvas").analyze();
      const serious = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(serious.map((v) => `${v.id}: ${v.nodes.length} nó(s) — ${v.nodes[0]?.target.join(" ")}`)).toEqual([]);
    });
  }
}
