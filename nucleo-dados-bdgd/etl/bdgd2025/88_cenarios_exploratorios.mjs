#!/usr/bin/env node
/**
 * Regera cenários condicionais a partir do contrato nacional auditado (sem GDB).
 * Uso: node etl/bdgd2025/88_cenarios_exploratorios.mjs --source-commit 8e2eab8
 *      node etl/bdgd2025/88_cenarios_exploratorios.mjs --source-commit 8e2eab8 --check
 * Não classifica como previsão validada; não gera totais Brasil; não inventa N/D.
 */
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const entrada = join(raiz, "output-historico/contrato-integracao/serie_fisica_nacional.csv");
const saida = join(raiz, "web/public/data/previsoes/cenarios-exploratorios-2026-2030.json");
const saidaEstados = join(raiz, "web/public/data/historico/estados-contrato.json");
const commitIndex = process.argv.indexOf("--source-commit");
const commitOrigem = commitIndex >= 0 ? process.argv[commitIndex + 1] : "";
if (!/^[0-9a-f]{7,40}$/i.test(commitOrigem ?? "")) {
  console.error("Informe --source-commit SHA do contrato nacional (PR #4).");
  process.exit(2);
}
const arquivo = readFileSync(entrada);
const blobShaOrigem = createHash("sha1").update("blob " + arquivo.length + "\0").update(arquivo).digest("hex");

function csv(texto) {
  const rows = [];
  let celula = "", linha = [], quoted = false;
  for (let i = 0; i < texto.length; i++) {
    const c = texto[i];
    if (quoted) {
      if (c === '"' && texto[i + 1] === '"') { celula += '"'; i++; }
      else if (c === '"') quoted = false;
      else celula += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { linha.push(celula); celula = ""; }
    else if (c === "\n") {
      linha.push(celula.replace(/\r$/, ""));
      rows.push(linha);
      linha = []; celula = "";
    } else celula += c;
  }
  if (celula || linha.length) { linha.push(celula); rows.push(linha); }
  const cabecalho = rows.shift()?.map((x) => x.replace(/^\uFEFF/, ""));
  if (!cabecalho?.includes("conceitoId") || !cabecalho?.includes("tipo_lacuna")) throw Error("CSV não corresponde ao contrato nacional.");
  return rows.filter((r) => r.length === cabecalho.length)
    .map((r) => Object.fromEntries(cabecalho.map((k, i) => [k, r[i]])));
}
function tendencia(valores, alvo) {
  const n = valores.length;
  const centroX = (n - 1) / 2;
  const centroY = valores.reduce((s, v) => s + v, 0) / n;
  const inclinacao = valores.reduce((s, v, i) => s + (i - centroX) * (v - centroY), 0) /
    valores.reduce((s, _, i) => s + (i - centroX) ** 2, 0);
  return Math.max(0, centroY + inclinacao * (alvo - centroX));
}
const linhas = csv(arquivo.toString("utf8"));
const conjuntos = new Map();
for (const r of linhas) {
  const chave = [r.dist, r.conceitoId, r.metrica, r.unidade, r.perimetroId].join("|");
  if (!conjuntos.has(chave)) conjuntos.set(chave, []);
  conjuntos.get(chave).push(r);
}
const series = [];
for (const conjunto of conjuntos.values()) {
  if (conjunto.length !== 4) continue;
  const pontos = [...conjunto].sort((a, b) => Number(a.ano) - Number(b.ano));
  if (pontos.some((p, i) =>
    Number(p.ano) !== 2022 + i ||
    !["observado", "zero_verificado"].includes(p.estado) ||
    p.valor.trim() === "" || !Number.isFinite(Number(p.valor)) || Number(p.valor) < 0 ||
    (p.estado === "zero_verificado" && Number(p.valor) !== 0) ||
    Number(p.cobertura) !== 1 ||
    p.ruptura_desde_ano_anterior.toLowerCase() === "true" ||
    p.nao_somar_em_agregados.toLowerCase() === "true" ||
    p.perimetroBridgeId.trim() !== ""
  )) continue;
  const valores = pontos.map((p) => Number(p.valor));
  const tendenciaLinear = Array.from({ length: 5 }, (_, i) => tendencia(valores, i + 4));
  const maePersistencia = Math.abs(valores[2] - valores[3]);
  const maeTendencia = Math.abs(tendencia(valores.slice(0, 3), 3) - valores[3]);
  const primeira = pontos[0];
  series.push([
    Number(primeira.dist), primeira.empresa, primeira.conceitoId, primeira.metrica,
    primeira.unidade, valores, tendenciaLinear, [maePersistencia, maeTendencia],
    pontos.map((p) => p.publicacao_id), pontos.map((p) => p.status_homologacao),
    pontos.map((p) => p.estado === "zero_verificado" ? "Z" : "O"),
  ]);
}
series.sort((a, b) => a[0] - b[0] || a[2].localeCompare(b[2]));
const produto = {
  versao: "cenarios-bdgd-exploratorios-1.0.1+republicacao-editorial-1",
  origem: "ANEEL/BDGD; contrato-nacional-1.0.1+republicacao-editorial-1",
  commitOrigem,
  blobShaOrigem,
  anosObservados: [2022, 2023, 2024, 2025],
  anosSimulados: [2026, 2027, 2028, 2029, 2030],
  numeroOrigensBacktest: 1,
  previsaoValidada: false,
  legendaEstado: { O: "observado", Z: "zero_verificado (auditoria independente pendente)" },
  campos: [
    "dist", "empresa", "conceitoId", "metrica", "unidade", "historico", "tendenciaLinear",
    "erros2025PersistenciaTendencia", "publicacaoIds2022a2025", "homologacao2022a2025",
    "estadoHistorico2022a2025",
  ],
  series,
};
const conteudo = JSON.stringify(produto);
// Sem alterar a matriz nem homologar fontes: transporta os estados explícitos
// do contrato, inclusive DIST/ano sem publicação que não estão no pacote 2025.
const estados = {};
for (const r of linhas) {
  (estados[r.conceitoId] ??= []).push([
    Number(r.dist), Number(r.ano), r.estado, r.tipo_lacuna,
    r.nao_somar_em_agregados === "true",
  ]);
}
const conteudoEstados = JSON.stringify({ commitOrigem, blobShaOrigem, celulas: estados });
if (process.argv.includes("--check")) {
  if (readFileSync(saida, "utf8") !== conteudo || readFileSync(saidaEstados, "utf8") !== conteudoEstados) {
    console.error("Cenários publicados divergem do contrato; regenere com este script.");
    process.exit(1);
  }
  console.log("CENARIOS EXPLORATORIOS OK: " + series.length + " séries, blob " + blobShaOrigem);
} else {
  mkdirSync(dirname(saida), { recursive: true });
  writeFileSync(saida, conteudo);
  writeFileSync(saidaEstados, conteudoEstados);
  console.log("Geradas " + series.length + " séries condicionais, origem " + commitOrigem);
}
