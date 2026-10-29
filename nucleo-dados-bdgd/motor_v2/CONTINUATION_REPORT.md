# Continuidade do Motor V2 — 29/10/2026

Base publicada: `f92eb3e6ddc8b014d68144c35a758d0e10503c29`. Branch: `feat/motor-v2-granular-territorial`. Checkout: `D:/NUCLEO_BDGD_2025/wt-motor-v2`.

## Estado encontrado e preservado

Havia alterações locais em `integration.py` e `runner.py`, além de `comparison.py`, `comparison.json`, `temporal.py` e dois arquivos de testes ainda não rastreados. Esses arquivos foram retomados. Os 12 agregados de `runs/e37812185a2af670`, seus checkpoints e as projeções exploratórias anteriores permaneceram preservados. O comparativo `comparative/comparison/23455ac5a8506c49` já estava concluído com 114 registros de experimentos/bloqueios; ele também permanece em disco.

O teste de independência salvo havia falhado: o lançamento PowerShell com redirecionamento retornava apenas depois da finalização do Python. Foi substituído por um lançador com processo sem console, descritores explícitos e sem pipes herdados. A identificação agora inclui `launch_id`, evitando confundir o status de uma execução anterior com a retomada corrente. A finalização dos processos, incluindo o redirecionador Python do venv, é aguardada nos testes antes de limpar os arquivos temporários.

## Implementação concluída nesta continuação

O executor chama o comparativo, que utiliza `ml.build` para OLS, Ridge, Elastic Net, Poisson, Random Forest e HistGradientBoosting, além da persistência. Cada DIST × UCBT × quantidade possui candidatos individuais, compartilhados no **pool das três distribuidoras (6600, 6585, 26)** e transferência de um par escolhido apenas com dados de treino. O compartilhado foi corrigido para incluir as três empresas no treino elegível; antes excluía a empresa-alvo. O agrupamento não representa o setor nacional.

Seleção de variáveis, padronização e busca limitada de hiperparâmetros ocorrem dentro dos folds. A origem interna precede a externa; municípios de teste são excluídos de todas as empresas do treino. Foi acrescentado o bloqueio de rótulos internos divulgados após a origem externa. Sem validação interna elegível, registra-se uma configuração fixa com estoque defasado. Não se afirma que essa configuração foi otimizada.

Checkpoints comparativos possuem assinatura e SHA-256 do conteúdo. Checkpoint ausente, corrompido ou inválido é recalculado isoladamente. Código, configuração, entradas e versões de bibliotecas integram a assinatura da execução. Os relatórios sintéticos dos testes recebem marcação explícita, sem homologação. A escolha de pares também rejeita empresas sem urbanização disponível, em vez de atribuir zero à informação desconhecida. A média usada nessa distância descreve apenas os municípios com urbanização conhecida; não é uma estimativa da urbanização total da concessão.

## Execuções reais e retomada

Execução corrigida: `D:/NUCLEO_BDGD_2025/motor_v2/comparative/comparison/d91386f2e9afa03f`.

Foram usados apenas os agregados municipais já existentes, com leitura seletiva DuckDB. Não houve leitura de ZIP/GDB, download de dados ou nova agregação dos microdados. A comparação foi executada novamente porque a definição do pool e a proteção temporal mudaram; a última correção da escolha de pares sem urbanização também foi verificada, mantendo os resultados numéricos idênticos; a execução anterior não foi sobrescrita. São 19 candidatos por empresa/modalidade: 1 baseline + 6 algoritmos × 3 escopos. Total: 114 registros; 57 bloqueados em point-in-time e 57 com avaliações reconciliadas experimentais. Há 54 combinações de algoritmo/escopo com ajustes e 3 baselines experimentais.

A retomada real completou com **114 reutilizados e 0 executados**. SHA-256 e mtime de todos os 114 checkpoints permaneceram idênticos. Os 12 agregados anuais também permaneceram idênticos. Evidência: `D:/NUCLEO_BDGD_2025/motor_v2/comparative/continuation-verification.json`. O comando de retomada devolveu o controle em aproximadamente 1.92 s. O teste de integração comprova que o processo continua vivo e grava agregados depois de encerrados os dois lançadores.

## Modalidades temporais

