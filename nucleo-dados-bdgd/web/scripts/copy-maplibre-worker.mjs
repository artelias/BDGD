// Copia o worker oficial do MapLibre para /public (servido como estático, com versão no nome para cache imutável).
import fs from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const pkg = require("maplibre-gl/package.json");
const src = new URL("../node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs", import.meta.url);
fs.mkdirSync(new URL("../public/maplibre/", import.meta.url), { recursive: true });
fs.copyFileSync(src, new URL(`../public/maplibre/maplibre-gl-worker-${pkg.version}.mjs`, import.meta.url));
fs.writeFileSync(new URL("../src/lib/maplibre-version.ts", import.meta.url), `// gerado por scripts/copy-maplibre-worker.mjs\nexport const MAPLIBRE_WORKER_URL = "/maplibre/maplibre-gl-worker-${pkg.version}.mjs";\n`);
console.log("worker MapLibre", pkg.version);
