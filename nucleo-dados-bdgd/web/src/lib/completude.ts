/** Completude dos cenários de uma série (regra única para o produto público e o Motor V2).
 *
 *  COMPLETA      os três cenários (Conservador, Moderado, Agressivo) publicados com os 5 anos;
 *  PARCIAL       o Moderado publicado e um ou os dois extremos não publicados, cada um com o motivo;
 *  SEM_PREVISAO  nenhum cenário publicável: a projeção não é exibida (cenários incompletos), só o histórico e o motivo.
 *
 *  Extremo sem Moderado não existe: os extremos são definidos em relação ao Moderado, e os produtos recusam esse estado. */
export type Completude = "COMPLETA" | "PARCIAL" | "SEM_PREVISAO";

export const ROTULO_COMPLETUDE: Record<Completude, string> = {
  COMPLETA: "Três cenários publicados",
  PARCIAL: "Previsão parcial",
  SEM_PREVISAO: "Cenários incompletos: previsão não publicada",
};

export interface CompletudeSerie<C extends string> {
  estado: Completude;
  publicados: C[];
  /** Motivo de cada cenário não publicado, em linguagem do usuário. */
  naoPublicados: [C, string][];
}

/** Estado a partir dos cenários publicados; lança erro para extremo publicado sem o Moderado (estado inconsistente). */
export function estadoCompletude<C extends string>(ordem: readonly C[], moderado: C, publicados: readonly C[], onde = "série"): Completude {
  if (publicados.length && !publicados.includes(moderado)) throw Error(`Cenário extremo publicado sem o Moderado em ${onde}.`);
  return publicados.length === ordem.length ? "COMPLETA" : publicados.length ? "PARCIAL" : "SEM_PREVISAO";
}

/** Frase curta para cards, legenda do gráfico e legenda da tabela: "Previsão parcial · 1 de 3 cenários publicados (Moderado)". */
export function resumoCompletude<C extends string>(c: CompletudeSerie<C>, rotulo: (x: C) => string, total = 3): string {
  if (c.estado === "SEM_PREVISAO") return `${ROTULO_COMPLETUDE.SEM_PREVISAO} · 0 de ${total} cenários`;
  return `${ROTULO_COMPLETUDE[c.estado]} · ${c.publicados.length} de ${total} cenários publicados (${c.publicados.map(rotulo).join(", ")})`;
}
