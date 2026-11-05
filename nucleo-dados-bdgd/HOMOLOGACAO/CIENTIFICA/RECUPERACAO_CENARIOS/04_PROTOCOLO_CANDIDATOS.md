# 04 — Protocolo de recuperação dos cenários ausentes (pré-registrado)

**Versão:** `recuperacao-1`.
**Branch:** `exp/recuperacao-cenarios-20261104`. Ela parte de `homologacao/cientifica-20261103@3748c95` e recebe por merge `exp/otimizacao-modelos-20261103@997c4d7`. É separada da RC 1.0 (`rc/1.0-20261101@dba5fdf`), que não é alterada.
**Estado de todo resultado:** EXPERIMENTAL. Não é homologação científica, não altera o produto publicado e não substitui nenhum Moderado.

Este protocolo é commitado **antes** de qualquer cálculo série a série com candidatos que não estão publicados. Os parâmetros estão também no código (`PROTOCOLO` em `recuperar.py`). Uma mudança depois de ver resultados gera a versão `recuperacao-2`, e os resultados da versão 1 ficam preservados.

## 0. O que já era conhecido antes de congelar

Calculado a partir do produto publicado, sem nenhum candidato novo:
- **Totais do produto.** 2.202 séries: 755 completas, 1.206 parciais e 241 sem previsão. Também os modelos e o WAPE de cada métrica.
- **Relatórios anteriores.** O relatório da otimização (1.343 séries completas no registro técnico; 14 de 104 melhoras) e o dossiê científico (`10_PARECER_CIENTIFICO_CONSOLIDADO.md`).
- **Coerência dos 2.495 extremos publicados**, medida série a série com a regra de ordem:
  - 673 ficam do lado oposto ao Moderado, ou o cruzam em algum ano;
  - 292 são iguais ao Moderado;
  - 61 diferem dele em menos de 0,05 p.p./ano.
- **As 241 séries sem previsão.** 236 têm histórico contíguo insuficiente (120 delas com 2023 `nao_homologado`). Outras 6 têm trajetória implausível.

Nenhum resultado série a série de modelo não publicado foi calculado antes deste commit.

## 1. Escopo e dados

- **Dados:** os mesmos do gerador público (`motor_cenarios/cenarios.py`):
  - contrato nacional `output-historico/contrato-integracao/serie_fisica_nacional.csv`;
  - variáveis internas e IBGE em `motor_cenarios/entrada/`.
  - Os SHA-256 são registrados no manifesto de saída.
  - **Só as competências BDGD de 2022 a 2025.** As variáveis externas do IBGE são as do produto, divulgadas até 15/12/2023.
  - Nenhuma extração nova.
- **Universo:** as 2.202 séries (DIST × conceito × métrica) das 27 métricas com série. As duas combinações bloqueadas (potência de reguladores e de transformadores de medida) não têm série e ficam de fora.
- **Métricas em kVA** (`trafo_dist/potencia_kva`, `trafo_forca/potencia_kva`): entram na auditoria com a marca `EXPERIMENTAL_KVA`. O dossiê científico as classifica como não homologáveis. As contagens são relatadas com e sem elas.
- **Granularidade:** distribuidora. Os modelos do piloto granular (conjunto × ano; `G-HIER` da rede BT e `G-RIDGE` de kVA) não projetam por DIST e ficam **congelados e sem uso** (`11_CANDIDATOS_CONFIRMATORIOS.md`).
- **Recursos:**
  - um processo, com `n_jobs=1`;
  - numpy, scipy e scikit-learn 1.8.0 de `D:/NUCLEO_BDGD_2025/.venv-motor`, as versões do gerador público;
  - nenhuma dependência nova.

## 2. Separação temporal e estado da evidência

| Etapa | Treino | Alvo | Uso |
|---|---|---|---|
| S | transições até 2023 | 2024, h=1 | única etapa usada em **escolhas novas** (φ, κ, calibração inicial) |
| F | transições até 2024 | 2025, h=1 | relatada e usada como guarda de tolerância; 2025 **já foi consultado** |
| H2 | transições até 2023 | 2025, h=2 | relatada como diagnóstico |
| PRODUTO | pontos S + F + H2 | — | WAPE agregado, o critério do gerador publicado |
| Projeção | transições até 2025 | 2026–2030 | trajetórias; não há alvo observado |

