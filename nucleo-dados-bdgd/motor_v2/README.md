# Motor V2 — execução isolada e auditável

Esta entrega implementa a infraestrutura e o piloto UCBT; **não é a conclusão do motor nacional completo**. O motor V1, seus resultados e o dashboard não são alterados. A base é o commit 74190e2 do PR #18.

## Execução sem agente

No PowerShell, a partir de `nucleo-dados-bdgd`:

```powershell
.\motor_v2\control.ps1 start
.\motor_v2\control.ps1 status
.\motor_v2\control.ps1 stop
.\motor_v2\control.ps1 resume
```

Alternativa: `motor_v2\control.bat start`. O processo Python fica independente do chat, com janela oculta, PID, logs em disco e lock exclusivo. Stop é cooperativo entre competências; cada tarefa possui limite de tempo, isolamento em subprocesso e checkpoints anuais. O executor retoma tarefas sem repetir agregações cujo fingerprint e hash de saída continuam válidos. A verificação de hash ainda lê os bytes do Parquet para detectar alterações.

Configuração de extração: `pilot.json`. Saídas, temporários e ambiente: `D:/NUCLEO_BDGD_2025/motor_v2`. DuckDB 2 GB / duas threads; somente um worker. O seletor anual original permanece preservado. Para comparar modelos nos agregados já salvos, usar `comparison.json`:

```powershell
.\motor_v2\control.ps1 start -Config .\motor_v2\comparison.json
.\motor_v2\control.ps1 status -Config .\motor_v2\comparison.json
.\motor_v2\control.ps1 stop -Config .\motor_v2\comparison.json
.\motor_v2\control.ps1 resume -Config .\motor_v2\comparison.json
```

O lançamento usa `launch.py` com processo sem console e sem herança dos pipes do PowerShell. `launch.json` identifica a solicitação; `status.json` registra o PID efetivo e o mesmo `launch_id`. No Windows, o PID do redirecionador do ambiente virtual pode diferir do PID efetivo. Logs persistentes têm nomes únicos por lançamento. Stop do comparativo é cooperativo entre experimentos/folds; uma chamada de ajuste em andamento termina antes da parada. Não há treinamento nacional neste modo.

## Contratos e regras

- Reutiliza `motor_universal.registry`, validadores, modelos individuais e escritor/leitor `bdgd-parquet-2`. UCBT é extensão explícita do objetivo consumidores; não substitui UC total (BT+MT+AT).
- Chave UC: COD_ID + PN_CON, com precedência AT/energia e desempate territorial determinístico da UC-v3. Conflitos territoriais são quantificados; não são automaticamente expansão física.
- Agregação DIST/ano/MUN/CONJ/CTMT/ARE_LOC. Nenhum identificador de UC é exportado. Energia exige todos os 12 campos, e NULL não vira consumo zero. Densidade indisponível sem denominador de área validado. Entradas/saídas permanecem indisponíveis sem continuidade de identidade certificada.
- Datas de disponibilidade usam a revisão da publicação ArcGIS. O acervo atual de 2022–2024 foi publicado/revisado em 2025; não pode entrar no treino de uma origem 2023/2024. Bloquear ML nessas origens é resultado correto, não falha operacional.
- Escolha individual DIST × objetivo × métrica, mesmos pontos elegíveis de teste, MAE + instabilidade e ganho mínimo de 5%. Poucos folds independentes implicam persistência, sem alegar que ela venceu um teste não executado.
- Cenários neutros coincidem quando não existem hipóteses futuras validadas. Taxas explicitadas no config são sensibilidades, não projeções oficiais. Ordem inválida é rejeitada, nunca corrigida por troca de rótulos ou clipping.
- Município fora da UF predominante é mantido e auditado. Nunca é imputada a população inteira de uma UF. Pesos de UC são exposição de clientes, não participação da população; `ml.exposure` exige participações municipais explícitas. Código com sete dígitos é apenas sintaticamente válido; validação IBGE e municípios compartilhados ainda são pendências.

## ML e generalização: estado real

`comparison.py` integra os pipelines de `ml.build` ao executor para UCBT: persistência, OLS, Ridge, Elastic Net, Poisson, Random Forest e HistGradientBoosting. Cada algoritmo tem escopos individual, **pool das três distribuidoras** (26, 6585, 6600) e transferência de um par escolhido no conjunto de treino. O pool compartilhado inclui os três DIST; o par é uma das outras duas empresas mais próxima em estoque/urbanização. Isso não representa seleção nacional ou agrupamento validado do setor.

