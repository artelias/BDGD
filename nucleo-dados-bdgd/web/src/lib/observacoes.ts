import data from './observacoes-dados.json';
export interface ContextoObservacao { dists?: Array<number | string>; anos?: number[]; ativos?: string[]; metricas?: string[]; filtro?: Record<string, string[]> }
export const observacoes = data.observacoes;
export function selecionarObservacoes(c: ContextoObservacao = {}) {
  return observacoes.filter((n) => (!c.dists || c.dists.map(String).includes(String(n.dist))) &&
    (!c.anos || c.anos.includes(n.ano)) && (!c.ativos || c.ativos.includes(n.ativo) || c.ativos.includes(n.conceito)) &&
    (!c.metricas || c.metricas.includes(n.metrica)) && Object.entries(n.recorte_afetado).every(([dim, codes]) =>
      !c.filtro?.[dim]?.length || codes?.some((code: string) => c.filtro![dim].includes(code))));
}
export const COLUNAS_OBSERVACOES = ['observacoes_ids','observacoes_e_ressalvas','valor_publicado_fonte','subtotal_observado','arquivo_origem','versao_origem'];
export function camposObservacoes(c: ContextoObservacao) {
  const rows = selecionarObservacoes(c);
  return [rows.map((n) => n.id).join(' | '),rows.map((n) => `${n.distribuidora} (${n.dist}), ${n.competencia}: ${n.problema} ${n.tratamento} ${n.impacto_evolucao_previsao}`).join(' | '),
    rows.map((n) => `${n.id}=${n.valor_publicado}`).join(' | '),rows.filter((n) => n.subtotal_observado !== null).map((n) => String(n.subtotal_observado)).join(' | '),
    rows.map((n) => n.origem.arquivo).join(' | '),rows.map((n) => n.origem.versao).join(' | ')];
}
