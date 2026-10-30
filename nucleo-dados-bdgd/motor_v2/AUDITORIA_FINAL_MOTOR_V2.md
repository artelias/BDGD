# Motor V2 — auditoria final da execução nacional (2026-10-30)

O estado é **experimental e interno**. Nenhuma previsão foi homologada.

O que **não** foi feito nesta revisão:
- novo processamento nacional integral ou repetição dos 20.571 candidatos de ML;
- aquisição de bases;
- alteração do contrato nacional, dos produtos públicos ou do dashboard;
- merge ou deploy.

Base: commit `d4982e8`. O estado anterior está preservado em `D:/NUCLEO_BDGD_2025/motor_v2/nacional/_v1_d4982e8/`.

| Arquivo | Conteúdo |
|---|---|
| [`reports/nacional/`](reports/nacional/) | artefatos compactos |
| [`nacional/METODOLOGIA.md`](nacional/METODOLOGIA.md) | metodologia atualizada |
| `D:/NUCLEO_BDGD_2025/motor_v2/nacional/` | artefatos completos |

## O que foi reexecutado (somente o afetado)

| Componente | Motivo | Escopo | Tempo |
|---|---|---|---|
| Nível B, revisão 1 | política única de elegibilidade (estoque × transição) | 947 de 2.850 séries (assinatura de insumos diferente da regra legada); demais mantidas | 58 min |
| Nível B, revisão 2 | sucessão societária não é transição comparável | 469 séries | 17 min |
| Comparativos do nível A | ponte experimental da Celesc 2023 | Celesc mais 121 alvos dependentes, nos 5 ativos: 10 lotes de no máximo 16 DIST; 1.489 candidatos de ML com 7.631 ajustes externos e 60.155 de seleção interna; 10 de 10 concluídos na 1ª tentativa | 59 min |
| Projeção A | reaproveita os comparativos vigentes; só refaz o ajuste final e os cenários | 516 decisões | 5 min |
| Envelopes dos cenários (A e B) | triagem v2 | todas as séries; a trajetória moderada é lida e mantida | < 1 min |

- **Determinismo.**
  - 12 séries não afetadas, recalculadas pela regra nova, reproduziram exatamente as decisões da v1.
  - 6 séries afetadas, recalculadas pela regra legada, também reproduziram as da v1.
- **Rastreio das alterações.** O comparativo antes/depois (`ANTES_DEPOIS_*`) atribui cada alteração a uma causa e não encontrou nenhuma alteração sem causa.
  - 873 séries mudaram: elegibilidade v2 (745), só o envelope v2 (75), ponte da Celesc (27), sucessão (22) e política de estoque (4).
  - A trajetória moderada só mudou em séries com insumo alterado.

## 1. Divergência A × B e sua resolução (Enel SP, DIST 390)

**Causa.**
- As 30 células `INTERVALO_NAO_ANUAL` (6 publicações × 5 ativos) eram usadas no nível A e excluídas no nível B.
- A Enel SP 2025 tem `dataBase` 31/12/2025, `estado` observado e `BASE.DAT_FNL` correto. Apenas o `DAT_INC` está em 01/12/2024.
- A regra antiga do nível B descartava o estoque válido de 31/12 por causa disso, e a âncora B da Enel SP caía para 2024.

**Resolução: política única, sem alterar o contrato** (`nacional/elegibilidade.py`).
- **Estoque elegível:** `observado` ou `zero_verificado`, `dataBase` = 31/12 da competência e somável.
  - `INTERVALO_NAO_ANUAL` passa a ser **ressalva**, não exclusão.
  - Uma célula `nao_somar_em_agregados` não entra: Energisa Nova Friburgo 2022, incorporada pela Energisa MR. O nível A passou a bloquear suas 4 séries (antes eram projetadas com âncora 2022, mas já ficavam fora dos totais).
- **Transição elegível:** os dois estoques elegíveis, 31/12 consecutivos, sem ruptura no contrato e sem incorporação oficial (`eventos_sucessao.csv`) efetivada entre as datas-base.
  - Essa última condição corrige a Energisa PB 2022 → 2023 (`EPB_EBO_2023`, +222.783 clientes da Borborema), que o nível B tratava como crescimento orgânico (deriva de 6,1% ao ano).
  - O nível A já retinha essas unidades pela ponte de perímetro.