- **A competência 2025 já participou de várias escolhas:** do Moderado publicado, da otimização (etapa F) e do dossiê científico. Toda comparação que usa 2025 é **evidência histórica já consultada**, e o resultado é **exploratório**. Nenhuma melhora é declarada confirmada com base nela.
- **Os candidatos novos** (seção 7) e a regra série a série são congelados ao fim da execução, em `selecao_congelada.json` com o SHA-256 registrado. A confirmação fica para a primeira competência posterior a 2025 (origem 2025 → alvo 2026).
- **Os horizontes de 2 a 5 anos não têm homologação**, e nada aqui a supre.

## 3. Taxonomia das ausências (Gate A)

Cada série tem três posições: Conservador, Moderado e Agressivo. Cada posição ausente recebe **uma causa primária**, e as causas secundárias ficam em coluna própria.

### 3.1 Moderado ausente (série `SEM_PREVISAO`)

O segmento usado é o contíguo de observações positivas que termina em 2025, cortado em ruptura (`segmento` do gerador). Quando o segmento é curto, a causa é dada pelo **primeiro ano que o interrompe, contando de 2025 para trás**. A causa primária segue esta ordem:

| Código | Condição |
|---|---|
| **G** (ruptura ou problema cadastral) | o segmento é curto (< 3 anos) porque foi cortado por `ruptura_desde_ano_anterior`, ou por ano `nao_homologado` (`BLOQUEIO_COMPETENCIA`, `BASE_INCONSISTENTE`) |
| **F** (falta histórico comparável) | o segmento é curto por ano `ausente` (publicação não localizada, entidade vazia), `zero_verificado` ou `nao_aplicavel`, ou não há contrato para a série |
| **E** (fisicamente implausível) | a trajetória do Moderado na série tem razão 2030/2025 fora de [0,5; 3] (`TRAJETORIA_IMPLAUSIVEL_NA_SERIE`) |
| **J** (outra causa) | qualquer outro caso, com texto |

Nessas séries, os dois extremos recebem **H** (falta Moderado), e a causa do Moderado vai como secundária.

### 3.2 Extremo ausente com Moderado publicado

- **O modelo do extremo existe na métrica, mas não na série:** E, se foi removido por implausibilidade na série; F, se não há projeção na série.
- **A métrica não tem modelo para o extremo:** a série é avaliada com os **9 modelos originais** do gerador, reexecutados sem nenhuma mudança (seção 4.1). Define-se:
  - *elegíveis*: os modelos ≠ Moderado que o gerador marca como elegíveis, com plausibilidade da métrica e projeção não negativa;
  - *competitivos*: os elegíveis com WAPE_PRODUTO ≤ 1,25 × WAPE_PRODUTO do Moderado (`TOLERANCIA_ERRO`).

| Código | Condição |
|---|---|
| **A1** (não existe modelo alternativo elegível) | nenhum outro modelo elegível na métrica |
| **B** (erro excessivo) | há elegíveis, mas nenhum competitivo |
| **I** (elegível na DIST, rejeitado pelo critério agregado nacional) | algum competitivo é `COERENTE` na série (seção 6) |
| **E** | o melhor estado entre os competitivos é `IMPLAUSIVEL` |
| **C** (cruza o Moderado) | o melhor estado é `CRUZA` |
| **D** (coincide com o Moderado) | o melhor estado é `COINCIDE` |
| **A2** (sem alternativa do lado pedido) | todos os competitivos ficam `LADO_OPOSTO` |
| **F** | nenhum competitivo projeta a série |

O "melhor estado" segue a precedência COERENTE > IMPLAUSIVEL > CRUZA > COINCIDE > LADO_OPOSTO > SEM_PROJECAO.

### 3.3 Extremo publicado

Ele não é uma ausência. Mesmo assim, é auditado com a seção 6. Se falhar, recebe `PUBLICADO_REPROVADO`, com o estado como subcausa (C, D, E, A2). A série conta como completa no produto e **não** conta como completa defensável.

### 3.4 Agrupamento das causas

