# 03 — Cobertura nacional final do Motor V2

Este documento descreve a cobertura gerada por `motor_v2/nacional/cobertura.py`, sem treinar nada novo. A matriz linha a linha está em `02_MATRIZ_COMPLETA_MODELOS.csv` e, no Motor V2, em `motor_v2/reports/nacional/MATRIZ_COBERTURA_SERIES.csv` e `MATRIZ_COBERTURA_COMPLETA.csv.gz` (DIST × objetivo × métrica × ano × cenário).

## Universo

| Item | Valor |
|---|---|
| DIST no contrato nacional | **114** (nenhuma descartada em silêncio) |
| Pares objetivo/métrica do catálogo | 29, mais a UCBT como sub-série hierárquica de Consumidores |
| Combinações DIST × objetivo × métrica | **3.420** |
| Células DIST × objetivo × métrica × ano × cenário | **51.300** |

## Dois indicadores separados

| Indicador | Resultado |
|---|---|
| Cobertura de **processamento** (combinações analisadas, com estado e motivo) | **3.420 de 3.420 (100%)** |
| Cobertura de **previsão** (combinações com os 15 valores: 5 anos × 3 cenários) | **2.707** (79,2% do universo; **97,1% das aplicáveis**, sem `NAO_APLICAVEL` e sem `SUCESSAO_SOCIETARIA`) |
| … das quais com âncora 2025 | 2.597 |
| … das quais com âncora anterior (`SEM_ANCORA_2025`, fora dos totais) | 110 |
| Pares do catálogo com previsão em pelo menos uma DIST | **28 de 29** (falta só TUC 575 kVA, não aplicável) |
| DIST com alguma projeção | 102 |
| `BLOQUEIO_TECNICO` (defeito de código) | **0** |

**Cobertura do estoque físico em 2025.** Para as 25 métricas do contrato, as séries projetadas com âncora 2025 cobrem **100% do estoque elegível de 2025** do contrato. Mesmo assim, todo total nacional é **PARCIAL**, porque três DIST aplicáveis não têm publicação de 2025 e o estoque delas em 2025 é desconhecido:
- Cerci (5279), última publicação em 2023;
- Ceres (5274), última publicação utilizável em 2022;
- Cooperalianca (2904), âncora em 2023.

As métricas de kVA (TUC 565 e TUC 570) e a UCBT não fazem parte do contrato, e a cobertura delas é medida pelo número de DIST.

## Estados

| Estado | Combinações |
|---|---|
| `PROJETADA_BASELINE` | 1.602 |
| `PROJETADA_EXPERIMENTAL` | 995 |
| `SEM_ANCORA_2025` | 110 |
| `SUCESSAO_SOCIETARIA` | 360 (12 códigos × 30) |
| `NAO_APLICAVEL` | 273 |
| `DADO_NAO_HOMOLOGADO` | 41 |
| `SEM_SEMANTICA_FISICA_HOMOGENEA` | 33 |
| `HISTORICO_INSUFICIENTE` | 6 |
| `SEM_PUBLICACAO`, `BLOQUEIO_TECNICO` | 0 |

## As 438 combinações do nível B sem série em `6327239`

Cada combinação foi auditada individualmente (`motor_v2/reports/nacional/LACUNAS_VERSUS_6327239.csv`):

| Classe | Casos | Evidência |
|---|---|---|
| A — sem publicação | 0 isoladas | as ausências de publicação aparecem junto de anos em que o ativo não se aplica |
| B — sucessão / mudança de perímetro | 275 | contrato `SUCESSAO_SOCIETARIA`, com o motivo da DIST que reporta o perímetro |
| C — fisicamente não aplicável | 162 | contrato `ATIVO_NAO_APLICAVEL`, **conferido nos Parquets locais**: 589 células, 0 com registros na entidade (BAR, CTAT, SSDAT, SUB, EQRE, EQCR por tipo) |
| D — estoque ausente ou não homologado | 1 | Coprel, circuitos AT: 2022 com bloqueio de competência, 2023 com base inconsistente, 2024 sem publicação e 2025 com a entidade vazia na origem |
| E — histórico parcial com âncora utilizável | já projetadas | 110 séries `SEM_ANCORA_2025`, com o ano da âncora e o horizonte real |
| F — bloqueio por limitação do código | **0** | nenhuma célula com estoque utilizável ficou sem série |
| G — outro impedimento | 0 | — |