- **Evidência empírica** (25 conceitos, mediana ± 5 MAD com piso de 0,02):
  - 7,7% das 196 transições que tocam células `INTERVALO_NAO_ANUAL` são atípicas, contra 8,0% das 6.107 demais.
  - 12 das 15 atípicas são da Amazonas Energia 2022 → 2023, um degrau de nível da publicação 2022 (estável de 2023 em diante). A Equatorial GO, com a mesma BASE de 31 dias, não mostra esse degrau.
  - Sem a Amazonas, 1,7% (`AUDITORIA_INTERVALO_NAO_ANUAL.csv`).

**Comparação de conceito (mesma coorte de DIST).**
- O A conta só a tabela UCBT; o B conta a união de UCBT, UCMT e UCAT, deduplicada pela regra UC-v3.
- A auditoria UC-v3 do próprio ETL, sobre a mesma publicação, fecha **exatamente** os 385 pares DIST × ano em que há auditoria e valor nos dois níveis: A = UCBT ativas, B = união (`RECONCILIACAO_AB_CONSUMIDORES_DIST_ANO.csv`).
- Enel SP 2025: A = 8.200.759; B = 8.215.027 = A + 14.080 UCMT + 188 UCAT.

| Coorte comum (98 DIST, âncora 2025) | Nível A (UCBT) | Nível B (consumidores) | B − A |
|---|---|---|---|
| 2025 observado | 89.932.832 | 90.251.993 | 319.161 = 318.422 UCMT + 2.029 UCAT − 1.290 em mais de uma tabela |
| 2030 conservador | 87.326.180 | 87.620.142 | 293.962 |
| 2030 moderado | 93.112.341 | 94.715.778 | 1.603.437 |
| 2030 agressivo | 106.236.504 | 105.983.865 | −252.639 |

**Origem do B − A de 2030 no cenário moderado.**
- 0,32 milhão é diferença de conceito na âncora.
- 1,28 milhão vem de **modelos de crescimento diferentes**, escolhidos independentemente em cada nível. 11 das 98 DIST diferem em mais de 1 ponto percentual de CAGR.
- Principais contribuições:

| DIST | A | B | Diferença em 2030 |
|---|---|---|---|
| Enel SP | 0,25% ao ano (OLS territorial) | 2,44% ao ano (CAGR) | +0,95 milhão |
| Copel | persistência | 1,4% ao ano | +0,38 milhão |
| Enel RJ | persistência | 1,9% ao ano | +0,28 milhão |
| Light | −1,2% ao ano | −3,0% ao ano | −0,33 milhão |

- Essa diferença é das escolhas por nível e foi mantida, não forçada: harmonizar o modelo exigiria uma regra nova, a decidir.

**Antes e depois:**
- Coorte comum: de 97 para 98 DIST (a Enel SP entrou).
- Total B moderado de consumidores em 2030: de 86,3 milhões (97 DIST) para 94,7 milhões (98 DIST).
- Por DIST: `RECONCILIACAO_AB_CONSUMIDORES_POR_DIST.csv`, com conceito, âncora, inclusão, modelo e CAGR de cada nível.

## 2. Celesc 2023 (DIST 5697): decisão, evidências e impacto

**Decisão:** ponte `MUN_RECODE_5697_2023` aplicada **somente na camada experimental derivada** (`nacional/painel`), com status `APLICADA_EXPERIMENTAL_NAO_HOMOLOGADA` (`pontes.py`, `pontes_experimentais.json`).
- A extração, o staging e o contrato não foram tocados.
- O arquivo do painel antes da ponte está preservado byte a byte em `painel/_originais_ponte/`, com SHA-256 conferido. A fonte da extração continua com o hash original `04d1ef47…`.
- `preparar.py` reaplica a ponte, com as mesmas verificações, se o painel for reconstruído.

