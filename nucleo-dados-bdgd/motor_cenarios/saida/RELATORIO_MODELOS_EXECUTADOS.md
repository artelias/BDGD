# Relatório dos modelos executados — Motor de Expansão Elétrica

Produto: `web/public/data/previsoes/cenarios-motor.json` (esquema `cenarios-motor-1`). Ano-base 2025; horizonte 2026–2030; origens de backtest 2023, 2024. Todos os números abaixo vêm da execução real (`motor_cenarios/cenarios.py`), regenerável e verificada no CI com `--check`.

## Resumo

- Métricas (ativo × métrica) avaliadas: **29** (25 ativos; quantidade/extensão do contrato nacional e potência kVA experimental de transformadores TUC 565/570 via EQ→UN).
- Três cenários: **10**
- Dois cenários: **13**
- Somente moderado: **2**
- Somente baseline (persistência): **2**
- Bloqueado: **2**
- Métricas cujo modelo moderado supera a persistência no backtest: **21**
- Métricas com algum cenário usando variáveis externas: **8**
- Métricas experimentais: **4**
- Ativos com trajetória 2026–2030 no cenário moderado: **25** — Alimentadores, Bancos de capacitores, Barramentos, Chaves, Circuitos de alta tensão, Conjuntos, Disjuntores, Geradores, Iluminação pública, Medidores, Postes, Ramais de ligação, Reatores, Rede de alta tensão, Rede de baixa tensão, Rede de média tensão, Reguladores, Religadores, Seccionalizadores, Subestações, Torres, Transformadores de distribuição, Transformadores de força, Transformadores de medida, Unidades consumidoras
- Séries DIST × métrica com histórico ≥ 1 ano terminando em 2025: 2202; com trajetória moderada: **1961**

## Modelos selecionados por cenário (contagem de métricas)

| Cenário | Modelo | Métricas |
|---|---|---|
| Conservador | Persistência (passeio aleatório sem deriva) | 8 |
| Conservador | k vizinhos mais próximos (distribuidoras análogas) | 4 |
| Conservador | Ridge em painel com variáveis externas IBGE | 1 |
| Conservador | Random Forest em painel (log-crescimento anual) | 1 |
| Conservador | Regressão Ridge em painel (log-crescimento anual) | 1 |
| Conservador | HistGradientBoosting em painel (log-crescimento anual) | 1 |
| Moderado | Regressão Ridge em painel (log-crescimento anual) | 8 |
| Moderado | k vizinhos mais próximos (distribuidoras análogas) | 7 |
| Moderado | Persistência (passeio aleatório sem deriva) | 6 |
| Moderado | Random Forest em painel (log-crescimento anual) | 3 |
| Moderado | HistGradientBoosting em painel (log-crescimento anual) | 1 |
| Moderado | Ridge em painel com variáveis externas IBGE | 1 |
| Moderado | Passeio aleatório com deriva (drift) | 1 |
| Agressivo | Ridge em painel com variáveis externas IBGE | 6 |
| Agressivo | Random Forest em painel (log-crescimento anual) | 6 |
| Agressivo | Regressão Ridge em painel (log-crescimento anual) | 3 |
| Agressivo | k vizinhos mais próximos (distribuidoras análogas) | 2 |

## Matriz por métrica

