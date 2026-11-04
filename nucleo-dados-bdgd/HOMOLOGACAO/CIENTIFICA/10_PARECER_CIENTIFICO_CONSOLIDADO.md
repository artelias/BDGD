# 10 — Parecer científico consolidado (preparado para revisão; **não é homologação nem assinatura**)

**Branch:** `homologacao/cientifica-20261103`, que inclui o piloto `exp/piloto-granular-hierarquico-20261104@4f0ab99` por fast-forward.

Este parecer consolida a evidência já produzida, sem novo treinamento. **Nenhum critério estatístico foi alterado depois de conhecidos os resultados.** Os critérios são os de `01_PROTOCOLO_VALIDACAO.md` (commit `8dc088e`) e de `PILOTO_GRANULAR/01_PROTOCOLO.md` (commit `d988416`). Só entram competências de 2022 a 2025 (diretriz de 04/11/2026).

## 1. Conclusão

| Horizonte | Estado |
|---|---|
| **h = 1 ano** (avaliação final 2024 → 2025) | 7 Moderados publicados **validados retrospectivamente, com restrições**; 18 **experimentais**; 2 **não homologáveis** (as métricas em kVA) |
| **h = 2 a 5 anos** (2027–2030 das trajetórias) | **NÃO HOMOLOGÁVEL COM A EVIDÊNCIA ATUAL**, nas 27 métricas: não existe origem independente com alvo a 2–5 anos em 2022–2025 |
| **Cenários Conservador / Agressivo** | não são intervalos de confiança; não recebem nível estatístico; passam só pelo portão de plausibilidade (engenharia) |
| **Previsões 2026–2030 como um todo** | **não são cientificamente homologadas** |

Para todo uso, a classificação mais forte, "validado retrospectivamente, com restrições", tem três restrições:
- há uma só origem final e o horizonte é de 1 ano;
- a avaliação final dos Moderados publicados **não é independente** da seleção, porque o motor também usou 2025 para escolhê-los;
- o bootstrap reamostra grupos econômicos, mas não capta choques comuns entre anos.

**Mesmo entre os 7 validados, 6 têm R² do crescimento negativo** (de −0,41 a −0,01), e o de ramais é +0,03. O ganho sobre os baselines vem de errar menos o nível do estoque, não de prever a taxa de crescimento.

## 2. Evidência consolidada

| Fonte | O que avaliou | Resultado |
|---|---|---|
| **Backtest dos Moderados publicados** (`03`, `04`) | 27 métricas, h=1 (2024 → 2025) e h=2 (2023 → 2025), contra persistência, deriva e CAGR; bootstrap por grupo (2.000 réplicas) | tabela da seção 3 |
| **Otimização experimental** (`exp/otimizacao-modelos-20261103@997c4d7`) | 1.504 ajustes; seleção de variáveis e hiperparâmetros em 2023 → 2024; avaliação final em 2024 → 2025 | 14 de 104 otimizados melhoraram fora da amostra, 59 pioraram, 31 sem ganho; R² do crescimento mediano −0,02; nada publicado |
| **Piloto granular e hierárquico** (`PILOTO_GRANULAR`, `4f0ab99`) | 5 famílias com painel por município ou conjunto; modelos global, hierárquico, HGB, RF e KNN; configuração congelada antes de 2025 | UCBT, trafos (quantidade) e rede BT: **sem ganho**; rede MT: **rejeitado** (pior que o atual, IC95% > 0); trafos (kVA): **validado restrito contra o baseline**, sem ganho significativo sobre o atual. Os modelos atuais ficam mantidos |
| **Disponibilidade histórica** (`02`) | catálogo ANEEL 2016–2025 | antes de 2022 há leiautes diferentes e vintage não comprovável; **excluído por diretriz** |
| **Diagnóstico granular** (`06`) | unidades, transições, ICC e cobertura | a granularidade não cria origens temporais; o ICC de 0,28–0,55 em UCBT limita o n efetivo |

## 3. Estado por métrica no horizonte de 1 ano (Moderado publicado; avaliação final 2024 → 2025)