**Verificações (todas exigidas, todas passaram):**
- Correspondência unívoca: 275 códigos para 275 destinos distintos, cada um com prefixo único.
- Nenhuma colisão com código já presente no arquivo.
- 275 de 275 destinos são códigos IBGE válidos.
- Totais de todas as colunas numéricas preservados; 2.821 linhas.
- Só as 2.821 linhas com código mapeado mudaram; as demais colunas ficaram idênticas linha a linha.
- Nenhuma chave duplicada criada.
- Continuidade: mesmo conjunto de 275 municípios em 2022, 2023 e 2024. Clientes de 2023 sobre 2022 por município: p1 = 0,991, mediana = 1,015, p99 = 1,077.
- **Evidência cruzada:** nos transformadores TUC 565 da mesma publicação (`UN.MUN`), os códigos de 2023 já são IBGE oficiais. Os 275 destinos estão todos lá, e 100% dos clientes ficam em municípios com transformador. A ponte não se aplica a esses arquivos e os deixa intactos.
- **Excesso de quarentena corrigido:** os ativos por conjunto (redes MT e BT) também estavam em quarentena, embora não dependam do código municipal.

**Impacto no nível A** (a Celesc passou de 1 para 2 origens medidas):

| Ativo | Modelo antes → depois | WAPE do modelo de projeção antes → depois | Moderado 2030 antes → depois |
|---|---|---|---|
| UCBT | persistência → CAGR | 3,15% → 1,02% | 3.554.543 → 4.051.317 |
| Transformadores, quantidade | persistência → deriva | 2,53% → 0,98% | 205.647 → 230.563 |
| Transformadores, kVA | persistência → deriva | 5,35% → 1,74% | 9,40 milhões → 11,68 milhões |
| Rede MT (km) | persistência → deriva | 1,08% → 0,44% | 86.705 → 91.233 |
| Rede BT (km) | persistência → deriva | 0,73% → 0,58% | 71.488 → 71.898 |

- Em nenhum dos 5 ativos o melhor ML supera o melhor baseline. Exemplo: no UCBT, `ols:individual` tem score robusto 146,0 contra 140,0 do CAGR.
- Dos 121 alvos dependentes:
  - 22 tiveram apenas o score do ML alterado;
  - 2 mudaram a escolha experimental (DIST 47: `ols:comparaveis` → `poisson:comparaveis`; DIST 5346: nenhum → `elastic_net:comparaveis`, ambos em transformadores);
  - 2 mudaram apenas a trajetória moderada (DIST 37 e 2866, que mantiveram o ML escolhido, reajustado com a Celesc no pool);
  - os demais ficaram idênticos.
- Detalhe em `DEPENDENCIAS_CELESC.json` e `ANTES_DEPOIS_SERIES.csv`.

## 3. Auditoria dos cenários extremos

**Diagnóstico da triagem v1.** As 535 transições que a regra v1 (só mediana ± 5 MAD do corte nacional) excluía foram reclassificadas pela triagem v2:

| Classe v2 | Transições | Tratamento na v2 |
|---|---|---|
| Degrau isolado | 205 | sai |
| Sem ano seguinte | 137 | sai do envelope central; entra na sensibilidade |
| Típica para o próprio porte | 72 | volta |
| Reversão | 49 | sai |
| Evidência de variação real (fase 4) | 46 | volta |
| Persistente | 26 | volta |

- No total, 144 transições excluídas sem fundamento voltam ao envelope. Entre elas estão 7 de geração distribuída, que a v1 cortava.

**Triagem v2 adotada** (`cenarios.py`): evidência da fase 4 (persistência de `COD_ID`) primeiro; depois objeto × ano × **porte** (tercil do estoque em t−1); depois o padrão temporal do salto.
- Exclui 434 das 7.629 transições: 224 degraus isolados, 155 sem ano seguinte e 55 reversões.
- A trajetória moderada não muda.

**Sensibilidade dos totais 2030** (agressivo; conservador entre parênteses):

