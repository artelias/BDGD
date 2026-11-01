# Motor V2 — reconciliação hierárquica UCBT ⊂ Consumidores (2026-10-30)

O estado é **experimental e interno**. Nada foi homologado.

O que **não** foi feito nesta etapa:
- novo treinamento nacional ou reexecução dos candidatos de ML;
- inclusão de variável externa;
- alteração de produto público, merge ou deploy.

Base: commit `0cf98d8` (seções 1–8) e `ad1a636` (seção 9, fechamento e preparação de integração).

| Arquivo | Conteúdo |
|---|---|
| `nacional/hierarquia.py` | código da reconciliação e verificador de completude |
| `nacional/erro_retrospectivo.py` | erro retrospectivo ponta a ponta (§9.2) |
| `nacional/fonte_canonica.py` | fonte canônica interna de consumidores (§9.3) |
| `reports/nacional/CONTRATO_HIERARQUIA_CONSUMIDORES.json` | contrato |
| `reports/nacional/PROJECOES_CONSUMIDORES_RECONCILIADAS.csv` | projeções originais e reconciliadas |
| `reports/nacional/VIOLACOES_E_AJUSTES.csv` | violações e ajustes por DIST, ano e cenário |
| `reports/nacional/ESTRATEGIAS_RECONCILIACAO_CONSUMIDORES.csv` | estratégias comparadas |
| `reports/nacional/COMPLEMENTO_POR_DIST.csv` | complemento e método por DIST |
| `D:/NUCLEO_BDGD_2025/motor_v2/nacional/hierarquia_consumidores/` | artefatos completos |

## 1. Problema

- Os níveis A (UCBT) e B (Consumidores) foram modelados de forma independente.
- **Observado:** a relação Consumidores = UCBT + UCMT + UCAT − sobreposição fecha exatamente nos 385 pares DIST × ano auditados.
- **Projetado:** a relação se perdia.
  - 101 células DIST × ano × cenário com Consumidores < UCBT, em 24 DIST.
  - Em 2030: 5 DIST no conservador, 14 no moderado (déficit de 478.372; Light 324.343) e 5 no agressivo.
  - Violação agregada nacional no agressivo de 2029 e 2030: UCBT 106.236.504 contra Consumidores 105.983.865 na coorte de 98 DIST.

## 2. Contrato de reconciliação hierárquica

Para a mesma DIST, competência e cenário:

```
Consumidores = UCBT + complemento,  complemento = UCMT + UCAT − sobreposição ≥ 0   (identidade UC-v3: COD_ID + PN_CON, ativas)
Consumidores_reconciliado ≥ UCBT;  inteiros ≥ 0;  Conservador ≤ Moderado ≤ Agressivo
```

**Pares compatíveis:** mesma publicação, estoques elegíveis pela política comum e fechamento exato com a auditoria UC-v3 do ETL.
- Isso dá 384 pares, que usam todos os 385 fechamentos exceto a Energisa Nova Friburgo 2022, inelegível por `nao_somar`.
- Nenhum complemento observado é negativo.
- Uma transição do complemento só é comparável se a transição B for elegível (sem ruptura nem sucessão) e o nível A não tiver ruptura.

**Estratégia adotada (`hierarquica_complemento`):**
1. A projeção UCBT do nível A (modelo e cenários) é preservada sem alteração.
2. A série observada do complemento B − A é montada só com os pares compatíveis.
3. O complemento é modelado com os baselines que o histórico de 4 pontos suporta (persistência, deriva e CAGR), escolhidos por DIST com o mesmo backtest (origens 2023 e 2024) e a mesma regra de escolha do motor.
   - Uma tendência só entra se for ≥ 5% melhor que a persistência e não pior em nenhuma origem.
   - Resultado: persistência em 63 DIST, deriva em 20, CAGR em 20.
4. Os cenários do complemento seguem `cenarios.scenarios` com a triagem v2 aplicada ao corte nacional dos complementos.
5. Consumidores reconciliado = UCBT (inteiro, como publicado) + arredondamento half-up do complemento. Como os dois termos são ordenados, o resultado também é.
6. A previsão independente do B e o modelo que a gerou ficam em colunas próprias (`consumidores_B_original`, `modelo_B_original`).
   - O ajuste aplicado (`ajuste` = reconciliado − original), o método do complemento e a classificação de cada célula também são registrados.

