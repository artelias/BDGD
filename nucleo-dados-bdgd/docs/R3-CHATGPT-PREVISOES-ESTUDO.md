# R3 — Viabilidade estatística de Previsões (estudo independente)

**Data-base da avaliação:** 23/10/2026. **Status:** estudo e arquitetura, sem treinamento de modelo ou publicação de projeções.

## Evidência efetivamente disponível

- 2025: 99 de 99 GDBs elegíveis processados, pacote BDGD homologado no contrato técnico. Homologação do contrato **não** implica que toda métrica de negócio esteja apta para modelagem.
- Checkpoint versionado em `web/src/data/historico_status.json` (gerado em 23/10/2026): 2022 = 74/99 elegíveis processadas, 4 em quarentena; 2023 = 62/89 processadas, 7 em quarentena; 2024 = 76/97 processadas, 0 em quarentena. **Zero competências históricas homologadas** nos três anos. Contagens do checkpoint não substituem valores anuais auditados.
- 2025: as 14 distribuidoras distintas com conflitos de UC v2 (22 tabelas) impedem uma série nacional de UC comparável sem regra específica. Potência de geração N/D; não modelar.
- Quatro anos de calendário (2022–2025) significam, no máximo, **quatro pontos anuais por unidade observacional**, mesmo que haja centenas de milhões de registros BDGD.

## Unidade estatística, elegibilidade e população

Chave da série: `(perimetro_referencia, dist_canonico, conceito, tuc_ou_entidade, metrica, unidade, versao_regra, ano)`.

É preciso guardar: valor, `estado` (observado, ausência de GDB, não homologado, não aplicável, zero verdadeiro, ruptura), data-base, conjunto de predecessoras, fonte, cobertura e prova de aditividade. Não imputar zero para falta; não concatenar métricas sob versões incompatíveis. Para agregação nacional, declarar universo exato (somente GDBs elegíveis 2025 versus concessões históricas), evitando mudar o denominador silenciosamente.

Duas visões:
1. **Original regulatória**: cada DIST/ano como publicada.
2. **Perímetro comparável 2025**: reconstrução condicionada a atos, mapas de concessão, provas de disjunção e comparabilidade por métrica. Nunca agregar 100% de predecessora em transferência territorial parcial.

O caso EPB/EBO não autoriza soma por nome: observar a incorporação em 30/04/2023, verificar nos GDBs se 2023 já contempla o perímetro inteiro e evitar contagem dupla.

## Viabilidade por método

| Método | Requisito de dados | Parecer atual |
|---|---|---|
| Último observado (`naive`) | 1 valor elegível + perímetro estável | Baseline técnico, não evidência de crescimento |
| Incremento absoluto anual | >= 2 anos homogêneos | Cenário exploratório, sensível a outliers |
| Tendência linear por DIST | 3–4 anos completos | Identificável, mas altamente instável; extrapolação longa não validada |
| Taxa composta CAGR | 2 extremos positivos, mesmo perímetro | Cenário descritivo, não intervalo probabilístico calibrado |
| ETS/ARIMA por DIST | Série longa para identificar componentes e testar resíduos | Não apropriado como modelo validado com 4 pontos |
| Painel hierárquico (parcial pooling) | Muitas DISTs comparáveis, covariáveis temporais históricas, quebras documentadas | Possível pesquisa exploratória posterior; **não** cria quatro anos de informação temporal independente |
| LSTM/transformer/gradient boosting | Muitos períodos e validação temporal robusta | Sem justificativa estatística na situação atual |

Para ativos escassos, separar *zero estrutural* (ausência substantiva) de *zero amostral/cadastral*. Considerar modelos em duas partes (presença + magnitude) somente se a série e o número de unidades permitirem. Não aplicar log(x) cego em zeros, nem MAPE quando denominadores são zero ou próximos de zero.

## Backtesting que realmente cabe no intervalo

Com 2022–2025, cortes temporais candidatos são:
- treino 2022–2023 → teste 2024 (horizonte 1), desde que o método seja identificável com apenas dois pontos;
- treino 2022–2024 → teste 2025 (horizonte 1).
- treino 2022–2023 → teste 2025 (horizonte 2): somente como *stress test* de métodos que requerem no máximo dois pontos; **não** uma avaliação sólida do horizonte 2.

Apenas duas origens possíveis para horizonte 1 e uma para horizonte 2, dependendo da série. Não existe validação externa convincente para horizontes de três ou quatro anos (2028–2029). Dividir aleatoriamente linhas BDGD ou distribuir anos futuros aleatoriamente no treino gera vazamento.

**Critério de elegibilidade:** publicar predição probabilística por horizonte somente se os horizontes tiverem backtests temporais suficientes, cobertura empírica de intervalos avaliada e melhoria estável contra naive; critérios mínimos devem ser pré-registrados após a homologação histórica. Não calibrar intervalos 80%/95% apenas sobre duas diferenças anuais. Para grupo/Brasil, reconciliar somas somente de séries compatíveis e cobertura equivalente.

**Métricas propostas:** MAE, viés médio, WAPE com denominador positivo e MASE com denominador de treino definido. Separar perdas por quantidade, km e kVA; não colapsar em score arbitrário único. Reportar cobertura temporal/hierárquica e taxa de previsão não disponível.

## Covariáveis possíveis (não aprovadas para inclusão automática)

UC homologada, extensão de rede e nível de tensão, demanda/energia distribuída, população municipal e atividade econômica, clima e eletrificação, obras e expansão, migração de concessões e regulação. Para cada covariável verificar: fonte, data de disponibilização (as-of), granularidade territorial, alterações metodológicas, integridade retrospectiva e influência de alvo. Indicadores medidos após o ano previsto não podem ser usados como entradas de previsão anterior.

## Contrato de arquitetura (sem ML nesta branch)

Uma tabela privada `series_anual` com chave da série, status e metadados; tabela `perimetro_bridge` versionada; `experimento_baseline` com cortes; e `previsoes_publicaveis` ainda **vazia**. O frontend pode receber somente: `ano_origem, ano_alvo, conceito, unidade, perimetro, valor_previsto, limite_inferior, limite_superior, estado_validacao, modelo_id, versao_dados` após gate técnico. Limites e valores ficam nulos se não estimados/validados. A rota de Previsões não deve receber números sintéticos.

## Critérios para iniciar implementação estatística

1. Homologação integral dos ETLs 2022, 2023 e 2024 ou declaração de subconjuntos comparáveis por indicador.
2. Ponte oficial de sucessões assinada e auditoria dos efeitos sobre série por DIST/grupo.
3. Catálogo de semântica de KPIs estável e uniforme nos quatro anos.
4. Relatório de completude e inexistência de vazamento.
5. Protocolo de baselines e avaliação por horizonte pré-registrado.
6. Aprovação específica do proprietário antes de treinamento/modelagem exploratória.

**Decisão R3 atual:** não iniciar treinamento. Gerar primeiro auditoria de elegibilidade das séries e um relatório estatístico descritivo quando os históricos estiverem homologados.