**Point-in-time:** nenhum ponto elegível nas origens 2023/2024. As revisões disponíveis de 2022 e 2023 datam de 08/10/2025; as de 2024, 07/10/2025; as de 2025, 01/09/2026. Datas não foram alteradas. Métricas permanecem ausentes, sem zeros artificiais. `persistencia:individual` nesse modo é a política de fallback, não um vencedor medido.

**Retrospectiva reconciliada experimental:** admite explicitamente essas revisões posteriores, conservando as datas, para explorar relações entre os estoques históricos. O rótulo é `retrospective_reconciled_NOT_operational_NOT_leakage_free`. Esses erros não estimam desempenho operacional disponível nas origens históricas. Nenhuma previsão probabilística ou intervalo de confiança foi produzido.

`historical_publications.json` registra publicações e hashes dos inventários consultados. O inventário local não reconstrói todas as revisões anteriores da fonte; portanto o bloqueio significa **vintage elegível não comprovada no acervo**, e não prova de que nunca tenha existido. Obter snapshots históricos verificáveis permanece pendente.

## Resultados comparativos experimentais

| DIST | Escopo | Melhor exploratório | MAE municipal | WAPE | Escore robusto |
|---|---|---|---:|---:|---:|
| 6600 | individual | persistencia | 606.81 | 7.630% | 1039.21 |
| 6600 | shared_pilot | ols | 664.37 | 8.354% | 1166.12 |
| 6600 | peers_pilot | poisson | 661.87 | 8.322% | 1200.73 |
| 6585 | individual | persistencia | 352.47 | 4.311% | 552.76 |
| 6585 | shared_pilot | poisson | 376.08 | 4.600% | 687.24 |
| 6585 | peers_pilot | poisson | 360.76 | 4.413% | 646.62 |
| 26 | individual | ols | 792.17 | 6.143% | 1047.95 |
| 26 | shared_pilot | poisson | 917.27 | 7.113% | 1255.67 |
| 26 | peers_pilot | poisson | 985.18 | 7.640% | 1321.69 |

MAE, RMSE, viés e WAPE são calculados sobre pontos município/ano dentro de cada empresa, não sobre UCs individuais nem sobre o total nacional. Escore robusto = média do MAE por origem + desvio populacional entre origens; com duas origens, equivale ao pior MAE anual. Não se escolhe pelo WAPE nacional. Todos os 19 candidatos de cada empresa foram comparados nas mesmas chaves de teste: EPB 448, EMR 142 e EAC 44 pontos, em duas origens e três partições territoriais.

Na EAC, OLS individual tem escore robusto 1047,95 contra 1128,77 da persistência, embora seu WAPE agregado experimental seja maior (6,143% contra 5,887%). Essa diferença ilustra a distinção entre desempenho médio e estabilidade anual. **Nenhum modelo foi promovido:** duas origens são inferiores ao mínimo configurado de três. A persistência continua como fallback nas três empresas. Não há nova liberação operacional nem previsão 2026–2030 produzida pelos vencedores exploratórios.

A matriz pública `reports/pilot_comparison.csv` contém 114 linhas com métricas, variáveis selecionadas/rejeitadas por fold, justificativas, hiperparâmetros e bloqueios, apenas em nível de empresa. Os JSON locais preservam tentativas internas, coeficientes/importâncias e previsões municipais para auditoria. Coeficientes dos modelos logarítmicos se referem a variáveis padronizadas e resposta log1p; importâncias não representam efeitos causais.

## Cobertura e limitações

A interseção municipal cobre 100% dos estoques municipais dos alvos 2024/2025 nas três empresas. Na transição 2022→2023, a EPB possui somente 86,8276% do estoque de 2023 em municípios encontrados nos dois anos; EMR/EAC têm 100%. Ausência de município não vira zero. Essa seleção da coorte de treino limita a comparabilidade. O ano inicial não tem transição anterior disponível.

Códigos municipais são validados apenas sintaticamente; homologação com cadastro IBGE, mudanças de perímetro, conflitos territoriais e continuidade dos identificadores ainda precisam ser concluídos. Os conflitos já auditados (EPB/2022=16, EMR/2023=1) permanecem documentados. Municípios fora da UF predominante não são descartados. Não foi atribuída população de UF às empresas. Não foram usadas variáveis externas não verificadas. Entradas/saídas seguem indisponíveis sem continuidade cadastral comprovada.

