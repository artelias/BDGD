# Motor Universal BDGD — primeira entrega executável

## Decisões de integração adotadas

O formato principal é **Parquet**: `targets.parquet` em long, chave **ANO + DIST + OBJETIVO_ID + METRICA**, e `features.parquet` em wide, chave **ANO + DIST**. A granularidade inicial é DIST × ano. O núcleo usa chaves territoriais extensíveis, mas o adaptador Parquet v1 recusa dados municipais: a ativação futura exige contrato territorial v2, pesos, cobertura e prova de ausência de sobreposição. Nenhuma distribuição municipal é inferida de um agregado DIST.

O bundle contém `manifest.json` com versão, granularidade, chaves, definições de features e SHA-256 dos dois arquivos. Os alvos incluem `UNIDADE`, `VALOR_ALVO` nullable, `STATUS_QUALIDADE`, **`STATUS_HOMOLOGACAO`**, **`RUPTURA_CADASTRAL`**, `PROVENIENCIA_JSON`, `NATUREZA_ALVO`, cobertura, fonte, competência, disponibilidade, perímetro/regra, `HOMOLOGADO`, `NAO_SOMAR`, `COMPARABILIDADE_VALIDADA` e evidência de comparabilidade. `METADADOS_JSON` preserva metadados opcionais, sem duplicar as features. O reader verifica hashes, esquema, chaves e cardinalidade m:1 da junção antes de executar modelos. Duas regras/perímetros para a mesma chave long são recusadas: o fornecedor deve canonicalizar formalmente.

No wide, cada coluna `nome_feature` tem seu valor tipado e colunas auxiliares `nome_feature__disponivel_em`, `__referencia`, `__fonte` e `__cenario_id` nullable. Tipo e unidade ficam no manifesto; nomes não podem conter `__`. Features específicas de ativo usam nomes qualificados, por exemplo `trafo_dist_potencia_media`, e `objetivos_aplicaveis` na definição. Valores diferentes da mesma feature no mesmo DIST × ano são conflito, não observações adicionais. Linhas wide futuras podem fornecer cenários; o adaptador cria apenas alvos **null**, identificados como linhas exclusivas de features.

Os nulls permanecem null em Parquet e viram N/D na interface; zero técnico permanece 0 com seu estado e fica fora do treino. Não há preenchimento automático de alvos. Potência, consumo, demanda e qualquer métrica nova fora de quantidade/extensão exigem comparabilidade validada e evidência em cada linha usada. Todas as features externas também exigem `comparabilidade_validada=true` e `evidencia_comparabilidade`, além das datas. Ausência de comprovação bloqueia o candidato. Os limiares não homologam a evidência: a frente de auditoria continua responsável por fornecê-la.

**Alvo desta versão: estoque físico.** Variação líquida é a diferença entre dois estoques comparáveis e contíguos, com sinal negativo permitido nessa diferença; não se calcula ao atravessar ruptura, ausência ou métrica não comparável. Necessidade de expansão permanece **null / não identificável apenas por estoque**. Não se inferem entradas, reposições, baixas, demanda reprimida, obras ou CAPEX a partir de uma diferença líquida positiva.

O artefato de execução publica **`projecoes.parquet`, `backtests.parquet` e `metricas.parquet`**, além de manifestos JSON de definições/execução e diagnósticos. `--debug-json` é uma cópia opcional para auditoria, não o formato principal. O adaptador CSV nacional é somente uma migração dos produtos já processados: o CLI grava e relê o bundle Parquet antes de executar o motor. JSON é usado apenas para metadata, fixtures/migração e a **visão web comprimida**, carregada sob demanda. As bases Parquet completas não são versionadas no git nem carregadas pelo navegador.

Base inspecionada em 26/10/2026: PR #9, `bf0cbfa3b7aea303bb672263d5422a87b89f3d89`, dependente de #8 → #6 → #4; todos abertos e sem merge. Branch própria `feat/motor-universal-ativos-bdgd`. O catálogo tem 17 conceitos semânticos, 25 ativos nomeados e 29 combinações válidas de ativo/métrica. Não é uma lista fixa de TUCs.

## Executar

A partir de `nucleo-dados-bdgd` (Python ≥ 3.11):