- **Seleção:** I.
- **Evidência de modelo:** A1, A2, B, C, D, E.
- **Dados:** F, G, e H pela causa do Moderado.

## 4. Inventário dos modelos existentes (insumo do Gate B)

### 4.1 Originais (O)

São as 9 configurações de `cenarios.py`, sem nenhuma alteração: persistência, deriva, tendência OLS, CAGR, Ridge, Ridge com externas, KNN, Random Forest e HGB.

- **Por que reexecutar:** o produto persiste só as 3 trajetórias escolhidas por métrica, e as das demais séries não existem em arquivo. A reexecução é justificada pela mudança de contrato (escolha por série).
- **Verificação obrigatória.** A execução aborta se falhar qualquer destas condições:
  - o modelo escolhido em cada posição é igual ao publicado;
  - o WAPE de cada modelo é igual ao publicado (|Δ| < 1e-9);
  - as trajetórias publicadas são reproduzidas dentro da tolerância do `--check`: no máximo 1 unidade em no máximo 0,5% das contagens; km e kVA com |Δ| ≤ 0,001.

### 4.2 Otimizados (X)

São as 4 configurações por métrica de `otimizar.py`: Ridge, KNN, RF e HGB, com as variáveis e os hiperparâmetros de `MODELOS_AVALIADOS.csv` (`997c4d7`).

- **Verificação:** a reexecução nos pontos da própria otimização precisa reproduzir `S_wape` e `F_wape` até 1e-6. Se não reproduzir, o candidato fica `SEM_EVIDENCIA` (defeito registrado).
- **Avaliação:** depois, cada um é avaliado nos **mesmos pontos do produto**, o que dá o WAPE_PRODUTO.

### 4.3 Demais candidatos

- **Hierárquicos do piloto (H):** `NAO_APLICAVEL_AO_PAINEL_DIST`, sem uso.
- **Regra condicional da otimização (B-HIST):** é uma regra, não um modelo (seção 5.3).

### 4.4 Classificação de cada candidato por métrica

| Classe | Condição |
|---|---|
| `SEM_EVIDENCIA_SUFICIENTE` | backtest incompleto nos pontos do produto, treino com < 15 pares ou reprodução falhou |
| `REJEITADO` | não é elegível, ou não é competitivo: tolerância de 1,25 no WAPE_PRODUTO e, para X e para os novos, também 1,25 × WAPE_F do Moderado, porque as variáveis e os hiperparâmetros foram escolhidos na etapa S |
| `VALIDO_PARA_MEDIA_NACIONAL` | competitivo, com CAGR agregado 2025→2030 a ≥ 0,05 p.p./ano do CAGR agregado do Moderado (o critério do produto) |
| `VALIDO_NA_DISTRIBUIDORA` | competitivo e `COERENTE` (seção 6) em ≥ 1 série; o número de séries por lado é registrado |
| `VALIDO_APENAS_RETROSPECTIVAMENTE` | competitivo, sem nenhuma das duas validades anteriores |

Um candidato pode ser válido para a média nacional e na distribuidora ao mesmo tempo, e as duas marcas são registradas.

## 5. Regra por série e precedência (Gates B e C)

- **O Moderado é sempre o publicado**, nunca substituído.
- **Sem Moderado publicado, não há extremo.**

Para cada série com Moderado e cada lado (Conservador ou Agressivo), a posição é preenchida pela **primeira** etapa que atender à seção 6:

| Ordem | Etapa | Categoria | Origem |
|---|---|---|---|
| P1 | o extremo publicado, mantido se aprovado | A (modelo) | produto |
| P2 | O ∪ X competitivos: o de **menor WAPE_PRODUTO**; no empate, a menor complexidade, depois o id | A (modelo independente) | existente |
| P3 | novos modelos de previsão N1 e N2 (seção 7), competitivos com a guarda F: o de menor WAPE_PRODUTO | A (modelo novo) | novo |
| P4 | B-HIST (seção 5.3) | B (condicional) | regra existente, sem treino |
| P5 | N6, elasticidade à carga (seção 7) | B (condicional estrutural) | novo |
| P6 | N5, quantil condicional calibrado (seção 7) | B (condicional) | novo |
| — | nenhuma etapa aprovada | `INDISPONIVEL`, com a causa | — |

