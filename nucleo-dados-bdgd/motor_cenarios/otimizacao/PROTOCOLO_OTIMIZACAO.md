# Protocolo da otimização experimental dos modelos de cenários

Este protocolo foi registrado e versionado **antes** da primeira execução de `otimizar.py`. A data e o commit ficam no histórico git da branch `exp/otimizacao-modelos-20261103`. Os parâmetros abaixo estão no código (`PROTOCOLO` em `otimizar.py`) e não foram alterados depois de ver resultados. Qualquer mudança posterior gera uma nova versão do protocolo, registrada no histórico, e os resultados da versão anterior são preservados.

Escopo: o produto de cenários (`motor_cenarios`, 27 métricas com série) sobre o contrato nacional 2022–2025. Não altera o produto publicado nem a RC. Não instala dependências: usa numpy e scikit-learn 1.8.0, as versões fixadas do gerador.

## 1. Separação temporal

Pares de treino: (variáveis em t−1, ln(y_t / y_{t−1})), como no motor original. Valem só transições comparáveis: observado → observado, valores positivos, sem ruptura.

| Etapa | Treino | Alvo avaliado | Uso |
|---|---|---|---|
| **Seleção (S)** | transições até 2023 (só 2022→2023) | y_2024, horizonte 1 | disponibilidade, filtros, importância por permutação, subconjuntos e hiperparâmetros |
| **Final (F)** | transições até 2024 | y_2025, horizonte 1 | **só avaliação**: nenhuma escolha usa esta etapa |
| Diagnóstico de horizonte 2 | transições até 2023 | y_2025, horizonte 2 | relatado; não usado em escolha |

O ano de 2025 não entra em nenhuma escolha de variável ou hiperparâmetro. O modelo original foi escolhido pelo motor com as duas origens, logo também com 2025; por isso **a comparação "original × otimizado" na etapa F não é cega para o original**. Isso fica registrado como limitação, e o status permanece experimental.

## 2. Métricas

Calculadas nos mesmos pontos para todos os candidatos de uma métrica e etapa:

- WAPE, MAE, RMSE e viés relativo;
- erro físico depois de arredondar contagens (meio para cima), da mesma forma que no produto;
- erro por origem (S, F) e por horizonte (1; e 2 no diagnóstico);
- ganho de WAPE contra o melhor baseline (persistência, deriva, CAGR) nos mesmos pontos;
- estabilidade = |WAPE_F − WAPE_S|.

R², sempre fora da amostra:
- `r2_estoque` = 1 − SSE/SST nos níveis. Fica dominado pelo porte das empresas e é relatado, não usado para escolher;
- `r2_variacao` = o mesmo sobre as variações anuais Δ = y_alvo − y_origem;
- `r2_crescimento` = o mesmo sobre ln(y_alvo/y_origem), sem escala.

R² fica **não definido** (null) quando n < 5 pontos ou SST = 0; nunca é substituído por zero. R² de treino não é calculado como evidência.

Dentro de cada distribuidora há no máximo 1 ponto por etapa, então R² por distribuidora é não definido. A matriz traz o erro absoluto da variação por distribuidora na etapa F.

## 3. Variáveis candidatas e filtros (só com o treino da etapa S)

Candidatas: as 9 originais (`FEAT_INT` + `FEAT_EXT`), mais as derivadas de séries já existentes no contrato:
- ln de transformadores de distribuição, alimentadores, subestações e rede AT;
- crescimento anterior do próprio ativo;
- crescimento anterior das UCs.

Município e conjunto não existem no painel por distribuidora (granularidade diferente) e ficam registrados como não aplicáveis. A potência fica de fora, porque é experimental e não homologada.

Filtros:
1. **Disponibilidade temporal:** a variável precisa existir em pelo menos 50% dos pares de treino da etapa S. Crescimentos defasados exigem 2021, que não existe, e são descartados como `INDISPONIVEL_NA_ORIGEM`. As externas do IBGE foram divulgadas até 15/12/2023, dentro da origem S (31/12/2023).
2. **Constante:** desvio-padrão menor que 1e-9 no treino S.
3. **Redundância/colinearidade:** |correlação de Pearson| > 0,95 no treino S. Fica a de maior prioridade (ordem da lista), e a outra é descartada com o par registrado.
4. **Importância por permutação** sobre a validação S (y_2024), com 5 repetições e semente 42, no ajuste com todas as variáveis restantes e os hiperparâmetros originais.
5. **Seleção progressiva:** prefixos da ordem de importância (top-1, top-2…), no máximo 8. Para depois de **2 prefixos seguidos sem melhora** do WAPE_S.
6. **Regularização:** α do Ridge na grade de hiperparâmetros.
7. **Estabilidade das variáveis entre origens:** sobreposição do top-3 de importância S × F. É calculada **depois** de fixadas as escolhas, só como diagnóstico.