**Cobertura:**
- 103 DIST reconciliadas, nenhuma sem coorte.
- 5 têm âncora anterior a 2025 (2904, 5274, 5279, 5370 e 6611). São reconciliadas no próprio horizonte e ficam fora dos totais.

## 3. Comparação das estratégias (coorte de 98 DIST, âncora 2025, 1.470 células)

| Estratégia | Admissível | Violações | Células alteradas vs. B original | Conservador 2030 | Moderado 2030 | Agressivo 2030 | CAGR moderado 2025–2030 | Amplitude (agressivo − conservador) / moderado | Complemento 2030 (moderado) |
|---|---|---|---|---|---|---|---|---|---|
| **hierarquica_complemento** (adotada) | sim | 0 | 1.190 | 87.642.247 | 93.460.778 | 106.671.042 | 0,70% | 20,4% | 348.437 |
| hierarquica_participacao | sim | 0 | 1.182 | 87.637.706 | 93.446.198 | 106.619.486 | 0,70% | 20,3% | 333.857 |
| ajuste_minimo | sim, com ressalva | 0 | 312 | 87.993.113 | 95.251.884 | 106.685.610 | 1,08% | 19,6% | 2.139.543 |
| b_prevalece (referência) | **não**: altera a UCBT do nível A | — | 0 | 87.620.142 | 94.715.778 | 105.983.865 | 0,97% | 19,4% | — |

**Hierárquica com complemento × participação constante.**
- As duas dão praticamente o mesmo resultado: menos de 0,02% de diferença no total.
- A adotada usa o histórico do próprio complemento.
- A participação constante supõe que UCMT e UCAT crescem no ritmo da UCBT, uma hipótese não verificada.

**Ajuste mínimo.**
- Altera só as células violadas, mas mistura o crescimento de dois modelos independentes.
- O "complemento" implícito em 2030 seria de 2,14 milhões, 6,7 vezes o complemento observado em 2025 (319.161). Isso é fisicamente implausível para UCMT + UCAT, por isso a estratégia não foi adotada.

**B prevalece.** Removeria a violação reduzindo a UCBT do nível A, contrariando a exigência de preservar o nível territorial.

**Consequências da adotada.**
- Crescimento: o moderado nacional de Consumidores passa de 0,97% para 0,70% ao ano e acompanha a UCBT.
- Amplitude: o leque dos cenários passa de 19,4% para 20,4%, porque herda a amplitude da UCBT territorial.

## 4. Auditoria das violações e dos ajustes (`VIOLACOES_E_AJUSTES.csv`)

Todas as DIST e os anos 2026–2030 nos três cenários: 1.545 células reconciliadas.

Classificação de cada célula:
- `violacao_mesma_dist`: a diferença de modelo supera o complemento;
- `sem_violacao; diferenca de modelo`;
- `sem_violacao; diferenca so de conceito`: o B original já era UCBT + complemento;
- `sem_coorte`: nenhuma célula;
- e uma linha `NACIONAL_COORTE` por ano e cenário, com a violação agregada.

| 2030 | Violação na mesma DIST | Sem violação, diferença de modelo | Sem violação, só conceito |
|---|---|---|---|
| Conservador | 5 | 82 | 16 |
| Moderado | 14 | 49 | 40 |
| Agressivo | 5 | 87 | 11 |

**Efeito do ajuste (reconciliado − B original) em 2030:**

| Cenário | Soma | Maior alta | Maior baixa |
|---|---|---|---|
| Conservador | +21.457 | Light +330.620 | Enel RJ −280.949 |
| Moderado | −1.255.227 | Light +331.366 | Enel SP −951.126 (o CAGR do B dá lugar à UCBT do A + complemento) |
| Agressivo | +687.471 | DIST 369 +607.787 | DIST 5160 −19.404 |

No total, 605 células foram elevadas, 610 reduzidas e 330 ficaram inalteradas.

## 5. Totais nacionais revisados (`TOTAIS_NACIONAIS_SERIES_COMPLETAS.csv`, nível `B_reconciliado_A`)

- Somam só a coorte comparável: 98 DIST com âncora 2025 em A e B e complemento observado.
- O status é **PARCIAL**, com cobertura de 99,894% do estoque 2025 de consumidores. Ficam fora quatro cooperativas sem estoque 2025 utilizável e as reconciliadas com âncora anterior.