Os testes externos combinam origens 2023/2024 e três partições municipais; o mesmo município nunca entra em treino e teste, mesmo entre empresas. Hiperparâmetros e subconjuntos de variáveis são escolhidos em uma origem interna anterior e municípios internos separados. Sem fold interno elegível, usa-se configuração fixa com estoque defasado, explicitamente registrada. O orçamento inicial é de três tentativas por algoritmo/fold e 90 segundos verificados entre folds (limite cooperativo, não interrupção forçada de um fit). Padronização é ajustada somente no treino. Energia e urbanização incompletas não são imputadas; a tentativa é rejeitada. Candidatos só são comparados se tiverem exatamente as mesmas chaves de avaliação.

As modalidades produzem diretórios/checkpoints e rótulos distintos: `point_in_time` exige disponibilidade de features, revisões e alvos de treino na origem, inclusive rótulos usados na seleção interna; `reconciled_retrospective` é **experimental, não operacional e não livre de vazamento de revisão**. Esta última conserva as datas reais e admite explicitamente vintages reconciliadas posteriores. Ambas proíbem competências futuras de treino e features contemporâneas ao alvo. A métrica de escolha é MAE municipal médio por origem + desvio entre origens, calculada por empresa. Duas origens não satisfazem o mínimo de três para promover um vencedor. Contagem de municípios não aumenta o número de origens independentes.

Binomial negativa, hierárquico completo e duas etapas estão registrados, mas não implementados. Não houve classificação de expansão porque esse alvo não foi validado. Comparação do piloto não promove modelos nem substitui as projeções exploratórias existentes.

`adapters.py` fornece funções para Rede MT e potência UN–EQ (TUC 565/570), com situações separadas e conversão MVA/kVA. Ainda requerem integração ao executor e testes com dados reais antes da fase C. As demais famílias constam no registro de objetivos, mas não possuem executor granular V2 implementado.

O catálogo externo reaproveita fontes IBGE locais e registra SAMP, migração, DEC/FEC, EPE e PDD como não ingeridos. Não há preenchimento artificial. Faltam ingestão versionada, participações territoriais validadas e cenários externos para esses dados. O comparativo testa subconjuntos de estoque, urbanização e consumo defasados, registra variáveis rejeitadas e coeficientes/importâncias quando disponíveis. Permutação, ablação exaustiva e orçamento adaptativo continuam pendentes. A investigação temporal usa inventários locais: ausência de uma vintage antiga no acervo não comprova que ela nunca existiu na fonte oficial.

## Artefatos

`status.json`, `runs/<fingerprint>/manifest.json`, registro de objetivos, catálogo externo, logs por tarefa, checkpoints e QA por ano, agregados territoriais Parquet, resultados por empresa, backtest/variáveis/hiperparâmetros, JSON e Parquet de projeções exploratórias, bundle de integração validado. Nenhum arquivo de produção é substituído. A primeira execução com chave COD_ID isolada está marcada `SUPERSEDED.json` e não deve ser usada.

Comparativo: `comparative/comparison/<fingerprint>/` contém `manifest.json` (entradas/código/versões), `coverage.json`, `historical_publications.json`, `MATRIZ_COMPARATIVA.csv`, `summaries.json`, resultados por modalidade/empresa, `progress.json` e checkpoints por experimento com SHA-256. Retomar uma configuração inalterada reutiliza os checkpoints válidos; corrupção de checkpoint recalcula apenas aquele experimento. Mudança de código, versões ou entradas gera outra execução e preserva a anterior. Só os pequenos agregados municipais são lidos; GDB, ZIP e Parquets individuais não são reprocessados no comparativo.

## Testes

```powershell
D:\NUCLEO_BDGD_2025\motor_v2\.venv\Scripts\python.exe -m unittest discover -s motor_v2/tests -v
```

Amostras sintéticas verificam chave composta, nulidade energética, vazamento temporal/territorial, seleção em pontos comuns, projeções negativas/ordenação e exposição territorial. O piloto real é separado desses testes e não equivale a treinamento nacional.
