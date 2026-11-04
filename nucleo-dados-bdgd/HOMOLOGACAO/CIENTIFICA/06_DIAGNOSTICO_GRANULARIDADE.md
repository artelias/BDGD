# 06 — Diagnóstico de viabilidade: Motor V2 com granularidade 2022–2025

**Diretriz de 04/11/2026:**
- só as competências BDGD validadas de 2022 a 2025;
- nenhuma competência anterior a 2022 no treinamento ou na homologação;
- prioridade para o horizonte de 1 ano, com os horizontes maiores como experimentais;
- a RC não muda;
- nenhum modelo novo é publicado sem comparação e aprovação.

**Este documento é só diagnóstico. Nada foi treinado.** As medições usam:
- os agregados territoriais já extraídos pelo Motor V2 (`motor_v2/nacional/painel`, com checkpoints e hashes);
- o contrato nacional (rupturas), os eventos de sucessão e a ponte municipal pendente;
- os **metadados** dos Parquets originais (rodapé: linhas, colunas, nulos), sem ler os dados.

Três medições exploratórias usaram só a transição de seleção (2023 → 2024). **A transição 2024 → 2025, reservada à avaliação final, não foi usada em nenhuma escolha.**

Script: `granularidade/diagnosticar.py`. Saídas: `granularidade/06a_UNIDADES_POR_ANO.csv`, `06b_TRANSICOES_UTILIZAVEIS.csv`, `06c_VARIAVEIS_COBERTURA.csv` e `06d_RESUMO.json`.

## Conclusão em uma frase

A granularidade **aumenta a informação transversal** (de dezenas para centenas de observações efetivas por transição) e permite modelar **onde** o crescimento se concentra. Ela **não cria origens temporais**: com 2022–2025 continuam existindo 3 transições e 1 avaliação final independente (2024 → 2025, horizonte de 1 ano). O melhor resultado possível com esta base é "validado retrospectivamente, com restrições" no horizonte de 1 ano. **Homologação plena, ou horizontes maiores que 1 ano, não são atingíveis** com a evidência temporal disponível.

## 1. Unidades territoriais comparáveis por ano

Unidades com estoque positivo no agregado da competência selecionada no contrato.

| Ativo (painel) | Nível | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| UCBT (clientes) | DIST | 97 | 93 | 97 | 98 |
| | município | 5.231 | 6.166 | 6.161 | 6.232 |
| | conjunto | 2.822 | 3.112 | 3.134 | 3.152 |
| | circuito MT (CTMT) | 22.631 | 27.984 | 23.517 | 23.940 |
| Transformadores de distribuição (quantidade e kVA) | DIST | 97 | 93 | 97 | 99 |
| | município (via UN.MUN, vínculo 1:1 EQ→UN) | 5.500 | 6.306 | 6.299 | 6.388 |
| | conjunto | 2.817 | 3.105 | 3.132 | 3.150 |
| Rede BT (km) | DIST / conjunto | 97 / 2.746 | 93 / 3.106 | 97 / 3.126 | 99 / 3.126 |
| Rede MT (km) | DIST / conjunto | 97 / 2.819 | 93 / 3.113 | 97 / 3.131 | 99 / 3.132 |

Observações:
- O total de 2022 é menor porque 5 DIST não têm 2022 extraído (`2381`, `4950`, `5343`, `5372` e `7467`, com ZIP sem conversão ou publicação ausente) e porque o DIST 40 tem 80 municípios em 2022 contra 167 em 2023.
- O DIST 7019 tem 109 municípios em 2023 contra 68 em 2022 e 66 em 2024, um indício de código municipal anômalo em 2023.
- A Celesc (5697) em 2023 tem a recodificação municipal com ponte **proposta e não homologada**, e fica de fora no nível municipal.
- A rede BT/MT não tem município no segmento. Só conjunto e circuito são campos do próprio segmento; não há inferência espacial.

## 2. Transições temporais efetivamente utilizáveis

Regras aplicadas **antes** de qualquer variação:
- fica de fora a DIST-transição com ruptura do conceito no contrato, com evento de sucessão (origem e destino) ou com recodificação municipal pendente;
- no nível granular, a chave precisa ser **estável**: pelo menos 95% do estoque em unidades presentes nos dois anos, nos dois sentidos. Senão a DIST-transição sai desse nível. Não há reatribuição sem ponte homologada;
- unidades novas (0 → n) ou extintas não entram como crescimento, porque são margem extensiva.

