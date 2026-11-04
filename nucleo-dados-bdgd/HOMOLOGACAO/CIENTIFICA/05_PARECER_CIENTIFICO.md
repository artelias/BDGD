# 05 — Parecer científico (preparado para revisão; não constitui homologação)

**Branch:** `homologacao/cientifica-20261103`. **Protocolo e critérios:** `01_PROTOCOLO_VALIDACAO.md`, commitado em `8dc088e` **antes** da avaliação.

**Objeto:**
- os modelos Moderados publicados do produto de cenários (`motor_cenarios`, RC `e4bc55c`);
- os candidatos originais e os otimizados (`exp/otimizacao-modelos-20261103@997c4d7`);
- os baselines.

**Escopo:** 27 métricas com série.

**Este parecer não é uma assinatura nem um aceite.** A homologação exige os revisores da seção 7.

## 1. Conclusão

**Estado geral: `NAO_HOMOLOGAVEL_COM_EVIDENCIA_ATUAL` para a finalidade do produto, que são cenários de 2026 a 2030 (horizontes de 1 a 5 anos).**

- **Horizonte de 1 ano:** há evidência retrospectiva com restrições para 7 Moderados publicados e evidência experimental para os demais.
- **Horizontes de 2 a 5 anos:** não há nenhuma avaliação independente possível com as competências 2022–2025. É exatamente onde estão os anos 2027–2030 das trajetórias.
- **Nenhum modelo é "homologado para o horizonte avaliado".** O critério exige pelo menos 3 origens independentes, e só existe 1.
- **Os cenários Conservador e Agressivo não são intervalos de confiança** e não recebem nível estatístico. Eles passam pela auditoria de plausibilidade da RC (documentos 11, 12 e 14 de `docs/ENTREGA_FINAL_2026`).

O motor pode ser **tecnicamente aceito** (Processo A) e continuar **cientificamente experimental**. Essa é a situação atual.

## 2. Viabilidade de dados históricos anteriores a 2022 (diagnóstico)

Fonte: inventário do catálogo ANEEL coletado em 22/10/2026 (`02_DISPONIBILIDADE_HISTORICA.csv`, 998 combinações DIST × competência). Nada foi baixado novamente.

| Questão | Achado | Consequência |
|---|---|---|
| **Disponibilidade efetiva** | Competências de 2016 a 2021 publicadas para 86 a 104 distribuidoras por ano; 77 DIST com 2016–2025 completo | Tecnicamente recuperável (cerca de 600 GDBs) |
| **Data em que cada versão estava disponível** | Todos os itens foram **recriados no portal entre 09 e 14/10/2025**; antes de 2022 há uma única versão por DIST e competência | A disponibilidade pública na época **não é comprovável** pelo catálogo |
| **Instante da informação** | O carimbo de geração no nome do arquivo mostra defasagem mediana de 5 a 12 meses depois da data-base. Pré-2022, 74 a 92 DIST por ano têm geração em até cerca de 13 meses (compatível com envio regular); as demais foram geradas 2 a 6 anos depois (possíveis revisões). 43 DIST têm 2016–2021 inteiro com geração regular | Um backtest **sem informação futura** pode usar só os arquivos com geração compatível com a origem. As revisões tardias precisam ficar de fora ou ser tratadas como informação posterior |
| **Comparabilidade de entidades, TUC e atributos** | Leiaute M6 (2016) → M10 (2017–2020) → V10 (2021) → V11 (2022–2025) | Exige um mapeamento auditado entre leiautes. Sem ele, a série antiga não é comparável à atual |
| **Sucessões e rupturas** | 59 competências fora de 31/12 (cortes societários no meio do ano). Mais as rupturas já tratadas em 2022–2025 (EPB/EBO, Celesc 2023 e outras) | Pontes societárias auditadas são necessárias antes de usar 2016–2021 |
| **Reproduzir previsões sem informação futura** | Possível em princípio para as origens 2018–2024, com as restrições de vintage e leiaute acima | Permitiria origens múltiplas e horizontes de 3 e 5 anos (por exemplo origem 2020 → alvo 2025) |

**O caminho para a homologação** seria:
1. autorização para baixar os GDBs de 2016–2021;
2. um ETL de leiaute com mapeamento auditado M6/M10/V10 → V11;
3. o filtro de vintage pela data de geração;
4. as pontes societárias;
5. reexecutar a seção 3 com pelo menos 3 origens por horizonte.

Esses dados históricos **não foram inventados nem interpolados**.

## 3. Resultados com os dados atuais

Evidência:
- `03_RESULTADOS_BACKTEST.csv`: 635 linhas por modelo, métrica e horizonte, com IC95% por bootstrap de grupo econômico (2.000 réplicas, semente 20261103);
- `04_MATRIZ_APROVACAO_MODELOS.csv`: 689 linhas, com horizontes 3 e 5 explicitamente não homologáveis.

### Moderado publicado, h=1 (origem 2024 → alvo 2025)