| Objeto | Sem triagem | v1 MAD nacional | **v2** | v2 + não verificáveis | v2 K = 3 | v2 K = 8 | v2 sem evidência |
|---|---|---|---|---|---|---|---|
| A UCBT (milhões) | 117,8 (81,6) | 105,6 (87,3) | **106,2 (87,3)** | 108,0 (87,3) | 100,7 (88,8) | 113,2 (84,2) | 106,2 (87,3) |
| A kVA de transformadores (milhões) | **750,7** (198,3) | 245,3 (213,3) | **245,4 (213,3)** | 246,1 (212,9) | 244,9 (213,3) | 251,2 (204,7) | 245,4 (213,3) |
| B consumidores (milhões) | 118,3 (81,9) | 106,0 (87,6) | **106,0 (87,6)** | 108,4 (87,6) | 101,0 (89,0) | 113,7 (84,6) | 106,0 (87,6) |
| B geradores (milhões) | 36,7 (9,9) | 32,2 (9,9) | **36,7 (10,5)** | 36,7 (10,3) | 36,7 (10,8) | 36,7 (9,9) | 33,6 (10,5) |
| B religadores (mil) | 747 (213) | 387 (240) | **372 (240)** | 733 (213) | 353 (240) | 408 (240) | 355 (240) |

**Leitura da sensibilidade:**
- Os 752 milhões de kVA da primeira execução continuam sendo o caso "sem triagem". A v2 chega a 245 milhões pelo padrão temporal (degraus e reversões), não por divergência do corte nacional.
- A v2 preserva o crescimento legítimo da geração distribuída (36,7 milhões no agressivo), que a v1 cortava para 32,2 milhões.
- O agressivo de UCBT e de consumidores é sensível a K: entre 100,7 e 113,7 milhões para K de 3 a 8. Religadores são sensíveis aos não verificáveis: 372 mil contra 733 mil.

**Crescimento anual implícito, mediana por série com âncora 2025** (conservador / moderado / agressivo):

| Objeto | Conservador | Moderado | Agressivo |
|---|---|---|---|
| A UCBT | 0,68% | 1,28% | 2,62% |
| A kVA | 1,98% | 2,93% | 4,98% |
| B consumidores | 0,88% | 1,54% | 2,67% |
| B geradores | 15,7% | 16,1% | 47,5% |

- A variação acumulada 2025–2030 de cada série e cenário está em `AUDITORIA_CENARIOS_SERIES.csv`.

**Séries extremas.** Limiares só de relato, nada é limitado:
- Agressivo ≥ 2× a âncora: 231 séries (A: 2; B: 229). 98 são de geradores, 36 de religadores, 23 de transformadores de medida e 18 de reguladores.
- Conservador ≤ 0,5× a âncora: 17 séries.
- 645 séries têm no máximo duas transições comparáveis (A: 114; B: 531). Seus envelopes repousam em uma ou duas observações.

**Participação de DIST no excesso agressivo** (`AUDITORIA_CENARIOS_PARTICIPACAO_DIST.csv`):

| Série | DIST | Participação |
|---|---|---|
| B seccionalizadores | Celesc | 95,6% |
| B torres | DIST 86 | 72,5% |
| B reguladores | DIST 31 | 54,4% |
| A kVA | Copel | 24,9% |
| A UCBT | DIST 43 | 15,0% |

**Cenários condicionais propostos (documentados):**
- Os cenários são hipóteses de ritmo sustentado, não intervalos.
- A v2 trata saltos não sustentados como mudança de nível: o nível fica na âncora, mas o ritmo não é repetido por 5 anos.
- Os parâmetros (K = 5, piso de MAD 0,02, tercis de porte, ≥ 5 empresas por referência) e a sensibilidade a cada um estão nos arquivos `AUDITORIA_CENARIOS_*`.

## 4. Política para `INTERVALO_NAO_ANUAL`

Ver a seção 1. Em resumo:
- **Estoque:** elegível, com ressalva `intervalo_base_nao_anual`. A competência regulatória é `DAT_FNL` (31/12), e `DAT_INC` delimita só o período dos campos de fluxo.
- **Transição:** elegível com a mesma ressalva, salvo ruptura ou sucessão.
- A política vale igualmente para os níveis A e B, e o contrato não é alterado.
- A decisão humana pendente da fase 4 sobre produtos públicos **não** é tomada aqui.

