import type { Metric } from "./types";

/** Camada semântica: nomes de negócio, conceitos de ativos e indicadores com explicação em dois níveis.
 *  O código técnico BDGD continua disponível para especialistas, mas não é o nome primário. */

export const NOME_NEGOCIO: Record<string, string> = {
  UCBT: "Consumidores de baixa tensão", UCMT: "Consumidores de média tensão", UCAT: "Consumidores de alta tensão",
  UGBT: "Geração conectada em baixa tensão", UGMT: "Geração conectada em média tensão", UGAT: "Geração conectada em alta tensão",
  SSDBT: "Rede de baixa tensão", SSDMT: "Rede de média tensão", SSDAT: "Rede de alta tensão", RAMLIG: "Ramais de ligação", SEGCON: "Tipos de condutor",
  UNTRMT: "Transformadores MT/BT — instalações", UNTRAT: "Transformadores AT — instalações",
  EQTRMT: "Transformadores MT/BT — equipamentos", EQTRAT: "Transformadores AT — equipamentos", EQTRM: "Transformadores de medida",
  UNSEBT: "Seccionamento BT — instalações", UNSEMT: "Seccionamento MT — instalações", UNSEAT: "Seccionamento AT — instalações", EQSE: "Chaves, disjuntores e religadores — equipamentos",
  UNREMT: "Reguladores MT — instalações", UNREAT: "Reguladores AT — instalações", EQRE: "Reguladores de tensão — equipamentos",
  UNCRBT: "Compensação de reativos BT — instalações", UNCRMT: "Compensação de reativos MT — instalações", UNCRAT: "Compensação de reativos AT — instalações", EQCR: "Capacitores e compensadores — equipamentos",
  EQME: "Medidores", PONNOT: "Estruturas e pontos notáveis", PIP: "Pontos de iluminação pública",
  SUB: "Subestações", CTMT: "Circuitos de média tensão", CTAT: "Circuitos de alta tensão", BAR: "Barramentos", BAY: "Bays (vãos de subestação)", CONJ: "Conjuntos de unidades consumidoras",
  PT: "Perdas técnicas", PNT: "Perdas não técnicas", BE: "Balanço de energia", EP: "Energia passante", CRVCRG: "Curvas de carga típicas", ARAT: "Área de atuação",
};
export const nomeNegocio = (ent: string, fallback?: string) => NOME_NEGOCIO[ent] ?? fallback ?? ent;

export interface Conceito {
  id: string;
  nome: string;
  descricao: string;
  entidades: string[];
  /** equipamento -> instalação: as duas visões descrevem a mesma população e nunca são somadas */
  pares?: Array<[string, string]>;
  /** recortes patrimoniais (TUC do MCPSE) válidos para o conceito */
  tucs?: Array<{ tuc: string; entidade: string; nome: string }>;
}