| Ativo | Nível | DIST-transições com chave estável (22→23 / 23→24 / 24→25) | Unidades utilizáveis | ICC intra-DIST do crescimento | **n efetivo por transição** |
|---|---|---|---|---|---|
| UCBT | DIST | 86 / 90 / 94 | 86 / 90 / 94 | — | 86 / 90 / 94 |
| | município | 84 / 89 / 94 | 4.499 / 5.605 / 5.724 | 0,55 / 0,28 / 0,41 | **139 / 279 / 206** |
| | conjunto | 83 / **74** / 91 | 2.526 / 1.418 / 2.789 | 0,79 / 0,31 / 0,28 | **47 / 87 / 142** |
| | circuito | 71 / 77 / 77 | 15.914 / 20.170 / 20.484 | 0,02 / 0,01 / 0,00 | 3.370 / 6.678 / 12.307 (dominado por reconfiguração, ver nota) |
| Trafos (quantidade) | município | 80 / 87 / 96 | 4.050 / 5.276 / 6.285 | 0,24 / 0,15 / 0,09 | **280 / 484 / 881** |
| | conjunto | 79 / 73 / 93 | 2.296 / 1.322 / 3.051 | 0,22 / 0,05 / 0,07 | **144 / 386 / 509** |
| Trafos (kVA) | município | 80 / 87 / 96 | 4.050 / 5.276 / 6.285 | 0,52 / 0,25 / 0,07 | **137 / 300 / 1.041** |
| Rede BT | conjunto | 81 / 74 / 93 | 2.343 / 1.418 / 2.921 | 0,07 / 0,07 / 0,05 | **441 / 306 / 696** |
| Rede MT | conjunto | 83 / 74 / 93 | 2.526 / 1.418 / 2.922 | ≈0 (−0,00 a 0,04) | **2.526 / 499 / 2.922** |

Leitura:
- **Milhões de linhas não são milhões de observações.** Os cerca de 90 milhões de UCBT por ano viram cerca de 5.600 municípios. Como o crescimento dos municípios de uma mesma distribuidora é correlacionado (ICC de 0,28 a 0,55 em UCBT), essas unidades equivalem a **140–280 observações independentes por transição**.
  - n efetivo = unidades / efeito de desenho, com efeito = 1 + (m − 1)·ICC, limitado a ≥ 1.
  - Os testes e os intervalos têm de reamostrar **distribuidoras ou grupos econômicos**, nunca linhas.
- **Conjunto:** em 2023 → 2024, **17 distribuidoras renumeram os conjuntos** (continuidade do estoque < 95%: 26, 38, 40, 47, 63, 369, 371, 383, 385, 391, 404, 405, 2937, 4950, 6072, 6587, 6600). O nível conjunto perde 1/5 das DIST nessa transição, salvo com ponte por circuito homologada (`motor_v2/conj_bridge.py` tem a proposta, pendente de homologação).
- **Circuito (CTMT):**
  - 13 a 18 DIST por transição renumeram ou reconfiguram circuitos; em alguns casos a continuidade é 0%: 405 em 2023, 5707 em 2024, 5355 em 2025;
  - nas estáveis há 700–900 circuitos por transição com variação maior que 100%, e o ICC fica perto de zero;
  - a variação no circuito é dominada pela **reconfiguração da rede** (clientes transferidos entre alimentadores), não pela expansão;
  - **o circuito não serve como unidade-alvo de crescimento.** Serve no máximo como suporte de variáveis (carga por alimentador) quando a continuidade é ≥ 95%.
- **Distribuição do crescimento:**
  - o crescimento das distribuidoras vem das unidades já existentes; a margem extensiva (municípios ou conjuntos novos) tem mediana 0;
  - ele é **concentrado**: 10% dos municípios concentram 66–70% das novas UCs e cerca de 50% dos novos transformadores, e 10% dos conjuntos concentram 75–84% da rede BT nova;
  - esse é o espaço de ganho do modelo granular: prever **onde** cresce, e somar.

## 3. Variáveis disponíveis e cobertura

