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

Configuração: `pilot.json`. Saídas, temporários e ambiente: `D:/NUCLEO_BDGD_2025/motor_v2`. DuckDB 2 GB / duas threads; somente um worker. Não iniciar lote nacional nesta fase. O `max_trials` representa o orçamento para o módulo de pesquisa ML; o runner piloto ainda usa o seletor anual legado, com amostra mínima e bloqueio temporal.

## Contratos e regras

- Reutiliza `motor_universal.registry`, validadores, modelos individuais e escritor/leitor `bdgd-parquet-2`. UCBT é extensão explícita do objetivo consumidores; não substitui UC total (BT+MT+AT).
- Chave UC: COD_ID + PN_CON, com precedência AT/energia e desempate territorial determinístico da UC-v3. Conflitos territoriais são quantificados; não são automaticamente expansão física.
- Agregação DIST/ano/MUN/CONJ/CTMT/ARE_LOC. Nenhum identificador de UC é exportado. Energia exige todos os 12 campos, e NULL não vira consumo zero. Densidade indisponível sem denominador de área validado. Entradas/saídas permanecem indisponíveis sem continuidade de identidade certificada.
- Datas de disponibilidade usam a revisão da publicação ArcGIS. O acervo atual de 2022–2024 foi publicado/revisado em 2025; não pode entrar no treino de uma origem 2023/2024. Bloquear ML nessas origens é resultado correto, não falha operacional.
- Escolha individual DIST × objetivo × métrica, mesmos pontos elegíveis de teste, MAE + instabilidade e ganho mínimo de 5%. Poucos folds independentes implicam persistência, sem alegar que ela venceu um teste não executado.
- Cenários neutros coincidem quando não existem hipóteses futuras validadas. Taxas explicitadas no config são sensibilidades, não projeções oficiais. Ordem inválida é rejeitada, nunca corrigida por troca de rótulos ou clipping.
- Município fora da UF predominante é mantido e auditado. Nunca é imputada a população inteira de uma UF. Pesos de UC são exposição de clientes, não participação da população; `ml.exposure` exige participações municipais explícitas. Código com sete dígitos é apenas sintaticamente válido; validação IBGE e municípios compartilhados ainda são pendências.

## ML e generalização: estado real

`ml.py` contém pipelines com padronização ajustada no fold, candidatos sklearn e busca aleatória limitada em folds temporais e municípios disjuntos. Esse módulo ainda **não está integrado ao runner de microdados para seleção nacional/pares/individual**. Não confundir sua presença com experimentos concluídos. Binomial negativa, hierárquico completo e duas etapas estão registrados, mas não implementados. Não houve classificação de expansão porque esse alvo não foi validado.

`adapters.py` fornece funções para Rede MT e potência UN–EQ (TUC 565/570), com situações separadas e conversão MVA/kVA. Ainda requerem integração ao executor e testes com dados reais antes da fase C. As demais famílias constam no registro de objetivos, mas não possuem executor granular V2 implementado.

O catálogo externo reaproveita fontes IBGE locais e registra SAMP, migração, DEC/FEC, EPE e PDD como não ingeridos. Não há preenchimento artificial. Faltam ingestão versionada, participações territoriais validadas e cenários externos para esses dados. Seleção por permutação, ablação, orçamento adaptativo e explicações para modelos treinados permanecem pendentes.

## Artefatos

`status.json`, `runs/<fingerprint>/manifest.json`, registro de objetivos, catálogo externo, logs por tarefa, checkpoints e QA por ano, agregados territoriais Parquet, resultados por empresa, backtest/variáveis/hiperparâmetros, JSON e Parquet de projeções exploratórias, bundle de integração validado. Nenhum arquivo de produção é substituído. A primeira execução com chave COD_ID isolada está marcada `SUPERSEDED.json` e não deve ser usada.

## Testes

```powershell
D:\NUCLEO_BDGD_2025\motor_v2\.venv\Scripts\python.exe -m unittest discover -s motor_v2/tests -v
```

Amostras sintéticas verificam chave composta, nulidade energética, vazamento temporal/territorial, seleção em pontos comuns, projeções negativas/ordenação e exposição territorial. O piloto real é separado desses testes e não equivale a treinamento nacional.
