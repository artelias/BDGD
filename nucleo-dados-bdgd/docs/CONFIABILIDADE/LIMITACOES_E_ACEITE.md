# Limitações e critérios de aceite

## Limitações conhecidas

**Dados**
* DEC/FEC são oficiais; a infraestrutura por conjunto é **derivada e exploratória** (declarada pelas distribuidoras na
  BDGD, agregada aqui, não homologada). A potência nominal (kVA) tem escala inconsistente entre distribuidoras.
* A BDGD é a fotografia de 31/12; o DEC/FEC é apurado ao longo do ano. Mudanças no meio do ano não aparecem.
* Polígonos só de 31/12/2025: conjuntos extintos antes disso ficam sem mapa (aparecem na lista com aviso). Os Parquets
  2022–2024 foram convertidos sem geometria.
* A reconstrução por DIC/FIC usa critério experimental de 5% / 0,05; 82 combinações DIST × ano × indicador (34 empresas)
  ficam abaixo de 80% reconciliados (detalhe em FORMULAS_E_RECONCILIACAO.md). O valor oficial nunca é substituído.
* Consumidores somados por conjunto diferem levemente da união do portal (EPB +22, ESE +10, EAC −4 em 2025).
* A proveniência ANEEL gravada antes de 12/11/2026 registra a identidade DEC = soma de quatro componentes; a correta é
  DEC = DECIP + DECIND (corrigido no código; vale na próxima preparação). Nenhum valor publicado dependia dela.

**Estatística**
* Observacional: associação não é causa; causalidade reversa é plausível (religadores onde o DEC já era alto).
* Clima, vegetação, descargas, idade de ativos, manutenção e automação efetiva não estão nos dados. O R² fora da amostra
  é 0,43–0,53 (DEC) e 0,31–0,42 (FEC).
* Quatro anos não bastam para precedência temporal robusta; variações sofrem com mudanças cadastrais.

**Interface**
* O agregado da distribuidora é derivado (ponderado por NumCon) e pode diferir em centésimos do global ANEEL.
* O arquivo nacional do ano (~1 MB; 479 kB com gzip) é baixado no comparador, no benchmarking e na escala
  "Conjuntos do Brasil"; a maior distribuidora (4950) baixa 3,1 MB + 1,5 MB de geometria (596 + 433 kB com gzip).
* O texto de ajuda do ECharts sobre `grid.containLabel` aparece no console (padrão herdado do portal, nível `log`, não erro).

## Critérios de aceite da homologação

| # | Critério | Como verificar | Situação em 12/11/2026 |
|---|---|---|---|
| 1 | `/confiabilidade` responde 200, renderiza, sobrevive a recarga, sem exceção nem erro de console | e2e "P0: responde 200, sobrevive a recarga…" | atendido |
| 2 | Só dados reais; nenhum demonstrativo | auditoria A3 (`demonstrativo: false`), Vitest "índice real" | atendido |
| 3 | Manifesto íntegro | auditoria A1 (204 arquivos, 0 divergentes) | atendido |
| 4 | Chave DIST + CONJ + ano única; conjunto em uma só distribuidora por ano | auditoria A2 (12.502 chaves, 0 duplicadas) | atendido |
| 5 | Totais de infraestrutura do piloto = portal (EPB 6600, ESE 6587, EAC 26) | auditoria A4 | atendido (consumidores com diferença documentada) |
| 6 | Zero observado × N/D corretos; supressão 1–4 preservada | testes Python e Vitest | atendido |
| 7 | Fórmulas PRODIST (soma mensal, ponderação por NumCon, componentes internas) | testes Python + Vitest + e2e da ficha | atendido |
| 8 | Reconciliação por DIST × ano × indicador publicada | `auditoria/RECONCILIACAO_…csv` | atendido (critério experimental) |
| 9 | Mapa: Brasil → distribuidora → conjunto, DEC/FEC, ano, mês, % do limite, legenda, hover, clique, zoom, volta ao Brasil | e2e "mapa:" e "alternar DEC/FEC…" | atendido |
| 10 | Ficha, comparador (CSV), benchmarking, fatores, metodologia | e2e | atendido |
| 11 | Celular sem rolagem horizontal; tema claro e escuro | e2e `@mobile` e "tema" | atendido |
| 12 | Frases sem linguagem causal | Vitest + e2e | atendido |
| 13 | Estatística reprodutível, com vereditos pré-definidos e SEM_DADOS/INCONCLUSIVA quando cabe | `fatores.json`, teste de contrato, reexecução idêntica | atendido |
| 14 | `typecheck`, `lint`, `test`, `build`, `e2e` | RELATORIO_FINAL.md, seção 8 | atendido (e2e no build de homologação, como a CI) |
| 15 | RC, produção, Motor de Expansão e bases BDGD intocados; sem merge nem deploy | `git log`, nenhum push fora da branch | atendido |
| 16 | Revisão de conteúdo por especialista de regulação (componentes, expurgos, limites) | homologação humana | **pendente** |
