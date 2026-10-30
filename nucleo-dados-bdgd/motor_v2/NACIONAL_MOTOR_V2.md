# Motor V2 — execução nacional experimental (2026-10-30)

O estado é **experimental e interno**. Nenhum modelo foi homologado, porque há 2 origens independentes e são exigidas 3. Nenhuma previsão foi publicada, nenhum produto público foi alterado e não houve merge, deploy nem download.

A metodologia completa está em [`nacional/METODOLOGIA.md`](nacional/METODOLOGIA.md). Os artefatos compactos estão em [`reports/nacional/`](reports/nacional/). Os artefatos completos ficam em `D:/NUCLEO_BDGD_2025/motor_v2/nacional/`.

## 1. Execução efetiva

| Etapa | Escopo | Tempo | Resultado |
|---|---|---|---|
| Conversão dos 12 ZIPs do contrato | local, sem download | ~35 min no total (Cemig 2022, 4 GB: 17 min) | 12/12 convertidos, 0 com competência confirmada, 12 em quarentena |
| Extração nível A | 104 DIST, 7 lotes (6×16 + 8) | 2,79 h | 1.906 células extraídas, 23 sem valor válido de kVA, 151 indisponíveis; 0 falhas sistêmicas; 100% dos itens lidos são ordinários |
| Preparação | painel nacional, IBGE, quarentena | 70 s | 1 quarentena: Celesc 2023 (ponte pendente) |
| Comparativos nível A | 5 ativos × 34 lotes, 2 processos em paralelo | 2,01 h | 34/34 `completed` na 1ª tentativa; 18.864 experimentos |
| Nível B | 25 conceitos × 114 DIST | 49 min | 2.850 séries avaliadas |
| Projeção nível A | 516 séries | 4,4 min | 0 falhas de reconciliação |

- **RAM.** O pico de RSS por DIST na extração UCBT foi 0,885 GiB (Cemig), com o DuckDB limitado a 512 MB. Nos ativos, o pico foi ≤ 0,45 GiB.
- **DIST mais lentas.** Cemig levou 1.782 s, Enel SP 1.498 s e Neoenergia Pernambuco (47) 1.180 s.
- **Estado de cada lote.** `completed_with_errors` não é aceito como sucesso. Cada lote registra falhas por DIST × ativo × ano (`INTEGRIDADE.csv`), e os bloqueios sistêmicos interrompem a execução.

## 2. Contagens de distribuidoras (comprovadas)

| | DIST |
|---|---|
| No contrato nacional | 114 |
| No inventário local | 104 |
| Elegíveis (≥ 1 competência `observado` no contrato) | 104 |
| Efetivamente processadas (≥ 1 célula extraída) | 104 |
| Com ML treinado e avaliado (níveis A ou B) | 97 |
| Com projeção 2026–2030 | 104 (nível A: 104; nível B: 103) |

Das 104 com projeção, 98 têm âncora 2025 em UCBT. As outras 6 usam a última competência confiável (2022, 2023 ou 2024), com o horizonte real registrado.

## 3. Catálogo do Motor Universal (29 objetivos × métrica)

- **Com projeção:** 26 objetivos.
  - 25 conceitos do contrato no nível B (série por distribuidora).
  - 5 deles também no nível A territorial: UCBT ⊂ consumidores, trafo_dist em quantidade e kVA, rede MT e rede BT.
  - `trafo_dist/potencia_kva` existe só no nível A.
- **Bloqueados:** 3, com motivo registrado.
  - `trafo_forca/potencia_kva`
  - `trafo_medida/potencia_kva`
  - `reguladores/potencia_kva`
- **Séries DIST × objeto:**
  - Nível A: 516 calculadas, 0 bloqueadas.
  - Nível B: 2.412 calculadas e 438 bloqueadas: 420 sem competência utilizável no contrato (275 por sucessão societária, 145 de ativo não aplicável) e 18 por publicação ou indicador ausente.
- **Matriz:** `MATRIZ_ELEGIBILIDADE_CATALOGO.csv` traz unidade, natureza, entidades, filtro MCPSE/TUC, campos territoriais, vínculo de instalação e cobertura.

## 4. Modelos

- **Nível A.**
  - 3.700 candidatos de ML avaliados, com 18.172 ajustes externos e 139.775 ajustes da seleção interna.
  - Os escopos usam o painel nacional: individual, grupo econômico e comparáveis.
- **Nível B.** 16.871 candidatos de ML avaliados.
- **Escolhas experimentais estáveis** (≥ 5% melhores que o melhor baseline e não piores em nenhuma origem):
  - Nível A: 42 ML e 178 de tendência (deriva/CAGR). As outras 296 séries ficam com o fallback.
  - Nível B: 392 ML e 436 de tendência. As outras 1.584 séries ficam com o fallback.