Os registros originais estão nas competências selecionadas no contrato: 97, 94, 97 e 99 DIST com Parquet em 2022, 2023, 2024 e 2025.

| Entidade | 2022 | 2023 | 2024 | 2025 | Variáveis verificadas (presentes em 100% das linhas em todos os anos) |
|---|---|---|---|---|---|
| UCBT (consumidores BT) | 89,1 mi | 100,8 mi | 102,6 mi | 104,4 mi | MUN, CONJ, CTMT, ARE_LOC, DAT_CON, CAR_INST, ENE_01…ENE_12, CEG_GD, SIT_ATIV, FAS_CON, CLAS_SUB |
| UCMT | 0,29 mi | 0,32 mi | 0,35 mi | 0,35 mi | MUN, CONJ, CTMT, ARE_LOC, DAT_CON, CAR_INST, CEG_GD (o nome `ENE_P_01` não existe: a energia de MT usa outros campos) |
| UGBT (geração distribuída BT) | 1,4 mi | 2,3 mi | 3,2 mi | 3,9 mi | MUN, CONJ, CTMT, POT_INST, DAT_CON, CEG_GD |
| UNTRMT / EQTRMT (transformadores MT) | 4,8 / 4,9 mi | 5,9 / 6,0 mi | 6,1 / 6,1 mi | 6,2 / 6,3 mi | UN: MUN, CONJ, CTMT, SUB, POT_NOM, DAT_CON, ARE_LOC, SIT_ATIV; EQ: UNI_TR_MT, POT_NOM (código de domínio), TUC |
| SSDMT / SSDBT (segmentos de rede) | 33,7 / 32,8 mi | 40,2 / 39,6 mi | 41,0 / 40,0 mi | 42,7 / 41,1 mi | CONJ, CTMT, SUB, COMP, ARE_LOC (BT: UNI_TR_MT) |
| RAMLIG (ramais) | 71,6 mi | 87,5 mi | 83,0 mi | 84,5 mi | CONJ, CTMT, COMP |
| PONNOT (postes e estruturas) | 53,2 mi | 60,0 mi | 60,6 mi | 62,2 mi | CONJ, MUN, TIP_PN (não tem CTMT) |
| CTMT (circuitos MT) | 23,4 mil | 26,1 mil | 26,7 mil | 27,9 mil | COD_ID, SUB, ENE_01…12 (energia injetada), PERD_*, PNTMT_*, TEN_NOM |
| SUB / CONJ (cadastros) | 6.825 / 2.815 | 7.680 / 3.107 | 7.698 / 3.126 | 7.792 / 3.147 | COD_ID, NOME, Shape_Area (área do conjunto: densidade) |

São cerca de **350 milhões de registros por competência**, ou 1,4 bilhão em 2022–2025.

**Ressalvas da cobertura:**
- **Nulos físicos não medem a ausência semântica.** A fração nula do rodapé fica perto de 0 em todas as colunas (UCBT.CEG_GD: 3–4%), mas na BDGD a ausência costuma vir como vazio, `0` ou código inválido. Isso só se mede nos valores.
- **Códigos municipais:** a auditoria existente (`motor_v2/nacional/auditoria/CODIGOS_MUNICIPAIS_POR_DIST_ANO.csv`) acha códigos fora do IBGE em ≤ 0,0003% dos clientes em 2022, 2024 e 2025. A exceção é **a Celesc em 2023: 100% dos códigos fora do IBGE**, 3,8% dos clientes nacionais daquele ano, com ponte proposta e não homologada.
- **Potência:**
  - `UNTRMT.POT_NOM` é potência em kVA e entra no painel de trafos;
  - `EQTRMT.POT_NOM` é código de domínio e não é usado;
  - a métrica kVA continua **experimental**, sem homologação do contrato; pode servir como variável explicativa, sinalizada, nunca como alvo homologado.
- **Variáveis derivadas já disponíveis nos painéis**, sem extração nova:
  - por município × conjunto × circuito × área: clientes ativos, energia anual (ENE_01…12), conexões nos 12 meses antes da data-base (`DAT_CON`, informação conhecida na origem);
  - transformadores e kVA por município × conjunto;
  - km BT/MT por conjunto.