| Métrica | Moderado publicado | DIST / grupos | WAPE | Melhor baseline (WAPE) | IC95% dif. vs baseline (p.p.) | MAE | RMSE | Viés | R² crescimento | Estado h=1 | Piloto granular |
|---|---|---|---|---|---|---|---|---|---|---|---|
| alimentadores / quantidade | random_forest_painel | 90 / 66 | 3,37% | deriva (3,82%) | [-1,48; 0,38] | 10,4 | 28,1 | -1,8% | -0,040 | experimental | — |
| bancos_capacitores / quantidade | hgb_painel | 87 / 64 | 3,98% | persistencia (4,64%) | [-1,68; 0,75] | 16,7 | 37,9 | 0,9% | -0,009 | experimental | — |
| barramentos / quantidade | persistencia | 60 / 38 | 2,60% | crescimento_geometrico (3,16%) | [-2,57; 0,32] | 17,5 | 42,5 | -1,8% | -0,041 | experimental | — |
| chaves / quantidade | ridge_painel | 86 / 62 | 2,93% | persistencia (5,81%) | [-3,38; -2,35] | 1.394 | 4.211 | -2,2% | -0,085 | validado (restrições) | — |
| circuitos_at / quantidade | ridge_painel_ext | 35 / 15 | 4,87% | persistencia (6,16%) | [-3,43; 0,86] | 10,4 | 24,1 | -1,7% | -0,140 | experimental | — |
| conjuntos / quantidade | persistencia | 90 / 66 | 0,72% | deriva (3,69%) | [-4,79; -1,48] | 0,2 | 1,5 | -0,6% | -0,012 | validado (restrições) | — |
| consumidores / quantidade | ridge_painel | 88 / 65 | 2,56% | persistencia (2,98%) | [-0,72; -0,13] | 25.004 | 54.109 | -2,0% | -0,413 | validado (restrições) | — |
| disjuntores / quantidade | ridge_painel | 53 / 29 | 3,52% | deriva (4,41%) | [-3,14; 0,32] | 16,1 | 35,6 | -1,5% | 0,013 | experimental | — |
| geradores / quantidade | deriva | 90 / 66 | 6,63% | crescimento_geometrico (13,50%) | [-9,79; -2,59] | 2.885 | 9.215 | -0,2% | -0,111 | validado (restrições) | — |
| iluminacao / quantidade | persistencia | 90 / 65 | 5,25% | crescimento_geometrico (6,59%) | [-2,10; -0,37] | 12.278 | 45.039 | -3,6% | -0,195 | validado (restrições) | — |
| medidores / quantidade | knn_analogos | 91 / 66 | 1,12% | deriva (1,58%) | [-0,85; -0,15] | 12.883 | 40.113 | -0,3% | -0,052 | validado (restrições) | — |
| postes / quantidade | random_forest_painel | 91 / 66 | 0,56% | deriva (0,62%) | [-0,35; 0,18] | 3.411 | 7.764 | 0,2% | -0,030 | experimental | — |
| ramais / extensao_km | knn_analogos | 91 / 66 | 3,51% | persistencia (4,57%) | [-1,78; -0,19] | 611 | 1.728 | -0,6% | 0,027 | validado (restrições) | — |
| reatores / quantidade | persistencia | 11 / 3 | 3,58% | deriva (7,17%) | [-13,56; 4,35] | 1,0 | 3,0 | 3,6% | -0,219 | experimental | — |
| rede_at / extensao_km | ridge_painel | 49 / 24 | 2,17% | persistencia (2,01%) | [-0,96; 1,28] | 64,9 | 126 | 0,8% | -0,013 | experimental | — |
| rede_bt / extensao_km | ridge_painel | 91 / 66 | 1,09% | persistencia (1,19%) | [-0,37; 0,21] | 209 | 652 | 0,5% | -0,021 | experimental | sem ganho |
| rede_mt / extensao_km | random_forest_painel | 91 / 66 | 0,63% | deriva (0,76%) | [-0,73; 0,31] | 215 | 709 | 0,3% | 0,127 | experimental | rejeitado |
| reguladores / quantidade | ridge_painel | 82 / 58 | 4,27% | deriva (4,81%) | [-1,49; 0,36] | 24,7 | 59,1 | 1,3% | 0,080 | experimental | — |
| religadores / quantidade | knn_analogos | 86 / 61 | 7,47% | deriva (7,41%) | [-1,79; 2,02] | 120 | 300 | -5,6% | -0,298 | experimental | — |
| seccionalizadores / quantidade | persistencia | 28 / 16 | 6,63% | deriva (6,86%) | [-3,03; 3,40] | 64,4 | 137 | 2,0% | -0,044 | experimental | — |
| subestacoes / quantidade | knn_analogos | 65 / 40 | 2,98% | persistencia (3,22%) | [-0,80; 0,39] | 3,6 | 7,5 | 0,3% | -0,024 | experimental | — |
| torres / quantidade | knn_analogos | 50 / 26 | 2,54% | persistencia (2,40%) | [-1,10; 0,71] | 182 | 322 | 0,8% | -0,141 | experimental | — |
| trafo_dist / potencia_kva | ridge_painel | 88 / 65 | 4,00% | deriva (5,97%) | [-4,89; 0,49] | 100.101 | 540.860 | 2,9% | 0,037 | não homologável | validado restrito (kVA experimental) |
| trafo_dist / quantidade | knn_analogos | 88 / 65 | 0,84% | crescimento_geometrico (0,90%) | [-0,51; 0,36] | 553 | 1.345 | -0,4% | 0,051 | experimental | sem ganho |
| trafo_forca / potencia_kva | persistencia | 60 / 37 | 14,94% | deriva (11,92%) | [-3,49; 14,50] | 415.215 | 1.296.878 | 7,6% | -0,016 | não homologável | — |
| trafo_forca / quantidade | ridge_painel | 61 / 38 | 4,17% | persistencia (4,44%) | [-0,61; 0,22] | 6,3 | 14,0 | -2,5% | -0,042 | experimental | — |
| trafo_medida / quantidade | knn_analogos | 75 / 55 | 13,72% | persistencia (15,96%) | [-4,16; -0,97] | 1.101 | 4.863 | -9,5% | -0,018 | experimental | — |
| ucbt (painel Motor V2) / quantidade | ridge_painel (Moderado de consumidores, reexecutado) | — / — | N/D | — | N/D | N/D | N/D | N/D | N/D | — | sem ganho |