| Nível | Métricas |
|---|---|
| **Validado retrospectivamente, com restrições** (7) | chaves (Ridge, WAPE 2,93% contra 5,81% da persistência; IC95% da diferença [−3,4; −2,3] p.p.), conjuntos (persistência, 0,72% contra 3,69%), consumidores (Ridge, 2,56% contra 2,98%; IC [−0,72; −0,13] p.p.), geradores (deriva, 6,63% contra 13,50%), iluminação (persistência, 5,25% contra 6,59%), medidores (KNN, 1,12% contra 1,58%), ramais (KNN, 3,51% contra 4,57%) |
| **Experimental** (18) | as demais métricas de contagem e extensão. O IC95% inclui zero: não há evidência de que superem o melhor baseline. Exemplos: transformadores de distribuição (KNN 0,84% contra CAGR 0,90%; IC [−0,51; +0,36] p.p.), postes, rede BT/MT/AT, subestações, torres, religadores (WAPE 7,47% ≈ deriva 7,41%), transformadores de medida (WAPE 13,7%; viés −9,5%, perto do limite de reprovação) |
| **Não homologável com os dados disponíveis** (2) | potência de trafos de distribuição e de força (kVA via EQ→UN, métrica experimental por natureza) |
| **Reprovado** (0) | nenhum Moderado publicado |

**Restrição de todos os "validados":**
- há 1 origem final e o horizonte é h=1;
- para os Moderados publicados, **a avaliação final não é independente da seleção**, porque o motor os escolheu também com o alvo de 2025;
- o bootstrap reamostra grupos econômicos, mas com um único ano-alvo não capta choques comuns entre anos, então os intervalos são otimistas.

### Horizonte 2 (diagnóstico 2023 → 2025) e horizontes 3 a 5

Todos ficam `NAO_HOMOLOGAVEL_COM_EVIDENCIA_ATUAL`: não há origem final independente.

### Demais candidatos (h=1)

| | Experimental | Validado com restrições | Reprovado | Não homologável |
|---|---|---|---|---|
| **Originais** | 98 | 16 | 11 | 10 |
| **Otimizados** | 73 | 16 | 7 | 8 |
| **Baselines** | 49 | 7 | 19 | 6 |

Os otimizados foram selecionados só na origem 2023, então para eles a avaliação final é independente da seleção. Mesmo assim, a otimização piorou 59 de 104 pares (relatório da branch experimental).

### R² fora da amostra

O R² do crescimento anual por distribuidora, sem escala, fica perto de zero ou negativo em quase todos os modelos (mediana −0,02). O desempenho em WAPE vem da persistência do estoque, não da previsão da variação. **R² do nível não é evidência**, porque fica dominado pelo porte das empresas.

## 4. Robustez

- **Outliers:** excluindo as 5% maiores variações relativas observadas, o sinal da comparação com o melhor baseline se mantém em todas as linhas h=1 dos Moderados publicados (`sensibilidade_outliers = mantem_sinal`). A única inversão é chaves em h=2 (diagnóstico): o Ridge é pior que o baseline com todos os pontos (3,66% contra 3,50%) e melhor sem os outliers (3,26% contra 3,57%). Em h=2, chaves já é não homologável.
- **Rupturas e ausências:** pontos com ruptura cadastral, sucessão ou valor não observado ficam fora da avaliação.

## 5. Comparação externa

**Pendente.** Não há, versionada no projeto, uma série externa de consumidores por distribuidora (ANEEL SAMP/indicadores de mercado ou EPE, Anuário Estatístico) para 2022–2025. Para não inventar valores, a comparação não foi feita.

O que é necessário:
- a série anual de unidades consumidoras por distribuidora;
- a data de publicação de cada valor (para respeitar a origem);
- o mapeamento do código da distribuidora;
- o tratamento das mesmas sucessões.

Para ativos físicos não há fonte externa compatível conhecida.

## 6. Qualidade da evidência

**Baixa para a finalidade do produto:**
- 4 anos;
- 1 origem final;
- 1 horizonte avaliável;
- choques comuns não estimáveis;
- seleção do Moderado publicado não cega ao alvo final.

**Moderada só para a afirmação restrita** de que, em h=1, 7 Moderados publicados superaram o melhor baseline simples em 2025 com intervalo por grupo totalmente negativo.

## 7. Assinaturas humanas necessárias (não registradas)

| Papel | Nome | Decisão | Data | Assinatura |
|---|---|---|---|---|
| Revisor estatístico independente (séries temporais / validação fora da amostra) | | | | |
| Especialista do setor elétrico (BDGD, regulação de distribuição) | | | | |
| Responsável técnico pelo motor | | | | |
| Responsável pela decisão de publicação | | | | |

Decisões que cabem aos revisores:
1. aceitar ou não o nível "validado com restrições" para h=1 nas 7 métricas, dada a não independência da seleção;
2. autorizar a recuperação das competências 2016–2021 (download, ETL de leiaute e vintage);
3. definir a fonte externa de consumidores;
4. manter a comunicação de "cenários experimentais" para 2027–2030 até haver avaliação em horizontes longos.
