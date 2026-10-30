# Motor V2 — aproveitamento integral dos dados existentes e primeiro lote controlado (30/10/2026)

Decisão do projeto: não exigir 2021 ou anos anteriores; usar os registros BDGD já disponíveis; 2022–2025 é o histórico ordinário; bases extraordinárias só para treino e pesquisa, auditadas e isoladas dos produtos públicos. Nada foi baixado, nenhum produto público ou contrato do site foi alterado, não houve processamento nacional, merge nem deploy. **Nenhuma previsão foi validada ou homologada.**

## A. Inventário dos arquivos locais (`python -m motor_v2.inventory`)

Somente metadados (recibos `*.ok.json` de 2022–2024, `conversao.json` e tabela BASE de 2025, inventários ArcGIS, contrato nacional); nenhuma página de dados lida. Saída: `reports/lote_validacao_1/INVENTARIO_PUBLICACOES_LOCAIS.csv` e `INVENTARIO_RESUMO.json`.

| Item | Valor |
|---|---|
| Publicações locais (DIST × competência × item) | 412 |
| Ordinárias (selecionadas no contrato nacional) | 399 (387 com Parquet + 12 só como ZIP bruto, sem conversão) |
| Extraordinárias | 13, todas **versões alternativas da mesma competência** (11 de 2023, 2 de 2022), publicadas em 2025-10-08 |
| Extraordinárias que são **nova observação temporal** | **0** |
| Datas-base encontradas | só 31/12 de 2022, 2023, 2024 e 2025 (nenhuma base de outra data existe localmente) |
| Não identificadas | 1 (item ArcGIS "DUP", GDB de 16 MB, DIST e competência desconhecidas; não convertido) |
| DIST com as 4 competências ordinárias em Parquet | 86 (11 com 3, 3 com 2, 4 com 1) |
| Linhas ordinárias (todas as entidades) | 1.871.303.328 |
| UCBT / SSDMT / SSDBT / EQTRMT / UNTRMT (ordinárias) | 396,9 M / 157,6 M / 153,5 M / 23,4 M / 23,0 M |
| Disponibilidade (publicação/revisão ArcGIS) | 2022–2024: out/2025; 2025: set/2026 |

Revisões × duplicatas: cada versão alternativa é comparada à ordinária entidade a entidade (linhas) e pelo checksum da origem. Diferenças pequenas (ex.: 2866/2022: −199 segmentos MT, −14 trafos; 5381/2023: +580 UCBT) estão em `delta_vs_ordinaria`; versões com contagens iguais nas entidades-chave mas checksum diferente são revisões de conteúdo, não duplicatas.

## Diagnóstico da capacidade de treinamento

1. **Profundidade temporal é o limite, não o volume.** Com estoques anuais 2022–2025 há 3 transições por DIST, mas só **2 origens de previsão com treino** (2023 e 2024): na origem 2022 não existe nenhum par (t−1 → t) anterior para treinar. As 13 extraordinárias são a mesma competência: não acrescentam origem. Logo **a exigência de 3 origens independentes não é atingível com as bases atuais**, qualquer que seja o número de registros. O treinamento experimental com 2 origens continua permitido e é rotulado.
2. **Milhões de registros dão largura, não independência.** no lote, 54 M linhas UCBT viram 3.946 unidades município × ano (no país, da ordem de 5,6 mil municípios × 4 anos); o comparativo usa agregados municipais, partições territoriais fixas (nunca aleatórias) e conta como amostra independente as **origens**, não as UCs nem os municípios. Nenhuma divisão aleatória é feita.
3. **Point-in-time continua sem ponto elegível**: todo o acervo 2022–2024 foi (re)publicado em out/2025. Os resultados são `retrospective_reconciled_NOT_operational_NOT_leakage_free`.
4. **Informação nova dentro do snapshot (implementada):** `UCBT.DAT_CON` permite medir, no próprio snapshot de t−1, a fração de UCs ativas ligadas nos 12 meses anteriores (`recent_connection_share`). É disponível na origem (mesma publicação do estoque), sem ler publicação posterior. Ressalvas medidas: inclui trocas de titularidade (10–16% das UCs/ano em várias DIST, bem acima do crescimento líquido) e é **instável entre publicações** (Celesc: 2,1% em 2023, 0,9% em 2024, 0,0% em 2025; 46/381/5368 caem à metade de 2023 para 2024). Uso como feature exige auditoria por DIST.
5. **Reconstrução de estoques anteriores a 2022 por `DAT_CON`** é possível só como série de pesquisa extraordinária (viés de sobrevivência: UCs desligadas antes do snapshot não aparecem). Não foi feita; está no plano.