- **Variáveis externas por município** (IBGE já em disco, com data de divulgação): população 2010/2021/2022 e PIB municipal 2020–2023.
- **Variáveis que dependem de extração nova:**
  - GD por município (UGBT: POT_INST, DAT_CON);
  - postes por município e conjunto (PONNOT);
  - carga instalada e classe por município (UCBT: CAR_INST, CLAS_SUB);
  - km por circuito (SSDMT.CTMT), só como suporte.

## 4. Granularidade adequada por família de ativos

| Família | Unidade-alvo recomendada | Por quê | Não usar |
|---|---|---|---|
| Clientes (UCBT, consumidores; UCMT/UCAT agregados) | **Município × ano**, com conjunto como sensibilidade | código IBGE estável; variáveis externas municipais alinhadas; conexões recentes por município | circuito (reconfiguração) |
| Transformadores de distribuição (quantidade, kVA) | **Município × ano** (UN.MUN com vínculo 1:1) e conjunto | ICC baixo (0,07–0,24), maior n efetivo; o kVA é métrica experimental (não homologada) | equipamento sem vínculo 1:1 |
| Redes BT/MT (km) | **Conjunto × ano** | o segmento só traz conjunto e circuito; o conjunto exclui as 17 DIST renumeradas em 2024, salvo com ponte homologada | município (exigiria inferência espacial) |
| Geração distribuída (UGBT) | Município × ano (precisa de extração) | tem MUN, POT_INST e DAT_CON; é o maior crescimento relativo | — |
| Postes e estruturas (PONNOT) | Município ou conjunto × ano (precisa de extração) | tem CONJ e MUN | — |
| Proteção, manobra e regulação (chaves, religadores, seccionalizadores, reguladores, bancos) | **DIST × ano** | contagens pequenas por unidade, muitos zeros e reclassificações no contrato (12–13 DIST com `alteracao_classificacao`) | granular |
| Subestações, alimentadores, circuitos AT, trafos de força, barramentos, conjuntos, torres | **DIST × ano** | o próprio ativo é a unidade; há poucas por DIST | granular |
| Alimentador/circuito | Só como suporte de variáveis, quando a continuidade é ≥ 95% | reconfiguração frequente | unidade-alvo |

## 5. Estratégia de treinamento e validação sem vazamento

1. **Etapas temporais**, as mesmas do protocolo 01:
   - **seleção:** treino com as transições até 2023 e validação no alvo 2024;
   - **avaliação final:** treino até 2024 e alvo 2025, intocado;
   - **diagnóstico:** h=2 (2023 → 2025), só registrado.

   A otimização, a seleção de variáveis e os hiperparâmetros usam só a etapa de seleção.
2. **Sem vazamento territorial ou de empresa:**
   - **variáveis:** toda variável é medida em t−1 ou está disponível na origem (as externas do IBGE respeitam a data de divulgação). Nenhuma variável de vizinhança é calculada com o ano-alvo;
   - **validação cruzada interna:** dentro do treino, a importância por permutação e a seleção de subconjuntos usam validação cruzada **agrupada por grupo econômico**. As unidades de uma empresa nunca ficam dos dois lados;
   - **efeitos por distribuidora:** os efeitos específicos (modelo hierárquico) são estimados só com as transições de treino.
3. **Modelos a comparar**, nos mesmos pontos e agregados à DIST para comparar com os modelos atuais:
   - **painel global por unidade:** Ridge e HistGradientBoosting com os parâmetros globais;
   - **hierárquico com encolhimento:** inclinações globais mais intercepto por distribuidora, encolhido pela variância entre distribuidoras, por Bayes empírico em numpy, **sem dependência nova** (não há statsmodels no ambiente);
   - **de baixo para cima:** soma das previsões das unidades até a DIST;
   - **referências:** os modelos DIST já executados (produto e otimização) e os baselines (persistência, deriva, CAGR por unidade e por DIST).
4. **Métricas**, iguais às da otimização:
   - R² do crescimento fora da amostra, na DIST e na unidade;
   - WAPE, MAE, viés e estabilidade |WAPE_F − WAPE_S|;
   - erro físico depois do arredondamento;
   - erro por horizonte.

   O R² do nível não é evidência.
