# Relatório da otimização experimental dos modelos de cenários

**Branch:** `exp/otimizacao-modelos-20261103`. **Protocolo:** `PROTOCOLO_OTIMIZACAO.md`, commitado em `bab1162` antes da execução completa. **Resultado experimental:** não altera o produto publicado nem a RC 1.0, e não é homologação científica.

**Escopo:** 27 métricas com série. A execução fez 1.504 ajustes, somando 843 s de ajuste (cerca de 20 min no total). A reprodução do Ridge original deu diferença máxima de 0,0 contra o gerador do produto.

## Leitura essencial

1. **A maioria das otimizações não sobreviveu fora da amostra.** Dos 104 pares "otimizado × original do mesmo algoritmo":
   - **14** melhoraram na avaliação final independente (2024 → 2025) pelo critério fixado;
   - **59** pioraram;
   - **31** não tiveram ganho significativo.

   A seleção de variáveis e de hiperparâmetros na etapa de seleção (2023 → 2024, com uma única transição de treino) sobreajusta com frequência. A regra de rejeição funcionou como foi desenhada.
2. **O R² do crescimento fora da amostra fica perto de zero.** Nos modelos originais, a mediana é −0,02 (de −5,8 a 0,13; 135 modelos). O crescimento anual de cada distribuidora é quase imprevisível com 2022–2025. O WAPE baixo (por exemplo 0,6–1% em transformadores e rede MT) vem de o estoque mudar pouco de um ano para outro, não de os modelos acertarem a variação. O R² do nível do estoque, sempre perto de 1 e dominado pelo porte, não é usado como evidência.
3. **A cobertura de três cenários defensáveis sobe de 755 para 1.343 séries**, de 1.961 com Moderado, no registro técnico. Isso vem sobretudo da comparação **por distribuidora**: a regra do produto exige um modelo alternativo na média nacional da métrica, e a comparação por DIST encontra alternativas coerentes em cada série. Em métricas que já tinham três cenários, a exigência de coerência por DIST em todos os anos **reduz** a contagem (por exemplo alimentadores: 89 → 68; subestações: 65 → 33).

## Exemplo obrigatório: transformadores de distribuição, quantidade

| Modelo | WAPE seleção (2023 → 2024) | WAPE final (2024 → 2025) | WAPE h=2 (2023 → 2025) | R² crescimento (final) | Veredito |
|---|---|---|---|---|---|
| KNN original (**Moderado publicado**) | 0,89% | 0,84% | 1,66% | 0,05 | — |
| Random Forest original | 1,40% | **0,63%** | 2,35% | 0,08 | — |
| Random Forest otimizado (`ext_cresc_pop_2010_2022`, `ln_estoque_por_uc`; leaf 10, max_features 0,3) | 1,06% | 0,89% | 1,69% | −0,00 | **PIOROU_FORA_DA_AMOSTRA**: rejeitado |
| KNN otimizado (`ln_estoque`, `int_mwh_por_uc`; k=9) | 0,90% | 0,85% | 1,64% | 0,05 | PIOROU_FORA_DA_AMOSTRA |
| Ridge otimizado (`int_mwh_por_uc`, `ext_cresc_pop_2010_2022`; α=10) | 0,93% | 0,83% | 1,53% | 0,01 | SEM_GANHO_SIGNIFICATIVO (não bate o melhor baseline, CAGR 0,90%) |
| Melhor baseline na etapa final (CAGR) | 2,76% | 0,90% | 5,19% | 0,01 | — |

- Os 1,11% (KNN) e 1,40% (RF) citados no pedido são o WAPE agregado das duas origens do produto.
- **A seleção de variáveis melhorou o Random Forest só nos dados de seleção** (1,40% → 1,06%) e piorou na avaliação final (0,63% → 0,89%). Por isso a melhora foi rejeitada.
- O RF **original** tem o menor erro final das três etapas desta tabela. Ele não substitui o KNN como Moderado porque a escolha do Moderado só considera otimizados que vencem nas duas etapas (protocolo 6.1); o RF original perde na seleção.
- Não há ganho artificial a declarar.

## Respostas pedidas

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Métricas com três cenários antes | **10** de 27 (estado `tres_cenarios`); **755** séries com os três |
| 2 | Com três cenários depois da otimização | **1.343** séries com Conservador e Agressivo defensáveis e distintos (registro técnico, não publicado). Métricas com pelo menos 90% das séries completas: **4** (postes, ramais, consumidores, rede MT). Por DIST, o conceito de "métrica com três cenários" deixa de ser binário |
| 3 | Modelos que melhoraram realmente fora da amostra | **14** de 104 (lista em `RESUMO_OTIMIZACAO.json`, `q3`). Em 3 métricas o otimizado também supera o Moderado publicado nas duas etapas e o **substitui** no registro: medidores (KNN k=5 com variáveis externas), rede AT (KNN k=15) e torres (KNN k=15) |
| 4 | Variáveis descartadas | **157** descartes (variável × métrica), todos na etapa de seleção. Crescimento anterior do ativo e das UCs: 27 de 27 (`INDISPONIVEL_NA_ORIGEM`, exigem 2021). Redundância com \|r\| > 0,95: estoques de transformadores (26), km BT (20), subestações (20), alimentadores (18), UCs (11) e outras. Constante: 1. Município, conjunto e potência: não aplicáveis ao painel por DIST |
| 5 | Variáveis mais relevantes por família (importância por permutação, seleção) | Clientes: km BT, km MT, estoque. Medição: UCs, estoque por UC, crescimento populacional. Estruturas: km MT, PIB per capita, estoque por UC. Redes: PIB per capita, subestações, estoque. Transformação: estoque, subestações, UCs. Seccionamento e proteção: alimentadores, crescimento populacional, estoque. Subestações e circuitos: crescimento populacional, UC por km BT, estoque. Mais selecionadas no geral: `ln_estoque` (47), externas do IBGE (39 cada), `ln_estoque_por_uc` (35) |
| 6 | Cenários com modelos independentes | **2.987** cenários extremos (DIST × métrica × direção) |
| 7 | Trajetórias condicionais do mesmo modelo | **246** |
| 8 | Sem evidência suficiente | **689** coincidentes com o Moderado (não publicáveis como distintos), mais 241 séries sem Moderado |
| 9 | Modelos que pioraram com a otimização | **59** de 104 (lista em `q9`). Exemplos: todos os otimizados de bancos de capacitores, chaves, postes e circuitos AT, e o RF/HGB/KNN de transformadores de distribuição |
| 10 | R² e erros melhoraram em relação ao original? | **Não, em geral.** Mediana da variação na etapa final: WAPE +0,026 p.p. (pior), com 44 melhoras e 59 pioras; R² do crescimento −0,006. As melhoras reais (14) são localizadas e pequenas |

## Limitações (impedem qualquer alegação de homologação)

- Há uma única origem de seleção, com uma transição de treino, e uma única origem final, em h=1. Horizontes de 2 a 5 anos não têm avaliação independente.
- O Moderado publicado foi escolhido pelo motor com as duas origens, logo também com o alvo de 2025. A comparação "publicado × otimizado" na etapa final não é cega para o publicado.
- O bootstrap por grupo e os níveis de aprovação estão no dossiê científico (branch `homologacao/cientifica-20261103`), que usa `PONTOS_AVALIACAO.csv`.
- A escolha por DIST e as trajetórias condicionais são **registro técnico**. Publicá-las exigiria:
  - regenerar o produto com essa regra;
  - o portão de plausibilidade do Motor V2 sobre os novos extremos;
  - as regressões completas e a revisão humana.
