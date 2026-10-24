#!/usr/bin/env node
// Validador da série histórica 2022–2025 (gate de CI): nenhuma célula com valor sem estado "validado",
// somente as quatro competências permitidas, ano "homologado" só sem pendências e asset web coerente com o pacote.
// Uso: node etl/validate-serie-historica.mjs output-historico/2022-2025 web/public/data/historico/serie.json
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const [dir, webFile] = process.argv.slice(2);
const erros = [];
const ANOS = new Set(["2022", "2023", "2024", "2025"]);
const ESTADOS = new Set(["validado", "ausente", "campo_ausente", "bloqueado", "revisao_pendente", "nao_processado", "competencia_divergente", "sem_publicacao", "pendente"]);
const deny = /(^|_)(cod_id|cpf|cnpj|nome_consumidor|endereco|numero_medidor|matricula)(_|$)/i;
function csv(nome) {
  const txt = fs.readFileSync(path.join(dir, nome), "utf8").replace(/^﻿/, "").trim().split(/\r?\n/);
  const split = (l) => { const o = []; let v = "", q = false; for (let i = 0; i < l.length; i++) { const c = l[i]; if (q) { if (c === '"' && l[i + 1] === '"') { v += '"'; i++; } else if (c === '"') q = false; else v += c; } else if (c === '"') q = true; else if (c === ",") { o.push(v); v = ""; } else v += c; } o.push(v); return o; };
  const h = split(txt[0]);
  if (h.some((x) => deny.test(x))) erros.push(`${nome}: coluna individualizada`);
  return txt.slice(1).map((l) => Object.fromEntries(split(l).map((v, i) => [h[i], v])));
}
const man = JSON.parse(fs.readFileSync(path.join(dir, "manifest.json"), "utf8"));
for (const [nome, sha] of Object.entries(man.checksums ?? {})) {
  const h = crypto.createHash("sha256").update(fs.readFileSync(path.join(dir, nome))).digest("hex");
  if (h !== sha) erros.push(`checksum divergente: ${nome}`);
}
for (const [nome, ka] of [["serie_ativos_original.csv", "ano"], ["serie_ativos_perimetro_2025.csv", "ano_base"]]) {
  for (const [i, r] of csv(nome).entries()) {
    const w = `${nome} linha ${i + 2}`;
    if (!ANOS.has(r[ka])) erros.push(`${w}: competência fora de 2022–2025 (${r[ka]})`);
    if (!ESTADOS.has(r.status)) erros.push(`${w}: estado inválido ${r.status}`);
    if (r.valor !== "" && r.status !== "validado") erros.push(`${w}: valor publicado sem estado validado`);
    if (r.valor !== "" && !/^\d+(\.\d+)?$/.test(r.valor)) erros.push(`${w}: valor numérico inválido`);
  }
}
for (const c of man.cobertura ?? []) if (c.status_ano.startsWith("homologado") && c.pendentes > 0) erros.push(`ano ${c.ano} homologado com pendências`);
if (webFile) {
  const web = JSON.parse(fs.readFileSync(webFile, "utf8"));
  if (web.versao_regra !== man.versao_regra || web.gerado_em !== man.gerado_em) erros.push("asset web gerado de outro pacote histórico");
  for (const [k, cel] of Object.entries(web.original)) for (const c of cel) if (c[2] !== null && c[3] !== "v") erros.push(`asset web: valor sem validação em ${k} ${c[0]}/${c[1]}`);
}
for (const e of erros.slice(0, 40)) console.error("ERRO: " + e);
if (erros.length) { console.error(`BLOQUEADO: ${erros.length} erro(s).`); process.exitCode = 1; }
else console.log("SÉRIE HISTÓRICA OK: " + (man.cobertura ?? []).map((c) => `${c.ano} ${c.status_ano} (${c.validadas}/${c.publicadas})`).join(" · "));
