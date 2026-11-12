// Tempo de carga e bytes do módulo /confiabilidade sobre o build estático (out/).
//   node scripts/servir-estatico.mjs out 3231   (em outro terminal)
//   node scripts/medir-confiabilidade.mjs http://127.0.0.1:3231 [saida.json]
// Cenários: desktop sem limitação e celular com rede 4G (9 Mbit/s, 60 ms) e CPU 4× mais lenta. O servidor local não
// comprime: os bytes e tempos limitados são o pior caso (a hospedagem serve JSON com gzip, ~3–5× menor).
import { chromium } from "@playwright/test";
import fs from "node:fs";

const base = process.argv[2] ?? "http://127.0.0.1:3231";
const saida = process.argv[3];
const CASOS = [
  { nome: "Brasil", url: "/confiabilidade/", pronto: '[data-testid="conf-lista-dist"]' },
  { nome: "EPB 6600 (75 conjuntos)", url: "/confiabilidade/?dist=6600", pronto: '[data-testid="conf-mapa-pronto"][data-conjuntos="75"]' },
  { nome: "Energisa AC 26 (15 conjuntos)", url: "/confiabilidade/?dist=26", pronto: '[data-testid="conf-mapa-pronto"][data-conjuntos="15"]' },
  { nome: "Maior distribuidora 4950", url: "/confiabilidade/?dist=4950", pronto: '[data-testid="conf-mapa-pronto"][data-conjuntos]' },
  { nome: "Ficha EPB Mataraca", url: "/confiabilidade/?dist=6600&conj=16849", pronto: '[data-testid="conf-ficha"]' },
  { nome: "Benchmarking EPB", url: "/confiabilidade/?aba=benchmarking&dist=6600&conj=16849", pronto: '[data-testid="conf-pares"] tbody tr' },
  { nome: "Fatores", url: "/confiabilidade/?aba=fatores", pronto: '[data-testid="conf-hipoteses"] tbody tr' },
];
const PERFIS = [
  { nome: "desktop", ctx: { viewport: { width: 1440, height: 900 } } },
  { nome: "celular 4G + CPU 4×", ctx: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }, rede: { latency: 60, downloadThroughput: (9e6 / 8), uploadThroughput: (1.5e6 / 8) }, cpu: 4 },
];

const browser = await chromium.launch();
const resultados = [];
for (const perfil of PERFIS) for (const caso of CASOS) {
  const ctx = await browser.newContext({ ...perfil.ctx, locale: "pt-BR", reducedMotion: "reduce" });   // contexto novo = cache frio
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send("Network.enable");
  if (perfil.rede) await cdp.send("Network.emulateNetworkConditions", { offline: false, ...perfil.rede });
  if (perfil.cpu) await cdp.send("Emulation.setCPUThrottlingRate", { rate: perfil.cpu });
  const urls = new Map(); let bytesDados = 0, bytesTotal = 0;
  cdp.on("Network.responseReceived", (e) => urls.set(e.requestId, e.response.url));
  cdp.on("Network.loadingFinished", (e) => { bytesTotal += e.encodedDataLength; if ((urls.get(e.requestId) ?? "").includes("/data/confiabilidade/")) bytesDados += e.encodedDataLength; });
  const erros = [];
  page.on("pageerror", (e) => erros.push(e.message));
  const t0 = Date.now();
  await page.goto(base + caso.url, { waitUntil: "domcontentloaded", timeout: 180000 });
  await page.waitForSelector(caso.pronto, { state: "attached", timeout: 180000 });
  const ms = Date.now() - t0;
  resultados.push({ perfil: perfil.nome, caso: caso.nome, ms, kB_dados_modulo: Math.round(bytesDados / 1e3), kB_total: Math.round(bytesTotal / 1e3), erros });
  console.log(`${perfil.nome.padEnd(20)} ${caso.nome.padEnd(30)} ${String(ms).padStart(6)} ms  dados ${String(Math.round(bytesDados / 1e3)).padStart(6)} kB  total ${String(Math.round(bytesTotal / 1e3)).padStart(6)} kB${erros.length ? "  ERROS: " + erros.join(" | ") : ""}`);
  await ctx.close();
}
await browser.close();
if (saida) fs.writeFileSync(saida, JSON.stringify({ base, medido_em: new Date().toISOString(), resultados }, null, 1));
