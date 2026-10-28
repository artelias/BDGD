# Reconciliação de anomalias BDGD e KNN — PR #13

Base verificada: `19880695ef112a22144d856baab3d7cbd474494c`, dependente do PR #12. Sem merge, deploy, reextração da base, alteração de GDB/ZIP/checkpoints ou homologação humana. Foram usadas as dependências já declaradas; nenhum pacote foi adicionado aos manifests/lockfiles.

## Diagnóstico e antes/depois

[Quadro por DIST × ano × ativo](ANTES_DEPOIS.csv). Os arquivos originais da série 2022–2025, a matriz de homologação, auditorias F4/F6 e os artefatos patrimoniais permanecem preservados; assinaturas em [origens-preservadas.json](evidencias/origens-preservadas.json).

| Caso | Evidência publicada | Tratamento |
|---|---|---|
| Coopera 5370 / 2025 | UCBT vazia; UCMT 224 AT + 18 DS; UCAT 1 AT | UCBT **0\*** cadastral; quantidade física/total consumidores **N/D**; subtotal observado **225**, sem treinamento ou CAGR como total completo |
| Equatorial Goiás 6072 / 2025 | UCBT 13.492 AT e 3.449.443 DS; UCMT 9.711 AT e 61 DS; UCAT 48 DS | Preservar **23.203** da regra AT com ressalva. Não converter DS em AT; ruptura/comparabilidade impedem treino. Presença de energia mensal nas DS não foi aferida nestes artefatos |
| Certel 7371 / 2025 / EQTRM | 64 em 2024; entidade com 0 registros em 2025, ranking F4 #166 | Quantidade física **N/D**, zero cadastral preservado como evidência. Sem atribuição automática a RT/AT2: esses artefatos não demonstram essa causa |
| Cooperzem 5374 / PIP | 4.954 → 5.040 → 1.545 → 5.249; 4.966 identificadores de 2023 reaparecem em 2025 | 2024 continua **N/D/não homologado**; 2025 observado com ressalva/ruptura. Não inferir baixas/expansão da queda/retomada |

**Achado sobre o PR anterior:** o contrato nacional já tinha Coopera 2025 NULL, Certel 2025 NULL e Cooperzem 2024 NULL. O problema remanescente estava nos totais/cubos de apresentação e pacote 2025. Não se afirma que o motor canônico treinava com o subtotal Coopera: essa série já estava bloqueada. A nova versão acrescenta rastreabilidade e fecha a inconsistência entre produtos.

Coopera 2022–2024 permanece **26.773 / 27.315 / 28.141** pela regra UC v3, sem reconstrução a partir da soma bruta das entidades. UCMT 224 e UCAT 1 são quantidades **ativas** de 2025; as contagens técnicas de registros/distintos, inclusive DS e histórico cadastral, são preservadas separadamente.

No pacote 2025, a soma de consumidores entre DISTs passa de **90.252.218** (99 com valor) para **90.251.993** (98 com valor e 1 N/D). É subtotal do pacote disponível, não total Brasil completo. Em transformadores de medida, a soma permanece **746.074**, mas Certel passa de zero a N/D e a cobertura de 99 para 98 com valor. Os agregados nacionais do contrato já excluíam as células bloqueadas: não se subtrai Coopera novamente.

## Nova consulta à fonte oficial

Em 27/10/2026, a busca paginada ArcGIS `owner:aneel_aneel AND (Coopera OR 5370)` retornou 21 itens (incluindo outros anos, Cooperaliança e imagens), `nextStart=-1`. O filtro exato DIST 5370, competência 2025, tipo File Geodatabase, identifica **uma publicação**: `Coopera_5370_2025-12-31_V11_20260822-0914.gdb.zip`, item `5d0f7ea5db5d48aeb365998fabaa9db7`.

O ZIP foi baixado novamente, somente para conferência de assinatura: **7.860.642 bytes**, SHA-256 `5da0502b286b1ec7c8df898a56f2e8ecc1d2c896c139058436e9cfd9606732fb`, igual ao registrado na auditoria de integridade. A identidade criptográfica vincula o arquivo atual à inspeção de entidades preservada em F4; não foi realizada nova extração de GDB nem leitura individual de clientes. Não se certifica ausência de publicações futuras ou fora do catálogo oficial consultado. Respostas brutas e comprovante em `evidencias/`.

## ETL, contratos e apresentação

- `reconciliacao/derivados.py` aplica correções dirigidas aos derivados, preservando contagens brutas, cubos observados e assinaturas de origem. Outra assinatura de ZIP ou uma entidade novamente preenchida interrompe a aplicação, exigindo reauditoria; ressalva antiga não pode apagar dados novos.
- Estágio final reproduzível: `python etl/bdgd2025/89_reconciliar_anomalias.py` após 80/85/86/87. Não varre/reprocessa GDBs. Depois, regenerar 88 e motor com o contrato reconciliado. Assinaturas dos derivados antes/depois são registradas, e o histórico original não é sobreposto.
- Contrato nacional **1.0.1** preserva as 11.400 linhas e estados, acrescentando `observacao_id`, `subtotal_observado` e `valores_publicados_json`. Esses campos não são alvos nem features. `valor` continua NULL nas células bloqueadas; o adaptador transporta a evidência ao Parquet long.
- Pacote 2025 recebe versão `-rec1`, estado global `com_ressalvas`, sem nova homologação. Totais, fatos físicos, matriz, complementares e assets correspondentes são coerentes. UCBT física NULL convive com contagem cadastral de registros 0.
- Metadados de cobertura por população nos cubos impedem que BT desconhecida da Coopera e TUC 575 desconhecida da Certel virem zero ou subtotal completo. Filtros exclusivamente MT/AT da Coopera e outros TUC da Certel mantêm valores observados.
- Percentuais e comparações de agregados incompletos ficam N/D. Gráficos preservam lacunas; não convertem NULL em barra de valor zero.
- `observacoes.json` é a fonte única, com chave DIST × ANO × ATIVO × MÉTRICA, entidade, valor publicado, problema, evidência, tratamento, impacto, arquivo/versão/assinatura. A seção **Observações e ressalvas dos dados** acompanha recortes em Panorama, Explorar, Matriz, Comparador, Evolução, Previsões e Metodologia. CSVs e o diagnóstico JSON incluem as ressalvas.
- Corrigido seletor de cenários: consumidores Coopera permanece selecionável como N/D/bloqueado, sem trocar silenciosamente para outro ativo elegível.