export const CONCEITOS: Conceito[] = [
  { id: "transformadores", nome: "Transformadores", descricao: "Transformação de tensão na distribuição (MT/BT) e na alta tensão. Instalações (UN) e equipamentos (EQ) são duas visões da mesma população.",
    entidades: ["UNTRMT", "EQTRMT", "UNTRAT", "EQTRAT"], pares: [["EQTRMT", "UNTRMT"], ["EQTRAT", "UNTRAT"]],
    tucs: [{ tuc: "565", entidade: "EQTRMT", nome: "Transformadores de distribuição (TUC 565)" }, { tuc: "570", entidade: "EQTRMT", nome: "Transformadores de força na rede MT (TUC 570)" }, { tuc: "570", entidade: "EQTRAT", nome: "Transformadores de força na alta tensão (TUC 570)" }] },
  { id: "redes", nome: "Redes", descricao: "Segmentos de rede por nível de tensão e ramais que ligam a rede às unidades consumidoras.", entidades: ["SSDMT", "SSDBT", "SSDAT", "RAMLIG"] },
  { id: "consumidores", nome: "Consumidores", descricao: "Unidades consumidoras por nível de tensão. A contagem principal usa códigos distintos validados.", entidades: ["UCBT", "UCMT", "UCAT"] },
  { id: "geracao", nome: "Geração conectada", descricao: "Unidades geradoras conectadas à rede da distribuidora (inclui micro e minigeração).", entidades: ["UGBT", "UGMT", "UGAT"] },
  { id: "seccionamento", nome: "Seccionamento e proteção", descricao: "Chaves, disjuntores e religadores: equipamentos e as instalações onde estão montados.",
    entidades: ["UNSEMT", "UNSEBT", "UNSEAT", "EQSE"], pares: [["EQSE", "UNSEMT"]],
    tucs: [{ tuc: "160", entidade: "EQSE", nome: "Chaves (TUC 160)" }, { tuc: "210", entidade: "EQSE", nome: "Disjuntores (TUC 210)" }, { tuc: "345", entidade: "EQSE", nome: "Religadores (TUC 345)" }] },
  { id: "regulacao", nome: "Regulação de tensão", descricao: "Reguladores de tensão: equipamentos e instalações.", entidades: ["UNREMT", "UNREAT", "EQRE"], pares: [["EQRE", "UNREMT"]],
    tucs: [{ tuc: "340", entidade: "EQRE", nome: "Reguladores de tensão (TUC 340)" }] },
  { id: "compensacao", nome: "Compensação de reativos", descricao: "Bancos de capacitores, compensadores e reatores.", entidades: ["UNCRMT", "UNCRBT", "UNCRAT", "EQCR"], pares: [["EQCR", "UNCRMT"]],
    tucs: [{ tuc: "125", entidade: "EQCR", nome: "Bancos de capacitores (TUC 125)" }] },
  { id: "medicao", nome: "Medição", descricao: "Medidores e transformadores de medida.", entidades: ["EQME", "EQTRM"] },
  { id: "estruturas", nome: "Estruturas e iluminação", descricao: "Estruturas da rede (postes e pontos notáveis) e pontos de iluminação pública.", entidades: ["PONNOT", "PIP"] },
  { id: "subestacoes", nome: "Subestações e circuitos", descricao: "Subestações, barramentos, bays e circuitos de média e alta tensão.", entidades: ["SUB", "BAR", "BAY", "CTMT", "CTAT", "CONJ"] },
  { id: "perdas", nome: "Perdas e balanço", descricao: "Registros de perdas e balanço energético declarados (não são ativos físicos).", entidades: ["PT", "PNT", "BE", "EP", "CRVCRG"] },
];

export interface Indicador {
  id: string;
  nome: string;
  /** frase curta, sem fórmula */
  resumo: string;
  /** explicação em linguagem direta */
  explicacao: string;
  /** cálculo técnico, sob demanda */
  tecnico: string;
  ent: string | null;
  metric: Metric;
  ressalva?: string;
  conceito: string;
}