## 5. Matriz de potências (`MATRIZ_POTENCIAS.csv`, `POTENCIA_POR_DIST_ANO.csv`)

- Leitura das publicações do contrato: 104 DIST × 4 competências (386 DIST-ano), em 5 min.
- Nenhuma conversão é feita entre kVA, kW e kVAr.

| Família | Grandeza | Campo / domínio | Registros | Código válido | Status |
|---|---|---|---|---|---|
| Transformadores de distribuição (TUC 565) | aparente, kVA | `EQTRMT`/`EQTRAT.POT_NOM` → TPOTAPRT; UN em kVA, ou MVA × 1000 | 22,5 milhões | 99,998% | experimental, em uso no nível A (99 DIST com ≥ 2 competências no gate). 2025: 204,1 GVA pelo equipamento, 202,1 GVA pela instalação |
| Transformadores de força (TUC 570) | aparente, kVA | idem; `POT_F01`/`POT_F02` (ventilação forçada) não somadas | 37.050 | 99,91% | **liberação experimental proposta**: 72 DIST com ≥ 2 competências no gate (todo código válido e quantidade igual à do contrato). 2025: 183,6 GVA pelo equipamento, 177,5 GVA pela instalação (−3,4%). Série ainda não projetada |
| Transformadores de medida (TUC 575) | **não aplicável** | `EQTRM` não tem campo de potência | 2,45 milhões | — | não aplicável: transformador de instrumento, sem potência de transformação. Quantidade confere com o contrato em 385 de 386 DIST-ano. 4 registros TUC 575 cadastrados em `EQTRMT`/`EQTRAT` têm `POT_NOM` e foram registrados |
| Reguladores | aparente, kVA (DDA) | `EQRE.POT_NOM` → TPOTAPRT; `COR_NOM` é corrente (A) | 172.035 | 99,98% | **bloqueado por semântica não homogênea**: valores misturam potência própria (138–833 kVA) e passante (1.300–7.000 kVA), com p10/p50/p90 = 276/1.750/4.200 kVA. A soma nacional 2025 (315,8 GVA) supera toda a transformação de distribuição (204,1 GVA), então não é estoque aditivo |
| Bancos de capacitores | reativa, kVAr | `UNCR*.POT_NOM` → TPOTRTV | — | — | semântica registrada; fora do escopo |
| Geradores | ativa, kW | `UG*.POT_INST` | — | — | semântica registrada; fora do escopo |

- **Liberação dos reguladores:** classificar cada registro por `POT_NOM` contra √3 × tensão do circuito × `COR_NOM` (TCOR), e liberar só as DIST com convenção única comprovada.
- O catálogo passa a distinguir `liberacao_experimental_proposta`, `nao_aplicavel` e `bloqueado`.

## 6. Totais nacionais reconciliados e identificados

- Cada total em `TOTAIS_NACIONAIS_SERIES_COMPLETAS.csv` traz `status_total`, a cobertura do estoque 2025 e as DIST de fora.
- O universo de cada objeto é toda DIST **em operação** (não sucedida) com estoque elegível em 2025 ou, se a publicação 2025 falta, com o último estoque observado como peso aproximado.
- **Só 4 de 30 totais são `COMPLETO`:** disjuntores, reatores, seccionalizadores e torres.
- Os demais são **`PARCIAL`**, porque Cooperalianca, Ceres e Cerci não têm publicação 2025 e a Coopera tem UCBT vazia em 2025:
  - cobertura de 96,7% a 99,98% do estoque 2025;
  - circuitos AT: 85,5%;
  - kVA de transformadores: cobertura desconhecida, porque o contrato não tem kVA.
- 12 códigos de sucessão (CPFL, RGE, Energisa Borborema e Nova Friburgo, Cejama) estão contidos em outras DIST e não fazem parte do universo.

**Totais 2030 do cenário moderado (todos `PARCIAL`):**