## C. Isolamento das extraordinárias (`motor_v2/extraordinary.py`)

- Cada observação tem `Provenance`: item, DIST, competência, data-base, data de disponibilidade, versão, natureza, tipo, qualidade e origem.
- `assert_public_safe` recusa item extraordinário **ou desconhecido** em qualquer produto público; `assert_contract_ordinary` verifica o contrato nacional real (passa: 0 itens não ordinários).
- `research_path` só aceita saídas sob `D:/NUCLEO_BDGD_2025/motor_v2/pesquisa_extraordinaria` e recusa `web/public`, `web/src`, `output-historico`, `output-publicavel` e `motor_cenarios/{saida,entrada}`.
- `usable_at` impede uso antes da data de disponibilidade (sem retroação).
- `training_role`: versão alternativa de competência já coberta → **só sensibilidade**, nunca observação adicional; competência sem item ordinário → treino experimental sinalizado; não identificada → inutilizável. Plano por item em `reports/lote_validacao_1/PLANO_EXTRAORDINARIAS.csv`.
- O executor do lote só resolve fontes pelo contrato (ordinárias); verificado: os 44 itens lidos são todos ordinários.

## D. Executor em lotes

`motor_v2/lote.py` encadeia extração UCBT (subprocesso por DIST, limite de tempo, guarda de RAM, checkpoints anuais), extração de transformadores e rede MT, um comparativo por ativo (`pool='lote'`, manifesto explícito, máximo de 16 DIST) e o relatório. Reexecutar o mesmo manifesto reaproveita todos os checkpoints válidos; `STOP` interrompe entre etapas. O guarda de RAM passa a derivar do limite do DuckDB (+0,25 GiB).

### Lote de validação 1 (`lotes/lote-validacao-1.json`)

11 DIST (3 pilotos + 8 novas): 26, 6585, 6600, 6587, 404 (Energisa); 40 (Neoenergia); 380 (EDP; tem versão extraordinária em 2023, não usada); 5697 (Celesc); 46, 381, 5368 (pequenas). Critérios: 4 competências ordinárias, 0 rupturas no contrato, 20 mil a 3,7 M linhas UCBT/ano. São 13,6% das linhas UCBT ordinárias nacionais.

| Etapa | Tempo | Pico de memória |
|---|---|---|
| Extração UCBT (11 DIST × 4 anos, 54 M linhas) | 697 s | 0,68 GiB (DuckDB 512 MB) |
| Transformadores + rede MT | 115 s | — |
| Comparativo UCBT / trafo qtd / trafo kVA / rede MT | 628 / 589 / 415 / 226 s | — |
| **Total** | **~44,5 min** | máquina com ~0,7 GiB de RAM livre (aplicativos abertos) |

Maior DIST (Celesc, 3,6 M UCs ativas): 257 s e 0,68 GiB.

**Reexecução determinística:** o mesmo manifesto rodado de novo levou 4,3 min (contra 44,5): mesmo `runid` de extração, checkpoints anuais revalidados por hash, 2.200 experimentos de comparação reaproveitados e 0 reexecutados; `RESULTADOS_LOTE.csv` e `RESUMO_LOTE.csv` idênticos byte a byte (SHA-256).

## E. Resultados (modo retrospectivo reconciliado; `reports/lote_validacao_1/RESULTADOS_LOTE.csv`, 2.200 linhas)

Cada linha DIST × ativo × métrica × modo × candidato registra observações de treino e teste, unidades territoriais, DIST no treino, origens, período-alvo, features selecionadas, modelo, função, parâmetros, MAE/RMSE/viés/WAPE, MAE físico (contagens), WAPE do total da distribuidora, ganho contra persistência, deriva e CAGR, cobertura territorial e status. **Todas as 2.200 linhas são `experimental`; nenhuma tem 3 origens.** Point-in-time: 0 candidatos com previsão.