| 2030 | UCBT (A) | Consumidores B original | **Consumidores reconciliado** | Complemento |
|---|---|---|---|---|
| Conservador | 87.326.180 | 87.620.142 | **87.642.247** | 316.067 |
| Moderado | 93.112.341 | 94.715.778 | **93.460.778** | 348.437 |
| Agressivo | 106.236.504 | 105.983.865 | **106.671.042** | 434.538 |

## 6. O que foi preservado

- Ponte da Celesc 2023 (camada derivada), `INTERVALO_NAO_ANUAL` (estoque e transição avaliados separadamente), sucessão societária, `DAT_CON` desligada e cenários v2: tudo inalterado.
- As projeções dos demais ativos e conceitos não foram tocadas. A reconciliação só lê a UCBT do nível A e os Consumidores do nível B, e escreve em arquivos próprios.
- **TUC 570:** só investigação adicional (`INVESTIGACAO_TUC570.csv`), sem liberação.
  - Das 272 DIST × ano no gate, 189 têm diferença de até 1% entre equipamento e instalação e 220 de até 5%.
  - Em 21, o kVA varia mais de 10% acima da variação no número de unidades.

## 7. Testes, verificações e hashes

- **230 testes, 230 OK** (estado da seção 1–8; o estado atual, 243/243, está em §9) (`MATRIZ_TESTES.csv`, `MANIFESTO_TESTES.json` com hashes): 221 anteriores e 9 novos.
  - `test_hierarquia.py` (8 testes) cobre: nenhuma violação após a reconciliação, ordem dos cenários, complemento ≥ 0, inteiros, UCBT intocada, previsão original preservada, determinismo e idempotência, pares incompatíveis não reconciliados e detector de violações.
  - `PublicVerifier` (1 teste) cobre a baseline das alterações públicas.
- **Teste intermitente:** `test_executor_integration` falhou uma vez sob carga (`completed_with_errors` com prazo de 60 s por tarefa). Passou isolado duas vezes e na rodada completa seguinte. O teste agora retém os artefatos de uma execução que não termine `completed`, para auditoria.
- **CI Linux:** novo workflow `.github/workflows/motor-v2-sintetico.yml`, com 10 suítes que não leem `D:` nem a base local.
  - A ausência desses caminhos foi emulada localmente, com bloqueio de leitura, e as 10 suítes passaram.
  - `test_features`, `test_ml` e `test_scale` dependem de dados locais e ficam só na auditoria completa local.
  - Primeira execução no GitHub falhou por falta de `pyogrio` (importado por `convert_zips`); a dependência foi fixada no workflow e o ambiente equivalente foi reproduzido localmente.
- **`VERIFICACOES_INTEGRIDADE.json`: ok.**
  - Hierarquia: 1.545 células reconciliadas, 0 violações, 385/385 fechamentos exatos e 101 violações originais preservadas para auditoria.
  - Além do que já era verificado: contagens, ordem, território = empresa, hashes do painel e original da Celesc.
- **Verificador público corrigido.** O `ok` agora reprova qualquer alteração em `web/`, `output-historico/`, `output-publicavel/` ou `motor_cenarios/` que não esteja na baseline versionada (`nacional/baseline_produtos_publicos.json`) com o mesmo caminho, status e SHA-256.
  - A única entrada é a alteração preexistente, só de fim de linha, em `web/src/lib/maplibre-version.ts`.
  - Alterações causadas pela execução: nenhuma.
  - A auditoria dos produtos públicos continua ok e idêntica.

## 8. Limitações

- O complemento tem só 4 competências por DIST, e 15 DIST têm 0 ou 1 origem de backtest; nesses casos ele fica em persistência.
- Seus cenários são hipóteses de ritmo sustentado, como os demais.
- A reconciliação herda a validação do nível A: 2 origens, sem point-in-time, horizonte acima de 1 ano não validado.
- Os totais continuam **PARCIAIS**.
- Nenhuma homologação científica é declarada.

## 9. Fechamento e preparação de integração (2026-10-30)

Base: commit `ad1a636`. Nada foi retreinado nem reprocessado: a etapa lê os resultados já calculados.

### 9.1 Verificador de completude (15 pares por DIST)

`hierarquia.incompletude` exige, para **cada DIST reconciliada**, exatamente 15 pares (ano, cenário) únicos (2026–2030 × 3 cenários): sem duplicidade, sem ausência, sem par fora do horizonte. Ele é aplicado:
- na própria `hierarquia.run()` (que falha se houver qualquer problema);
- em `verificacoes.run()` (o `ok` exige `incompletude == 0`);
- em `fonte_canonica` (recusa a fonte).