```sh
python3 -m pip install -r motor_universal/requirements.txt
python3 -m unittest discover -s motor_universal/tests -v
python3 -m motor_universal --output /tmp/experimento-bdgd-001
# Extra opcional para testar/treinar estimadores compatíveis, quando elegíveis:
python3 -m pip install -r motor_universal/requirements-ml.txt
# Produto compacto, carregado sob demanda na página Previsões:
python3 -m motor_universal --output /tmp/experimento-bdgd-002 --web-summary web/public/data/previsoes/motor-universal-resumo.json.gz
# CI: verifica se o produto versionado corresponde ao código e ao contrato:
python3 -m motor_universal --output /tmp/experimento-bdgd-check --web-summary web/public/data/previsoes/motor-universal-resumo.json.gz --check-web
# Painel enriquecido do fornecedor; substitui a leitura do contrato nacional:
python3 -m motor_universal --panel /caminho/bundle-parquet --registry /caminho/objetivos.json --base-year 2025 --final-year 2030 --as-of 2026-10-26 --output /tmp/experimento-enriquecido-001
```

Os comandos não baixam, extraem ou consolidam GDBs. Não sobrescrevem diretório de experimento existente. `experimento-manifesto.json` contém diagnósticos, períodos, hashes e restrições; os folds, projeções e métricas estão nos três Parquets. `experimento.json` completo só é escrito quando solicitado com `--debug-json`. `execucao.json` contém timestamp UTC, Python e versões instaladas; `objetivos.json` fixa as definições utilizadas. A identidade do experimento inclui painel, registro, horizontes, corte e SHA-256 do código. Reexecutar os mesmos bytes/configuração produz o mesmo experimento; timestamps de execução ficam separados. O artefato completo é gerado em diretório temporário/CI, não versionado como base volumosa. O núcleo de cálculo usa biblioteca padrão; a interface principal usa PyArrow 26.0.0; os seis estimadores opcionais usam scikit-learn 1.8.0.

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| registry.py | Registro dinâmico derivado do catálogo ou contrato `objetivos-1` fornecido pelo ChatGPT |
| contracts.py | Schema, chaves, tipos, unidades, estados, competências, cobertura e corte nas rupturas/lacunas |
| parquet_io.py | Alvos long e features wide, hashes, schemas, junção m:1 e resultados Parquet |
| adapters.py | Adaptador somente leitura das 11.400 linhas do contrato nacional, com conferência de SHA-256 |
| features.py | Defasagem, média móvel, crescimento defasado, razões/densidades/interações declaradas; encoder fit só no treino |
| models.py | Persistência, OLS com intercepto, crescimento histórico e candidatos opcionais Ridge/Lasso/Elastic Net/Poisson/Random Forest/HistGradientBoosting |
| engine.py | Origem expansiva, horizontes 1–5, comparação e seleção por série, auditoria na última origem, métricas por objetivo/família |
| reconcile.py | Agregação opt-in com universo explícito, cobertura completa e evidência de disjunção |
| __main__.py | CLI, registro reproduzível e produto compacto para web |

## Contrato de entrada para Claude/ChatGPT

O schema legível por máquina está em `schemas/painel.schema.json`. A validação semântica adicional é executada por `validate_panel`: um JSON Schema sozinho não prova unidade, população ou comparabilidade. `schemas/painel-sintetico.exemplo.json` é **sintético**, somente para testar o software; o parser web recusa sua publicação.

Envelope obrigatório:

| Campo | Tipo / regra |
|---|---|
| schema_version | string exata `painel-bdgd-1` |
| dataset_version | string imutável para cada versão de dados |
| sintetico | booleano explícito; nunca inferido pelo nome do arquivo |
| feature_definitions | objeto nome → definição; pode ser vazio |
| rows | array de observações e, opcionalmente, linhas futuras de features |

Cada observação requer `ano` inteiro, `DIST` código positivo, `objetivo_id`, `metrica`, `unidade`, `valor_alvo` número finito não negativo ou null, `features` objeto, `status_qualidade`, `fonte`, `competencia` AAAA-12-31, `disponivel_em` data ou null, `territorio: {nivel,id}`, `perimetro_id`, `regra_versao`, `ruptura`, `nao_somar`, `homologado` (booleanos), `status_homologacao` string explícita, `cobertura` número [0,1] ou null. A representação interna mantém nível/id territorial, perímetro e regra para auditoria; o adaptador principal exige unicidade estrita de ANO × DIST × OBJETIVO_ID × METRICA, sem usar versões como multiplicadores de observações. Para município/alimentador/subestação, o código deve identificar uma população comprovada dentro da DIST; esta camada não certifica geografia nem cria relações EQ*/UN*.