- **Gate B (sem treino novo):** é o contrafactual P1 + P2 + P4. P1 + P2 também é relatado só com O.
- **Gate C:** P3, P5 e P6 só se aplicam às posições que continuam `INDISPONIVEL` depois de P1 e P2. O escopo está na seção 7.1.

### 5.3 B-HIST, a regra condicional da otimização, com guardas mais estritas

- **Taxa:** g = a menor (Conservador) ou a maior (Agressivo) transição comparável da própria série, ln(y_t/y_{t−1}), entre 2022→2023, 2023→2024 e 2024→2025. São comparáveis as transições observado → observado, com valores positivos e sem ruptura.
- **Exigências:**
  - pelo menos 2 transições comparáveis;
  - g dentro do **P05–P95** das transições comparáveis da métrica (todas as DIST; pelo menos 20 transições).
- **Trajetória:** y_2025 · exp(h·g), aprovada pela seção 6.
- **Rótulo:** "simulação condicional: a distribuidora repete a cada ano o menor (maior) crescimento anual comparável observado em 2022–2025". Não é previsão independente nem intervalo.

O P05–P95 substitui o P01–P99 da otimização. A cauda das transições concentra mudanças cadastrais não marcadas como ruptura, e uma premissa sem erro retrospectivo próprio precisa de limite mais estrito que um modelo com erro medido.

### 5.4 Moderado ausente com segmento de 2 anos

Não há recuperação automática. Conta-se quantas séries sem Moderado têm 2 anos contíguos comparáveis terminando em 2025, com o Moderado da métrica sendo um modelo de painel, que usa só y_2025 e as variáveis. Essas séries recebem `MODERADO_RECUPERAVEL_SOB_DECISAO_DE_CONTRATO`:
- nenhuma trajetória é gerada;
- não entram em nenhuma contagem de recuperação;
- a mudança do histórico mínimo é uma decisão do responsável.

## 6. Regras de qualidade por série (Gate D)

Valem para **todo** extremo: publicado, O, X, novo ou condicional. Notação:
- y25 é o valor observado de 2025;
- M_t é o Moderado contínuo reexecutado, e M̂_t o Moderado publicado;
- E_t é o extremo contínuo, e Ê_t o publicado (contagens arredondadas meio para cima, km e kVA com 3 decimais; para o extremo publicado, o valor do produto);
- s = −1 para o Conservador e +1 para o Agressivo;
- g_X = ln(X_2030/y25)/5.

| Código | Regra |
|---|---|
| Q1 | todos os E_t são finitos e ≥ 0 |
| Q2 | E_2030/y25 ∈ [0,5; 3] (`RAZAO_PLAUSIVEL` do produto) |
| Q3 | g_E dentro do P01–P99 das transições comparáveis da métrica (todas as DIST, 2022→2025) |
| Q4 | o salto 2025→2026, ln(E_2026/y25), dentro do mesmo P01–P99 (coerência entre 2025 observado e 2026 projetado) |
| Q5 | ordem contínua: s·(E_t − M_t) ≥ 0 nos 5 anos |
| Q6 | ordem publicada: s·(Ê_t − M̂_t) ≥ 0 nos 5 anos |
| Q7 | diferença material: s·(g_E − g_M) ≥ 0,05 p.p./ano (`DIFERENCA_MINIMA_PP`) |
| Q8 | só contagens: s·(E_2030 − M_2030) ≥ 1 e s·(Ê_2030 − M̂_2030) ≥ 1, o que impede diferença criada só pelo arredondamento |
| Q9 | publicação física: contagens inteiras e km/kVA contínuos (`metric_contract`) |

**Estado do candidato na série**, aplicado nesta ordem:
1. sem trajetória: `SEM_PROJECAO`;
2. s·(E_t − M_t) ≤ 0 em todos os anos: `LADO_OPOSTO` se algum ano for < 0, senão `COINCIDE`;
3. falha Q1–Q4: `IMPLAUSIVEL`;
4. falha Q5 ou Q6: `CRUZA`;
5. falha Q7 ou Q8: `COINCIDE`;
6. passa em tudo: `COERENTE`.

