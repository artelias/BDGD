// Gate do asset web da homologação (Fase 4): confere homologacao.json contra os artefatos versionados em auditoria/fase4
// e contra a série histórica publicada. Uso: node validate-homologacao-web.mjs <auditoria/fase4> <homologacao.json> <serie.json>
import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";

// SHA-256 sobre o conteúdo com quebras de linha normalizadas para LF (independe de core.autocrlf / sistema operacional)
const lf = (b) => Buffer.from(b.toString("latin1").replace(/\r\n/g, "\n"), "latin1");

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
  const real = crypto.createHash("sha256").update(lf(fs.readFileSync(path.join(f4, f)))).digest("hex");
  if (real !== h) erros.push(`fonte ${f}: SHA-256 diverge (asset gerado de outra versão)`);
}
// 2) 25 ativos e uma célula por (dist, ano, ativo), igual à matriz
const M = csv(path.join(f4, "MATRIZ_HOMOLOGACAO_2022_2025.csv"));
const ativos = Object.keys(hom.celulas);
if (ativos.length !== 25) erros.push(`esperados 25 ativos, encontrados ${ativos.length}`);
const EST = { HOMOLOGADO: "H", COMPLETO_TECNICO: "T", APTO_COM_RESSALVAS: "R", PENDENTE_DECISAO: "P", BLOQUEADO: "B", NAO_DISPONIVEL: "N" };
const mat = new Map(M.filter((r) => r.nivel === "DIST").map((r) => [`${r.dist}|${r.ano}|${r.ativo}`, r]));
// A matriz da Fase 4 antecede as decisões editoriais documentadas para os 13 pares.
// Apenas esses pares podem mudar PENDENTE_DECISAO para R (valor) ou N (sem dado).
const paresSelecionados = new Set(Object.entries(hom.pares ?? {})
  .filter(([, p]) => p.decisao === "VERSAO_MAIS_RECENTE_SELECIONADA")
  .map(([k]) => k));
