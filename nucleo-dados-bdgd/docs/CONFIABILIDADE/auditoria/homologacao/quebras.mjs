import { readFileSync } from "node:fs";
const raiz = process.argv[2];
const { quebrasQuantis } = await import(`file:///${raiz}/src/lib/confiabilidade/escala.ts`);
const { linhasNacionais } = await import(`file:///${raiz}/src/lib/confiabilidade/calculo.ts`);
const out = {};
for (const a of [2022, 2023, 2024, 2025]) {
  const t = JSON.parse(readFileSync(`${raiz}/public/data/confiabilidade/nacional/${a}.json`, "utf8"));
  const l = linhasNacionais(t);
  out[a] = { dec: quebrasQuantis(l.map((x) => x.dec)), fec: quebrasQuantis(l.map((x) => x.fec)) };
}
console.log(JSON.stringify(out));
