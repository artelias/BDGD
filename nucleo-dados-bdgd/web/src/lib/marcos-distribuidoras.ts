/** Marcos editoriais curados: ano de referência != data de divulgação. Sem fonte, não publicar. */
export interface MarcoDistribuidora {
  dist: number;
  anoReferencia: number;
  dataDivulgacao: string;
  titulo: string;
  descricao: string;
  categoria: "reconhecimento" | "regulatorio" | "investimento" | "ouvidoria";
  fonte: string;
  fonteNome: string;
}
export const MARCOS_DISTRIBUIDORAS: readonly MarcoDistribuidora[] = [
  { dist: 6600, anoReferencia: 2025, dataDivulgacao: "2026-03-25",
    titulo: "Melhor concessionária do Brasil no IASC 2025",
    descricao: "Vencedora da categoria principal de concessionárias com mais de 500 mil unidades consumidoras. Resultado da pesquisa de 2025, premiado em março de 2026.",
    categoria: "reconhecimento", fonteNome: "ANEEL — comunicado oficial",
    fonte: "https://pt.linkedin.com/posts/aneel_a-aneel-realizou-nesta-quarta-feira-25-activity-7442678978093543425-hqK9" },
  { dist: 32, anoReferencia: 2025, dataDivulgacao: "2026-03-25",
    titulo: "Melhor distribuidora da Região Norte no IASC 2025",
    descricao: "Energisa Tocantins venceu a categoria regional Norte da pesquisa IASC 2025; premiação realizada em março de 2026.",
    categoria: "reconhecimento", fonteNome: "Energisa — resultado da premiação",
    fonte: "https://www.energisa.com.br/noticias/energia-que-transforma/energisa-paraiba-e-tricampea-do-premio-aneel-de-satisfacao-do" },
  { dist: 404, anoReferencia: 2025, dataDivulgacao: "2026-03-25",
    titulo: "Melhor distribuidora do Centro-Oeste no IASC 2025",
    descricao: "Energisa Mato Grosso do Sul venceu a categoria regional Centro-Oeste; premiação realizada em março de 2026.",
    categoria: "reconhecimento", fonteNome: "Energisa — resultado da premiação",
    fonte: "https://www.energisa.com.br/noticias/energia-que-transforma/energisa-paraiba-e-tricampea-do-premio-aneel-de-satisfacao-do" },
];
export function marcosDaDistribuidora(dist: number, ano = 2025): MarcoDistribuidora[] {
  return MARCOS_DISTRIBUIDORAS.filter((m) => m.dist === dist && m.anoReferencia === ano && /^https:\/\//.test(m.fonte));
}