Estados: `observado` positivo; `zero_verificado` exige valor 0 e `evidencia_zero` independente; `zero_tecnico` preserva o 0 mas fica fora do treino; `ausente`, `nao_homologado` e `nao_aplicavel` exigem null. Não há imputação do alvo. Campo desconhecido de qualidade, duplicidade, quantidade observada fracionária, unidade incompatível, NaN/infinito ou valores negativos interrompem a ingestão. Cobertura parcial, não somável, ponte pendente, ruptura ou lacuna interrompem o segmento treinável. Usa-se apenas o segmento contíguo mais recente, terminando no ano-base.

Opcionalmente: `empresa`, `motivo`, `proveniencia` (IDs de publicação, hashes e decisões), `evidencia_zero`, `ponte_pendente`, `limites` no envelope. O adaptador preserva a data-base de origem dentro da proveniência; a competência da linha é o ano solicitado no contrato. Fonte não informada continua explícita como ausência na publicação, referenciando o contrato que originou a linha.

Uma feature tem `{valor, disponivel_em, referencia, fonte, unidade}`. A definição contém `{tipo: numerica|categorica, unidade, comparabilidade_validada, evidencia_comparabilidade, objetivos_aplicaveis?: ids[], permite_imputacao?: boolean, dividir_por?: nomes[], interagir_com?: nomes[]}`. Exemplos: clientes por km, potência por equipamento e densidade populacional são razões **declaradas** pelo fornecedor, com unidades e população próprias; não são inferidas dos nomes. Datas e fontes são obrigatórias mesmo para demografia, PIB, energia ou clima. Razões/interações só aceitam duas features numéricas. Denominador não positivo gera feature ausente, nunca zero presumido. Ausência de covariável só é imputável se a definição autorizar; média/escala são ajustadas novamente em cada treino. Categorias são aprendidas só no treino; categoria nova é codificada como desconhecida, sem reestimar níveis com o teste.

Features de referência contemporânea/futura exigem `cenario_id` explícito. Linhas posteriores ao ano-base precisam ter alvo null; podem fornecer features de cenário. Nenhuma feature com disponibilidade posterior à origem é usada no backtest, ainda que seu ano de referência seja antigo. PIB revisado e clima observado no futuro não são cenários históricos admissíveis sem disponibilidade documentada. Quando faltar covariável futura, o candidato é bloqueado em vez de carregar o último valor ou inventar uma trajetória.

O registro substituível usa `schema_version: objetivos-1`, `objetivos: []`. Cada item exige `objetivo_id`, `nome`, `familia`, `entidades`, `metrica`, `unidade`, `regra_agregacao`; aceita filtros/atributos, `tipo_alvo`, `territorios`, `padrao`, elegibilidade e metadados de qualidade. O arquivo gerado `objetivos.json` é um exemplo completo. ID + métrica deve ser único. Alterações de unidade/população exigem nova versão; séries com regras/perímetros diferentes não são coladas. O adaptador nacional só conhece os IDs já existentes; renomeações sem mapeamento formal são recusadas, não adivinhadas.

## Validação e seleção

Cada origem usa todos os anos anteriores do segmento, nunca divisão aleatória. Os baselines exigem dois anos de treino; backtests iniciam no terceiro ponto. A última origem de um passo é reservada para auditoria e não participa da seleção. As origens anteriores comparam os mesmos pontos; candidato incompleto é inelegível. Seleção exige duas origens para baselines, três para ML, projeção física válida e ganho mínimo de 2% sobre persistência. Empates favorecem menor complexidade. Os limiares são conservadores de engenharia, não prova de suficiência científica. Quatro anos não os satisfazem: persistência permanece referência, enquanto OLS/crescimento são comparados como diagnósticos. Dados após o corte real de disponibilidade bloqueiam a série.