O detector antigo de violações (`violations`) não via duplicatas, porque indexa por (DIST, ano, cenário) e sobrescreve; a duplicidade agora é detectada separadamente e há teste cobrindo isso.
Resultado atual: **103 DIST × 15 = 1.545 linhas, 0 problemas.**

### 9.2 Erro retrospectivo ponta a ponta de Consumidores = UCBT + complemento

`nacional/erro_retrospectivo.py`. **Diagnóstico retrospectivo; não é validação científica.**

**Como foi medido.** Sem retreino: as previsões de 1 passo já armazenadas do nível A (total da distribuidora por origem) são somadas às previsões de 1 passo do complemento (baselines sobre o histórico de pares compatíveis) e comparadas com o realizado de Consumidores. O comparador independente é o backtest já armazenado do nível B, nas **mesmas células** (DIST × origem).
- Origens: 2023 e 2024, prevendo 2024 e 2025 (horizonte de **1 ano**).
- Células: **176** em **96 DIST**. Foram excluídas 30, cada uma com motivo registrado:
  - 19 sem complemento observado em `o` e `o+1`;
  - 9 em que o real do nível A difere da UCBT auditada;
  - 2 com ruptura ou sucessão.

**Resultado (todas as 176 células).**

| Variante | MAE | WAPE | Mediana APE | Viés | Vence B escolhido (vit/der/emp) | p (teste dos sinais) |
|---|---|---|---|---|---|---|
| UCBT (A escolhido) + complemento escolhido | 22.333 | 2,59% | 0,64% | −0,58% | 65/71/40 | 0,67 |
| UCBT (A escolhido) + complemento persistência | 22.333 | 2,59% | 0,64% | −0,58% | 58/73/45 | 0,22 |
| Persistência A + persistência complemento (sem escolha de modelo) | 28.678 | 3,33% | 1,99% | −1,30% | 14/116/46 | < 0,01 |
| **B independente (escolhido)** | 23.954 | 2,78% | 0,64% | — | — | — |
| B persistência | 28.694 | 3,33% | 1,99% | −1,30% | 10/114/52 | < 0,01 |
| B deriva | 39.897 | 4,63% | 0,74% | — | 19/96/61 | < 0,01 |
| B CAGR | 39.264 | 4,56% | 0,76% | — | 24/91/61 | < 0,01 |

Por origem, o WAPE do ponta a ponta reconciliado é 2,73% (2023) e 2,42% (2024), contra 2,94% e 2,59% do B escolhido. Sem as 3 maiores empresas: 2,80% contra 2,95%.

**Leitura.**
1. **O reconciliado e o B independente escolhido são estatisticamente indistinguíveis** nestas células: ganha em 65, perde em 71, empata em 40 (p = 0,67). A diferença de WAPE (2,59% contra 2,78%) é pequena e vem dos grandes DIST.
2. **A escolha do complemento praticamente não importa:** trocar o método escolhido pela persistência não altera o erro (MAE 22.333 nos dois). O desempenho vem da UCBT do nível A, e o complemento é cerca de 0,35% do total.
3. **Contra os baselines simples** (persistência, deriva e CAGR do B), o reconciliado erra menos, com p < 0,01.
4. **Verificação de consistência do método:** a variante sem escolha de modelo (persistência de A + persistência do complemento) reproduz a persistência do B (WAPE 3,33% nos dois), como a identidade de fechamento exige.

**Limites que valem para qualquer uso destes números.**
- Só 2 origens e só horizonte de 1 ano: o erro de 2026–2030 em horizontes maiores **não foi medido**.
- As variantes escolhidas (A, complemento e B) foram selecionadas **nessas mesmas origens**; a comparação é otimista para elas. Não há origem reservada.
- Sem vintage point-in-time.
- O erro assinado do B só existe para a persistência; para os demais usa-se o erro absoluto armazenado.

Artefatos: `ERRO_RETROSPECTIVO_CONSUMIDORES.csv` (por recorte e variante), `…_CELULAS.csv`, `…_EXCLUIDAS.csv` e `…_RESUMO.json`.

### 9.3 Fonte canônica interna de consumidores

