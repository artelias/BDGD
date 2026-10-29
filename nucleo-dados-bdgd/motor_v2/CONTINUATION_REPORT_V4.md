# Motor V2 — auditoria pré-escala (29/10/2026)

Base `8d24162`, mesma branch. Pilotos apenas em EPB (6600), EMR (6585) e EAC (26). Sem processamento nacional, sem merge, sem deploy, sem download. Nenhuma previsão foi declarada validada.

## 1. Implementação

| Prioridade | Módulo | O que foi feito |
|---|---|---|
| A. Baselines | `baselines.py`, `comparison.py` | Deriva e crescimento geométrico (CAGR) por município, avaliados **nos mesmos pontos, origens e folds** que persistência e ML. Segmento contíguo até a origem, cortado por ruptura, só com linhas elegíveis na modalidade (point-in-time ou reconciliada). Série curta, extremo não positivo, valor inválido ou previsão negativa ⇒ recuo explícito para a persistência, **contado e registrado por motivo** (`fallbacks`). O ML só é declarado vencedor se superar o **melhor baseline** (persistência, deriva ou CAGR) em ≥ 5% e com o mínimo de origens; os resumos trazem `ml_gain_vs_persistence`, `ml_gain_vs_best_baseline` e `ml_beats_best_baseline`. |
| B. Entre famílias | `shared.py`, `feature_registry.py`, `comparison.py` | Matriz de atributos por território × ano a partir dos agregados verificados por hash: município (UCBT.MUN, UNTRMT.MUN) e CONJ (UCBT, UNTRMT, SSDMT). SSDMT não tem MUN, então **a extensão da rede nunca é atribuída a município**. Transformadores e Rede MT recebem do UCBT urbanização, consumo e clientes, e entre si contagem/kVA/razões declaradas (valores de t−1, unidades originais antes do log). O próprio lag do alvo nunca é oferecido (duplicaria `log_stock`). A disponibilidade de cada feature é a da publicação de origem, e o gate point-in-time vale também para valores nos índices 0–2 que vêm de outra família. Seleção por DIST × ativo × métrica dentro do fold interno: subconjuntos obrigatórios + **seleção progressiva (forward)** opcional (`forward_selection`, `max_features`). O registro passou a 13 features. |
| C. Futuras | `future.py`, `feature_registry.py` | Auditado e reescrito: o erro anterior era projetar a taxa **no espaço log**. Agora projeta em unidade original e só depois transforma (log1p), conforme o registro (`source_variable`, `original_unit`, `transform`). Recusa unidade diferente da do registro, valor "oficial" não projetado, anos observados e fontes em conflito. Retorna `unavailable` com motivo para: sem fonte, hipótese não aprovada (exige `approved`, `approved_by`, `approved_at`), aprovada depois da origem, projeção oficial publicada depois da origem, unidade territorial incompatível e fonte não obtida. |
| D. Qualidade | `assets.py`, `comparison.py`, `audit_conj.py` | Auditoria de chaves EQ/UN (EQ duplicado, FK nulo, FK sem UN, UN compartilhada, UN duplicada, UN sem EQ 565). **Corrigido um bug**: a UN compartilhada contava o FK nulo como duplicata. Gate de cobertura territorial (soma territorial ÷ total físico e cobertura do vínculo ≥ 0,98 nos dois sentidos de ano) e gate de continuidade da unidade (`min_unit_continuity`), ambos desligados por padrão para preservar resultados. Quarentena EPB/EBO preservada (`PENDING_HOMOLOGATION`). |
| E. Validação | `origins_audit.py`, `report_matrix.py` | Levantamento de competências anteriores a 2022 no catálogo versionado e relatório por DIST × ativo × métrica × modalidade. |

**Testes: 110 OK** (66 anteriores → +44 líquidos; novos arquivos `test_baselines.py`, `test_future.py` e `test_scale.py`; os 3 testes antigos de futuras, que projetavam no espaço log, foram substituídos). Cobrem fórmulas e recuos dos baselines, contabilidade de ganho sobre o melhor baseline, matriz compartilhada, gate de disponibilidade das features cruzadas, gates de cobertura/continuidade, seleção progressiva sem olhar nada depois da origem interna, auditoria de CONJ, contagem de origens e contadores de chave EQ/UN.

## 2. Execução efetiva
- Extração `assets-3` (36 tarefas; agora com CONJ no agregado e auditoria de chaves): pico 0,14 GiB, 31 s. Chaves EQ/UN de TUC 565 em 2025: **zero** duplicatas, FK nulo, FK sem UN ou UN compartilhada nas três empresas; vínculo 100% (quantidade e potência). UN sem EQ 565 (1.422 / 1.598 / 14.368) são UN de outros tipos, não erro.
- 4 comparativos (UCBT, trafos quantidade, trafos kVA, Rede MT) × 3 empresas × 2 modalidades, com baselines, matriz compartilhada, forward selection (≤ 4 features), cobertura ≥ 0,98 e, na Rede MT, continuidade ≥ 0,95. Retomada: 108/108 candidatos reutilizados em 15 s.
- **Preservação** (hashes iguais após tudo): 12 agregados UCBT + checkpoints `585da4d176babebf`; 114 checkpoints do piloto UCBT `90169fb05589f3ba`; Parquets da extração `assets-1` `4c148fdf7951e9fc`.
- Recursos: DuckDB 1 GB, 1 thread, piso de RAM 0,6 GiB (a máquina tinha ~1 GiB livre); nenhum aplicativo seu foi encerrado.

