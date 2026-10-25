# Parecer — Fase 4: homologação assistida BDGD 2022–2025

**Data:** 24/10/2026 · **Natureza:** evidências e recomendações. Nenhuma decisão de homologação foi executada.
**Restrições cumpridas:** nenhum pipeline, checkpoint, Parquet, dado bruto, série ou pacote 2025 foi alterado. Nenhum GDB foi reprocessado e nada foi baixado. As únicas leituras de GDB foram a tabela BASE (1 registro por publicação) e a lista de camadas. A validação (`scripts/validar_fase4.py`, 29/29) confirma a preservação de 301 checkpoints, do `pipeline.py` (`d1811842211b`), do `pipeline_antijoin.py` (`e348a1afa64d`) e dos checksums do manifesto histórico.

## 1. Resumo executivo
| Estado (células DIST × ano × ativo, 11.025) | 2022 | 2023 | 2024 | 2025 | Total |
|---|---|---|---|---|---|
| HOMOLOGADO | 0 | 0 | 0 | 2.197 | 2.197 |
| COMPLETO_TECNICO | 2.028 | 1.785 | 2.108 | 0 | 5.921 |
| APTO_COM_RESSALVAS | 192 | 125 | 162 | 101 | 580 |
| PENDENTE_DECISAO | 50 | 300 | 1 | 3 | 354 |
| BLOQUEADO | 125 | 175 | 0 | 0 | 300 |
| NAO_DISPONIVEL (N/D) | 455 | 465 | 579 | 174 | 1.673 |

- **Pode ir ao dashboard agora:**
  - 2025 por DIST e Brasil, com as ressalvas indicadas;
  - 2024 por DIST e Brasil, como "completo (validação automática)";
  - 2022–2023 por DIST e painel balanceado (74 DIST em consumidores), identificando o universo.
- **Não pode:**
  - Brasil 2022–2023 como total nacional;
  - células `PENDENTE_DECISAO`/`BLOQUEADO`;
  - qualquer projeção.
- **Correção de contagem:** o catálogo tem **25** ativos, e não 26 como em documentos anteriores, que contavam o cabeçalho do CSV.

## 2. Conformidade BDGD Ordinária (`MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv`, 414 publicações)
- **Validação atual:**
  - o título exige a data completa `AAAA-12-31`;
  - o GDB exige `BASE.DAT_FNL = 31/12/AAAA` (campo regulatório correto; `DAT_EXT` nunca é usado);
  - o tipo ORDINÁRIA/EXTRAORDINÁRIA **não** é identificado em nenhum ponto;
  - as entidades do GDB não têm `DATA_BASE`.

  2025 segue a mesma regra (`bdgd_etl.py:103`, `DAT_FNL = 31/12/2025`).
- **Intervalo da BASE nas publicações em uso (374):**

  | Classe | Publicações | Detalhe |
  |---|---|---|
  | `01/01–31/12` exato | **367** | — |
  | Intervalo não anual | 6 | `DAT_INC 01/12` do ano anterior com `DAT_FNL` correto: Enel SP 2022 e 2025, Equatorial GO 2022, Amazonas 2022, EDP ES 2024, EDP SP 2024 |
  | Inconsistente | 1 | Coprel 2023, com `DAT_INC = DAT_FNL = DAT_EXT = 31/12/2023` |
  | Não verificadas | **0** | — |

- **Pares divergentes:** as 26 publicações dos 13 pares têm o intervalo anual exato e nenhuma tem tag `Extra`. São **republicações**, com carimbos de versão distintos e versão posterior geralmente de 2025, e não pares ordinária × extraordinária. Não há duplicação de catálogo (nenhum par repete o carimbo).
- **Excluídas por competência:** as 14 foram excluídas corretamente pelo `DAT_FNL`, todas `INCONSISTENTE`:
  - 9 publicadas como ano N com `DAT_FNL` de N+1;
  - Ceres 2023 com `DAT_FNL 31/12/2022`;
  - Cemig-D 2022 com `30/11/2022`;
  - Celetro 2022 com período 01/09/2022–31/08/2023;
  - Coprel 2022/2023 com datas degeneradas.
- **Tag `Extra`:**
  - 100% das 59 publicações com data-base fora de 31/12 (2019–2023), o que é consistente com bases extraordinárias de data intermediária;
  - 1 publicação 31/12 em uso de 2022 (RGE SUL);
  - **100% das 99 publicações 31/12/2025**, sem alternativa sem tag.

  As páginas públicas da ANEEL consultadas não documentam a tag. Conclusão: **nenhuma contaminação comprovada** por base extraordinária. O tipo regulatório segue `NAO_COMPROVADO_DOCUMENTALMENTE`, com evidência forte de ordinária anual em 367 + 26 publicações.