| Ativo | Métrica | Estado | Conservador | Moderado | Agressivo | WAPE moderado | WAPE persistência | Pontos | Séries projetadas |
|---|---|---|---|---|---|---|---|---|---|
| Geradores | quantidade | somente moderado | — | deriva | — | 10,23% | 31,46% | 260 | 90 |
| Iluminação pública | quantidade | dois cenários | — | persistencia | knn_analogos | 4,81% | 4,81% | 260 | 90 |
| Unidades consumidoras | quantidade | dois cenários | persistencia | ridge_painel | — | 3,70% | 4,20% | 254 | 88 |
| Postes | quantidade | dois cenários | ridge_painel | random_forest_painel | — | 0,89% | 2,67% | 261 | 91 |
| Torres | quantidade | dois cenários | persistencia | knn_analogos | — | 3,01% | 3,42% | 140 | 50 |
| Medidores | quantidade | dois cenários | random_forest_painel | knn_analogos | — | 1,24% | 3,10% | 263 | 91 |
| Transformadores de medida | potencia_kva (exp.) | bloqueado | — | — | — | N/D | N/D | 0 | 0 |
| Transformadores de medida | quantidade | dois cenários | — | knn_analogos | ridge_painel | 9,83% | 13,00% | 205 | 75 |
| Ramais de ligação | extensao_km | dois cenários | — | knn_analogos | random_forest_painel | 3,64% | 4,86% | 263 | 91 |
| Rede de alta tensão | extensao_km | três cenários | persistencia | ridge_painel | ridge_painel_ext | 2,66% | 2,85% | 139 | 49 |
| Rede de baixa tensão | extensao_km | três cenários | persistencia | ridge_painel | ridge_painel_ext | 1,69% | 1,99% | 261 | 91 |
| Rede de média tensão | extensao_km | três cenários | knn_analogos | random_forest_painel | ridge_painel_ext | 0,83% | 2,08% | 263 | 91 |
| Bancos de capacitores | quantidade | três cenários | persistencia | hgb_painel | ridge_painel_ext | 5,73% | 6,79% | 249 | 87 |
| Reatores | quantidade | somente baseline (persistência) | — | persistencia | — | 6,87% | 6,87% | 33 | 11 |
| Reguladores | potencia_kva (exp.) | bloqueado | — | — | — | N/D | N/D | 0 | 0 |
| Reguladores | quantidade | dois cenários | hgb_painel | ridge_painel | — | 4,43% | 7,85% | 234 | 82 |
| Chaves | quantidade | três cenários | ridge_painel_ext | ridge_painel | random_forest_painel | 2,93% | 6,08% | 238 | 85 |
| Disjuntores | quantidade | três cenários | knn_analogos | ridge_painel | random_forest_painel | 4,33% | 6,06% | 143 | 52 |
| Religadores | quantidade | dois cenários | — | knn_analogos | random_forest_painel | 6,95% | 10,98% | 236 | 85 |
| Seccionalizadores | quantidade | somente baseline (persistência) | — | persistencia | — | 7,08% | 7,08% | 76 | 28 |
| Alimentadores | quantidade | três cenários | knn_analogos | random_forest_painel | ridge_painel | 3,65% | 4,99% | 260 | 90 |
| Barramentos | quantidade | dois cenários | — | persistencia | knn_analogos | 3,01% | 3,01% | 172 | 60 |
| Circuitos de alta tensão | quantidade | dois cenários | persistencia | ridge_painel_ext | — | 5,47% | 6,43% | 97 | 34 |
| Conjuntos | quantidade | dois cenários | — | persistencia | ridge_painel_ext | 1,92% | 1,92% | 260 | 90 |
| Subestações | quantidade | três cenários | persistencia | knn_analogos | random_forest_painel | 3,54% | 3,60% | 189 | 65 |
| Transformadores de distribuição | potencia_kva (exp.) | três cenários | knn_analogos | ridge_painel | ridge_painel_ext | 5,70% | 7,65% | 250 | 87 |
| Transformadores de distribuição | quantidade | somente moderado | — | knn_analogos | — | 1,11% | 3,32% | 250 | 88 |
| Transformadores de força | potencia_kva (exp.) | dois cenários | — | persistencia | ridge_painel | 9,95% | 9,95% | 170 | 60 |
| Transformadores de força | quantidade | três cenários | persistencia | ridge_painel | random_forest_painel | 3,76% | 4,05% | 173 | 60 |

## Modelos executados — formulação

- **Persistência (passeio aleatório sem deriva)** (`persistencia`; baseline): `ŷ(T+h) = y(T)`
- **Passeio aleatório com deriva (drift)** (`deriva`; baseline de tendência): `ŷ(T+h) = y(T) + h·(y(T) − y(T0))/(T − T0)`
- **Tendência linear por mínimos quadrados (OLS)** (`tendencia_ols`; regressão temporal por série): `ŷ(t) = a + b·t, (a,b) = argmin Σ(y(t) − a − b·t)² no segmento`
- **Crescimento geométrico histórico (CAGR)** (`crescimento_geometrico`; baseline de crescimento): `ŷ(T+h) = y(T)·(1+g)^h, g = (y(T)/y(T0))^(1/(T−T0)) − 1`
- **Regressão Ridge em painel (log-crescimento anual)** (`ridge_painel`; regressão linear penalizada (L2)): `ĝ = β0 + xᵀβ, β = argmin Σ(g − β0 − xᵀβ)² + α‖β‖², α=1; ŷ(T+h) = y(T)·exp(h·ĝ)`
- **Ridge em painel com variáveis externas IBGE** (`ridge_painel_ext`; regressão linear penalizada (L2)): `igual ao Ridge em painel, com x acrescido de crescimento populacional 2010–2022 e ln PIB per capita 2021`
- **k vizinhos mais próximos (distribuidoras análogas)** (`knn_analogos`; não paramétrico por similaridade): `ĝ = mediana dos log-crescimentos dos k=9 pares de treino mais próximos em x padronizado; ŷ(T+h) = y(T)·exp(h·ĝ)`
- **Random Forest em painel (log-crescimento anual)** (`random_forest_painel`; ensemble de árvores (bagging)): `ĝ = média de 300 árvores (min_samples_leaf=5, max_features=0,5, semente 42); ŷ(T+h) = y(T)·exp(h·ĝ)`
- **HistGradientBoosting em painel (log-crescimento anual)** (`hgb_painel`; boosting de árvores): `ĝ = Σ árvores de gradiente (max_iter=150, learning_rate=0,05, max_depth=3, min_samples_leaf=10, semente 42); ŷ(T+h) = y(T)·exp(h·ĝ)`