| Ativo / métrica | Vencedor (política) | Origens | ML ≥ 5% melhor que o melhor baseline (não validado) |
|---|---|---|---|
| UCBT / quantidade | persistência em 11 | 2 (10), 1 (Celesc) | 26, 6587, 46 |
| Trafo / quantidade | persistência em 11 | 2 (11) | 6585, 40, 46 |
| Trafo / kVA (experimental) | persistência em 11 | 2 (9), 1, 0 | 6585, 6600, 6587, 381, 5368 |
| Rede MT / km | persistência em 11 | 2 (6), 1 (5) | 26, 6600, 6587, 404, 40, 380, 46, 5368 |

Mediana do ganho dos modelos ML sobre a persistência, por escopo (candidatos com previsão):

| Escopo | UCBT | Trafo | Rede MT |
|---|---|---|---|
| Individual | −48% | −61% | −15% |
| Global do lote | −537% | −177% | −1% |
| Grupo econômico | −24% | **+34%** | −41% |
| 3 mais semelhantes | −237% | −220% | −27% |

Leitura: com 2 origens, a persistência segue como política; o pool global mistura empresas de escala e dinâmica distintas e piora muito (sobretudo UCBT); o compartilhamento **por grupo econômico** é o único escopo com ganho mediano positivo (transformadores, grupo Energisa). Features mais selecionadas: estoque, urbanização, população, `recent_connection_share`, energia por cliente, PIB. Contrato físico: arquivos de reconciliação gravados pelo gate de contagens (`write_public_csv`), contagens inteiras; extensão e potência com decimais.

### Achados de qualidade de dados
- **Celesc 2023:** `MUN` gravado como `0` + código IBGE de 6 dígitos (`0410260` em vez de `4102604`). É sintaticamente válido, mas não casa com 2022/2024: continuidade territorial 0 e perda de 2 das 3 transições. Correção determinística possível (6 → 7 dígitos pela tabela IBGE), **não aplicada** sem homologação de ponte.
- **`DAT_CON`** instável entre publicações (ver diagnóstico 4).
- 12 publicações do contrato nacional existem localmente só como ZIP sem Parquet (103/2023, 2351/2022, 2381/2022, 3223/2023, 4950/2022 Cemig, 5274/2023, 5343/2022, 5364/2023, 5371/2023, 5372/2022, 5379/2023, 6603/2023): o executor não as lê até a conversão local.

## Plano de execução nacional (não iniciado)

1. **Pré-condições:** converter localmente os 12 ZIPs do contrato (sem download); homologar a ponte de código municipal da Celesc 2023 e procurar o mesmo defeito nas demais DIST (`unit_continuity` < 0,95 no `coverage.json`); decidir se `recent_connection_share` entra com auditoria por DIST.
2. **Extração:** 104 DIST em lotes de até 16, ordenados por tamanho; DuckDB 512 MB–1 GB, 2 threads, um worker, guarda de RAM, timeout de 1 h por DIST. Estimativa linear pelo lote 1 (13,6% do volume): **~1,5 h de extração UCBT e ~15 min de transformadores/rede** para o acervo inteiro; maior DIST (Cemig, 10,6 M linhas/ano) ~13 min, abaixo do timeout.
3. **Comparativos:** por lote, com escopos individual, grupo econômico e vizinhos; o pool global só dentro de estratos de tamanho (no lote 1 foi o pior escopo). ~31 min por lote de 11 DIST → **~5 h** para 9–10 lotes.
4. **Gates entre lotes:** integridade (todos os anos com checkpoint e hash; nenhuma falha não explicada), cobertura territorial ≥ 0,98, continuidade, itens 100% ordinários, contrato físico; um lote reprovado bloqueia o seguinte.
5. **Saídas** só em `D:/NUCLEO_BDGD_2025/motor_v2`; nada vai para o site sem homologação específica.

## Bloqueios e pendências
- **3 origens independentes: inatingível** com 2022–2025; nenhuma validação temporal é possível sem nova competência ordinária (ou extraordinária de outra data, que não existe localmente).
- Point-in-time sem ponto elegível (republicação de 2022–2024 em 2025).
- Ponte Celesc 2023, conversão dos 12 ZIPs e identificação do item "DUP" pendentes.
- Processamento nacional aguarda sua autorização após este lote.
