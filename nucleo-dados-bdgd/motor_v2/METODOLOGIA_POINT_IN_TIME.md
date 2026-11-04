# Metodologia point-in-time — competência, publicação, origem e ano-alvo (29/10/2026)

Revisão da metodologia point-in-time (PIT) do Motor V2. Nenhuma data real foi alterada, nenhum dado foi baixado e **nenhum backtest é declarado validado**: as vintages (publicações datadas e revisões) **não estão provadas** para as séries usadas.

## 1. Quatro datas que não se substituem

| Conceito | O que é | Exemplo |
|---|---|---|
| **Competência** | Ano de referência do dado (data-base da BDGD) | 2023 (data-base 2023-12-31) |
| **Publicação** | Dia em que *uma versão* daquela competência ficou disponível a um usuário; uma competência pode ter várias versões (publicação inicial, revisões) | 2022 v1 em 2023-06-30; 2022 v2 (revisão) em 2024-03-01 |
| **Origem da previsão** | **Data** em que a previsão é emitida (ISO completo), não "o fim do ano da competência" | 2024-01-15 |
| **Ano-alvo** | Ano que se quer prever | 2024 |

Consequências que o código passa a impor (`motor_v2/vintage.py`):

1. Na origem só se lê, para cada competência, a **versão mais recente já publicada até a data de origem** (o dia da publicação conta como disponível; versões do mesmo dia desempatam por número de revisão).
2. **Revisões posteriores à origem são rejeitadas**, mesmo de competências anteriores. O resultado lista o que foi recusado (`rejected_later`).
3. Uma competência ainda não publicada na origem é **indisponível**, nunca estimada nem preenchida.
4. O dado do próprio ano-alvo nunca entra; se o alvo **já estava publicado** na data de origem, não há previsão: é **vazamento** (`VintageError`), assim como uma origem posterior ao ano-alvo.
5. O **horizonte efetivo** é `ano-alvo − última competência disponível`. Com origem em 2024-01-15 e a competência 2023 ainda não publicada, prever 2024 é um horizonte de 2 anos sobre a competência 2022, não de 1.
6. Datas reais não são alteradas (`Release` é imutável; as funções não modificam as entradas); datas malformadas, impossíveis ou de uma publicação anterior à própria competência são recusadas.

## 2. Evidência da data: o que prova e o que é candidato

`Release.evidence`: `publication_record` (data oficial de publicação registrada pela fonte), `generation_stamp` (carimbo de geração do arquivo) e `inferred` (reconstruída ou assumida). `vintage.claim()` só devolve `vintage_proven` quando **toda** versão lida tem `publication_record` e o modo é `point_in_time`; carimbos e datas inferidas dão `vintage_unproven` com o motivo, e `reconciled_retrospective` nunca recebe credencial PIT. Mesmo `vintage_proven` não significa "validado": a validação continua exigindo as demais condições (≥ 3 origens independentes, cobertura, continuidade).

## 3. Situação atual do motor (o que continua verdadeiro)

- `temporal.usable()` usa o relógio legado `origem-12-31` por padrão (**comportamento inalterado**). Com ele, **0 de 19 competências** das três empresas (2021–2025) foram geradas antes do fim do próprio ano, então o modo PIT do motor não produz ponto elegível: os experimentos reportados são **retrospectivos reconciliados**, rotulados `retrospective_reconciled_NOT_operational_NOT_leakage_free`.
- O inventário local (`runner.publication_map`/`investigate`) traz `publicado_em` e `atualizado_em` **atuais** de cada item; ele **não reconstrói revisões anteriores**. Logo as datas de publicação por versão não existem como prova no repositório, e a conclusão registrada permanece: *nenhuma vintage anterior elegível foi provada no inventário local; isso não prova que nunca existiu*.
- Os carimbos de geração (`plan_2021.py`) são evidência **candidata**; não foram promovidos a publicação.
- As simulações 2026–2030 seguem **condicionais, sem validação preditiva e sem intervalos**.

## 4. O que foi implementado nesta etapa

- `motor_v2/vintage.py` (biblioteca padrão): `Release`, `available`, `rejected_later`, `select`, `view`, `claim`, `iso`.
- `temporal.usable(..., origin_date=None)`: parâmetro **opcional**; sem ele nada muda. Com ele, a origem é a data explícita (ex.: 2024-07-15 admite um alvo de treino publicado nesse dia, 2024-07-14 não) e revisões posteriores continuam recusadas.
- Nenhum chamador existente (`comparison.py`, `baselines.py`, `externals.py`) passa `origin_date`; portanto resultados, seleção, hashes e checkpoints preservados.

## 5. Pendências de decisão (não tomadas aqui)

1. **Definir o relógio por data de publicação** em vez de `origem-12-31`: cada origem do backtest receberia uma data explícita (≥ publicação da última competência usada) passada por configuração a `usable`. É decisão de projeto: muda quais origens existem e, em geral, aumenta o horizonte efetivo.
2. A regra que limita as **características de treino** ao fim do próprio ano da característica (`feature_cutoff = ano-12-31` em `usable`) também usa o relógio legado e precisaria de datas por exemplo de treino.
3. **Provar as vintages**: obter, por competência e versão, a data de publicação/revisão em registro da fonte (metadados da ANEEL/histórico do portal). Requer consulta externa e **autorização** (nada foi consultado nesta etapa).
4. Só depois de (1)–(3) e de ≥ 3 origens independentes é possível discutir um backtest PIT; até lá o rótulo correto é *retrospectivo*.

## 6. Testes (`motor_v2/tests/test_vintage.py`, 18)

Competência anterior publicada e disponível na origem é usada com sua primeira versão; revisão posterior (da mesma competência ou de outra) é rejeitada e listada; a revisão só vale a partir do dia da publicação; competência ainda não publicada é indisponível; origem posterior lê versões mais novas; empate no mesmo dia por revisão; alvo já publicado e origem após o ano-alvo são vazamento; nunca se lê o ano-alvo ou posterior; datas imutáveis e malformadas recusadas; `claim()` não promove carimbo, data inferida, modo reconciliado nem leitura vazia; `usable` com `origin_date` mantém o padrão, admite o publicado até a data, recusa a revisão tardia e não abre o futuro.