## Variáveis

| Variável | Tipo | Fonte | Disponível em | Utilizada | Modelos |
|---|---|---|---|---|---|
| `ln_estoque` | interna | Contrato nacional BDGD (serie_fisica_nacional.csv) | 31/12 do próprio ano (divulgação ANEEL posterior) | sim | hgb_painel, knn_analogos, random_forest_painel, ridge_painel, ridge_painel_ext |
| `ln_estoque_por_uc` | interna | Contrato nacional BDGD | idem | sim | hgb_painel, knn_analogos, random_forest_painel, ridge_painel, ridge_painel_ext |
| `int_ln_uc` | interna | Contrato nacional — consumidores (regra UC v3) | idem | sim | hgb_painel, knn_analogos, random_forest_painel, ridge_painel, ridge_painel_ext |
| `int_ln_km_bt` | interna | Contrato nacional — rede BT (km) | idem | sim | hgb_painel, knn_analogos, random_forest_painel, ridge_painel, ridge_painel_ext |
| `int_ln_km_mt` | interna | Contrato nacional — rede MT (km) | idem | sim | hgb_painel, knn_analogos, random_forest_painel, ridge_painel, ridge_painel_ext |
| `int_ln_uc_por_km_bt` | interna | Contrato nacional — UC e rede BT | idem | sim | hgb_painel, knn_analogos, random_forest_painel, ridge_painel, ridge_painel_ext |
| `int_mwh_por_uc` | interna | Parquets BDGD UCBT/UCMT/UCAT — ENE_01..12 (kWh) | idem | sim | hgb_painel, knn_analogos, random_forest_painel, ridge_painel, ridge_painel_ext |
| `ext_cresc_pop_2010_2022` | externa | IBGE Censo 2010 (SIDRA 1378) e Censo 2022 (SIDRA 4709) | 2023-08-31 (Censo 2022 revisado) | sim | ridge_painel_ext |
| `ext_ln_pib_pc_2021` | externa | IBGE PIB dos Municípios 2021 (SIDRA 5938) / estimativa populacional 2021 (SIDRA 6579) | 2023-12-15 | sim | ridge_painel_ext |
| `pop_estimativas_2024_2025` | externa | IBGE estimativas municipais 2024 e 2025 (SIDRA 6579) | 2024-08-29 / 2025-08 | não | — |
| `pib_municipal_2022_2023` | externa | IBGE PIB dos Municípios 2022–2023 (SIDRA 5938) | 2025-12-19 | não | — |
| `mercado_aneel_samp` | externa | ANEEL — SAMP / mercado de distribuição | não obtido | não | — |
| `dec_fec_aneel` | externa | ANEEL — indicadores DEC/FEC por conjunto | não obtido | não | — |
| `epe_projecoes` | externa | EPE — projeções de demanda (PDE) | não obtido | não | — |
| `atributos_tuc_a1_a6` | interna | Cubos DDA/TUC 2025 | apenas 2025 | não | — |

## Limitações

- Quatro competências anuais: backtest com 2 origens e horizontes 1–2; 2028–2030 são extrapolações sem verificação retrospectiva.
- Avaliação retrospectiva revisada (os anos 2022–2024 são `COMPLETO_TECNICO`/ressalvas, não homologação humana); não é point-in-time.
- Sem intervalos probabilísticos; a distância entre cenários não é intervalo de confiança.
- Estoque físico não identifica entradas, baixas, obras, necessidade técnica ou CAPEX. Nenhum total nacional projetado é publicado.
- Potência kVA (TUC 565/570) é experimental: derivada fora do contrato homologado, com portões de vínculo EQ→UN ≥ 98%, escala kVA e igualdade da contagem com o contrato.
- Potência de reguladores: indisponível (EQRE.POT_NOM é código de domínio e UNREMT não tem POT_NOM). Potência de transformadores de medida: não derivada nesta execução.
- Coopera 2025 (DIST 5370): consumidores sem projeção — UCBT vazia na fonte, mantida a ressalva; nunca convertida em zero.
