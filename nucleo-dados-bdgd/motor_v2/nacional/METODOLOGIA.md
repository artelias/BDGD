# Motor V2 — execução nacional experimental: metodologia

Todas as saídas desta execução são **experimentais e internas**. Nenhuma foi escrita em `web/`, `output-historico/`,
`output-publicavel/` ou `motor_cenarios/`, e nenhuma previsão foi publicada no dashboard. Nenhum modelo foi homologado.

## Dados

- **Somente publicações ordinárias.** A fonte é o item que o contrato nacional
  (`output-historico/contrato-integracao/serie_fisica_nacional.csv`) seleciona para cada DIST e competência 2022–2025.
  - A célula precisa ter `estado = observado`. Células bloqueadas, pendentes ou ausentes viram falha registrada do ano e nunca são lidas.
  - Nenhuma base extraordinária entra no treino nem nas projeções.
  - Cada lote verifica que todos os itens lidos são ordinários; um item não ordinário bloquearia a execução.
- **Os 12 ZIPs do contrato sem Parquet** foram convertidos localmente (`motor_v2/convert_zips.py`), sem download, numa raiz separada da árvore ordinária.
  - Classificação feita pela própria `BASE` de cada item e pela comparação das contagens por entidade com o item ordinário da competência que a `BASE` declara.
  - Só `competencia_confirmada` poderia entrar no treino. Nenhum dos 12 se enquadrou; todos ficam em quarentena, com o motivo registrado.
- **Códigos municipais.** A referência é a tabela oficial do IBGE (extratos SIDRA já em disco, com código e nome).
  - Um código fora da tabela não é unidade territorial: fica no total da empresa, como resíduo.
  - Um par (DIST, ano) com mais de 2% dos clientes fora da tabela entra em quarentena.
  - O padrão `'0' + 6 dígitos` gera uma ponte de recodificação **proposta**, com evidência auditável: prefixo único, UF coerente, presença nos anos vizinhos, concordância por CONJ e razão de clientes.
  - A ponte nunca é homologada automaticamente; o par (DIST, ano) segue em quarentena até haver decisão humana.
- **`recent_connection_share` está desligada por padrão.** `DAT_CON` também muda com troca de titularidade e seu padrão varia entre publicações.

## Nível A — territorial (Parquet → município ou conjunto)

| Ativo | Regra | Unidade territorial |
|---|---|---|
| UCBT quantidade | identidade UC-v3 (COD_ID+PN_CON), ativas | município (UCBT.MUN) |
| Transformadores TUC 565, quantidade | EQ → UN com vínculo bijetivo | município (UN.MUN) |
| Transformadores TUC 565, kVA | UNTRMT kVA; UNTRAT MVA×1000; vínculo ≥ 98% e sem potência inválida | município |
| Rede MT km | SSDMT.COMP / 1000 | conjunto (SSDMT.CONJ) |
| Rede BT km | SSDBT.COMP / 1000 | conjunto (SSDBT.CONJ) |

- **Comparação com o contrato.** Todo total extraído é comparado com a célula do contrato do mesmo conceito, e a diferença é registrada.
- **Painel.** Cada linha é (DIST, ano t, unidade), com features em t−1. Barreiras de cobertura (≥ 0,98) e de continuidade de conjuntos (≥ 0,95, só para redes), mais as quarentenas.
- **Escopos de treino.** São tirados do painel **nacional**, não do lote:
  - `individual`: só a própria DIST.
  - `grupo_economico`: empresas do mesmo controlador em 31/12/2025 (`etl/bdgd2025/config/grupos_2025.json`); controle não confirmado significa sem pool.
  - `comparaveis`: a própria DIST mais as 4 mais próximas no perfil padronizado (log do estoque total, log do número de unidades e, quando houver, participação urbana), medido nas linhas de treino.
  - Não há pool global indiscriminado; o lote 1 mostrou que misturar empresas heterogêneas piora o desempenho.
- **Validação.**
  - Origens 2023 e 2024, horizonte de 1 ano.
  - Três dobras territoriais por origem, com a unidade testada fora de todo treino.
  - Seleção de features e hiperparâmetros numa origem interna, dentro de cada dobra.
  - O modo point-in-time não tem origem elegível, porque as versões disponíveis na origem histórica não foram comprovadas.
