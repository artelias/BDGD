# 01 — Protocolo de validação científica do Motor (cenários 2026–2030)

**Processo B, independente da homologação de engenharia.** Branch `homologacao/cientifica-20261103`, criada a partir da RC `rc/1.0-20261101`.

Este protocolo e os critérios da seção 6 foram versionados **antes** da execução de `avaliar.py`; o histórico git prova a ordem. Nenhum critério foi ajustado depois de ver resultados. Quem revisar deve conferir que o commit do protocolo precede o dos resultados.

## 1. Pergunta e unidade de avaliação

A pergunta é se as trajetórias do motor para estoque físico por distribuidora, ativo e métrica prevêem o estoque observado melhor que os baselines simples, num horizonte definido, sem informação futura.

A unidade é a célula (DIST, ativo, métrica, horizonte), agregada por ativo/métrica e horizonte. Os cenários Conservador e Agressivo **não são intervalos de confiança**: são trajetórias condicionais e não recebem cobertura probabilística. A validação estatística mede só o Moderado e os modelos candidatos. Os extremos passam pela auditoria de plausibilidade (seção 8).

## 2. Dados disponíveis e viabilidade

> **Emenda de 04/11/2026 (diretriz do responsável):** só as competências BDGD validadas de 2022 a 2025 entram no treinamento e na homologação; as anteriores a 2022 ficam excluídas. Os critérios da seção 6 não mudam: o nível "homologado" exige pelo menos 3 origens independentes. Painéis granulares (município, conjunto, circuito) **não criam origens temporais novas**, e com 2022–2025 continua havendo 1 origem final (2024 → 2025).

Ver `02_DISPONIBILIDADE_HISTORICA.csv` e o parecer (`05`).

- **Hoje no Núcleo:** competências de 31/12/2022 a 31/12/2025, quatro anos e três transições anuais.
- **No catálogo ANEEL:** competências de 2016 a 2021 de 86 a 104 distribuidoras por ano, **não processadas**. O inventário foi coletado em 22/10/2026, sem novo download nesta etapa.
- **Vintage:** todos os itens foram recriados no portal entre 09 e 14/10/2025. A data de disponibilidade pública de cada versão **não é comprovável** pelo catálogo. O carimbo de geração no nome do arquivo é a melhor evidência do instante da informação.
  - Antes de 2022, há uma versão por DIST e competência.
  - De 74 a 92 DIST por ano (até 2020) têm geração até cerca de 13 meses após a data-base, compatível com o envio regular.
  - Os demais foram gerados de 2 a 6 anos depois, possivelmente revisados.
- **Comparabilidade:** o leiaute muda de M6 (2016) para M10 (2017–2020), V10 (2021) e V11 (2022–2025). Recuperar 2016–2021 exige um mapeamento auditado de entidades, TUC e atributos entre leiautes, mais as sucessões societárias (fusões e incorporações) anteriores a 2022.

## 3. Desenho temporal (fora da amostra, sem informação futura)

| Uso | Origem T (treino só com t ≤ T) | Alvo | Horizonte |
|---|---|---|---|
| Seleção de variáveis e hiperparâmetros | 2023 | 2024 | 1 |
| **Avaliação final** | 2024 | 2025 | 1 |
| Diagnóstico | 2023 | 2025 | 2 |
| Horizontes 3 e 5 | — | — | **impossíveis com 2022–2025** |

- Nenhuma escolha usa a avaliação final (2024 → 2025).
- O Moderado **publicado** foi escolhido com as duas origens, logo também com o alvo de 2025. Para ele a avaliação final **não é independente**, e o veredito fica limitado a "validado retrospectivamente, com restrições" no máximo.
- Variáveis externas só entram se divulgadas até a origem (IBGE: Censo 2022 divulgado em 31/08/2023 e PIB municipal 2021 em 15/12/2023, ambos antes de 31/12/2023).

## 4. Comparadores e métricas

