# Regras de publicação do dashboard — série BDGD 2022–2025 (Fase 4)

Estas regras orientam a Fase 5 (integração controlada). São recomendações técnicas e não substituem a homologação humana. Fonte de verdade para leitura automatizada: `MATRIZ_HOMOLOGACAO_2022_2025.csv`.

## 1. Estados de publicação (`estado_publicacao`)

| Estado | Significado | Exibição |
|---|---|---|
| `HOMOLOGADO` | Célula do pacote 2025 (homologação vigente), com intervalo da BASE 01/01–31/12 e sem ressalva própria | Valor normal |
| `COMPLETO_TECNICO` | Validada pelas regras automáticas (2022–2024), sem sinal temporal, quebra ou ressalva de BASE. **Não é homologação** | Valor com selo "validação automática" |
| `APTO_COM_RESSALVAS` | Valor validado, mas com ressalva (quebra de classificação, sinal temporal, intervalo não anual, tag `Extra`, anomalia de fonte plausível) | Valor e ícone de ressalva; texto de `motivo` no tooltip |
| `PENDENTE_DECISAO` | Publicações múltiplas divergentes, BASE inconsistente no item em uso, ou anomalia comprovada com bloqueio recomendado | **N/D**, com "aguardando decisão" |
| `BLOQUEADO` | Arquivo de outra competência ou valor não homologável pela regra; agregado Brasil 2022–2023 | **N/D**, com o motivo |
| `NAO_DISPONIVEL` | DIST sem publicação no ano, ativo inexistente na BDGD da DIST ou campo ausente do layout | **N/D** (nunca zero) |

Colunas separadas (não combinar): `integridade_processamento` (processamento), `qualidade_indicador` (regra do indicador), `conformidade_base_intervalo` e `tag_extra_catalogo` (tipo da base), `cobertura` (publicação da DIST), `autorizacao_publicacao` (decisão humana).

## 2. Zero, N/D e pendências
1. **Zero** só aparece quando a própria série validada registra quantidade zero (`status_serie = validado` e `valor = 0`). O validador da Fase 4 confirma que nenhum zero vem de ausência.
2. Estados `PENDENTE_DECISAO`, `BLOQUEADO` e `NAO_DISPONIVEL` têm `valor` vazio e `valor_nd = sim`, e o dashboard mostra "N/D".
3. Valor pendente **nunca** entra em soma. Cada linha agregada informa `n_dist_incluidas`, `n_dist_excluidas` e a lista `dists_excluidas`.

## 3. Agregados
| Agregado | Regra |
|---|---|
| Brasil 2022 e 2023 | `BLOQUEADO` como total nacional: faltam 7 e 19 DIST (pendentes/bloqueadas), entre elas a Cemig-D 2022 (DAT_FNL 30/11/2022). `valor_soma_parcial_nao_publicar` só serve para auditoria |
| Painel balanceado | `PAINEL_BALANCEADO` por ativo: universo fixo de DIST publicáveis nos 4 anos (74 DIST para consumidores). Exibir sempre o universo e a frase "não representa o total nacional" |
| Brasil 2024 | `APTO_COM_RESSALVAS`: completo tecnicamente (97/97 publicações), com células com ressalva. Rótulo: "completo (validação automática)" |
| Brasil 2025 | `HOMOLOGADO` ou `APTO_COM_RESSALVAS` conforme o ativo. **Destacar** a ressalva dos consumidores da Equatorial GO (3.449.443 UCBT marcadas `DS` na fonte) e indicar que Coopera (consumidores), Equatorial GO (geradores) e Certel (trafos de medida) estão fora da soma, pendentes de decisão |
| Sucessões | Nenhuma soma de predecessora sem ponte comprovada. A ENF (6612) 2022 é excluída de qualquer agregado (conjuntos já contidos na EMR 6585). A EBO (6611) 2022 fica fora do perímetro EPB até a decisão da ponte |

## 4. Variações temporais
- Toda variação que envolve célula com `flags` `quebra_classificacao` ou `sinal_temporal` deve exibir bandeira e não pode ser descrita como crescimento.
- CAGR e variação acumulada só entre anos `HOMOLOGADO`/`COMPLETO_TECNICO`/`APTO_COM_RESSALVAS` da mesma DIST e mesmo perímetro.
- A série de perímetro comparável usa somente pontes comprovadas (`PONTES_SUCESSOES_HISTORICAS.csv`).

## 5. Tipo da base (BDGD Ordinária)
- Critério operacional (responsável): ordinária anual = `BASE.DAT_INC = 01/01/AAAA` e `BASE.DAT_FNL = 31/12/AAAA`. A competência regulatória é `DAT_FNL`, e `DAT_EXT` (data de extração) não define competência. As entidades do GDB não têm `DATA_BASE` (a coluna do staging 2025 é acrescentada pelo ETL).
- A tag `Extra` do catálogo ANEEL é mantida como evidência separada e **não exclui sozinha**. Ela aparece em 100% das publicações com data-base fora de 31/12 (2019–2023) e em 100% das 99 publicações 31/12/2025.
- Intervalo não anual (`DAT_INC = 01/12` do ano anterior, `DAT_FNL` correto) → `APTO_COM_RESSALVAS` até decisão.

## 6. Projeções
Nenhuma projeção é exibida como previsão validada. Não há modelo treinado (`previsoes-contrato.ts`: estado `nao_treinado`).