let n = 0;
for (const [a, cs] of Object.entries(hom.celulas)) for (const [d, ano, e] of cs) {
  n++; const r = mat.get(`${d}|${ano}|${a}`);
  if (!r) erros.push(`célula ${d}/${ano}/${a} ausente da matriz`);
  else if (EST[r.estado_publicacao] !== e) {
    const revisada = r.estado_publicacao === "PENDENTE_DECISAO"
      && paresSelecionados.has(`${d}|${ano}`) && (e === "R" || e === "N");
    if (!revisada) erros.push(`célula ${d}/${ano}/${a}: estado ${e} ≠ matriz ${r.estado_publicacao}`);
  }
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
  // Lacunas: pendentes/bloqueadas, entidade vazia (flag 8) e conceitos N/D
  // comprovadamente ausentes na republicação mais recente (motivo documental 115).
  const excl = cs.filter((c) => c[2] === "P" || c[2] === "B" || (c[4] & 8)
    || (c[2] === "N" && paresSelecionados.has(`${c[0]}|${ano}`)
      && hom.motivos[c[3]] === "A publicação mais recente foi selecionada, mas o conceito está ausente nesta competência: N/D, não zero."))
    .map((c) => c[0]).sort((x, y) => x - y);
  if (cs.some((c) => c[4] & 8) && e === "H") erros.push(`Brasil ${ano}/${a}: homologado com distribuidora de entidade vazia fora da soma`);
  if (ninc !== inc.length || nexc !== excl.length || exc.join() !== excl.join()) erros.push(`Brasil ${ano}/${a}: contagens divergem da matriz`);
  if (v !== null) {
    const soma = inc.reduce((s, c) => s + serieIdx.get(`${c[0]}|${ano}|${a}`), 0);
    if (Math.abs(soma - v) > 1e-6 * Math.max(1, Math.abs(v))) erros.push(`Brasil ${ano}/${a}: ${v} ≠ soma ${soma}`);
  }
}
// 4b) entidade vazia na publicação (flag 8): nunca publicável, nunca zero
for (const [a, cs] of Object.entries(hom.celulas)) for (const c of cs) if (c[4] & 8 && PUB.has(c[2])) erros.push(`célula ${c[0]}/${c[1]}/${a}: entidade vazia marcada como publicável`);
// 5) painel balanceado: universo publicável nos quatro anos, sem DIST "não somar"
for (const [a, p] of Object.entries(hom.painel)) for (const [ano, v] of p.valores) {
  const cs = new Map(hom.celulas[a].filter((c) => c[1] === ano).map((c) => [c[0], c]));
  let soma = 0;
  for (const d of p.universo) { const c = cs.get(d); if (!c || !PUB.has(c[2]) || c[4] & 4) erros.push(`painel ${a}: DIST ${d} não publicável em ${ano}`); else soma += serieIdx.get(`${d}|${ano}|${a}`) ?? NaN; }
  if (Math.abs(soma - v) > 1e-6 * Math.max(1, Math.abs(v))) erros.push(`painel ${ano}/${a}: ${v} ≠ ${soma}`);
}
// 6) Contrato editorial: só liberar republicações com versão mais recente validada,
// prova de competência anual, hash, versão anterior preservada e série consistente.
for (const [k, p] of Object.entries(hom.pares)) {
  const [d, ano] = k.split("|").map(Number);
  const prov = hom.proveniencia[k] ?? [];
  if (p.decisao === "VERSAO_MAIS_RECENTE_SELECIONADA") {
    const carimbo = (s) => {
      const m = /^V\d+_(\d{8})-(\d{4})$/.exec(s ?? "");
      return m ? `${m[1]}${m[2]}` : null;
    };
    const a = carimbo(p.A?.versao), b = carimbo(p.B?.versao);
    if (!a || !b || b <= a) erros.push(`par ${k}: versão selecionada não é posterior`);
    const atual = prov.find((v) => v.item === p.B?.item);
    const anterior = prov.find((v) => v.item === p.A?.item);
    if (!atual || atual.uso !== "em_uso_na_serie" || atual.data_base !== `${ano}-12-31`
      || atual.intervalo !== "INTERVALO_ANUAL_COMPATIVEL" || !/^[a-f0-9]{64}$/i.test(atual.sha ?? ""))
      erros.push(`par ${k}: fonte selecionada sem comprovação de competência/integridade`);
    if (!anterior || anterior.uso !== "versao_anterior_preservada"
      || !/^[a-f0-9]{64}$/i.test(anterior.sha ?? ""))
      erros.push(`par ${k}: versão anterior ou hash não preservado`);
    for (const [ativo, cs] of Object.entries(hom.celulas)) {
      const cel = cs.find((v) => v[0] === d && v[1] === ano);
      const serieCel = serie.original[ativo]?.find((v) => v[0] === d && v[1] === ano);
      if (!cel || !serieCel) { erros.push(`par ${k}/${ativo}: célula ausente`); continue; }
      if (cel[2] === "R") {
        if (serieCel[3] !== "v" || typeof serieCel[2] !== "number")
          erros.push(`par ${k}/${ativo}: apto com ressalva sem valor verificado`);
      } else if (cel[2] === "N") {
        if (serieCel[2] !== null) erros.push(`par ${k}/${ativo}: N/D publicado com valor`);
      } else erros.push(`par ${k}/${ativo}: estado inesperado ${cel[2]}`);
    }
  } else if (p.decisao === "PENDENTE") {
    for (const [ativo, cs] of Object.entries(hom.celulas)) for (const cel of cs)
      if (cel[0] === d && cel[1] === ano && cel[2] !== "P" && cel[2] !== "N")
        erros.push(`par ${k}/${ativo}: valor publicável sem decisão registrada`);
  } else erros.push(`par ${k}: decisão desconhecida ${p.decisao}`);
}
if (Object.keys(hom.pares).length !== 13) erros.push(`esperados 13 pares, encontrados ${Object.keys(hom.pares).length}`);
for (const e of erros.slice(0, 40)) console.error("ERRO: " + e);
if (erros.length) { console.error(`BLOQUEADO: ${erros.length} erro(s).`); process.exitCode = 1; }
else console.log(`HOMOLOGAÇÃO WEB OK: ${n} células, ${ativos.length} ativos, ${comValorValidado} com valor validado, ${paresSelecionados.size} pares com seleção comprovada, Brasil 2022–2023 sem total nacional`);