Leitura agregada limitada a 512 MB/1 thread; ajustes limitam bibliotecas a duas threads e Random Forest a um worker. Orçamentos de tempo são cooperativos entre folds, não limites rígidos de memória RAM ou interrupção no meio de um fit. Não houve medição de pico de RAM nesta execução.

## Testes realmente executados

- `python -m unittest discover -s motor_v2/tests -v`: **23 testes passaram**. Incluem lançamento independente, outputs após saída do launcher, retomada, invalidação seletiva, parada, isolamento municipal entre empresas, seleção interna, bloqueio de publicação/revisão/rótulo futuro, urbanização ausente na escolha de pares, amostra temporal mínima, chave UC-v3, energia nula, cenários e exposição territorial.
- `python -m unittest motor_universal.tests.test_parquet -v`: **8 testes passaram** do contrato existente. Total final: **31 testes**, preservando os 17 iniciais.
- `git diff --check`: passou.
- Piloto real corrigido: concluído; retomada real: 114 reutilizados / 0 executados.

Logs: `D:/NUCLEO_BDGD_2025/motor_v2/tests-continuation-final.log` e `tests-contracts-final.log`. Os testes anteriores com falha não são contados como aprovações; as causas e correções estão descritas acima.

## Search First, Graphify e publicação

Graphify 0.9.92 reutilizou o grafo de `D:/NUCLEO_BDGD_2025/auditorias_codex/auditoria_20261027/graphify-out`. Foi preservado um backup e feita atualização incremental local de 21 arquivos Python, sem backend externo, por `graphify.watch._rebuild_code(changed_paths=..., no_cluster=True)` — a API incremental usada pelo mecanismo de update da versão instalada. O grafo passou de 333 para 476 nós. `query`, `path` e `explain` localizaram `experiment`, `choose_options`, `scope_pool`, `fit_predict` e `build`; as chamadas foram confirmadas no código original. Nenhum ZIP, GDB ou Parquet foi indexado. `motor-v2-source-map.json` contém os caminhos originais e hashes.

Foram inspecionados os arquivos do commit inicial e os acréscimos desta entrega: código, testes, configuração, documentação e matriz agregada. Nenhum Parquet, UC individual, ambiente virtual, binário ou segredo detectado foi incluído. A publicação limita-se à mesma branch, sem merge ou deploy. V1 e produção não foram modificados. Nenhuma dependência foi instalada nesta continuação.

## Operação e pendências

Na pasta `nucleo-dados-bdgd`, executar `powershell -NoProfile -ExecutionPolicy Bypass -File motor_v2/control.ps1 start -Config motor_v2/comparison.json`. Usar os mesmos argumentos com `status`, `stop` ou `resume`. O processo opera sem agente e grava status, progresso e logs em D:. A configuração do comparativo restringe o pool às três empresas; não iniciar lote nacional.

Pendentes: vintages para validação point-in-time; mais origens independentes; homologação territorial/cadastral; alvos de entradas/saídas; variáveis externas versionadas; generalização de transformadores/Rede MT e catálogo completo; binomial negativa/hierárquico/duas etapas; permutação e ablação ampliada; calibração probabilística. Os adapters e o catálogo inicial continuam infraestrutura preparatória, não experimentos concluídos.

## Integridade dos artefatos

- `manifest.json`: `b04294a3a487a8e48e075b0d00f97be02e49662a4640d59f5d4dce3261a3d044`.
- `summaries.json`: `bb8d7662408f16037ce94921268c9a3ec424624db70a07297ef1990071893ab4`.
- `MATRIZ_COMPARATIVA.csv`: `174c1c68922ee296d3a0b4f37341eb5c1807e280e60d294b8254f0dcf9349e88`.
- `continuation-verification.json`: `af2fb3d5dd0be56e779506770e106a3dd5992e94d5d43d812d4b1c4c4290379f`.
- `pilot_comparison.csv`: `79588a2fdf70d59353adf9580346cc40736e28fac4ddcdbc3127908516baeb46`.
- `tests-continuation-final.log`: `225ee681316ba90adc7cebe0ab4a5eef41f80d04504cf612284abe11befb1c45`.
- `tests-contracts-final.log`: `20845e8de3bb298d60791bf9ac8371f261d0144e531268e382fdda8adf3eacde`.
