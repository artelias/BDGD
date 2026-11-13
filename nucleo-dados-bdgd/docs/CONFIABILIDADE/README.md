# Módulo de Inteligência de Confiabilidade (DEC/FEC × infraestrutura)

Rota pública: `/confiabilidade`. Branch: `feat/inteligencia-confiabilidade-dec-fec-20261111`.
Estado: **pronto para homologação** (não integrado à RC `rc/1.0-20261101`, sem merge e sem deploy).

| Documento | Conteúdo |
|---|---|
| [ARQUITETURA.md](ARQUITETURA.md) | camadas, fluxo de dados, contrato do produto público, frontend |
| [FONTES_E_GEOMETRIA.md](FONTES_E_GEOMETRIA.md) | ANEEL (DEC/FEC, limites), BDGD (infraestrutura), polígonos dos conjuntos |
| [FORMULAS_E_RECONCILIACAO.md](FORMULAS_E_RECONCILIACAO.md) | PRODIST Módulo 8, agregação, componentes, zero × N/D, reconciliação DIC/FIC |
| [METRICAS_COMPARADOR_BENCHMARKING.md](METRICAS_COMPARADOR_BENCHMARKING.md) | dicionário de métricas, comparador A × B, pares semelhantes, rankings |
| [MODELOS_ESTATISTICOS.md](MODELOS_ESTATISTICOS.md) | estudo de fatores associados, hipóteses H1–H7, resultados |
| [TESTES_E_DESEMPENHO.md](TESTES_E_DESEMPENHO.md) | Python, Vitest, Playwright, auditoria; tamanhos e carregamento |
| [OPERACAO.md](OPERACAO.md) | comandos de atualização, nova distribuidora, novo ano |
| [LIMITACOES_E_ACEITE.md](LIMITACOES_E_ACEITE.md) | limitações conhecidas e critérios de aceite da homologação |
| [RELATORIO_FINAL.md](RELATORIO_FINAL.md) | relatório da retomada: P0, correções, evidências, pendências |
| [CHECKLIST_REGULATORIO.md](CHECKLIST_REGULATORIO.md) | checklist para o especialista em regulação (decisão e assinatura em branco) |
| [HOMOLOGACAO_TECNICA.md](HOMOLOGACAO_TECNICA.md) | auditoria final de homologação: matriz, defeitos corrigidos, CI, recomendação |
| `auditoria/` | saída de `python -m confiabilidade.auditoria` (JSON + CSV por DIST × ano × indicador) |

Regra que atravessa tudo: **associação não é causa**. O módulo descreve diferenças e associações; nenhuma tela ou
documento afirma efeito de uma intervenção.