**Classes da série:**
- `COMPLETA_INDEPENDENTE`: os dois extremos são de categoria A (P1–P3);
- `COMPLETA_MISTA`: um extremo A e um B;
- `COMPLETA_CONDICIONAL`: os dois extremos B;
- `PARCIAL`;
- `SEM_PREVISAO`.

**Fora do alcance deste painel:**
- **Níveis territoriais:** não existem no produto público, que é só por DIST.
- **Agregados:** nenhuma soma nova é criada. A soma de extremos individuais continua rotulada como tal (NC-ENG-01).
- **UN e EQ:** são definidos pelo contrato, e nenhuma série é somada.

## 7. Novos modelos (Gate C)

### 7.1 Escopo

Entram no Gate C as posições `INDISPONIVEL` depois de P1 e P2, desde que a série tenha Moderado publicado e pelo menos 2 transições comparáveis. As demais ficam como irrecuperáveis nesta etapa, com a causa: F, G, H e séries com 1 transição.

### 7.2 Famílias testadas

Todas têm no máximo 2 parâmetros escolhidos, sem dado novo:

| Id | Família | Definição | Escolha (só na etapa S) |
|---|---|---|---|
| N1 | tendência amortecida (Gardner e McKenzie) | b = ln(y_T/y_T0)/(T − T0) do segmento; ŷ(T+h) = y_T · exp(b · Σ_{j=1..h} φ^j) | φ ∈ {0,8; 0,9}, pelo menor WAPE_S |
| N2n | crescimento encolhido, compartilhamento parcial nacional | g_i = w_i · ḡ_i + (1 − w_i) · μ, com ḡ_i = média das transições comparáveis da série até a origem, μ = mediana das transições comparáveis da métrica até a origem (todas as DIST), w_i = n_i/(n_i + κ); ŷ = y_T · exp(h·g_i) | κ ∈ {1; 3}, pelo menor WAPE_S |
| N2g | idem, compartilhamento por grupo econômico | μ = mediana do grupo econômico verificado (`grupos_2025.json`) quando ≥ 3 DIST do grupo têm transição; senão, o μ nacional | κ ∈ {1; 3}, pelo menor WAPE_S |
| N5 | regressão quantílica linear em painel (condicional) | `QuantileRegressor(quantile=τ, alpha=0, solver="highs")`, com o pré-processamento do gerador (winsorização 5–95% do alvo no treino, imputação pela mediana, padronização) e variáveis `FEAT_INT`; τ = 0,2 (Conservador) e 0,8 (Agressivo); ŷ = y25 · exp(h·q̂_τ) | nenhuma; exige pelo menos 60 pares na etapa S e **calibração**: a fração de crescimentos observados h=1 abaixo de q̂_0,2 (ou acima de q̂_0,8) em [0,10; 0,30] **nas etapas S e F** |
| N6 | elasticidade à carga (condicional estrutural) | g_ativo = a + β · g_UC, por MQO nas transições comparáveis dos dois ao mesmo tempo, sem ruptura em nenhum; extremo_t = M_t · (UC^ext_t / UC^mod_t)^β | nenhuma; vale só para medidores, ramais, rede BT, rede MT, postes e trafo_dist/quantidade; exige β > 0, β ≤ 3 e IC95% de β > 0 (bootstrap por grupo) **na amostra S** (2022→2023) e **na completa** (2022→2025); o extremo de consumidores usado tem de ser categoria A (P1–P3) na mesma DIST |

### 7.3 Excluídos, com motivo

| Família | Motivo |
|---|---|
| incremento mediano (diferenças) e Theil–Sen | com no máximo 2 incrementos nas origens de backtest, coincidem com a deriva e a OLS; não há evidência retrospectiva própria |
| Huber e outros robustos em painel | a winsorização 5–95% do alvo já existe; a robustez adicional não é testável em 3 transições |
| Ridge, KNN, RF e HGB com outras grades | já exploradas nos 1.504 ajustes da otimização (X); não são repetidas |
| modelos temporais com muitos parâmetros (ARIMA, ETS completo, redes) | há 3 transições por série |
| premissas de investimento | não há dado de plano de investimento nas fontes 2022–2025 do repositório |

- **N1 e N2 são previsões.** Entram em P3 com o critério de competitividade da seção 4.4.
- **N5 e N6 são cenários condicionais.** Não recebem tolerância de WAPE, porque não estimam a média. São rotulados como simulação condicional e nunca como intervalo de confiança.