## 4. Orçamento, algoritmos e grade (fixados)

| Algoritmo | Grade (≤ 9 combinações) |
|---|---|
| Ridge em painel | α ∈ {0,1; 1; 10} |
| KNN (mediana dos vizinhos) | k ∈ {5; 9; 15} |
| Random Forest em painel | min_samples_leaf ∈ {3; 5; 10} × max_features ∈ {0,3; 0,5; 1,0}; 300 árvores; semente 42 |
| HistGradientBoosting | max_depth ∈ {2; 3} × learning_rate ∈ {0,05; 0,1}; max_iter 150; min_samples_leaf 10; semente 42 |

- **Por métrica e algoritmo:** até 8 subconjuntos, mais até 9 hiperparâmetros, mais 1 configuração original. São no máximo 18 ajustes na etapa S e 2 na etapa F (original e otimizado).
- **Cache:** cada ajuste é guardado pelo hash da configuração em `saida/cache.json`, e uma nova execução não refaz o que já existe.
- **Custo:** número de tentativas e tempo registrados por métrica em `BUSCA_TENTATIVAS.csv`.
- Não há processamento nacional além do painel já usado pelo motor.

## 5. Critério de melhora (fixado antes)

Um candidato otimizado **melhora realmente** o original do mesmo algoritmo quando, **na etapa F**, cumpre as três condições:
1. WAPE_F(otimizado) ≤ 0,95 × WAPE_F(original) **e** a diferença é de pelo menos 0,05 p.p.;
2. r2_crescimento_F não piora mais de 0,02 (ou ambos são não definidos);
3. não fica pior que o melhor baseline na etapa F.

Melhora só na etapa S é **rejeitada** (`MELHORA_SO_NA_OTIMIZACAO`). Piora na etapa F é registrada como `PIOROU_FORA_DA_AMOSTRA`, e o original é mantido.

## 6. Nova escolha dos cenários (registro técnico experimental)

1. **Moderado:** mantém o modelo do produto publicado. Só é substituído por um candidato que melhora realmente (critério 5) **e** tem WAPE_S e WAPE_F menores que o do Moderado publicado.
2. **Candidatos competitivos para os extremos:** os modelos originais, os otimizados e os baselines univariados com WAPE_S ≤ 1,25 × WAPE_S(Moderado). **Só a etapa S entra nesta escolha**; o WAPE_F é relatado, não filtra. Projeção final a partir de 2025 (treino até 2025, como o produto).
3. **Por distribuidora**, entre os candidatos competitivos coerentes na direção:
   - coerência: a razão 2030/2025 fica em [0,5; 3], nenhum valor é negativo, o cenário fica abaixo (Conservador) ou acima (Agressivo) do Moderado da DIST **em todos os anos**, e a diferença do crescimento anual 2025→2030 é de pelo menos 0,05 p.p./ano;
   - escolha: o de **menor WAPE_S**, a melhor evidência retrospectiva, não o mais extremo;
   - o resultado é `MODELO_INDEPENDENTE`.
4. **Sem candidato:** cenário **condicional** do próprio Moderado, deslocando o crescimento log anual pelo menor ou maior crescimento de uma transição comparável da própria série (exige pelo menos 2 transições comparáveis), quando mais extremo que o Moderado em 0,05 p.p./ano e coerente em todos os anos. A taxa precisa ficar dentro do P01–P99 das transições comparáveis da métrica (todas as DIST). A razão 2030/2025 precisa estar em [0,5; 3]. O resultado é `CONDICIONAL_DO_MODERADO`.
5. **Sem evidência:** `SEM_EVIDENCIA_COINCIDENTE`, com o cenário igual ao Moderado e a justificativa. **Não é publicável como cenário distinto.**
6. Contagens arredondadas meio para cima no fim.

O "menos ruim" de cada direção é registrado mesmo quando não é publicável. Nenhum resultado desta etapa é publicado ou substitui a RC sem as regressões completas e a revisão humana.

## 7. O que este protocolo não permite afirmar

Há uma única origem de avaliação independente (2024 → 2025, horizonte 1) e uma origem de seleção com uma só transição de treino. Por isso:
- WAPE e R² otimizados **não são evidência de homologação científica**;
- horizontes de 2 a 5 anos não têm verificação retrospectiva independente;
- todo resultado permanece **experimental**.