- **Persistência superior empiricamente** (menor score medido): 133 séries no nível A e 847 no nível B. Nenhuma persistência que entrou por política foi contada como vitória empírica.
- **Lista completa:** `MODELOS_EXPERIMENTAIS_ESCOLHIDOS.csv`, com modelo, escopo e ganho sobre o melhor baseline.
  - Nível A: Poisson e Elastic Net no grupo econômico e OLS em comparáveis predominam. Os ganhos vão de 5,6% a 92%.
  - Nível B: Random Forest, HGB e Elastic Net em comparáveis predominam, com ganho mediano de 51%.

**Mediana do ganho do melhor ML sobre o melhor baseline** (sem filtro de estabilidade):

| Nível | Objeto | Ganho |
|---|---|---|
| A | UCBT | −2,2% |
| A | trafo, quantidade | −5,1% |
| A | trafo, kVA | −16,5% |
| A | rede MT | +3,3% |
| A | rede BT | +10,9% |
| B | rede MT | +31,5% |
| B | postes | +30,2% |
| B | trafo_dist | +20,7% |

O ML territorial raramente supera, de forma estável, as tendências por município ou conjunto.

## 5. Erros retrospectivos do modelo usado na projeção (nível A, origens 2023 e 2024)

| Ativo | Séries | WAPE mediano | WAPE p90 | Viés mediano | MAE físico mediano |
|---|---|---|---|---|---|
| UCBT (clientes) | 97 | 1,28% | 5,25% | −4,6 | 47,3 clientes |
| Trafo TUC 565 (itens) | 94 | 1,38% | 3,49% | −1,9 | 5,8 itens |
| Trafo TUC 565 (kVA) | 92 | 2,59% | 6,20% | −157 kVA | — |
| Rede MT (km) | 97 | 0,85% | 3,54% | −3,2 km | — |
| Rede BT (km) | 97 | 1,15% | 4,36% | −1,0 km | — |

- A cobertura territorial mínima mediana é 1,0.
- No nível B, o WAPE mediano fica entre 0,3% (rede MT) e 5,5% (geradores), com cauda alta em equipamentos de contagem pequena (seccionalizadores, reatores).
- Detalhe por série: `ERROS_DO_MODELO_DE_PROJECAO.csv`.

## 6. Cobertura física e territorial (âncora 2025, nível A)

| Ativo | DIST | Total físico 2025 | Na coorte territorial |
|---|---|---|---|
| UCBT | 98 | 89.932.832 clientes | 99,99997% |
| Trafo TUC 565, quantidade | 99 | 6.103.972 | 92,9% (7,1% sem vínculo bijetivo EQ→UN vão para o resíduo) |
| Trafo TUC 565, kVA | 92 | 192,8 GVA | 100% |
| Rede MT | 99 | 3.146.152 km | 100% |
| Rede BT | 99 | 1.750.884 km | 100% |

Os totais extraídos de trafo, rede MT e rede BT batem com as células do contrato nacional, com 0 diferenças materiais (só ruído de ponto flutuante).

## 7. Projeções 2026–2030

- **Volume.**
  - Nível A: 516 séries × 5 anos × 3 cenários, somando 7.740 linhas por distribuidora e 377.175 linhas territoriais (parquet interno).
  - Nível B: 2.412 séries, somando 36.180 linhas.
- **Física e reconciliação.**
  - Contagens são inteiros não negativos e km/kVA mantêm decimais.
  - Unidades territoriais mais o resíduo `NAO_TERRITORIALIZADO` = total da empresa, com 0 falhas.
- **Totais nacionais (2030, séries completas com âncora 2025):**

  | Nível | Objeto | Conservador | Moderado | Agressivo | DIST |
  |---|---|---|---|---|---|
  | A | UCBT | 86,9 mi | 92,6 mi | 105,6 mi | 98 |
  | A | Trafo, itens | 6,38 mi | 6,60 mi | 7,47 mi | 99 |
  | A | Rede MT | 3,18 mi km | 3,19 mi km | 3,58 mi km | 99 |
  | B | Consumidores | 79,8 mi | 86,3 mi | 96,7 mi | 97 |

- **Séries fora dos totais:** 29 do nível A e 576 do nível B, listadas em `SERIES_EXCLUIDAS_DOS_TOTAIS.csv`.
  - A Enel SP fica fora do total B de consumidores porque a célula de 2025 tem `INTERVALO_NAO_ANUAL` e a âncora B é 2024. Por isso o total B de consumidores fica abaixo do total A de UCBT.
- **Amplitude dos cenários.** Cada série sustenta por 5 anos o seu menor e o seu maior crescimento anual observado. Transições atípicas no corte nacional (mediana ± 5 MAD, com piso de MAD 0,02) ficam fora desse envelope: 494 no nível B, concentradas em equipamentos de contagem pequena. A trajetória moderada nunca é afetada.