## 3. Os 13 pares duplicados (ordem de impacto) — `DECISOES_DUPLICATAS_13_PARES.csv`
| # | Ano/DIST | Distribuidora | Ativos com diferença | Risco | Recomendação técnica |
|---|---|---|---|---|---|
| 1 | 2023/5381 | Cedrap | 14 | ALTO | Inconclusiva: B é posterior, A mais coerente com os vizinhos |
| 2 | 2023/404 | Energisa MS | 1 | MÉDIO | Inconclusiva |
| 3 | 2022/2866 | Copel-Dis | 1 | MÉDIO | Sugere-se B |
| 4 | 2023/86 | Eflul | 2 | MÉDIO | Sugere-se B |
| 5 | 2022/86 | Eflul | 1 | MÉDIO | Sugere-se B |
| 6 | 2023/5279 | Cerci | 1 | MÉDIO | Inconclusiva |
| 7 | 2023/6585 | Energisa Minas Rio | 1 | MÉDIO | Inconclusiva |
| 8–13 | 2023: 32, 369, 380, 5216, 6587, 6600 | Energisa TO, RO, EDP ES, Energisa Sul-Sudeste, SE, PB | 0 | BAIXO | Sem impacto nos 25 totais; sugere-se B (posterior) |

## 4. Os 20 sinais temporais mais críticos — `RANKING_ANOMALIAS_TEMPORAIS.csv`
| # | Distribuidora | Ativo | Anos | Valores | Categoria | Confiança |
|---|---|---|---|---|---|---|
| 1 | Cemig-D | chaves | 2023→2024 | 380.878 → 1.346.117 | alteração de classificação | plausível |
| 2 | Cemig-D | chaves | 2024→2025 | 1.346.117 → 581.779 | alteração de classificação | plausível |
| 3 | Equatorial MA | reatores | 2022→2023 | 35 → 59 | variação real | hipótese |
| 4 | Cemig-D | bancos de capacitores | 2023→2024 | 5.961 → 2.545 | recadastro (baixa persistência de COD_ID) | plausível |
| 5 | Elektro | rede AT (km) | 2022→2023 | 10.822 → 2.495 | ~22 mil segmentos AT de 2022 saem sem migrar para MT | hipótese |
| 6 | Equatorial PA | chaves | 2022→2023 | 196.052 → 472.207 | classificação | plausível |
| 7 | CEEE Equatorial | trafos de medida | 2024→2025 | 8.861 → 48.162 | inclusão de registros | hipótese |
| 8 | Copel-Dis | chaves | 2023→2024 | 538.721 → 257.374 | classificação | plausível |
| 9 | Equatorial MA | chaves | 2022→2023 | 96.958 → 323.566 | classificação | plausível |
| 10 | Equatorial PI | chaves | 2022→2023 | 49.820 → 256.467 | classificação | plausível |
| 11 | Celesc-Dis | torres | 2022→2023 | 5.035 → 16.688 | inclusão de registros | hipótese |
| 12 | Equatorial MA | seccionalizadores | 2023→2024 | 1.175 → 0 | sem evidência | — |
| 13 | **Equatorial GO** | **consumidores** | **2024→2025** | **3.471.824 → 23.203** | **anomalia de fonte: 3.449.443 UCBT `DS`** | **marcação comprovada; erro de cadastro = hipótese** |
| 14 | Equatorial AL | chaves | 2022→2023 | 15.016 → 150.454 | classificação | plausível |
| 15 | Equatorial GO | seccionalizadores | 2022→2023 | 988 → 0 | reclassificação de atributo | hipótese |
| 16 | CPFL Paulista | circuitos AT | 2022→2023 | 481 → 206 | recadastro | plausível |
| 17 | Equatorial GO | trafos de medida | 2022→2023 | 34.235 → 15.977 | recadastro | plausível |
| 18 | Neoenergia Brasília | disjuntores | 2023→2024 | 1.009 → 2.036 | sem evidência | — |
| 19 | Equatorial GO | barramentos | 2023→2024 | 2.706 → 1.267 | recadastro | plausível |
| 20 | **Equatorial GO** | **geradores** | **2024→2025** | **134.597 → 1.991** | **UGBT/UGAT sem registros no GDB 2025** | **comprovada** |

**Casos específicos investigados (evidências em `evidencias/investigacao_casos.json`):**
- **Enel CE, consumidores 2024→2025 (+65%):** explicação plausível.
  - Em 2025 houve recadastramento: os COD_ID das UCBT foram totalmente recodificados (0 coincidências com 2024).
  - Os registros `DS` caíram de 1,68 mi para 174 mil.
  - Os valores de 2023–2024 (~2,4 mi) provavelmente estão subestimados (2022: 3,23 mi `AT`).
- **Cooperzem, iluminação:** causa comprovada.
  - O PIP de 2024 tem 1.545 pontos, todos presentes em 2023 e em 2025.
  - 4.966 dos 5.040 pontos de 2023 reaparecem em 2025, portanto a publicação de 2024 está incompleta.
- **Elektro, rede AT 2022→2023:** hipótese.
  - Em 2022 eram 32.789 segmentos, 10.822 km e 372 circuitos; em 2023, 10.531 segmentos, 2.495 km e 164 circuitos.
  - 10.278 dos segmentos de 2023 já existiam em 2022.
  - A rede MT cresce só 660 km.
