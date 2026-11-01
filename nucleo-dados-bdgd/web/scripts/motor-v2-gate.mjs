/** Portão de publicação do Motor V2.
 *
 * O produto pré-calculado do Motor V2 (data-motor-v2/) é experimental e não homologado. Ele só entra em public/data/motor-v2/
 * numa build de homologação: NEXT_PUBLIC_MOTOR_V2=homologacao, ou uma build de preview da Vercel (VERCEL_ENV=preview).
 * Em produção a pasta é removida antes da build e a interface mostra apenas o aviso do portão. */
import { cpSync, existsSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const origem = resolve(web, "data-motor-v2");
const destino = resolve(web, "public/data/motor-v2");

function homologacao(env = process.env) {
  return env.NEXT_PUBLIC_MOTOR_V2 === "homologacao" || env.VERCEL_ENV === "preview";
}

rmSync(destino, { recursive: true, force: true });
if (homologacao()) {
  if (!existsSync(resolve(origem, "indice.json"))) throw new Error("Build de homologação sem data-motor-v2/indice.json.");
  cpSync(origem, destino, { recursive: true });
  console.log("MOTOR V2: build de homologação; produto experimental copiado para public/data/motor-v2.");
} else {
  console.log("MOTOR V2: build sem homologação; produto experimental fora de public/ (portão de publicação fechado).");
}
