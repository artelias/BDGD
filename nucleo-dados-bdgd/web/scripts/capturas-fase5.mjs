// Capturas da Evolução (Fase 5A) a partir do build estático servido em PW_BASE_URL. Uso: node scripts/capturas-fase5.mjs
import { chromium, devices } from "@playwright/test";
const base = process.env.PW_BASE_URL ?? "http://localhost:3211";
const out = "../docs/screenshots/fase5";
const casos = [
  ["brasil-consumidores", "/evolucao/?ativo=consumidores", "light"],
  ["brasil-consumidores-escuro", "/evolucao/?ativo=consumidores", "dark"],
  ["dists-pendencia-proveniencia", "/evolucao/?escopo=dists&dists=26,5381&ativo=rede_mt", "light"],
  ["elektro-rede-at-natureza", "/evolucao/?escopo=dists&dists=385&ativo=rede_at", "light"],
];
const b = await chromium.launch();
for (const [nome, url, tema] of casos) {
  const p = await b.newPage({ viewport: { width: 1440, height: 900 }, colorScheme: tema });
  await p.goto(base + url); await p.getByTestId("evo-tabela").locator("tbody tr").first().waitFor(); await p.waitForTimeout(900);
  await p.screenshot({ path: `${out}/${nome}.png`, fullPage: true }); await p.close();
}
const m = await b.newPage({ ...devices["Pixel 7"] });
await m.goto(base + "/evolucao/?escopo=dists&dists=26,31&ativo=consumidores"); await m.getByTestId("evo-tabela").waitFor(); await m.waitForTimeout(900);
await m.screenshot({ path: `${out}/celular-dists.png`, fullPage: true });
await b.close();
console.log("capturas em", out);