O IC95% é o percentil do bootstrap por grupo econômico da diferença de WAPE (modelo − melhor baseline). MAE e RMSE estão na unidade da métrica. R² do crescimento = 1 − SSE/SST de ln(y_alvo/y_origem) entre as distribuidoras. A coluna "Piloto granular" vale para a coorte do painel do Motor V2, que pode diferir do contrato (UCBT, por exemplo). Linha a linha, com os horizontes 2–5, em `09_ESTADO_POR_METRICA_E_HORIZONTE.csv` (gerado por `gerar_consolidado.py`).

## 4. Modelos preservados

- **Publicados:** os 27 Moderados avaliados permanecem como estão; nenhuma substituição.
- **Candidatos confirmatórios** (`11_CANDIDATOS_CONFIRMATORIOS.md`), não publicados:
  - Ridge por conjunto para kVA (experimental);
  - hierárquico por conjunto para rede BT;
  - deriva para rede BT, numa nova comparação independente.
- **Rejeitado:** o HGB por conjunto da rede MT.

## 5. Limitações (não contornáveis com a evidência atual)

1. Quatro competências, três transições, uma origem final, um horizonte avaliável.
2. Choques comuns por distribuidora e ano: nenhum modelo, por DIST ou granular, prevê bem a taxa anual de crescimento.
3. Seleção não cega dos Moderados publicados em relação ao alvo de 2025.
4. Pendências cadastrais excluídas, sem ponte: renumeração de conjuntos (15–17 DIST em 2023→2024), município da Celesc 2023 e DIST 7019 em 2023.
5. `DAT_CON` reescrita entre fotografias em parte das distribuidoras e identidade de UC não contínua.
6. Comparação externa (ANEEL/EPE) não feita: não há série externa versionada.

## 6. Para chegar à homologação (sem dados anteriores a 2022)

- **Novas origens:** cada nova competência publicada é uma origem independente. Com 3 origens por horizonte, o nível "homologado" do protocolo fica atingível.
- **Avaliação confirmatória dos candidatos** da seção 4 na primeira origem nova, com as configurações congeladas.
- **Indicadores antecedentes de demanda**, com data de disponibilidade.

## 7. Assinaturas humanas necessárias (não registradas)

| Papel | Nome | Decisão | Data | Assinatura |
|---|---|---|---|---|
| Revisor estatístico independente | | | | |
| Especialista do setor elétrico (BDGD/regulação) | | | | |
| Responsável técnico pelo motor | | | | |
| Responsável pela decisão de publicação | | | | |