- **Baselines:** persistência, deriva (passeio com tendência) e CAGR, nos mesmos pontos.
- **Erros:** MAE, WAPE, RMSE e viés relativo.
- **Contagens:** erro físico depois do arredondamento meio para cima, como publicado.
- **Escala:** R² fora da amostra do crescimento ln(y_alvo/y_origem), sem escala. O R² do nível (estoque) é relatado e não é critério, porque fica dominado pelo porte.
- R² não definido quando n < 5 ou SST = 0, nunca substituído por zero.

## 5. Incerteza e dependência

**Bootstrap por grupo econômico:** reamostra grupos (as distribuidoras de um mesmo grupo saem juntas; independentes e cooperativas são grupos unitários), com 2.000 réplicas e semente 20261103. O intervalo de 95% é percentil da diferença de WAPE (modelo − melhor baseline) e da razão de WAPE.

Limitação: com um único ano-alvo, o bootstrap capta a variação entre distribuidoras, não a variação entre anos (choques comuns a todas no mesmo ano). Isso é registrado e torna os intervalos otimistas.

## 6. Critérios de aprovação (pré-definidos)

Por ativo/métrica e horizonte, para o Moderado publicado e para cada candidato:

| Nível | Critério |
|---|---|
| **Homologado para o horizonte avaliado** | Avaliação final independente de toda escolha; ≥ 3 origens de avaliação independentes no horizonte; IC95% da diferença de WAPE contra o melhor baseline < 0 em todas as origens; viés relativo dentro de ±5%; erro físico (contagens) não pior que o melhor baseline. **Inatingível com 2022–2025** (há 1 origem final). |
| **Validado retrospectivamente, com restrições** | Na origem final (h=1), IC95% (bootstrap por grupo) da diferença de WAPE contra o melhor baseline totalmente < 0, viés dentro de ±5% e pelo menos 20 distribuidoras avaliadas. A restrição é registrada: 1 origem, h=1 apenas; para o Moderado publicado, a avaliação final não é independente da seleção. |
| **Experimental** | Melhor que o melhor baseline na estimativa pontual de WAPE na origem final, sem IC95% totalmente negativo; ou critério acima atendido com menos de 20 distribuidoras. |
| **Não homologável com os dados disponíveis** | Horizontes 2 a 5 (sem origem final independente), métricas sem pontos de avaliação suficientes (< 10) e métricas experimentais por natureza (potência via EQ→UN). Estado: `NAO_HOMOLOGAVEL_COM_EVIDENCIA_ATUAL`. |
| **Reprovado** | Na origem final (h=1), IC95% da diferença de WAPE contra o melhor baseline totalmente > 0 (pior que um baseline simples com evidência), ou viés relativo fora de ±10%. |

Não basta erro menor na mesma amostra que selecionou o modelo. Por isso o critério usa a origem final e, para os modelos otimizados, a seleção foi feita só na origem 2023.

## 7. Robustez a rupturas e ausência

- Pontos com ruptura cadastral (`ruptura_desde_ano_anterior`), sucessão ou valor não observado ficam fora da avaliação, e as exclusões são contadas.
- Sensibilidade: o veredito é recalculado excluindo as 5% maiores variações relativas observadas na origem final, para checar dependência de outliers cadastrais.
- Uma mudança de veredito vai para o parecer.

## 8. Plausibilidade dos três cenários

Usa a auditoria da RC (`docs/ENTREGA_FINAL_2026/11`, `12`, `14`) e a coerência por distribuidora: Conservador ≤ Moderado ≤ Agressivo, sem valores negativos e com contagens inteiras. Extremos não recebem nível de homologação estatística.

## 9. Comparação externa

ANEEL (SAMP/indicadores de mercado), EPE (Anuário Estatístico de Energia Elétrica: número de consumidores por distribuidora) e IBGE. Essas fontes são compatíveis para o número de consumidores e não para ativos físicos.

Não há série externa já versionada no projeto para consumidores por distribuidora. A comparação externa fica **pendente**, com a especificação dos dados necessários no parecer. Não é preenchida com valores não coletados.

## 10. Separação de papéis

A homologação científica é decisão humana de revisores com competência estatística e no setor elétrico. Este dossiê prepara a evidência e não registra assinatura, aceite nem nível de confiança que não tenha sido calculado.