| Total | Valor | DIST | Cobertura do estoque 2025 |
|---|---|---|---|
| UCBT (A) | 93,11 milhões | 98 | 99,89% |
| Consumidores (B) | 94,72 milhões | 98 | 99,89% |
| Transformadores, quantidade (A) | 6,66 milhões | — | 99,92% |
| Rede MT (A) | 3,20 milhões de km | — | 99,94% |
| Rede BT (A) | 1,76 milhão de km | — | 99,91% |
| Geradores (B) | 11,49 milhões | — | 96,66% |

## 7. Artefatos regenerados

Só foram regenerados os artefatos afetados:
- nível B: decisões, candidatos e projeções das séries recalculadas; envelopes de todas as séries;
- nível A: projeção completa, sobre os comparativos vigentes com 10 lotes de revisão;
- consolidação, catálogo e totais.

A extração, os 34 lotes originais de comparativos e a conversão dos ZIPs foram reaproveitados sem reexecução.

## 8. Testes, verificações e hashes

- **221 testes, 221 OK** (`MATRIZ_TESTES.csv`, `MANIFESTO_TESTES.json` com SHA-256 de cada arquivo de teste e o ambiente: Python 3.12.2, scikit-learn 1.9.1). Eram 207 antes; 14 são novos, em `test_auditoria_final.py`.
  - Os novos cobrem: política de estoque e transição; sucessão; triagem v2 (típica, degrau, reversão, persistente, não verificável, evidência, porte); verificações e reaplicação idempotente da ponte; precedência das revisões; matriz de potência; regra `COMPLETO`/`PARCIAL`.
- **`VERIFICACOES_INTEGRIDADE.json`: ok.**
  - 0 contagens não inteiras e 0 valores negativos nas 36.180 linhas B, 7.680 linhas A por empresa e 377.115 linhas territoriais.
  - Ordem conservador ≤ moderado ≤ agressivo respeitada.
  - 0 falhas de reconciliação território + resíduo = empresa.
  - 2.049 agregados do painel conferem com o hash do checkpoint e com a fonte da extração; o original da Celesc está preservado.
- **Auditoria dos produtos públicos:** ok e idêntica à anterior. Nenhum arquivo em `web/`, `output-historico/` ou `output-publicavel/` foi alterado. A única pendência local é a de fim de linha em `web/src/lib/maplibre-version.ts`, anterior e fora dos commits.
- **CI Linux:** não aplicável. Nenhum workflow do repositório executa `motor_v2`, e parte das suítes lê dados locais em `D:`.
- **Hashes:** `MANIFESTO_PROVENIENCIA.json` traz contrato, inventário, quarentena, código e todos os arquivos finais.

## 9. Limitações de validação científica (o que ainda impede a homologação)

1. **Só 2 origens independentes** (2023 e 2024), contra 3 exigidas. Os scores robustos equivalem ao pior erro entre duas origens.
2. **Point-in-time sem origem elegível:** as competências 2022–2024 disponíveis são republicações de outubro de 2025.
3. **Horizonte de 2 a 5 anos não validado:** o ML repete a variação de um passo; só o horizonte de 1 ano foi medido.
4. **Cenários são hipóteses de ritmo sustentado, não intervalos.**
   - 645 séries têm no máximo duas transições.
   - O agressivo de UCBT e de consumidores varia cerca de ±6% com K, e o de religadores dobra com os não verificáveis.
5. **A × B: modelos de crescimento escolhidos independentemente.** Somam 1,28 milhão de consumidores de diferença em 2030 (moderado) na coorte comum. Harmonizá-los exigiria uma regra nova.
6. **Totais nacionais parciais:** 4 cooperativas sem estoque 2025 utilizável; circuitos AT com 85,5%; kVA sem universo verificável no contrato.
7. **Pontes e políticas experimentais, não homologadas:**
   - ponte da Celesc 2023;
   - `INTERVALO_NAO_ANUAL` como ressalva, com a decisão da fase 4 ainda pendente;
   - reconhecimento de sucessão pelos eventos oficiais.
8. **Potência:** força (TUC 570) só proposta, sem série projetada; reguladores bloqueados.
9. **`DAT_CON`:** `recent_connection_share` segue desligada; falta a auditoria por DIST.
10. **Saltos sem ano seguinte:** 155 transições, sobretudo de 2025, só serão classificáveis com a competência 2026.