Também foi corrigido um caso de empresa incorporada tratada como ativa. A **Energisa Borborema (6611)**, incorporada à Energisa PB (6600) em 30/04/2023 (evento `EPB_EBO_2023`), tinha 25 séries projetadas a partir de 2022. Agora ela é `SUCESSAO_SOCIETARIA`; a projeção interna fica só como registro de auditoria. A Energisa Nova Friburgo (6612 → 6585) já estava assim.

## As 114 DIST do contrato e as 104 do inventário local

As 10 diferenças são identificadores históricos sem publicação própria em 2022–2025, todos `SUCESSAO_SOCIETARIA` no contrato:
- 70 CPFL Mococa, 71 CPFL Leste Paulista, 72 CPFL Santa Cruz (código antigo), 73 CPFL Sul Paulista, 75 CNEE, 84 CFLO, 386 EEB e 5217 EDEVP: perímetro reportado pela DIST 69 (CPFL Santa Cruz);
- 397 RGE (código antigo): perímetro reportado pela DIST 396;
- 6896 Cejama: perímetro reportado pela DIST 5372.

Não há duplicidade nem publicação disponível sem integração, e nenhuma nova aquisição é necessária. Com as incorporadas 6611 e 6612, são 12 códigos sem perímetro próprio.

## Métricas que estavam sem previsão

| Métrica | Antes | Agora |
|---|---|---|
| Transformadores de força, TUC 570, kVA | proposta (72 DIST candidatas) | **60 DIST projetadas** (53 com âncora 2025). 37 são `DADO_NAO_HOMOLOGADO`: kVA do equipamento × da instalação divergem mais de 5%, ou gate de código/quantidade. 5 são `HISTORICO_INSUFICIENTE`. A ventilação forçada nunca é somada. |
| Transformadores de medida, TUC 575, kVA | não aplicável | **`NAO_APLICAVEL` confirmado**: a EQTRM não tem campo de potência (relação e classe de exatidão) |
| Reguladores, potência | bloqueada | **59 DIST** com convenção única: 55 de potência própria e 4 de passante. 33 DIST são `SEM_SEMANTICA_FISICA_HOMOGENEA`. **Sem total nacional** |
| Transformadores de distribuição, kVA, por DIST | só territorial | **99 DIST** (nível A agregado; 92 com âncora 2025) |

## Totais 2030 (todos PARCIAL)

| Métrica | Conservador | Moderado | Agressivo |
|---|---|---|---|
| Consumidores reconciliados | 87.642.247 | 93.460.778 | 106.671.042 |
| UCBT | 87.326.180 | 93.112.341 | 106.236.504 |
| TUC 565 (kVA) | 213.286.945 | 216.696.491 | 245.379.290 |
| TUC 570 (kVA) | 103.926.264 | 111.442.669 | 127.036.261 |
| Rede MT (km, nível B) | 3.326.741 | 3.380.970 | 3.560.958 |
| Rede BT (km, nível B) | 1.751.603 | 1.801.194 | 2.003.331 |

Os totais de todas as métricas, por cenário, estão em `motor_v2/reports/nacional/COBERTURA_POR_OBJETIVO.csv`. As redes MT e BT aqui vêm do nível B (contrato) e diferem do nível A territorial do relatório anterior, que usa outro extrator.

## Expansão territorial

O nível territorial continua com as cinco séries do nível A: UCBT, transformadores de distribuição (quantidade e kVA), rede MT e rede BT, por município ou conjunto, com resíduo explícito e reconciliação com a DIST.

As demais entidades (geradores, iluminação, postes, alimentadores, ramais, rede AT, subestações, chaves) têm campos territoriais (MUN, CONJ, SUB, CTMT) e extração viável, mas **não foram territorializadas nesta entrega**. A projeção por distribuidora delas está completa. A territorialização exigiria rodar o extrator sobre todas as publicações e treinar o nível A para cada nova série. Foi deixada para depois, como permite a instrução de não atrasar as séries por DIST já válidas.
