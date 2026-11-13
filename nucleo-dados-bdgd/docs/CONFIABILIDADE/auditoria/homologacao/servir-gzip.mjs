/** Servidor estático mínimo para o E2E local sobre out/ (alternativa ao `serve`, que no Windows esgota descritores: EMFILE).
 *
 *   node scripts/servir-estatico.mjs [out] [3231]
 *   PW_BASE_URL=http://127.0.0.1:3231 npx playwright test
 *
 * Lê cada arquivo inteiro (sem streams abertos), resolve diretórios para index.html (trailingSlash) e devolve 404.html.
 * Só escuta em 127.0.0.1. Não é usado em produção. */
import { createServer } from "node:http";
import { gzipSync } from "node:zlib";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize, resolve, sep } from "node:path";

const raiz = resolve(process.argv[2] ?? "out");
const porta = Number(process.argv[3] ?? 3231);
const TIPOS = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2", ".gz": "application/gzip",
  ".geojson": "application/geo+json", ".csv": "text/csv; charset=utf-8", ".webmanifest": "application/manifest+json", ".pbf": "application/x-protobuf",
};

async function arquivo(caminho) {
  const alvo = resolve(join(raiz, normalize(decodeURIComponent(caminho))));
  if (alvo !== raiz && !alvo.startsWith(raiz + sep)) return null;
  try {
    const st = await stat(alvo);
    if (st.isDirectory()) return arquivo(join(caminho, "index.html"));
    return alvo;
  } catch { return null; }
}

createServer(async (req, res) => {
  try {
    const url = new URL(req.url ?? "/", "http://x");
    let alvo = await arquivo(url.pathname);
    let codigo = 200;
    if (!alvo) { alvo = await arquivo("/404.html"); codigo = 404; }
    if (!alvo) { res.writeHead(404).end(); return; }
    let corpo = await readFile(alvo); const comprimir = /gzip/.test(req.headers["accept-encoding"] ?? "") && /.(html|js|css|json|svg|txt|geojson|webmanifest)$/.test(alvo); if (comprimir) corpo = gzipSync(corpo);
    res.writeHead(codigo, { "Content-Type": TIPOS[extname(alvo)] ?? "application/octet-stream", "Content-Length": corpo.length, "Cache-Control": "no-store", ...(comprimir ? { "Content-Encoding": "gzip", Vary: "Accept-Encoding" } : {}) });
    res.end(req.method === "HEAD" ? undefined : corpo);
  } catch (e) {
    res.writeHead(500).end(String(e));
  }
}).listen(porta, "127.0.0.1", () => console.log(`servindo ${raiz} em http://127.0.0.1:${porta}`));
