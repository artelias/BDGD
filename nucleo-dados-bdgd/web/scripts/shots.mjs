// Capturas reais para revisão visual: node scripts/shots.mjs <baseURL> <saida> [rotas...]
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const base = process.argv[2] ?? "http://localhost:3210";
const out = process.argv[3] ?? "docs/screenshots";
const routes = process.argv.slice(4).length ? process.argv.slice(4) : ["/", "/matriz/", "/comparar/", "/explorar/", "/metodologia/"];
const views = [
  { name: "desktop", viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 },
  { name: "mobile", viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
];
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
for (const v of views) for (const scheme of ["light", "dark"]) {
  const ctx = await browser.newContext({ ...v, colorScheme: scheme, reducedMotion: "reduce", locale: "pt-BR" });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  for (const r of routes) {
    await page.goto(base + r, { waitUntil: "networkidle", timeout: 180000 });
    if (r === "/" || r.startsWith("/?")) await page.waitForSelector('[data-testid="map-ready"][data-ready="true"]', { state: "attached", timeout: 30000 }).catch(() => errors.push("mapa não ficou pronto"));
    await page.waitForTimeout(900);
    const file = path.join(out, `${(r.replace(/[/?=&:]+/g, "_").replace(/^_|_$/g, "") || "panorama")}-${v.name}-${scheme}.png`);
    await page.screenshot({ path: file, fullPage: process.env.FULL === "1" });
    console.log("ok", file);
  }
  if (errors.length) console.log("ERROS", v.name, scheme, [...new Set(errors)].slice(0, 8));
  await ctx.close();
}
await browser.close();
