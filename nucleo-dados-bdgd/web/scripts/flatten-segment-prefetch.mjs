// Export estático do Next 16: os arquivos de prefetch por segmento são gravados como
// "<rota>/__next.<seg>/__PAGE__.txt", mas o roteador cliente os requisita como
// "<rota>/__next.<seg>.__PAGE__.txt". Sem esta cópia, cada prefetch retorna 404 e a
// navegação cai no carregamento completo. Cria cópias com o nome plano esperado.
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.argv[2] ?? "out");
let n = 0;
function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (!e.isDirectory()) continue;
    if (e.name.startsWith("__next.")) flatten(p, dir, e.name);
    else if (e.name !== "_next" && e.name !== "data") walk(p);
  }
}
function flatten(segDir, parent, prefix, rel = "") {
  for (const e of fs.readdirSync(path.join(segDir, rel), { withFileTypes: true })) {
    const r = rel ? `${rel}/${e.name}` : e.name;
    if (e.isDirectory()) flatten(segDir, parent, prefix, r);
    else { fs.copyFileSync(path.join(segDir, r), path.join(parent, `${prefix}.${r.replaceAll("/", ".")}`)); n++; }
  }
}
walk(root);
console.log(`prefetch de segmentos: ${n} arquivo(s) com nome plano`);