Há MAE, RMSE, WAPE (null com denominador zero), viés e desvio dos erros, por série, horizonte, objetivo e família/unidade. Métricas de seleção são rotuladas separadamente das de auditoria. Agregações de erros por família são descritivas: não são somas de estoques, não provam independência e não permitem comparar grupos com cobertura diferente sem conferir `n`. Não se somam ativos sobrepostos ou itens com km/kVA. A função de reconciliação só soma o mesmo objetivo/unidade/perímetro/ano com universo completo e evidência de territórios disjuntos. Nenhum total nacional projetado é publicado nesta entrega.

Estimadores ML têm mínimos de treino fixados no registro (8, 12, 20 ou 30 observações anuais), parâmetros fixos e sementes onde aplicável; não há busca de hiperparâmetros sobre o holdout. Ajuste/seleção, quando elegíveis, ocorrem por série. Os contratos futuros permitem mais territórios, mas **pooling entre empresas e modelos hierárquicos não foram implementados**: não é defensável improvisar o painel sem as definições de população/território. GAM, binomial negativa, modelos sazonais e XGBoost/LightGBM/CatBoost são slots de extensão documentados, não algoritmos anunciados como treinados.

Projeções negativas/não finitas são rejeitadas e registradas; não são truncadas silenciosamente para zero. Não se calibram intervalos com tão poucas origens. O software não faz homologação humana e não produz `previsao_validada=true`. Mesmo com série longa, o resultado só pode dizer avaliação temporal sem homologação; promoção científica requer critérios e decisão formal da frente de auditoria.

## Experimento real inicial e integração

O contrato atual tem 11.400 linhas, 114 DIST, quatro anos (2022–2025), 25 ativos e principalmente quantidade/extensão. Não há painel completo de atributos individuais, variáveis externas nem disponibilidade original das observações. O adaptador não trata a data de geração de 2026 como se fosse data de publicação histórica. Avaliações são **retrospectivas revisadas**, não point-in-time. Zeros legados são técnicos sem evidência independente. Nada disso altera os arquivos canônicos.

A execução inicial identificou 2.850 séries: 1.545 com baseline executável, 1.305 bloqueadas; zero previsões homologadas. As 29 combinações incluem métricas sem histórico: esse número não significa 29 modelos treinados por empresa. A população difere das 1.555 séries do cenário legado, porque o novo motor corta segmentos, recusa zeros técnicos e avalia elegibilidade própria. Não se substituiu o produto anterior nem seu CSV.

Previsões mantém os cenários anteriores e acrescenta um explorador de experimentos sob demanda, com família/ativo/métrica/DIST/modelo/horizonte, histórico versus simulação, diagnóstico, motivos de bloqueio e exportação JSON com hashes/versões. A página não treina nem baixa o artefato completo. Potência sem histórico continua sem números. O consumidor web recusa schema desconhecido, dataset sintético, unidade incompatível e projeção negativa.

## Dependências externas e próxima ação

Claude: entregar painel versionado, inventário de atributos, chaves de relacionamento verificadas, matriz DIST × municípios com pesos/overlaps, features internas/externas com fonte, referência, unidade e disponibilidade, além de cenários futuros explícitos. ChatGPT: confirmar populações, contrato de métricas, critérios de homologação, sucessões e decisões de fontes. Nenhuma republicação divergente foi aprovada por este motor.

Ao receber esses produtos: validar com `--panel/--registry`, resolver bloqueios de qualidade, executar candidato elegível e comparar holdout/horizontes antes de promover qualquer previsão. Sem séries mais longas e definições de painel, não declarar Random Forest, modelos econômicos ou previsões 2026–2030 para todos os ativos como validados.

Referências primárias consultadas: [scikit-learn 1.8 — Pipelines](https://scikit-learn.org/1.8/modules/compose.html), [TimeSeriesSplit](https://scikit-learn.org/1.8/modules/generated/sklearn.model_selection.TimeSeriesSplit.html), [prevenção de leakage](https://scikit-learn.org/1.8/common_pitfalls.html). O motor implementa sua própria origem expansiva por ano/grupo; não aplica TimeSeriesSplit indiscriminadamente a linhas empilhadas de empresas.

Parquet: [Apache Arrow — leitura/escrita e tipos](https://arrow.apache.org/docs/python/parquet/parquet.html). As 11.400 linhas não são observações independentes; a comparação continua restrita a séries e blocos temporais, sem pooling artificial.