## KNN implementado e limite da avaliação real

`motor_universal/knn.py` reutiliza contratos, métricas, baselines e bundle Parquet existentes. Trata-se de um avaliador entre DISTs, separado dos candidatos por série do motor antigo. Não reconstrói o motor nem substitui alvos ausentes.

Usa o último estoque confiável e disponível como âncora, log do estoque e variáveis internas/externas numéricas explicitamente comparáveis. Cada variável exige fonte, unidade, referência, disponibilidade, versão e controle de ruptura. Há pelo menos uma variável externa declarada; ausências não viram zero. Sem painel comparável, âncora disponível ou vizinhos suficientes, a execução bloqueia.

Para cada origem, treino contém somente transições anuais cuja resposta estava disponível no corte, no mesmo objetivo/métrica/unidade/perímetro/regra. A DIST avaliada inteira fica fora do treino. Cada vizinho é uma **DIST distinta**, usando sua última transição elegível; linhas e anos empilhados não multiplicam vizinhos. Rupturas cortam o regime. Linhas municipais são recusadas, sem rateio/duplicação implícita. Zeros verificados podem ser respostas; zeros técnicos não entram, e âncora zero não define taxa de crescimento.

Escalas são ajustadas apenas nos vizinhos de treino. Grade padrão k=1/3/5 usa origens internas comuns; a última origem é reservada para auditoria. A comparação com persistência, OLS e crescimento histórico usa os mesmos pares e MAE, RMSE, WAPE e viés. A saída contém estimativa separada do observado, vizinhos/DISTs/anos/distâncias/proveniência e intervalo indicativo mínimo–máximo dos análogos, **não calibrado como intervalo de confiança**. Necessidade de expansão é NULL. `previsao_validada=false` em qualquer execução.

[Resultado real](knn-real.json): **bloqueado**, 0 variáveis externas entregues ao painel; âncora candidata Coopera 2024=28.141, mas disponibilidade original desconhecida. Estimativa e métricas reais KNN ficam NULL/N/D, `n=0`. A comparação numérica foi exercitada exclusivamente em fixtures sintéticas nos testes; não é validação com dados reais.

[Inventário das fontes externas e impedimentos](fontes-externas.json): SAMP tem recurso 2025 localizado e esquema consultado, com identificação por CNPJ/sigla, sem DIST BDGD; falta correspondência auditada, separação das unidades de mercado e versões disponíveis nas origens. IBGE exige associação municipal–DIST e pesos por ano, sem duplicar municípios entre distribuidoras; acesso integral da página retornou 403. EPE disponibiliza contexto regional/UF, mas não foi demonstrado painel DIST × ano comparável. Dados de 2025 publicados em 2026 não entram num corte de 2024. Não se declara que essas fontes inexistem ou que são inacessíveis em geral.

## Reprodutibilidade patrimonial

Run anterior `40558337116`, job `122380310830`: os 30 testes patrimoniais e 62 do motor passaram; a comparação `cmp` do produto web falhou no **byte 10**. O runner passou a Python 3.14. O byte de sistema operacional no cabeçalho gzip varia entre a geração original e Python ≥3.13; a mudança é documentada em https://docs.python.org/3/library/gzip.html#gzip.compress.

`patrimonio.verify` gera saídas temporárias e compara os bytes descomprimidos de JSON/CSV, e esquema/todos os valores/ordem dos Parquets. Imprime cabeçalhos e SHA-256 do conteúdo; não reescreve os artefatos versionados. Testes rejeitam mudança de NULL para zero ou alteração de valor Parquet. Nenhum artefato patrimonial foi trocado para fazer o CI passar. A auditoria antiga do motor também permanece arquivada; o snapshot novo fica em `docs/auditoria-reconciliacao-pr13`.

## Validação e critérios de aceitação

Resultados finais e links dos workflows/capturas são registrados no PR. Critérios: totais Coopera/Certel N/D nas visões afetadas; recortes completos mantêm observados; CSV contextual; histórico/auditorias preservados; nenhum alvo estimado publicado como observado; KNN real bloqueado sem dados comparáveis; reprodução patrimonial sem modificar artefatos; lint, tipos, testes, build e Playwright aprovados.

O E2E usa navegador real do runner com desktop, Android e iPhone de 320 px emulados; não equivale a Safari em aparelho físico. Pendências externas: painel enriquecido DIST × ano versionado e comparável, mapa de chaves/territórios, datas originais/vintages e decisão formal sobre as fontes anômalas. Presença de energia nas DS e explicação RT/AT2 da Certel dependem de evidência adicional. Nenhum cenário 2026–2030 é apresentado como previsão estatisticamente homologada.
