import { valorObservado, type SerieFisica } from "./previsoes-contrato";

/** Motor determinístico exploratório. Nunca transforma N/D em zero nem certifica previsões. */
export type MetodoCenario = "persistencia" | "tendencia_linear";
export interface PontoCenario {
  ano: number;
  valor: number;
  modo: "simulacao_condicional";
  metodo: MetodoCenario;
}
export interface DiagnosticoSerie {
  elegivel: boolean;
  motivos: string[];
  observacoes: number;
  anos: number[];
}
export interface ResultadoCenario {
  diagnostico: DiagnosticoSerie;
  pontos: PontoCenario[];
  metodo: MetodoCenario;
  backtest: { origens: number; maeModelo: number | null; maePersistencia: number | null };
}
function mesmaChave(a: SerieFisica, b: SerieFisica): boolean {
  return a.dist === b.dist && a.conceitoId === b.conceitoId &&
    a.metrica === b.metrica && a.unidade === b.unidade &&
    a.perimetroId === b.perimetroId && a.regraVersao === b.regraVersao;
}
function projetar(serie: { ano: number; valor: number }[], ano: number, metodo: MetodoCenario): number {
  const ultimo = serie[serie.length - 1];
  if (metodo === "persistencia" || serie.length < 3) return ultimo.valor;
  const n = serie.length;
  const mx = serie.reduce((s, p) => s + p.ano, 0) / n;
  const my = serie.reduce((s, p) => s + p.valor, 0) / n;
  const numerador = serie.reduce((s, p) => s + (p.ano - mx) * (p.valor - my), 0);
  const denominador = serie.reduce((s, p) => s + (p.ano - mx) ** 2, 0);
  const inclinacao = denominador ? numerador / denominador : 0;
  // Reta OLS com intercepto: passa pelas médias, não pelo último observado.
  return Math.max(0, my + inclinacao * (ano - mx));
}
export function gerarCenarioExploratorio(
  entrada: readonly SerieFisica[],
  anoFinal = 2030,
  metodo: MetodoCenario = "persistencia",
): ResultadoCenario {
  const motivos: string[] = [];
  if (!entrada.length) motivos.push("SEM_OBSERVACOES");
  const referencia = entrada[0];
  if (referencia && entrada.some((p) => !mesmaChave(p, referencia))) motivos.push("SERIES_INCOMPATIVEIS");
  const anos = entrada.map((p) => p.ano);
  if (new Set(anos).size !== anos.length) motivos.push("ANO_DUPLICADO");
  if (entrada.some((p) => !Number.isInteger(p.ano) || p.ano < 1900 || p.ano > 2100)) motivos.push("ANO_INVALIDO");
  if (entrada.some((p) => valorObservado(p) === null || (p.valor ?? -1) < 0)) motivos.push("OBSERVACAO_NAO_ELEGIVEL");
  if (entrada.some((p) => p.cobertura !== 1)) motivos.push("COBERTURA_INCOMPLETA");
  if (entrada.some((p) => p.perimetroBridgeId !== null)) motivos.push("PONTE_SOCietARIA_NAO_HOMOLOGADA");
  const ordenada = [...entrada].sort((a, b) => a.ano - b.ano);
  if (ordenada.some((p, i) => i > 0 && p.ano !== ordenada[i - 1].ano + 1)) motivos.push("LACUNA_TEMPORAL");
  if (entrada.length < 2) motivos.push("HISTORICO_INSUFICIENTE");
  if (ordenada.length && (!Number.isInteger(anoFinal) || anoFinal <= ordenada[ordenada.length - 1].ano || anoFinal > 2100)) motivos.push("HORIZONTE_INVALIDO");
  const diagnostico = { elegivel: motivos.length === 0, motivos, observacoes: entrada.length, anos: ordenada.map((p) => p.ano) };
  if (!diagnostico.elegivel) return { diagnostico, pontos: [], metodo, backtest: { origens: 0, maeModelo: null, maePersistencia: null } };
  const historico = ordenada.map((p) => ({ ano: p.ano, valor: valorObservado(p)! }));
  const errosModelo: number[] = [];
  const errosPersistencia: number[] = [];
  for (let i = 3; i < historico.length; i++) {
    const treino = historico.slice(0, i);
    errosModelo.push(Math.abs(projetar(treino, historico[i].ano, metodo) - historico[i].valor));
    errosPersistencia.push(Math.abs(treino[treino.length - 1].valor - historico[i].valor));
  }
  const media = (xs: number[]) => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
  const pontos: PontoCenario[] = [];
  for (let ano = historico[historico.length - 1].ano + 1; ano <= anoFinal; ano++) {
    pontos.push({ ano, valor: projetar(historico, ano, metodo), modo: "simulacao_condicional", metodo });
  }
  return { diagnostico, pontos, metodo, backtest: { origens: errosModelo.length, maeModelo: media(errosModelo), maePersistencia: media(errosPersistencia) } };
}