`nacional/fonte_canonica.py` e `FONTE_CANONICA_CONSUMIDORES_INTERNA.json`.
- **A projeção reconciliada (`consumidores_reconciliado`) é a fonte canônica interna** de consumidores por DIST × ano × cenário para integrações futuras.
- `consumidores_B_original` é mantida **somente** como resultado independente e material de auditoria; **nunca** como substituto quando falta valor canônico. Hoje todos os 103 DIST têm valor canônico; se um faltar, o consumidor da fonte deve tratar a ausência explicitamente.
- `carregar()` recusa a fonte se o SHA-256 diferir do contrato declarado ou se a série falhar nas regras (≥ UCBT, inteiros, ordem, 15 pares).
- O contrato declara `proibido`: publicar, exibir no dashboard e declarar homologação. Continua **interno e experimental**.

### 9.4 Idempotência, hashes e produtos públicos

- **Idempotência.** `hierarquia.run()` e `erro_retrospectivo.run()` foram executados duas vezes seguidas: todos os arquivos de saída (CSVs, Parquet e JSONs) ficaram com **SHA-256 idêntico**. Em relação à execução anterior, só o contrato JSON mudou (campos novos).
- **Hashes.** `VERIFICACOES_INTEGRIDADE.json` está `ok`: 2.049 agregados do painel sem divergência; a ponte da Celesc preserva o original byte a byte; 385/385 fechamentos exatos; 101 violações originais preservadas para auditoria.
- **Produtos públicos.** Nenhuma alteração atribuída à execução. A única alteração pública é a preexistente, só de fim de linha, em `web/src/lib/maplibre-version.ts`, identificada pela baseline (caminho + status + SHA-256).

### 9.5 Teste intermitente `test_executor_integration`

**Não reproduzido; causa não demonstrada.** A evidência da falha original se perdeu: o `tearDown` anterior apagava a execução mesmo com `completed_with_errors`. O que foi feito:
- **Canais de falha do executor** (todos registram `failure_<dist>.json`): o *guard* de memória (RAM livre < piso), o orçamento de 60 s por tarefa e o código de saída do worker.
- **Carga de CPU:** 5 execuções do teste com 4 processos saturando os 4 núcleos: 5/5 passaram (128–161 s, contra 31 s sem carga).
- **Pressão de memória** (RAM livre reduzida para 0,30 GiB): 1/1 passou.
- **Folga do orçamento de 60 s:** tempo de parede do worker por DIST = 4,2 s sem carga e 12–15 s com 4 núcleos saturados; a folga é de 4× a 14×. O estouro exigiria uma lentidão > 14× (por exemplo, I/O ou swap).
- **Folga de memória:** piso do *guard* = 0,5 GiB; a RAM livre medida nesta máquina (7,9 GiB) oscilou entre 0,76 e 1,24 GiB. **A hipótese mais plausível é o *guard* de memória, mas ela não foi demonstrada.**
- **Mudança:** o timeout **não foi alterado.** `diagnose()` agora mostra, quando o estado é `completed_with_errors`, o `failure_<dist>.json`, o fim do log da tarefa e a RAM livre, e a execução fica retida. Só o caso em que **todas** as falhas são o *guard* de memória vira *skip* explícito (a máquina, não o executor); orçamento estourado, saída ≠ 0, falhas mistas ou ausência de arquivo de falha continuam sendo **falha**. Há 4 testes determinísticos desse comportamento.

### 9.6 Testes

- **Auditoria completa local: 243 testes, 243 OK, 0 falhas, 0 erros, 0 ignorados** (`MATRIZ_TESTES.csv`, `MANIFESTO_TESTES.json` com hashes). São os 230 anteriores mais 13 novos:
  - 1 de completude de 15 pares (`test_hierarquia`);
  - 8 de erro retrospectivo ponta a ponta e fonte canônica (`test_erro_retrospectivo`);
  - 4 do diagnóstico do executor (`DiagnoseFailure`).
- **CI Linux sintético:** 11 suítes, 150 testes, sem acesso a `D:` ou à base local. O workflow `motor-v2-sintetico.yml` inclui `test_erro_retrospectivo`. A ausência de `D:` foi emulada localmente (bloqueio de leitura): as 11 suítes passam, com 1 *skip* herdado de `test_conj_plan`. A execução no GitHub desta etapa depende do push.

## 10. Estado de integração

- A reconciliação, o verificador, o erro retrospectivo e a fonte canônica estão prontos como **PR em rascunho**, sem merge, deploy ou publicação.
- Dependências e conflitos com os PRs #17–#20: `COMPATIBILIDADE_PRS.md`.
