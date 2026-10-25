// Gate do contrato de integração nacional (output-historico/contrato-integracao) consumido pelo motor do PR #6.
// Uso: node validate-contrato-nacional.mjs <contrato-integracao> <auditoria/fase4/MATRIZ_HOMOLOGACAO_2022_2025.csv>
import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";

// SHA-256 sobre o conteúdo com quebras de linha normalizadas para LF (independe de core.autocrlf / sistema operacional)
const lf = (b) => Buffer.from(b.toString("latin1").replace(/\r\n/g, "\n"), "latin1");

const [dir, matrizFile] = process.argv.slice(2);
const erros = [];
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
const man = JSON.parse(fs.readFileSync(path.join(dir, "MANIFESTO.json"), "utf8"));
for (const [f, h] of Object.entries(man.saidas)) if (crypto.createHash("sha256").update(lf(fs.readFileSync(path.join(dir, f)))).digest("hex") !== h) erros.push(`${f}: SHA-256 diverge do manifesto`);
const S = csv(path.join(dir, "serie_fisica_nacional.csv"));
const ESTADOS = new Set(["observado", "zero_verificado", "ausente", "nao_homologado", "nao_aplicavel", "ruptura"]);
const OBS = new Set(["observado", "zero_verificado"]);
const chaves = new Set();
const dists = new Set(S.map((r) => r.dist)), anos = new Set(S.map((r) => r.ano)), conc = new Set(S.map((r) => r.conceitoId));
if (S.length !== dists.size * anos.size * conc.size) erros.push(`universo incompleto: ${S.length} ≠ ${dists.size}×${anos.size}×${conc.size}`);
if (conc.size !== 25) erros.push(`esperados 25 conceitos, encontrados ${conc.size}`);
const M = new Map(csv(matrizFile).filter((r) => r.nivel === "DIST").map((r) => [`${r.ano}|${r.dist}|${r.ativo}`, r]));
const PUB = new Set(["HOMOLOGADO", "COMPLETO_TECNICO", "APTO_COM_RESSALVAS"]);
for (const r of S) {
  const k = `${r.ano}|${r.dist}|${r.conceitoId}|${r.metrica}|${r.perimetroId}`;
  if (chaves.has(k)) erros.push(`chave duplicada ${k}`); chaves.add(k);
  if (!ESTADOS.has(r.estado)) erros.push(`${k}: estado inválido ${r.estado}`);
  if (OBS.has(r.estado) !== (r.valor !== "")) erros.push(`${k}: valor e estado incoerentes (N/D nunca tem valor)`);
  if (r.estado === "zero_verificado" && Number(r.valor) !== 0) erros.push(`${k}: zero_verificado com valor ${r.valor}`);
  if (r.estado === "observado" && !(Number(r.valor) > 0)) erros.push(`${k}: observado sem valor positivo`);
  if ((r.fonte_homologada === "true") !== (r.status_homologacao === "HOMOLOGADO")) erros.push(`${k}: fonte_homologada só vale para HOMOLOGADO`);
  if (r.cobertura !== "" && (r.cobertura !== "1" || !OBS.has(r.estado))) erros.push(`${k}: cobertura 1 só para célula observada integral`);
  if (OBS.has(r.estado)) {
    if (!/^[0-9a-f]{64}$/.test(r.sha256) || !r.publicacao_id) erros.push(`${k}: observação sem publicação/SHA-256`);
    if (r.dataBase !== `${r.ano}-12-31`) erros.push(`${k}: dataBase ${r.dataBase} fora de 31/12`);
    const mt = M.get(`${r.ano}|${r.dist}|${r.conceitoId}`);
    if (!mt || !PUB.has(mt.estado_publicacao) || Math.abs(Number(mt.valor) - Number(r.valor)) > 1e-9) erros.push(`${k}: diverge da matriz de homologação`);
  } else if (r.tipo_lacuna === "") erros.push(`${k}: lacuna sem causa`);
}
// agregados: Brasil = soma das observações (sem "não somar"); 2022–2023 nunca total nacional
const A = csv(path.join(dir, "agregados_nacionais.csv"));
const soma = new Map();
for (const r of S) if (OBS.has(r.estado) && r.nao_somar_em_agregados !== "true") soma.set(`${r.ano}|${r.conceitoId}`, (soma.get(`${r.ano}|${r.conceitoId}`) ?? 0) + Number(r.valor));
for (const r of A.filter((x) => x.nivel === "brasil")) {
  if ((r.ano === "2022" || r.ano === "2023") && (r.valor !== "" || r.cobertura_completa === "true")) erros.push(`Brasil ${r.ano}/${r.conceitoId} como total nacional`);
  if (r.valor !== "" && Math.abs(Number(r.valor) - (soma.get(`${r.ano}|${r.conceitoId}`) ?? 0)) > 1e-6 * Math.max(1, Number(r.valor))) erros.push(`Brasil ${r.ano}/${r.conceitoId}: ${r.valor} ≠ soma das observações`);
  if (r.cobertura_completa === "true" && r.n_dist_excluidas !== "0") erros.push(`Brasil ${r.ano}/${r.conceitoId}: completo com exclusões`);
}
for (const e of erros.slice(0, 40)) console.error("ERRO: " + e);
if (erros.length) { console.error(`BLOQUEADO: ${erros.length} erro(s).`); process.exitCode = 1; }
else console.log(`CONTRATO NACIONAL OK: ${S.length} linhas (${dists.size} DIST × ${anos.size} anos × ${conc.size} conceitos), ${A.length} agregados, Brasil 2022–2023 sem total nacional`);