const KM = "convertidos para quilômetros";
export const INDICADORES: Indicador[] = [
  { id: "uc", nome: "Unidades consumidoras", conceito: "consumidores", ent: null, metric: "quantidade",
    resumo: "Consumidores de baixa, média e alta tensão, contados uma vez cada.",
    explicacao: "Número de unidades consumidoras distintas da distribuidora, somando baixa, média e alta tensão sem contar duas vezes um código que apareça em mais de um nível. Distribuidoras com registros ativos conflitantes ficam sem valor.",
    tecnico: "Por DIST: união de COD_ID distintos de UCBT, UCMT e UCAT; soma entre DISTs. Válido quando a regra UC v2 aprova as três entidades (sem COD_ID nulo, SIT_ATIV em AT/DS, no máximo um AT por COD_ID)." },
  { id: "ssdmt", nome: "Rede de média tensão", conceito: "redes", ent: "SSDMT", metric: "extensao_km",
    resumo: "Extensão declarada da rede de média tensão.", explicacao: `Soma dos comprimentos declarados de todos os segmentos de rede de média tensão, ${KM}.`,
    tecnico: "SUM(SSDMT.COMP) / 1000, em decimal exato. Comprimento declarado pela distribuidora, não medido na geometria." },
  { id: "ssdbt", nome: "Rede de baixa tensão", conceito: "redes", ent: "SSDBT", metric: "extensao_km",
    resumo: "Extensão declarada da rede de baixa tensão.", explicacao: `Soma dos comprimentos declarados de todos os segmentos de rede de baixa tensão, ${KM}.`,
    tecnico: "SUM(SSDBT.COMP) / 1000, em decimal exato." },
  { id: "untrmt", nome: "Transformadores de distribuição", conceito: "transformadores", ent: "UNTRMT", metric: "quantidade",
    resumo: "Instalações de transformação de média para baixa tensão.", explicacao: "Número de instalações transformadoras de média tensão registradas. Cada instalação pode abrigar um ou mais equipamentos; por isso este número não é somado com a contagem de equipamentos.",
    tecnico: "COUNT(*) de UNTRMT. Equipamentos ficam em EQTRMT (vínculo UNI_TR_MT) e não são somados a este total.", ressalva: "Não equivale automaticamente à contagem patrimonial TUC 565 do BI VPE; ver Explorar ativos." },
  { id: "eqtrmt", nome: "Potência de transformação MT/BT", conceito: "transformadores", ent: "EQTRMT", metric: "potencia_kva",
    resumo: "Potência nominal dos transformadores de média tensão.", explicacao: "Soma da potência nominal dos equipamentos transformadores de média tensão, segundo a tabela de potências do dicionário de dados da ANEEL.",
    tecnico: "SUM(TPOTAPRT.POT) via código EQTRMT.POT_NOM (DDA M10), em kVA; exibido em MVA quando grande.", ressalva: "Não somar com a potência das instalações (UNTRMT): é a mesma população." },
  { id: "ugbt", nome: "Geração conectada em BT", conceito: "geracao", ent: "UGBT", metric: "quantidade",
    resumo: "Unidades geradoras conectadas na baixa tensão.", explicacao: "Número de unidades geradoras registradas na baixa tensão, como sistemas fotovoltaicos de micro e minigeração.",
    tecnico: "COUNT(*) de UGBT.", ressalva: "A potência instalada das unidades geradoras não está homologada (unidade do campo POT_INST sem comprovação)." },
  { id: "ssdat", nome: "Rede de alta tensão", conceito: "redes", ent: "SSDAT", metric: "extensao_km",
    resumo: "Extensão declarada da rede de alta tensão.", explicacao: `Soma dos comprimentos declarados dos segmentos de rede de alta tensão, ${KM}.`, tecnico: "SUM(SSDAT.COMP) / 1000." },
  { id: "ramlig", nome: "Ramais de ligação", conceito: "redes", ent: "RAMLIG", metric: "extensao_km",
    resumo: "Extensão declarada dos ramais de ligação.", explicacao: `Soma dos comprimentos declarados dos ramais que ligam a rede às unidades consumidoras, ${KM}.`, tecnico: "SUM(RAMLIG.COMP) / 1000." },
  { id: "sub", nome: "Subestações", conceito: "subestacoes", ent: "SUB", metric: "quantidade", resumo: "Subestações registradas.", explicacao: "Número de subestações registradas pela distribuidora.", tecnico: "COUNT(*) de SUB." },
  { id: "ctmt", nome: "Circuitos de média tensão", conceito: "subestacoes", ent: "CTMT", metric: "quantidade", resumo: "Circuitos (alimentadores) de média tensão.", explicacao: "Número de circuitos de média tensão (alimentadores) registrados.", tecnico: "COUNT(*) de CTMT." },
  { id: "ctat", nome: "Circuitos de alta tensão", conceito: "subestacoes", ent: "CTAT", metric: "quantidade", resumo: "Circuitos de alta tensão.", explicacao: "Número de circuitos de alta tensão registrados.", tecnico: "COUNT(*) de CTAT." },
  { id: "ugmt", nome: "Geração conectada em MT", conceito: "geracao", ent: "UGMT", metric: "quantidade", resumo: "Unidades geradoras na média tensão.", explicacao: "Número de unidades geradoras conectadas na média tensão.", tecnico: "COUNT(*) de UGMT.", ressalva: "Potência instalada não homologada." },
  { id: "untrat", nome: "Transformadores de alta tensão", conceito: "transformadores", ent: "UNTRAT", metric: "quantidade", resumo: "Instalações transformadoras de alta tensão.", explicacao: "Número de instalações transformadoras de alta tensão (subestações de força).", tecnico: "COUNT(*) de UNTRAT." },
  { id: "eqtrat", nome: "Potência de transformação AT", conceito: "transformadores", ent: "EQTRAT", metric: "potencia_kva", resumo: "Potência nominal dos transformadores de alta tensão.", explicacao: "Soma da potência nominal dos equipamentos transformadores de alta tensão.", tecnico: "SUM(TPOTAPRT.POT) via EQTRAT.POT_NOM (DDA M10).", ressalva: "Não somar com UNTRAT." },
  { id: "eqse", nome: "Chaves, disjuntores e religadores", conceito: "seccionamento", ent: "EQSE", metric: "quantidade", resumo: "Equipamentos de seccionamento e proteção.", explicacao: "Número de equipamentos de seccionamento e proteção (chaves, disjuntores e religadores). Uma instalação pode ter mais de um equipamento.", tecnico: "COUNT(*) de EQSE." },
  { id: "eqre", nome: "Reguladores de tensão", conceito: "regulacao", ent: "EQRE", metric: "quantidade", resumo: "Equipamentos reguladores de tensão.", explicacao: "Número de equipamentos reguladores de tensão registrados.", tecnico: "COUNT(*) de EQRE." },
  { id: "eqcr", nome: "Capacitores e compensadores", conceito: "compensacao", ent: "EQCR", metric: "quantidade", resumo: "Equipamentos de compensação de reativos.", explicacao: "Número de equipamentos de compensação de energia reativa (capacitores, compensadores, reatores).", tecnico: "COUNT(*) de EQCR." },
  { id: "eqme", nome: "Medidores", conceito: "medicao", ent: "EQME", metric: "quantidade", resumo: "Medidores registrados.", explicacao: "Número de medidores registrados na base.", tecnico: "COUNT(*) de EQME." },
  { id: "ponnot", nome: "Estruturas da rede", conceito: "estruturas", ent: "PONNOT", metric: "quantidade", resumo: "Postes, torres e demais pontos notáveis.", explicacao: "Número de estruturas e pontos notáveis da rede (postes, torres e similares).", tecnico: "COUNT(*) de PONNOT." },
  { id: "pip", nome: "Iluminação pública", conceito: "estruturas", ent: "PIP", metric: "quantidade", resumo: "Pontos de iluminação pública.", explicacao: "Número de pontos de iluminação pública atendidos pela distribuidora.", tecnico: "COUNT(*) de PIP." },
];

