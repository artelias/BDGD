/** Confere os assets reais declarados pelo manifesto web, sem alterar a origem. */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const base = resolve(web, "public/data/2025-12-31");
const ler = (path) => JSON.parse(readFileSync(path, "utf8"));
const assets = ler(resolve(base, "assets.json"));
const index = ler(resolve(base, "index.json"));
const manifest = ler(resolve(web, "../output-publicavel/2025-12-31/manifest.json"));
assert.equal(assets.release_id, manifest.release_id, "assets de outra release");
assert.equal(index.release.release_id, manifest.release_id, "index de outra release");
assert.equal(index.release.data_base, "2025-12-31");
assert.ok(Array.isArray(assets.arquivos) && assets.arquivos.length > 0, "lista de assets vazia");
assert.equal(new Set(assets.arquivos).size, assets.arquivos.length, "asset duplicado");
for (const nome of assets.arquivos) {
  const path = resolve(base, nome);
  assert.ok(path.startsWith(base + sep), "asset fora do diretório público");
  const dado = ler(path);
  if (dado.release_id !== undefined) assert.equal(dado.release_id, manifest.release_id, nome);
}
console.log(`ASSETS WEB OK: ${assets.arquivos.length} arquivos JSON legíveis, release ${manifest.release_id}. Validação estrutural não equivale a homologação humana.`);
