# Parecer — Recuperação nacional BDGD 2022–2025 (Fase 6, Frente A)

**Data:** 25/10/2026 · **Base:** branch `feat/dashboard-bdgd-2025` (PR #4) a partir de `de15f98`. Nenhum checkpoint foi alterado, nenhum dado bruto foi modificado e nenhuma decisão humana foi tomada.

## 1. Escopo investigado
- **114 códigos de distribuidora** (todos os do inventário histórico e do pacote 2025, incluindo códigos de distribuidoras já incorporadas), **4 competências**, **25 ativos**: **11.400 células**.
- Catálogo oficial ANEEL/ArcGIS consultado de novo em 25/10/2026: 1.014 itens, nenhum novo ou alterado desde 23/10/2026 (`evidencias/catalogo_arcgis_atual.json`).

## 2. Resultado por causa (`INVENTARIO_LACUNAS_NACIONAL.csv`)
| Causa | Células | Recuperável? |
|---|---|---|
| Disponível (homologado, completo técnico ou apto com ressalvas) | 8.698 | — |
| Sucessão societária | 1.150 | Não é lacuna: perímetro reportado pela sucessora |
| Ativo não aplicável | 623 | Não (N/D legítimo) |
| Republicações divergentes | 325 | Decisão humana (13 pares) |
| Bloqueio por competência | 300 | Não, sem evidência para reatribuir o ano |
| Publicação não localizada | 275 | Não: inexistente no catálogo oficial |
| BASE inconsistente | 25 | Decisão humana (Coprel 2023) |
| Entidade vazia na origem | 3 | Decisão humana (bloquear até republicação) |
| Publicação incompleta na origem | 1 | Decisão humana |
| ZIP não baixado / corrompido / GDB não processado / falha de ETL / Parquet sem JSON | **0** | — |

**Células ausentes (exceto sucessão e não aplicável): 929. Recuperadas: 0. Recuperáveis tecnicamente sem decisão humana: 0.** Todas as causas técnicas corrigíveis foram verificadas e não ocorrem. O que falta é publicação oficial inexistente, conteúdo bloqueado pela regra de competência ou decisão humana.

## 3. Correções e verificações executadas (`RECUPERACAO_PUBLICACOES.csv`)
1. **Integridade dos 414 ZIPs locais** (315 de 2022–2024 e 99 de 2025): SHA-256 recalculado igual ao registrado e diretório central íntegro em todos. Nenhum novo download foi necessário.
2. **Catálogo atual:** busca por código de DIST, com qualquer data e por nome, para as 46 combinações DIST-ano sem publicação. 35 são códigos de distribuidoras incorporadas antes de 2022 ou depois de 2022 (EBO, ENF); 11 não têm publicação.
3. **Item oficial sem rótulo (`GDB_DUP`, `6c228d80…`)**: único download desta fase (16,3 MB, SHA-256 `e5579f5a…`, ZIP íntegro), mantido em quarentena em `D:\NUCLEO_BDGD_2022_2024\raw_fase6\`. Camada única `DUP`, com Declarações de Utilidade Pública: **não é BDGD**.
4. **14 arquivos excluídos por competência:** comparação camada a camada com a publicação do ano declarado na BASE e teste de posição temporal do conteúdo. Nenhum é cópia integral e nenhum tem evidência suficiente para mudar o ano. Três são comprovadamente outra versão de 2024.
5. **Cerci 2023:** o arquivo com título 2022 traz BASE 01/01–31/12/2023 e é uma terceira versão de 2023. Coincide parcialmente com as duas do par (30 e 25 de 43 camadas), o que reforça que o par é de republicações, sem resolver a escolha.
6. **Consistência Parquet → série → site:** nenhuma célula validada ausente do asset web.

## 4. Republicações e competência (A3)
- **13 pares:** os 26 itens têm intervalo anual 01/01–31/12 e nenhuma tag `Extra`. Os metadados oficiais só trazem o tipo do arquivo, sem descrição ou nota de substituição, e todos foram criados em lote em 08/10/2025. **Não há evidência documental inequívoca de substituição oficial.** A decisão segue pendente, e a versão mais recente não foi adotada automaticamente.
- **Intervalos não anuais (6):** explicação plausível é preenchimento do `DAT_INC`. Não há indício de base extraordinária, e não há impacto nos estoques, que são referidos ao `DAT_FNL` = 31/12 (detalhe em `PENDENCIAS_NAO_RECUPERAVEIS.md`).
- **Tag `Extra`:** não foi usada como prova.

## 5. Sucessões (A4)
| Ponte | Evidência | Estado |
|---|---|---|
| EPB ← EBO (incorporação efetivada em 30/04/2023) | Conjuntos disjuntos (8 × 67); EPB 2023 ≈ 0,99–1,02 × (EPB 2022 + EBO 2022) nos 6 ativos principais | **Pendente**: a série original não soma; o perímetro só soma após decisão |
| EMR ← ENF (30/11/2022) | 5 de 5 conjuntos da ENF na EMR em 2022 | ENF 2022 **fora de qualquer soma** (já contida) |
| EMR ← EMG | Mesmo código 6585 (EMG_6585 até 2020) | Renomeação, série contínua |
| CPFL Santa Cruz (69) ← 70, 71, 72, 73, 75, 84, 386, 5217 | Última publicação dos códigos em 2016–2017 | Anterior a 2022: sem efeito na série |
| RGE Sul (396) ← RGE (397) | 397 publica até 2018 | Anterior a 2022 |
| Cejama 5372 ← 6896 | 6896 publica até 2017 | Recodificação |

## 6. Cobertura antes e depois (`COBERTURA_ANTES_DEPOIS.csv`)
A cobertura não muda (0 recuperações). Distribuidoras com células publicáveis: 2022 = 95, 2023 = 82 (+ pares pendentes), 2024 = 97, 2025 = 99.

## 7. Decisões humanas necessárias
1. Escolher a versão nos 13 pares (`auditoria/fase4/DECISOES_DUPLICATAS_13_PARES.csv`).
2. Ponte EPB ← EBO.
3. Coprel 2023 (BASE degenerada).
4. Bloquear as anomalias comprovadas: Coopera, Equatorial GO (geradores) e Certel em 2025; Cooperzem em 2024.
5. Aceitar os 6 intervalos não anuais.
6. Pedir à ANEEL as 11 publicações inexistentes.