export const INDICADOR_PADRAO = ["uc", "ssdmt", "ssdbt", "untrmt", "eqtrmt", "ugbt"];
export const PRESETS_INDICADORES: Array<{ id: string; nome: string; ids: string[] }> = [
  { id: "essenciais", nome: "Essenciais", ids: INDICADOR_PADRAO },
  { id: "redes", nome: "Redes", ids: ["ssdmt", "ssdbt", "ssdat", "ramlig", "ctmt", "ctat"] },
  { id: "transformacao", nome: "Transformação", ids: ["untrmt", "eqtrmt", "untrat", "eqtrat", "sub", "eqre"] },
  { id: "operacao", nome: "Proteção e operação", ids: ["eqse", "eqre", "eqcr", "eqme", "sub", "ctmt"] },
  { id: "clientes", nome: "Clientes e geração", ids: ["uc", "ugbt", "ugmt", "pip", "ramlig", "eqme"] },
];
export const indicador = (id: string) => INDICADORES.find((i) => i.id === id);

/** Descrições MCPSE (Resolução ANEEL 674/2015, Tabela I) presentes no catálogo local; TUC ausente aqui não recebe nome inventado. */
export const TUC_NOME: Record<string, string> = {
  "125": "Banco de capacitores paralelo", "135": "Barramento", "160": "Chave", "165": "Compensador de reativos", "210": "Disjuntor", "295": "Medidor",
  "325": "Protetor de rede", "330": "Reator (ou resistor)", "340": "Regulador de tensão", "345": "Religador", "540": "Subestação SF6",
  "545": "Subestação unitária", "560": "Transformador de aterramento", "565": "Transformador de distribuição", "570": "Transformador de força", "575": "Transformador de medida",
};
export function tucNome(tuc: string) {
  if (tuc === "SEM_CODIGO") return "Sem TUC informada";
  const n = TUC_NOME[tuc];
  return n ? `${n} (TUC ${tuc})` : `TUC ${tuc} (sem descrição no catálogo MCPSE local)`;
}
