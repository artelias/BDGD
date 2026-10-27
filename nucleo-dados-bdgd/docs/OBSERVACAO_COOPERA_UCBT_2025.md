## Coopera (DIST 5370) — BDGD 2025

- Competência: `2025-12-31`.
- Fonte única encontrada no inventário ArcGIS/ANEEL de 25/10/2026: `Coopera_5370_2025-12-31_V11_20260822-0914.gdb.zip`, item `5d0f7ea5db5d48aeb365998fabaa9db7`.
- UCBT: **0 registros na publicação**, apresentado exclusivamente como `0*`; não é zero físico nem zero técnico comprovado.
- UCMT 2025: 224 AT, 18 DS; UCAT: 1 AT, 0 DS. Total observado AT de média e alta tensão = **225**, PARCIAL.
- Total de consumidores AT do ano: **N/D** por ausência de UCBT, apesar do legado apresentar `225` no pacote de conceitos. Não habilitar CAGR, crescimento, agregação nacional ou treino com 225 como se fosse total completo.
- Uma publicação adicional de 2025 **não foi encontrada** no catálogo arquivado. Nova publicação posterior ainda precisa de verificação em tempo real.

## Exibição

Na visão histórica, exibir `0*` para a **entidade UCBT** em nota de rodapé. `225*` refere-se exclusivamente ao subtotal observado em UCMT + UCAT e não substitui o total BT+MT+AT, que permanece N/D até reconciliação do contrato histórico.
O símbolo `*` deve explicar, no final das páginas, o arquivo, a competência, a ausência de registros, a hipótese (não comprovada) de omissão cadastral e o estado de validação.

## Método preditivo proposto: KNN/análogos exógenos

O método **não está treinado, nem homologado**. Nunca alimentar a célula ausente ou `0*` como alvo numérico zero. Para obter uma estimativa de referência:

1. Estabelecer uma âncora de UCBT na última competência observada e válida da Coopera (por exemplo, 2024), respeitando o perímetro.
2. Integrar séries externas verificadas — SAMP/ANEEL (energia e mercado por distribuidora), população e economia dos municípios atendidos/IBGE, e cenários de consumo da EPE; vincular fonte, divulgação, data de referência e compatibilidade territorial.
3. Usar k-vizinhos **distribuidoras comparáveis** em atributos de porte, perfil de consumo, crescimento do mercado, localização/território e estrutura da rede. Escalonar atributos nos dados de treino; ajustar k e métrica por validação temporal, sem ajustar com anos futuros.
4. Estimar a **taxa de evolução** BT com análogos, aplicar à âncora 2024, produzir cenários e faixas por dispersão dos vizinhos. Não usar medidores ou postes de 2025 para simular covariáveis se o ponto de previsão não conheceria esses valores.
5. Comparar contra baseline de persistência, abordagem exógena regularizada e histórico anterior (2019–2024, quando apto). Usar leave-one-distributor-out e backtest temporal; registrar número de vizinhos e qualidade do de/para.
6. Publicar num painel separado e rotulado como **estimativa não homologada**, nunca como observado, sem misturar com os estoques oficiais ou substituir original/Parquet.

## Restrições

Não alterar GDBs, ZIPs, Parquets ou hashes originais; não gerar estimativa numérica sem variáveis externas reais. A correção de integridade da série de consumidores, incluindo projeções e agregações, requer republicação dos derivados após o ETL aprovar o novo estado de cobertura parcial.

Fonte dos quantitativos: `auditoria/fase4/evidencias/investigacao_casos.json`, `auditoria/fase4/RANKING_ANOMALIAS_TEMPORAIS.csv`, catálogo `auditoria/fase6/evidencias/catalogo_arcgis_atual.json`.