## 8. Avaliação estatística (05)

Por métrica, candidato e etapa (S, F, H2, PRODUTO), nos mesmos pontos do produto:
- **Erros:** WAPE, MAE, RMSE e viés.
- **R²:** do estoque (só complementar), do crescimento ln(y/y0) e da variação Δ = y − y0. É nulo com n < 5 ou SST = 0.
- **Erro da expansão:** WAPE_EXPANSAO = Σ|ŷ − y| / Σ|y − y0|.
- **Robustez a outliers:** WAPE sem as 5% maiores variações relativas observadas.
- **Comparação com persistência, deriva, CAGR e o Moderado:**
  - diferença de WAPE e IC95% percentil por bootstrap pareado;
  - reamostragem de grupos econômicos inteiros (a DIST sem grupo verificado é o próprio grupo);
  - 2.000 réplicas, semente 20261104;
  - estimado só com pelo menos 20 DIST.
- **Robustez por distribuidora:** fração das DIST com erro absoluto ≤ ao do Moderado na etapa F, e WAPE_F do pior grupo econômico com ≥ 3 DIST.
- **Condicionais:** sem erro retrospectivo próprio. N5 relata a calibração, e N6 relata β com o IC95%.

## 9. Critérios de recomendação para integração futura

Nada disso é aplicado à RC.

| Origem | Recomendação possível |
|---|---|
| P1–P2 com O e X | regra série a série integrável como "simulação comparada retrospectivamente, experimental", depois da implementação pelo Codex no gerador, das regressões completas e da revisão humana |
| P3 (N1, N2) | só depois da confirmação na origem 2025 → 2026 com a configuração congelada |
| P4–P6 (condicionais) | integráveis só com o rótulo de simulação condicional, separado dos cenários por modelo, e só se a interface distinguir as categorias |
| Extremos publicados reprovados na seção 6 | recomendada a retirada ou a substituição na próxima versão do produto, por decisão humana |

## 10. Esquemas dos arquivos

| Arquivo | Chave | Conteúdo principal |
|---|---|---|
| `02_MATRIZ_SERIES_CENARIOS.csv` | DIST, conceito, métrica | empresa, grupo, ativo, família, unidade, natureza, kVA, padrão de estados 2022–2025, segmento, transições comparáveis, rupturas, restrições de qualidade, y_2025; Moderado e extremos publicados (modelo e 2030); estado publicado de cada extremo (seção 6); completude publicada e defensável; WAPE, R² e erro do Moderado; competitivos e otimizados disponíveis; causa de cada posição (seção 3); preenchimento final (etapa, categoria, modelo, 2030); classe final; possibilidade de recuperação; estado científico |
| `03_INVENTARIO_MODELOS_EXISTENTES.csv` | métrica, candidato | categoria (O, X, H, B-HIST), configuração, origem do resultado, reprodução, elegibilidade, competitividade, classe (seção 4.4) e séries coerentes por lado |
| `05_COMPARACAO_RETROSPECTIVA.csv` | métrica, candidato, etapa | as estatísticas da seção 8 |
| `06_AUDITORIA_PLAUSIBILIDADE.csv` | DIST, conceito, métrica, lado, origem do extremo | Q1–Q9, estado, valores 2026 e 2030 e o estado de cada candidato testado |
| `07_COBERTURA_ANTES_DEPOIS.csv` | nível (nacional, empresa, métrica, família), chave | contagens antes e depois por classe e por etapa, recuperadas, reprovadas, bloqueadas por causa, com e sem kVA |
| `selecao_congelada.json` | — | escolhas de φ, κ, calibração N5 e β N6, com o SHA-256 |

## 11. Coordenação com o Codex

- **Este script** (`recuperar.py`) é a **execução de referência** do protocolo, para auditoria. Não é a integração ao produto.
- **A integração ao gerador**, os testes automatizados e a coerência entre tela, JSON e CSV ficam com o Codex, conforme `09_RECOMENDACAO_INTEGRACAO.md`.
- **A implementação do Codex** é aceita se reproduzir `02` e `06` linha a linha nas posições integradas.
