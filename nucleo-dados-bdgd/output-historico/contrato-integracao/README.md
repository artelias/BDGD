# Contrato de integração nacional BDGD 2022–2025 (PR #4 → motor do PR #6)

Gerado por `etl/bdgd2025/87_contrato_nacional.py` e validado por `etl/validate-contrato-nacional.mjs` (no CI). Atende `docs/R3-HANDOFF-CLAUDE-FASE6.md` (branch `feat/chatgpt-r3-panorama-iasc-previsoes`).

| Arquivo | Conteúdo |
|---|---|
| `serie_fisica_nacional.csv` | 11.400 linhas: 114 códigos DIST × 4 anos × 25 conceitos, perímetro `publicacao_original` |
| `agregados_nacionais.csv` | Brasil (só anos elegíveis; 2022–2023 sem valor) e painel balanceado por ativo, com universo e exclusões |
| `pontes_sucessao.csv` | EPB ← EBO (pendente), EMR ← ENF (já incluída), renomeações |
| `esquema.json` | Campos, enums e regras de uso |
| `MANIFESTO.json` | SHA-256 de entradas e saídas, contagens e cobertura por ano |

## Estados × anos
| Ano | observado | zero_verificado | ausente | nao_homologado | nao_aplicavel | % observado sobre aplicável |
|---|---|---|---|---|---|---|
| 2022 | 1.963 | 257 | 57 | 175 | 398 | 90,5% |
| 2023 | 1.678 | 232 | 28 | 475 | 437 | 79,2% |
| 2024 | 2.011 | 259 | 129 | 1 | 450 | 94,6% |
| 2025 | 2.033 | 265 | 95 | 3 | 454 | 95,9% |

## Regras para o motor
- Treinar só com `estado` ∈ {`observado`, `zero_verificado`}. Os demais estados não têm valor e nunca viram zero.
- `fonte_homologada = true` **apenas** para `HOMOLOGADO` (pacote 2025). `COMPLETO_TECNICO` é validação automática.
- Cortar a série onde `ruptura_desde_ano_anterior = true` (classificação, cadastro, anomalia de fonte, sucessão ou variação sem explicação).
- Não somar linhas com `nao_somar_em_agregados = true` (ENF 2022, já contida na EMR). Não aplicar a ponte EPB ← EBO sem decisão.
- Brasil só com `cobertura_completa = true`. 2022–2023 nunca. Use o painel balanceado.

## Exemplos verificáveis
| ano | dist | conceito | estado | valor | causa / observação |
|---|---|---|---|---|---|
| 2024 | 390 (Enel SP) | circuitos_at | observado | 728 | ZIP `8d8bfeb472f9…` |
| 2025 | 390 (Enel SP) | circuitos_at | ausente | — | `ENTIDADE_VAZIA_NA_ORIGEM`: CTAT = 0 registros no GDB oficial 2025 (728 em 2022–2024) |
| 2023 | 5381 (Cedrap) | consumidores | nao_homologado | — | `REPUBLICACOES_DIVERGENTES` (par pendente) |
| 2025 | 5370 (Coopera) | consumidores | nao_homologado | — | UCBT sem registros no GDB 2025 |
| 2022 | 6612 (ENF) | consumidores | observado | 111.165 | `nao_somar_em_agregados = true` |
| 2022 | 70 (CPFL Mococa) | postes | nao_aplicavel | — | `SUCESSAO_SOCIETARIA`: código sem publicação desde 2017 (perímetro na DIST 69) |