- **Candidatos.** Baselines: persistência, deriva e CAGR. Modelos de ML: OLS, Ridge, Elastic Net, Poisson (só contagens), Random Forest e HistGradientBoosting.

## Nível B — distribuidora (todos os 25 conceitos do contrato nacional)

- **Série.** Valores do contrato (regras MCPSE/TUC do ETL existente). Uma célula é utilizável se `observado` ou `zero_verificado`, tem intervalo anual compatível e pode ser somada. Uma transição é comparável quando não há ruptura.
- **Features em t−1.** Log do estoque, log de consumidores, log de km de rede MT e o crescimento anterior comparável.
- **Alvo.** Crescimento em log1p.
- **Escopos.** `grupo_economico` e `comparaveis` (a DIST mais as 9 mais próximas no mesmo conceito). ML individual é impossível, pois cada série tem no máximo 2 linhas, e isso é registrado.
- **Validação.** Origens 2023 e 2024, com seleção interna dentro do pool.

## Política de escolha (`motor_v2/nacional/selecao.py`)

- **Score robusto** = média + desvio-padrão do MAE por origem, sobre as mesmas chaves de teste da persistência. Com duas origens, esse score é igual ao maior MAE por origem.
- **`melhor_modelo_experimental`**:
  - É escolhido o ML que for ≥ 5% melhor que o **melhor baseline** no score robusto **e** não pior em nenhuma origem.
  - Se nenhum ML se qualificar, é escolhida a tendência (deriva ou CAGR) que for ≥ 5% melhor que a persistência e não pior em nenhuma origem, desde que use o fallback de persistência em menos da metade das linhas.
  - Caso contrário, fica vazio, com o motivo.
- **`modelo_fallback`**: o melhor baseline medido; persistência por política quando nada foi medido.
- **`modelo_homologado`**: sempre vazio nesta execução, porque há 2 origens independentes e são exigidas 3.
- **`persistencia_superior_empiricamente`**: verdadeiro só quando a persistência tem o menor score medido. Uma persistência que entra por política nunca é contada como vitória empírica.

## Projeções 2026–2030 (`motor_v2/nacional/cenarios.py`)

- **Âncora.** A última competência com total físico válido: 2025 quando existe; senão, a última confiável, com o horizonte real registrado.
- **Moderado.** A trajetória do modelo de projeção:
  - persistência: y(T+h) = y(T);
  - deriva: y(T+h) = y(T) + h·inclinação;
  - CAGR: y(T+h) = y(T)·g^h;
  - ML: y(T+h) = expm1(log1p y(T) + h·d), onde d é a variação de um passo do modelo, mantida constante. Não existem covariáveis futuras e nenhuma foi inventada.
- **Conservador e agressivo.** A trajetória moderada, com o crescimento anual médio (em log1p) deslocado para o menor ou o maior crescimento anual observado nas transições comparáveis 2022–2025 da própria série, quando este for mais extremo. A ordem conservador ≤ moderado ≤ agressivo vale por construção.
  - **Atenção à amplitude:** um único ano atípico (por exemplo, regularização cadastral) sustentado por 5 anos produz cenários largos.
  - Isto é uma hipótese matemática, não um intervalo de confiança nem uma premissa oficial.
- **Contrato físico e reconciliação (nível A).**
  - Unidades territoriais da coorte mais o resíduo `NAO_TERRITORIALIZADO` somam exatamente o total da empresa.
  - Nas contagens, o total inteiro é o arredondamento half-up, e as unidades recebem inteiros por maior resto (Hamilton).
  - km e kVA mantêm unidade e decimais.
- **Totais nacionais.** Somam apenas séries **completas**: projeção gerada, âncora 2025, 5 anos × 3 cenários. Toda série excluída é listada com o motivo (`SERIES_EXCLUIDAS_DOS_TOTAIS.csv`).

## Execução

- **Lotes.** De até 16 DIST, com DuckDB limitado a 512 MB e um worker pesado de cada vez.
- **Controles.** Guarda de RAM, checkpoints por ano e por candidato com SHA-256, retomada idempotente, uma nova tentativa para DIST que falhe e falhas contadas por DIST, ativo e ano. `completed_with_errors` nunca é tratado como sucesso.
- **Processos.** Todos são destacados da sessão (`motor_v2/detach.py`) e encadeados por `motor_v2/nacional/pipeline.py`: extração → preparação (painel, IBGE, quarentena) → comparativos → projeção → consolidação.