5. **Inferência:** o bootstrap reamostra grupos econômicos (2.000 réplicas), nunca linhas.
6. **Critérios pré-definidos**, registrados antes da execução:
   - um modelo granular só **melhora** se, na avaliação final agregada à DIST, tiver WAPE ≤ 0,95 × o melhor modelo DIST atual da métrica e não for pior que o melhor baseline;
   - o nível "validado retrospectivamente, com restrições" exige IC95% (bootstrap por grupo) da diferença contra o melhor baseline totalmente < 0;
   - horizontes ≥ 2: sempre experimentais.

## 6. Ganho esperado e custo

**Ganho a investigar.** Não é prometido.
- **Previsão de onde cresce:** com o crescimento concentrado em 10% das unidades, variáveis locais podem melhorar a variação por DIST, onde o R² do crescimento hoje é cerca de 0:
  - conexões nos últimos 12 meses por município;
  - crescimento populacional municipal;
  - densidade de UC por km de rede;
  - transformadores por UC.
- **Sinal disponível, só na transição de seleção 2023 → 2024:** a taxa de conexões recentes (`DAT_CON` nos 12 meses) correlaciona **0,30** com o crescimento seguinte das UCs por distribuidora (R² linear 0,09) e **0,14** por município (R² 0,02). Isso é uma pista, não um resultado validado.
- **Limite do ganho:** o ICC de 0,28–0,55 em UCBT mostra choques comuns fortes por distribuidora e ano. Esses choques não são previsíveis com 3 transições e limitam o ganho do agregado. Hoje o WAPE na DIST é de 0,6–4% (transformadores, redes, consumidores), perto da persistência, e o espaço de ganho em WAPE é pequeno.
- **Expectativa realista:** R² do crescimento por DIST levemente positivo e WAPE igual ou ligeiramente menor nas famílias de clientes, transformadores e GD. Nenhuma mudança no nível de homologação além do horizonte de 1 ano.

**Custo computacional** (4 núcleos, 8 GB de RAM, DuckDB 2.0 e pyarrow já instalados; nenhuma dependência nova):

| Etapa | Base | Estimativa |
|---|---|---|
| Diagnóstico (este) | rodapés de cerca de 4 mil Parquets e os painéis existentes | 29 s nos painéis e 128 a 355 s nos metadados (a segunda leitura usa o cache de disco) |
| Modelagem dos 5 ativos já extraídos (UCBT; trafos quantidade e kVA; redes BT e MT) | ≤ 6.400 unidades × 3 transições por ativo; ajustes em segundos | cerca de 1 a 2 h com busca limitada e cache (a otimização DIST com 1.504 ajustes levou 20 min) |
| Extração nova: UGBT (GD) por município, PONNOT (postes) por município e conjunto, variáveis de UCBT por município (energia, carga instalada) | DuckDB em fluxo, uma DIST por vez, só as colunas necessárias, memória < 2 GB | UCBT completo levou 2,5 h e os demais ativos 0,3 h na extração anterior (99 DIST × 4 anos). Por linhas (seção 3): na vazão observada na extração anterior (UCBT cerca de 44 mil linhas/s; demais ativos cerca de 380 mil linhas/s): UGBT (10,8 mi linhas em 4 anos) de 1 a 5 min; PONNOT (236 mi) de 10 min a 1,5 h; UNTRMT com campos novos (23 mi) de 1 a 10 min; releitura de UCBT para carga instalada e classe (397 mi) cerca de 2,5 h, **dispensável** se bastarem as variáveis do painel atual. Total de 15 min a 4,5 h, uma DIST por vez |
| Pontes de conjunto (17 DIST em 2024) | proposta existente em `conj_bridge.py` | precisa de homologação humana; sem ela, essas DIST-transições ficam fora do nível conjunto |

## Decisões necessárias antes de implementar

1. Aprovar as unidades-alvo da seção 4: município para clientes, trafos e GD; conjunto para redes; DIST para os demais.
2. Aprovar a extração nova (UGBT e PONNOT por município/conjunto; variáveis de UCBT) ou restringir aos 5 ativos já extraídos.
3. Decidir sobre as pontes pendentes:
   - recodificação municipal da Celesc 2023;
   - conjuntos de 17 DIST em 2024;
   - anomalia municipal do 7019 em 2023.

   Sem essa decisão, essas DIST-transições ficam fora dos níveis afetados.
4. Aprovar os critérios da seção 5.6 como pré-registro, antes da primeira execução.