## 8. Dados: bloqueios resolvidos e pendentes

- **12 ZIPs do contrato.** Todos foram convertidos, e a `BASE` de cada um desmente a competência atribuída. O contrato já marcava as 12 células como `BLOQUEADO`.
  - 9 são outra versão de uma competência vizinha.
  - 1 é de um período de teste (5343).
  - 1 traz só a data de extração (2351).
  - Cemig 2022 tem data-base 30/11/2022: competência 2022, mas intervalo não anual até 2023.
  - Nenhum entra no treino.
- **Celesc 2023.**
  - Todos os 275 códigos municipais estão gravados como `'0' + 6 dígitos`.
  - A ponte proposta mapeia 275/275 com prefixo único, sem colisão, com UFs coerentes (PR/SC), todos presentes em 2022 e 2024, 121/121 conjuntos estáveis e concordância por CONJ de 99,9999%.
  - Status: `PENDENTE_HOMOLOGACAO` (`reports/nacional/PONTE_MUN_RECODE_5697_2023_*`). A Celesc 2023 segue em quarentena.
  - Nenhum outro par (DIST, ano) passa de 2% de clientes fora do IBGE. O maior é 7019/2023, com 0,32% de códigos de 6 dígitos, que vão para o resíduo.
- **`recent_connection_share`.** Desligada em todo o processamento nacional.
- **Intervalo não anual.** 30 células do nível A (Enel SP 2022/2025, EDP ES, EDP SP, Equatorial GO e Amazonas Energia, cada uma × 5 ativos) vêm de células do contrato `observado` com `INTERVALO_NAO_ANUAL`. Elas são usadas no nível A e excluídas no nível B (`CELULAS_INTERVALO_NAO_ANUAL_NIVEL_A.csv`). A regra precisa ser harmonizada.

## 9. O que ainda impede a homologação científica

1. **Só 2 origens independentes** (2023 e 2024), contra 3 exigidas. O score robusto com 2 origens equivale ao maior MAE por origem. Validar exige a competência 2026 (origem 2025) ou um histórico anterior a 2022 comprovado.
2. **Point-in-time sem nenhum ponto elegível.** As versões 2022–2024 disponíveis em cada origem histórica não foram comprovadas, porque o acervo foi republicado em 10/2025.
3. **Horizontes 2–5 de ML.** Usam a variação de um passo mantida constante, já que não há covariáveis futuras. Nunca foram validados além de 1 ano.
4. **Decisões humanas pendentes:**
   - a ponte da Celesc 2023;
   - a regra para células `INTERVALO_NAO_ANUAL` nos dois níveis;
   - a semântica de potência de trafo_forca, trafo_medida e reguladores;
   - a auditoria de `DAT_CON` por DIST.
5. **kVA de trafo segue experimental.** Exige vínculo ≥ 98%, e 23 células ficaram sem valor válido.

## Artefatos

| Entregável | Arquivo (`reports/nacional/`) |
|---|---|
| Inventário nacional (DIST × competência × ativo/métrica) | `INVENTARIO_NACIONAL.csv` |
| Matriz de candidatos e escolhidos | `MATRIZ_MODELOS_A_TERRITORIAL.csv.gz`, `RESULTADOS_CANDIDATOS_B.csv.gz`, `DECISOES_A.csv`, `DECISOES_B.csv` |
| MAE, RMSE, WAPE, viés, erro físico, cobertura | nas matrizes + `ERROS_DO_MODELO_DE_PROJECAO.csv` |
| Features, parâmetros, função e metodologia | matrizes (`features`, `parametros`, `funcao`) + `nota_projecao` nas decisões + `nacional/METODOLOGIA.md` |
| Projeções 2026–2030, 3 cenários | `PROJECOES_A_DISTRIBUIDORA.csv`, `PROJECOES_B.csv.gz`; territorial em `D:/.../nacional/projecao/PROJECOES_A_TERRITORIAL_INTERNO.parquet` |
| Casos indisponíveis e causas | `CASOS_INDISPONIVEIS.csv`, `INDISPONIVEIS_B.csv` |
| Proveniência e hashes | `MANIFESTO_PROVENIENCIA.json` (+ `D:/.../nacional/painel/MANIFESTO_PAINEL.json`) |
| Tempos, memória, checkpoints, retomadas | `RECURSOS_EXECUCAO.json` + `D:/.../nacional/extracao/STATUS.json`, `comparativos/STATUS.json`, `PIPELINE.json` |
| Resumo nacional | `RESUMO_NACIONAL.json`, `TOTAIS_NACIONAIS_SERIES_COMPLETAS.csv`, `SERIES_EXCLUIDAS_DOS_TOTAIS.csv` |
