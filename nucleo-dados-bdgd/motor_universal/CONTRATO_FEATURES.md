# Integração de features reais — Parquet v2

Versão implementada: engine 1.1.0, envelope `painel-bdgd-1`, bundle `bdgd-parquet-2`, registro `objetivos-1`. Nenhuma mudança nos produtos históricos originais. O leitor mantém compatibilidade com `bdgd-parquet-1`; o escritor publica v2. `dataset_version` identifica uma entrega imutável; não reutilizar a versão para bytes diferentes. O manifesto registra hashes de todos os Parquets; a execução registra código, dados, dependências, corte e resultados.

## Arquivos e cardinalidade

| Arquivo | Chave única | Conteúdo |
|---|---|---|
| targets.parquet | ANO + DIST + OBJETIVO_ID + METRICA | Alvos long; estrutura histórica preservada, estados, unidade, competência/disponibilidade, homologação, ruptura e proveniência |
| features.parquet | ANO + DIST | Covariáveis compartilhadas wide |
| features_objetivo.parquet, opcional | ANO + DIST + OBJETIVO_ID | Covariáveis wide específicas de ativos |
| manifest.json | Uma entrega | Schema, granularidade, chaves, versões, definições, hashes |

As duas junções são **m:1**, nunca m:m. A mesma feature compartilhada não pode ter valores/proveniências conflitantes na mesma chave. Variáveis específicas podem variar entre ativos, mas não entre duas métricas do mesmo ativo; nesse caso o fornecedor precisa definir duas variáveis com nomes distintos. Duplicidades não são resolvidas com média, soma ou escolha da primeira linha. Mudanças de regra/perímetro não autorizam duplicar uma chave long.

O writer `write_bundle(panel, registry, pasta_nova)` faz a separação segundo `objetivos_aplicaveis`. O reader `read_bundle(pasta, registry)` valida esquema Arrow, tipos, nomes reservados/duplicados, hashes, unicidade e associações. Features específicas são filtradas por escopo; novos ativos exigem entrada no catálogo/registro, sem lista fixa no motor. Diretórios de experimentos existentes não são sobrescritos.

## Definição e metadados por variável

A definição no manifesto exige `tipo: numerica|categorica` e `unidade`; para uso pelo candidato exige `comparabilidade_validada: true` e `evidencia_comparabilidade`. `objetivos_aplicaveis: [ids...]` não vazio indica escopo específico; ausente/vazio indica escopo compartilhado. `permite_imputacao` é booleano e vale apenas para treino. Razões/interações usam `dividir_por`/`interagir_com` e duas variáveis numéricas declaradas.

| Coluna por variável x | Tipo Arrow / regra |
|---|---|
| x | float64 ou string, nullable |
| x__referencia | date32: competência do valor usado, distinta de ANO do alvo |
| x__disponivel_em | date32: primeira data em que essa versão do valor estava disponível |
| x__fonte | string não vazia, referência rastreável da variável |
| x__cenario_id | string nullable; obrigatório para referência contemporânea/futura ao alvo ou posterior à própria disponibilidade |
| x__status_comparabilidade | string nullable: VALIDADA, PENDENTE ou INCOMPATIVEL |
| x__evidencia_comparabilidade | string nullable, evidência específica da observação |
| x__ruptura | bool nullable; true bloqueia o candidato enriquecido |
| x__versao | string nullable, versão específica da variável/observação |

Metadados específicos são preservados; quando omitidos, o contrato legado usa o status/evidência da definição e a versão imutável do dataset. Não há homologação automática dessas declarações. Para a entrega enriquecida, fornecer os controles por observação sempre que houver revisões, rupturas ou comparabilidade variável. Na representação interna esses campos são `referencia`, `disponivel_em`, `fonte`, `cenario_id`, `status_comparabilidade`, `evidencia_comparabilidade`, `ruptura` e `versao`.

NULL é ausência, não zero. Um objeto de feature com valor NULL mantém fonte/datas; ausência integral pode ser representada com todas as colunas NULL, sem inventar data de divulgação. Valor presente sem fonte/referência/disponibilidade é inválido. Status pendente/incompatível e ruptura bloqueiam o candidato; potência, consumo e demanda não recebem exceções por nome.

## Tempo e uso estatístico

Uma feature divulgada depois da origem é recusada mesmo com referência antiga e mesmo que permita imputação. Transformações e categorias são ajustadas somente nos exemplos de treino de cada fold. Ausência genuína no treino só pode usar média/codificação aprendida no treino mediante autorização; coluna inteiramente ausente não recebe valor arbitrário. Falta de qualquer covariável futura necessária, inclusive NULL, bloqueia o candidato enriquecido em vez de projetar a média ou carregar o último valor.

Features ligadas ao ano y podem conter covariáveis defasadas: declarar a referência real, não trocar sua data para y. Cenários futuros precisam estar disponíveis no corte e possuir `cenario_id`; rótulo de cenário não libera divulgação posterior ao corte. No backtest os alvos futuros observados nunca entram nos lags nem nos baselines. Divulgação conhecida tardia do alvo bloqueia o fold; divulgação desconhecida permite somente diagnóstico retrospectivo explicitamente marcado.

Features de cenário podem ser fornecidas como linhas wide futuras: o leitor associa por série e cria apenas placeholders de alvo NULL identificados como `features_only`, sem observação histórica inventada. O maior ano de outra distribuidora não corta cenários de uma série mais curta. Nenhuma série se torna elegível só por receber features: persistem cobertura, estado, comparabilidade e segmento final do alvo.

A comparação seleciona candidatos nas mesmas origens de um passo, reserva a última origem para auditoria e mantém métricas por horizonte. Agregados entre modelos com coberturas diferentes são descritivos, não rankings pareados. Quatro observações anuais não validam modelos enriquecidos nem cenários 2026–2030.

## Granularidade municipal futura

A ingestão continua em **DIST × ano**. Arquivo municipal não é aceito como se fosse DIST. `territorial_mapping` opcional, contrato `municipios-dist-1`, permite pré-validar chaves ANO + município IBGE + DIST, pesos, fonte, população do peso e evidência de rateio. Município multi-DIST não pode ter peso 1 repetido: os pesos para a mesma população/ano somam 1 e exigem evidência. Essa pré-validação não certifica geografia nem aplica os pesos às features/alvos. Densidades e médias não devem ser somadas ou rateadas como estoques. Adaptador territorial de ingestão/rateio continua pendente de contrato e evidências do fornecedor.

## Entrega necessária do Claude

Fornecer bundle imutável, registro/catálogo adicional se necessário, dicionário de unidades e populações, fontes por variável, competência, disponibilidade de cada versão, provas de comparabilidade e rupturas; indicar explicitamente quais valores futuros são cenários. Para rateio futuro, entregar matriz municipal com pesos por população e prova de cobertura/overlap. Não usar contagens de equipamentos e instalações como populações independentes nem somar recortes sobrepostos. Os testes sintéticos de chegada estão exclusivamente em `tests/test_enriched_integration.py`.

Executar em diretório novo:

```sh
python -m motor_universal --panel /caminho/bundle --registry /caminho/objetivos.json --base-year 2025 --final-year 2030 --as-of 2026-10-26 --output /tmp/experimento-enriquecido-novo
```

A aceitação técnica não é aprovação de fontes, validação causal, homologação estatística ou autorização para publicar previsões. Necessidade de expansão permanece NULL: não é identificável apenas pela diferença de estoques.
