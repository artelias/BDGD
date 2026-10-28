import { selecionarObservacoes, type ContextoObservacao } from '@/lib/observacoes';
import s from './observacoes-dados.module.css';
export function ObservacoesDados(props: ContextoObservacao) {
  const rows = selecionarObservacoes(props);
  if (!rows.length) return null;
  return <section className={s.section} aria-label="Observações e ressalvas dos dados" data-testid="observacoes-dados">
    <h2>Observações e ressalvas dos dados</h2>
    <p>As ressalvas abaixo correspondem ao recorte selecionado. Valores publicados, ausências cadastrais e estimativas têm naturezas diferentes.</p>
    {rows.map((n) => <details key={n.id} open={rows.length === 1}>
      <summary>{n.distribuidora} · DIST {n.dist} · {n.ano} · {n.ativo.replaceAll('_',' ')} · {n.metrica}</summary>
      <p><b>Publicado:</b> {n.valor_publicado.toLocaleString('pt-BR')}{n.valor_publicado === 0 && n.bloqueia_total ? ' — 0* cadastral; quantidade física N/D.' : n.estado === 'ausencia_cadastral' ? ' — subtotal parcial; total N/D. UCBT: 0* (tabela vazia), UCMT: 224 AT, UCAT: 1 AT.' : ''}</p>
      <p><b>Problema:</b> {n.problema}</p><p><b>Evidência técnica:</b> {n.evidencia_tecnica}</p>
      <p><b>Tratamento:</b> {n.tratamento}</p><p><b>Impacto na evolução e previsão:</b> {n.impacto_evolucao_previsao}</p>
      <p>Competência {n.competencia} · entidades {n.entidades.join(', ')}. <a href={`https://www.arcgis.com/home/item.html?id=${n.origem.item_id}`} target="_blank" rel="noreferrer">{n.origem.arquivo}</a> · versão {n.origem.versao}.</p>
      <p className={s.source}>Evidência: {n.origem.evidencia_arquivo}. SHA-256 do ZIP: <code>{n.origem.sha256_zip || 'Não registrado nesta auditoria'}</code>.</p>
    </details>)}
  </section>;
}