## 3. Resultados experimentais (retrospectiva reconciliada; **não operacionais**)
Escore robusto = MAE médio por origem + desvio. Ganhos em relação ao melhor baseline entre persistência, deriva e CAGR. Point-in-time: 0 pontos elegíveis nas 12 combinações.

| Ativo (DIST) | Persistência | Deriva | CAGR | Melhor ML | Ganho ML vs persistência | **Ganho ML vs melhor baseline** |
|---|---|---|---|---|---|---|
| UCBT EPB | 1039,2 | 1164,0 | 1158,5 | ols compartilhado 1132,8 | −9,0% | **−9,0%** |
| UCBT EMR | 552,8 | 733,7 | 726,9 | poisson peers 646,1 | −16,9% | **−16,9%** |
| UCBT EAC | 1128,8 | 1370,5 | 1378,0 | ols individual 873,8 | +22,6% | **+22,6%** (44 pts) |
| Trafos qtd EPB | 8,9 | 4,4 | 4,5 | ridge compartilhado 4,4 | +50,8% | **+1,4%** |
| Trafos qtd EMR | 22,5 | 14,9 | 14,8 | poisson peers 13,7 | +39,4% | **+7,7%** |
| Trafos qtd EAC | 164,4 | 69,0 | 65,3 | ols individual 82,0 | +50,1% | **−25,5%** |
| Trafos kVA EPB* | 930,8 | 820,6 | 1078,6 | ols individual 604,2 | +35,1% | **+26,4%** |
| Trafos kVA EMR* | 835,5 | 384,8 | 366,9 | ridge individual 346,2 | +58,6% | **+5,6%** |
| Trafos kVA EAC* | 3116,9 | 1312,0 | 1214,7 | ridge compartilhado 1404,2 | +54,9% | **−15,6%** |
| Rede MT EPB† | 7,3 | 7,3 | 7,3 | ols compartilhado 3,3 | +54,5% | +54,5% (**1 origem; baselines degenerados**) |
| Rede MT EMR | 6,8 | 9,5 | 9,5 | elastic net 7,7 | −13,5% | **−13,5%** |
| Rede MT EAC† | 39,5 | 39,5 | 39,5 | ols peers 32,3 | +18,2% | +18,2% (**1 origem; baselines degenerados**, 15 pts) |

\* potência kVA é experimental. † deriva/CAGR recuaram para a persistência em todas as linhas (os gates de continuidade deixaram uma origem): não são baselines independentes.

Leitura: os ganhos de 35–58% sobre a persistência nos transformadores eram quase todos **tendência**. Contra o melhor baseline o ganho cai para 1–8% (quantidade) e fica negativo em EAC; só kVA da EPB mantém 26%. Nenhum resultado tem as 3 origens exigidas, logo **nenhum é validado**. Os ganhos de Rede MT não são evidência (1 origem, baselines degenerados).

**Variáveis efetivamente selecionadas** (`FEATURES_UTILIZADAS.csv`; "no melhor ML" = nas dobras do melhor candidato). UCBT: população, crescimento intercensitário, PIB, urbanização e energia (3–6 dobras cada). Trafos: PIB e crescimento intercensitário (6), contagem de trafos para kVA (5), população (3), kVA, energia e urbanização do UCBT (1–3). Rede MT: energia, clientes e kVA (1 dobra cada). Ser selecionada **não prova efeito**: nenhum modelo com essas variáveis superou o melhor baseline com evidência suficiente.

## 4. Continuidade do CONJ (`reports/conj/`)
Dentro de um ano o código é consistente entre entidades (100% do km de SSDMT em CONJ presentes no UCBT). **Entre anos não é contínuo:** EAC 2024 só 53% do km (SSDMT) em CONJ do ano anterior (CONJ 12590 e 12597, 8.730 km, somem; 17306–17311 surgem), EMR 2023 95% (UCBT 81%), EPB 2023 e 2024 94,7% (UCBT 87%). Conclusão: CONJ é utilizável só dentro de cada ano; entre anos exige o gate. Por isso a Rede MT por CONJ ficou com 1 origem na EPB e na EAC.

## 5. Origens históricas (`reports/origens/`)
O catálogo ANEEL versionado tem competências **anteriores a 2022**: EAC 2019–2021 (V10), EMR e EPB 2016–2021 (M6/M10/V10), com duplicatas na EPB 2021 e EAC 2020. Incluir 2021 daria 3 origens (2022–2024) e a série contígua inteira até 5–8. **Nada foi baixado ou convertido**: usar esses dados exige autorização de download, conversão GDB→Parquet, compatibilidade de DDA/TUC/identidade por layout (V10, M10, M6) e decisão sobre duplicatas. Os carimbos `_AAAAMMDD` nos títulos são candidatos a evidência de vintage (data de geração do pacote), não prova de disponibilidade pública, e não foram aplicados. O mínimo de 3 origens não foi reduzido.

## 6. Pendências
- Ampliar origens (item 5) e verificar vintages, o único caminho para validação.
- Deriva/CAGR com `baseline_min_points=2` usa um único intervalo de crescimento; vale comparar com mínimo 3 quando houver mais anos.
- Unidade CONJ depende de decisão sobre a redefinição de 2023/2024; DEC/FEC seguem sem vínculo CONJ→MUN e sem fonte.
- `future.py` está pronto e testado, mas não há hipótese aprovada nem projeção oficial: 2026–2030 retornam "indisponível".
- Ponte EPB←EBO pendente de homologação; o UCBT agora aplica a quarentena (difere do piloto anterior em 3 municípios).
- Potência kVA experimental; executor UCBT original ainda separado do de novos ativos.