- **Equatorial GO 2025:** a marcação `DS` está comprovada na fonte. A UGBT também está vazia.
- **Coopera 2025:** a UCBT está sem registros, causa comprovada.
- **Certel 2025:** os trafos de medida estão sem registros na entidade de origem.
- **Classificação de chaves:** 25 sinais têm mudança da parcela sem TUC acima de 5 p.p. ou quebra marcada.

**Distribuição dos 238 sinais:**

| Categoria | Sinais |
|---|---|
| Variação real plausível | 95 |
| Base pequena | 78 |
| Alteração de classificação | 25 |
| Alteração cadastral | 25 |
| Sem evidência | 9 |
| Anomalia de fonte | 6 |

Por confiança: 5 comprovadas, 1 mista, 103 plausíveis, 42 hipóteses e 87 sem explicação.

## 5. Sucessões — `PONTES_SUCESSOES_HISTORICAS.csv`
- **EPB ← EBO:** as áreas são disjuntas (8 × 67 conjuntos). Nas **duas** publicações da EPB 2023, os ativos principais equivalem a 0,99–1,02 × (EPB 2022 + EBO 2022), contra 1,07–1,17 × EPB 2022 isolada (`evidencias/absorcao_epb_ebo_2023.csv`). Há evidência quantitativa forte de absorção, mas a ponte segue **pendente** de decisão. Se aceita, o perímetro 2022 da EPB passa a somar a EBO (+15% em consumidores).
- **EMR ← ENF:** os 5 conjuntos da ENF já estão na EMR em 2022 (`ja_incluida`). A ENF fica **fora de qualquer agregado** para evitar dupla contagem.
- **EMR ← EMG:** é renomeação com o mesmo código (6585), sem ponte. O mesmo vale para Enel GO → Equatorial GO (6072).
- **DIST sem 2025:** Cooperaliança, Ceres e Cerci (2022–2023), além de EBO e ENF. Não há evidência de sucessora nos dados, então essas DIST permanecem apenas na série original.

## 6. Decisões humanas necessárias
1. **Pares com impacto nos totais (7):**
   - Cedrap 2023, Energisa MS 2023, Cerci 2023 e Energisa Minas Rio 2023: recomendação inconclusiva;
   - Copel-Dis 2022, Eflul 2022 e Eflul 2023: sugere-se B.
2. **Pares sem impacto (6):** confirmar a versão posterior (decisão em bloco).
3. **Ponte EPB ← EBO:** aceitar ou não (evidência forte).
4. **Anomalias comprovadas (recomendação: bloquear):**
   - Coopera, consumidores 2025;
   - Equatorial GO, geradores 2025;
   - Certel, trafos de medida 2025;
   - Cooperzem, iluminação 2024.
5. **Equatorial GO, consumidores 2025:** manter com ressalva destacada ou bloquear.
6. **Coprel 2023 (BASE degenerada):** manter ou excluir.
7. **Seis intervalos não anuais:** aceitar como base anual.
8. **Tag `Extra`:** confirmar o significado com a ANEEL para o ciclo 2025 e para a RGE SUL 2022.
9. **Brasil 2022–2023:** confirmar o uso exclusivo do painel balanceado.
10. **Sinais temporais:** revisar as 42 hipóteses e os 9 casos sem evidência; os 78 de base pequena são de baixa prioridade.

## 7. O que impede a homologação nacional completa
- 2022 e 2023: 13 pares pendentes e 14 publicações de outra competência (com a Cemig-D 2022) deixam 7 e 19 DIST fora.
- A ponte EPB ← EBO está pendente.
- O tipo regulatório não está comprovado documentalmente, já que a tag `Extra` não tem documentação.
- Há anomalias de fonte em 2024–2025.

## 8. Sequência recomendada para a Fase 5 — integração controlada
1. Registrar as decisões 1–8 num arquivo versionado (`DECISOES_HUMANAS_FASE4.csv`, com responsável e data), sem editar as fontes.
2. Gerar um **contrato de dados** a partir da matriz (estado, `valor_nd`, motivo, universo) e um validador que bloqueie o build se um N/D virar zero ou se uma célula pendente entrar em soma.
3. Exibir na Evolução os estados e ressalvas (selos, tooltips, painel balanceado com universo), sem mudar números.
4. Reaplicar as decisões pela cadeia (79 → validador), regenerar a matriz e repetir os testes da Fase 4.
5. Preview, revisão humana e só então homologação 2022–2024. Merge e deploy apenas com autorização explícita.

## 9. Limitações
- A persistência de COD_ID é medida no nível da entidade, sem o filtro do ativo: indica recadastro, mas não prova a causa.
- A classificação dos sinais é indicativa.
- A recomendação técnica dos pares não é homologação.
- O significado da tag `Extra` não foi documentado.
- A data de publicação vem do carimbo de versão do título e da data de criação do item no ArcGIS. Os itens históricos foram recriados em lote em 10/2025, então a data de criação pouco informa.
