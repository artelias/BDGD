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
- **Elegibilidade: uma única política para os dois níveis** (`motor_v2/nacional/elegibilidade.py`, desde a auditoria final).
  - **Estoque** observado numa data-base é elegível quando o `estado` é `observado` ou `zero_verificado`, a `dataBase` é 31/12 da competência e a célula pode ser somada (`nao_somar_em_agregados` falso).
  - **Transição** t−1 → t (crescimento, alvo de treino, envelope dos cenários) é elegível quando os dois estoques são elegíveis, as datas-base são 31/12 consecutivos e o contrato não registra ruptura em t.
  - `INTERVALO_NAO_ANUAL` (`BASE.DAT_INC` em 01/12 com `DAT_FNL` correto em 31/12) é **ressalva, não exclusão**. `DAT_INC` delimita o período dos campos de fluxo (energia); o inventário físico é a fotografia em `DAT_FNL`.
    - Verificação empírica (25 conceitos, mediana ± 5 MAD com piso 0,02): 7,7% das 196 transições com ressalva são atípicas, contra 8,1% das 6.132 demais.
    - 12 das 15 atípicas são da Amazonas Energia 2022 → 2023, um degrau de nível da publicação 2022 que a Equatorial GO 2022, com a mesma BASE de 31 dias, não mostra. Sem ela, 1,7%.
    - A primeira execução (d4982e8) excluía esses estoques no nível B; a mudança afetou as séries listadas em `REVISAO_ELEGIBILIDADE_B.json`.
  - **Sucessão societária:** uma transição também não é elegível quando a DIST é destino de uma incorporação oficial (`eventos_sucessao.csv`) efetivada entre as duas datas-base.
    - O contrato fica no perímetro da publicação original e não marca a ruptura.
    - Caso da Energisa PB 2022 → 2023, que absorve a Energisa Borborema (`EPB_EBO_2023`): o salto é mudança de perímetro, não crescimento. O estoque segue elegível.
    - No nível A, as unidades da Borborema já ficam fora pela ponte de perímetro, e a série física da empresa ganha a quebra.
  - O contrato nacional não é alterado. A homologação pendente da fase 4 (produtos públicos) não é decidida aqui.
- **Códigos municipais.** A referência é a tabela oficial do IBGE (extratos SIDRA já em disco, com código e nome).
  - Um código fora da tabela não é unidade territorial: fica no total da empresa, como resíduo.
  - Um par (DIST, ano) com mais de 2% dos clientes fora da tabela entra em quarentena.
  - O padrão `'0' + 6 dígitos` gera uma ponte de recodificação **proposta**, com evidência auditável: prefixo único, UF coerente, presença nos anos vizinhos, concordância por CONJ e razão de clientes.
  - A ponte nunca é homologada automaticamente.
  - **Celesc 2023 (`MUN_RECODE_5697_2023`):** aplicada em 30/10/2026, por autorização do responsável, **somente na camada derivada** (`nacional/painel`), por `motor_v2/nacional/pontes.py`. Status: `APLICADA_EXPERIMENTAL_NAO_HOMOLOGADA`.
    - Verificações: mapeamento unívoco, sem colisão, alvos IBGE válidos, totais e demais colunas idênticos, só códigos mapeados alterados e continuidade com 2022 e 2024. Evidência cruzada: os 275 destinos aparecem em `UN.MUN` dos transformadores da mesma publicação.
    - O arquivo original fica preservado byte a byte; a extração e o contrato não são tocados.
    - Só a Celesc e os comparativos dependentes dela foram reexecutados (`revisao_a.py`).
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
- **Conservador e agressivo.** A trajetória moderada, com o crescimento anual médio (em log1p) deslocado para o menor ou o maior crescimento anual observado nas transições da própria série que entram no envelope. A ordem conservador ≤ moderado ≤ agressivo vale por construção.
  - **Triagem v2 do envelope** (`cenarios.py`). Uma variação extrema nunca é tratada como erro só por divergir do corte nacional:
    1. Evidência documentada por registro (`auditoria/fase4/RANKING_ANOMALIAS_TEMPORAIS.csv`, persistência de `COD_ID`):
       - `alteracao_cadastral`, `alteracao_classificacao` e `anomalia_fonte` saem do envelope;
       - `variacao_real_plausivel` fica, qualquer que seja o tamanho (por exemplo, geração distribuída).
    2. Sem evidência, a referência é o mesmo objeto, no mesmo ano e no mesmo **porte** (tercil do estoque em t−1): mediana ± 5 MAD (piso de 0,02 em log1p).
    3. Salto atípico, classificado pelo ano seguinte:
       - `persistente` (mudança estrutural) fica;
       - `reversao` (oscilação cadastral) sai;
       - `degrau_isolado` (mudança de nível já embutida na âncora; o ritmo não é sustentado por 5 anos) sai;
       - `sem_ano_seguinte` (não verificável) sai do envelope central e entra na variante de sensibilidade.
  - A sensibilidade às variantes (sem triagem, MAD nacional v1, v2, v2 com não verificáveis, K = 3 e K = 8, v2 sem evidência) está em `AUDITORIA_CENARIOS_*`.
  - Isto é uma hipótese matemática condicional, não um intervalo de confiança nem uma premissa oficial. A trajetória moderada não muda.
- **Contrato físico e reconciliação (nível A).**
  - Unidades territoriais da coorte mais o resíduo `NAO_TERRITORIALIZADO` somam exatamente o total da empresa.
  - Nas contagens, o total inteiro é o arredondamento half-up, e as unidades recebem inteiros por maior resto (Hamilton).
  - km e kVA mantêm unidade e decimais.
- **Totais nacionais.** Somam apenas séries **completas**: projeção gerada, âncora 2025, 5 anos × 3 cenários. Toda série excluída é listada com o motivo (`SERIES_EXCLUIDAS_DOS_TOTAIS.csv`).
  - Cada total traz `status_total`. É `COMPLETO` só quando toda DIST com estoque 2025 elegível do objeto está dentro dele; caso contrário é `PARCIAL`, com a cobertura do estoque 2025 observado e as DIST de fora.
  - Uma soma parcial nunca é apresentada como total nacional.
- **Potência.** Matriz separada (`motor_v2/nacional/potencia.py`, `MATRIZ_POTENCIAS.csv`): aparente (kVA), ativa (kW) e reativa (kVAr) nunca são convertidas entre si.
  - TUC 565: em uso experimental no nível A.
  - TUC 570: liberação experimental proposta.
  - TUC 575: não aplicável (sem campo de potência).
  - Reguladores: bloqueados (semântica não homogênea).

## Execução

- **Lotes.** De até 16 DIST, com DuckDB limitado a 512 MB e um worker pesado de cada vez.
- **Controles.** Guarda de RAM, checkpoints por ano e por candidato com SHA-256, retomada idempotente, uma nova tentativa para DIST que falhe e falhas contadas por DIST, ativo e ano. `completed_with_errors` nunca é tratado como sucesso.
- **Processos.** Todos são destacados da sessão (`motor_v2/detach.py`) e encadeados por `motor_v2/nacional/pipeline.py`: extração → preparação (painel, IBGE, quarentena) → comparativos → projeção → consolidação.
