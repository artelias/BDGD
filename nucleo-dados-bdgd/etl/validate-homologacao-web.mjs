// Gate do asset web da homologação (Fase 4): confere homologacao.json contra os artefatos versionados em auditoria/fase4
// e contra a série histórica publicada. Uso: node validate-homologacao-web.mjs <auditoria/fase4> <homologacao.json> <serie.json>
import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";

const [f4, homFile, serieFile] = process.argv.slice(2);
const hom = JSON.parse(fs.readFileSync(homFile, "utf8"));
const serie = JSON.parse(fs.readFileSync(serieFile, "utf8"));
const erros = [];
const PUB = new Set(["H", "T", "R"]);

function csv(file) {
  const txt = fs.readFileSync(file, "utf8").replace(/^﻿/, "");
  const rows = []; let row = [], cell = "", q = false;
  for (let i = 0; i < txt.length; i++) {
    const ch = txt[i];
    if (q) { if (ch === '"') { if (txt[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += ch; }
    else if (ch === '"') q = true; else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n") { row.push(cell.replace(/\r$/, "")); rows.push(row); row = []; cell = ""; } else cell += ch;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const [h, ...d] = rows; return d.filter((r) => r.length > 1).map((r) => Object.fromEntries(h.map((k, i) => [k, r[i] ?? ""])));
}

// 1) rastreabilidade: SHA-256 das fontes iguais aos arquivos versionados
for (const [f, h] of Object.entries(hom.fontes ?? {})) {
  const real = crypto.createHash("sha256").update(fs.readFileSync(path.join(f4, f))).digest("hex");
  if (real !== h) erros.push(`fonte ${f}: SHA-256 diverge (asset gerado de outra versão)`);
}
// 2) 25 ativos e uma célula por (dist, ano, ativo), igual à matriz
const M = csv(path.join(f4, "MATRIZ_HOMOLOGACAO_2022_2025.csv"));
const ativos = Object.keys(hom.celulas);
if (ativos.length !== 25) erros.push(`esperados 25 ativos, encontrados ${ativos.length}`);
const EST = { HOMOLOGADO: "H", COMPLETO_TECNICO: "T", APTO_COM_RESSALVAS: "R", PENDENTE_DECISAO: "P", BLOQUEADO: "B", NAO_DISPONIVEL: "N" };
const mat = new Map(M.filter((r) => r.nivel === "DIST").map((r) => [`${r.dist}|${r.ano}|${r.ativo}`, r]));
let n = 0;
for (const [a, cs] of Object.entries(hom.celulas)) for (const [d, ano, e] of cs) {
  n++; const r = mat.get(`${d}|${ano}|${a}`);
  if (!r) erros.push(`célula ${d}/${ano}/${a} ausente da matriz`); else if (EST[r.estado_publicacao] !== e) erros.push(`célula ${d}/${ano}/${a}: estado ${e} ≠ matriz ${r.estado_publicacao}`);
}
if (n !== mat.size) erros.push(`células: asset ${n} ≠ matriz ${mat.size}`);
// 3) nenhuma célula não publicável com valor na série consumida pela página (N/D nunca vira valor nem zero)
const est = new Map(); for (const [a, cs] of Object.entries(hom.celulas)) for (const [d, ano, e] of cs) est.set(`${d}|${ano}|${a}`, e);
let comValorValidado = 0;
for (const [a, cs] of Object.entries(serie.original)) for (const [d, ano, v, st] of cs) {
  const e = est.get(`${d}|${ano}|${a}`);
  if (e === undefined) erros.push(`série ${d}/${ano}/${a} sem estado na matriz`);
  if (v !== null && st === "v") { comValorValidado++; if (!PUB.has(e)) continue; }
  if (v !== null && st !== "v") erros.push(`série ${d}/${ano}/${a}: valor sem validação`);
  if (PUB.has(e) && st !== "v") erros.push(`célula ${d}/${ano}/${a} publicável sem valor validado na série`);
}
// 4) agregados Brasil: 2022–2023 nunca como total nacional; demais = soma das células publicáveis, exceto "não somar"
const serieIdx = new Map(); for (const [a, cs] of Object.entries(serie.original)) for (const [d, ano, v] of cs) serieIdx.set(`${d}|${ano}|${a}`, v);
for (const [a, linhas] of Object.entries(hom.brasil)) for (const [ano, v, e, ninc, nexc, exc] of linhas) {
  if ((ano === 2022 || ano === 2023) && (v !== null || e !== "B")) erros.push(`Brasil ${ano}/${a} publicado como total nacional`);
  const cs = hom.celulas[a].filter((c) => c[1] === ano);
  const inc = cs.filter((c) => PUB.has(c[2]) && !(c[4] & 4) && serieIdx.get(`${c[0]}|${ano}|${a}`) !== null);
  const excl = cs.filter((c) => c[2] === "P" || c[2] === "B").map((c) => c[0]).sort((x, y) => x - y);
  if (ninc !== inc.length || nexc !== excl.length || exc.join() !== excl.join()) erros.push(`Brasil ${ano}/${a}: contagens divergem da matriz`);
  if (v !== null) {
    const soma = inc.reduce((s, c) => s + serieIdx.get(`${c[0]}|${ano}|${a}`), 0);
    if (Math.abs(soma - v) > 1e-6 * Math.max(1, Math.abs(v))) erros.push(`Brasil ${ano}/${a}: ${v} ≠ soma ${soma}`);
  }
}
// 5) painel balanceado: universo publicável nos quatro anos, sem DIST "não somar"
for (const [a, p] of Object.entries(hom.painel)) for (const [ano, v] of p.valores) {
  const cs = new Map(hom.celulas[a].filter((c) => c[1] === ano).map((c) => [c[0], c]));
  let soma = 0;
  for (const d of p.universo) { const c = cs.get(d); if (!c || !PUB.has(c[2]) || c[4] & 4) erros.push(`painel ${a}: DIST ${d} não publicável em ${ano}`); else soma += serieIdx.get(`${d}|${ano}|${a}`) ?? NaN; }
  if (Math.abs(soma - v) > 1e-6 * Math.max(1, Math.abs(v))) erros.push(`painel ${ano}/${a}: ${v} ≠ ${soma}`);
}
// 6) decisões humanas não foram tomadas: pares pendentes e células dos pares fora da publicação
for (const [k, p] of Object.entries(hom.pares)) {
  if (p.decisao !== "PENDENTE") erros.push(`par ${k}: decisão registrada no asset (não permitido nesta fase)`);
  const [d, ano] = k.split("|").map(Number);
  for (const [a, cs] of Object.entries(hom.celulas)) for (const c of cs) if (c[0] === d && c[1] === ano && c[2] !== "P" && c[2] !== "N") erros.push(`par ${k}: célula ${a} publicável`);
}
if (Object.keys(hom.pares).length !== 13) erros.push(`esperados 13 pares, encontrados ${Object.keys(hom.pares).length}`);
for (const e of erros.slice(0, 40)) console.error("ERRO: " + e);
if (erros.length) { console.error(`BLOQUEADO: ${erros.length} erro(s).`); process.exitCode = 1; }
else console.log(`HOMOLOGAÇÃO WEB OK: ${n} células, ${ativos.length} ativos, ${comValorValidado} com valor validado, 13 pares pendentes, Brasil 2022–2023 sem total nacional`);
