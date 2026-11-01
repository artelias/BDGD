# Motor V2 — relatório consolidado (2026-10-31)

> **Estado: experimental e interno.** Nenhuma previsão foi homologada cientificamente, publicada no dashboard ou escrita em produto público. Os números de erro abaixo são **diagnósticos retrospectivos**, não validação independente.

Este é o documento de entrada. O detalhe está em:

| Documento | Conteúdo |
|---|---|
| `nacional/METODOLOGIA.md` | metodologia completa, regra por regra |
| `NACIONAL_MOTOR_V2.md`, `AUDITORIA_FINAL_MOTOR_V2.md` | execução nacional e auditoria final (A × B, Celesc, cenários, potência) |
| `HIERARQUIA_CONSUMIDORES_MOTOR_V2.md` | reconciliação UCBT ⊂ Consumidores, erro ponta a ponta, fonte canônica |
| `REPRODUCAO_MOTOR_V2.md` | como reproduzir e como o CI é dividido |
| `COMPATIBILIDADE_PRS.md`, `integracao/pr19/` | integração com os PRs #17–#20 e patches propostos |
| `reports/nacional/` | relatórios compactos (CSV/JSON) com hashes |

## 1. Objetivo

Projetar 2026–2030, em três cenários, a infraestrutura física das distribuidoras a partir das publicações BDGD 2022–2025, em dois níveis:
- **Nível A, territorial:** município ou conjunto, a partir dos Parquets.
- **Nível B, distribuidora:** os 25 conceitos do contrato nacional.

Regras gerais: rastreabilidade de cada número até a publicação de origem, respeito à natureza física (contagens inteiras; km e kVA contínuos) e separação estrita entre pesquisa interna e produto público.

## 2. Dados utilizados

- **Contrato nacional** `output-historico/contrato-integracao/serie_fisica_nacional.csv`. Só publicações **ordinárias**, com `estado = observado` (ou `zero_verificado` no nível B), data-base em 31/12 e células somáveis.
- **Parquets BDGD 2022–2025** das 104 DIST do inventário local.
  - Os 12 ZIPs sem Parquet foram convertidos localmente; nenhum teve competência confirmada, e todos ficam em quarentena.
- **Referências:**
  - tabela municipal oficial do IBGE (SIDRA, em disco);
  - eventos de sucessão societária (`eventos_sucessao.csv`);
  - evidência por registro da fase 4 (`RANKING_ANOMALIAS_TEMPORAIS.csv`);
  - grupos econômicos em 31/12/2025.
- **Nenhuma base nova foi adquirida.** Nenhuma publicação extraordinária entra no treino, nas projeções ou em produto público (§13).

## 3. Cobertura nacional experimental

| Item | Valor |
|---|---|
| DIST no contrato nacional / no inventário local / processadas | 114 / 104 / 104 |
| DIST com ML avaliado / com projeção (A e B) | 97 / 103 |
| Séries projetadas: nível A / nível B | 512 / 2.412 |
| Objetivos × métricas do catálogo / com projeção / bloqueados | 29 / 26 / 1 (mais 1 não aplicável e 1 com liberação só proposta) |
| Candidatos de ML avaliados: nível A / nível B | 3.754 / 17.857 |
| Cobertura territorial da UCBT 2025 (soma territorial / total físico) | 99,99997% |

Os totais nacionais somam só séries completas (âncora 2025, 5 anos × 3 cenários).
- São `COMPLETO` apenas 4 objetos do nível B: disjuntores, reatores, seccionalizadores e torres.
- Todos os demais são **`PARCIAL`**, com a cobertura do estoque 2025 e as DIST de fora listadas.

## 4. Modelos e baselines

- **Baselines**, sempre sobre as mesmas linhas de teste:
  - persistência: y(T+1) = y(T);
  - deriva: y(T+1) = y(T) + (y(T) − y(T0)) / (T − T0);
  - CAGR: y(T+1) = y(T)·(y(T)/y(T0))^(1/(T−T0)).
  Quando uma tendência não pode ser calculada, o baseline cai para a persistência e o motivo é contado.
- **Modelos de ML:** OLS, Ridge, Elastic Net, Poisson (só contagens), Random Forest e HistGradientBoosting.
- **Escopos de treino:**
  - nível A: `individual`, `grupo_economico` e `comparaveis` (a DIST e as 4 mais próximas no perfil);
  - nível B: `grupo_economico` e `comparaveis` (a DIST e as 9 mais próximas). ML individual é impossível no B, porque cada série tem no máximo 2 linhas.
  - Não há pool global indiscriminado.
- **Escolha** (`nacional/selecao.py`):
  - **Score robusto:** média + desvio-padrão do MAE por origem (com 2 origens, é o maior MAE por origem).
  - **ML:** só é escolhido se for ≥ 5% melhor que o **melhor baseline** e não pior em nenhuma origem.
  - **Tendência:** só se for ≥ 5% melhor que a persistência e não pior em nenhuma origem.
  - **Caso contrário:** fallback no melhor baseline medido.
  - **`modelo_homologado`:** sempre vazio (2 origens < 3 exigidas).

Escolhas da UCBT (nível A, 103 séries): 11 ML experimentais, 43 tendências e 49 fallbacks. A persistência teve o menor erro medido em 24 séries. As demais famílias estão em `RESUMO_ESCOLHAS_POR_OBJETO.csv`.

## 5. Metodologia por ativo e métrica

**Nível A**

| Ativo / métrica | Natureza | Regra de extração | Unidade territorial |
|---|---|---|---|
| UCBT quantidade | contagem | identidade UC-v3 (COD_ID + PN_CON), ativas | município |
| Transformadores TUC 565, quantidade | contagem | EQ → UN com vínculo bijetivo | município |
| Transformadores TUC 565, kVA | capacidade (kVA) | UNTRMT kVA; UNTRAT MVA × 1000; vínculo ≥ 98% | município |
| Rede MT | extensão (km) | SSDMT.COMP / 1000 | conjunto |
| Rede BT | extensão (km) | SSDBT.COMP / 1000 | conjunto |

**Nível B:** os 25 conceitos do contrato nacional, com as regras MCPSE/TUC do ETL existente.

**Potência:** kVA, kW e kVAr nunca são convertidos entre si.
- TUC 565: em uso experimental.
- TUC 570: liberação só **proposta**.
- TUC 575: não aplicável.
- Reguladores: bloqueados.

## 6. Variáveis e equações

**Variáveis.**
- **Nível A**, sempre em t−1:
  - `log_stock`, `urban_share`, `log_energy_per_client`;
  - externas IBGE versionadas: `log_population`, `population_growth_census`, `log_gdp`, `dec`, `fec`;
  - compartilhadas entre ativos: `log_ucbt_clients`, `log_trafo_count`, `log_trafo_kva`, `log_clients_per_trafo`, `log_kva_per_client`;
  - `recent_connection_share` fica **desligada**, porque `DAT_CON` muda com troca de titularidade.
  - A seleção de features é feita numa origem interna, dentro de cada dobra.
- **Nível B:** log do estoque, log de consumidores, log de km de rede MT e o crescimento anterior comparável. O alvo é o crescimento em log1p.
- **Covariáveis futuras:** não existem e nenhuma foi inventada.

**Trajetórias (moderado).**
- Persistência: y(T+h) = y(T).
- Deriva: y(T+h) = y(T) + h·inclinação.
- CAGR: y(T+h) = y(T)·g^h.
- ML: y(T+h) = expm1(log1p y(T) + h·d), com d constante.

**Conservador e agressivo.** Deslocam o crescimento médio (em log1p) para o menor ou o maior crescimento anual das transições que passam pela triagem v2 do envelope. A triagem usa:
- a evidência por registro da fase 4;
- o mesmo objeto × ano × porte, com mediana ± 5 MAD e piso de 0,02;
- o padrão temporal (persistente fica; reversão, degrau isolado e não verificável saem).

**Contrato físico.**
- Contagens publicáveis: arredondamento half-up do valor contínuo.
- Unidades territoriais: inteiros por maior resto (Hamilton), somando exatamente o total da empresa, com o resíduo `NAO_TERRITORIALIZADO`.
- km e kVA mantêm unidade e decimais.
- A seleção de modelos usa sempre o erro **contínuo**; o erro físico (pós-arredondamento) é reportado ao lado.

**Hierarquia de consumidores.**
- Consumidores_rec = UCBT_A + round_half_up(C), com C = UCMT + UCAT − sobreposição ≥ 0.
- C é modelado pelo próprio histórico de pares compatíveis (persistência, deriva ou CAGR, com a regra do motor).

## 7. Cenários 2026–2030

São **hipóteses matemáticas condicionais** de ritmo sustentado, **não intervalos estatísticos de confiança**. A ordem conservador ≤ moderado ≤ agressivo vale por construção. Totais de 2030 (todos **`PARCIAL`**; só a coorte com âncora 2025):

| Objeto | Unidade | Conservador | Moderado | Agressivo | DIST | Cobertura do estoque 2025 |
|---|---|---|---|---|---|---|
| UCBT (A) | clientes | 87.326.180 | 93.112.341 | 106.236.504 | 98 | 99,89% |
| **Consumidores reconciliado** (A + complemento) | itens | 87.642.247 | 93.460.778 | 106.671.042 | 98 | 99,894% |
| Transformadores TUC 565 (A) | itens | 6.409.525 | 6.661.061 | 7.442.219 | 99 | 99,92% |
| Transformadores TUC 565 (A) | kVA | 213.286.945 | 216.696.491 | 245.379.290 | 92 | n/d |
| Rede MT (A) | km | 3.179.836 | 3.197.639 | 3.559.738 | 99 | 99,94% |
| Rede BT (A) | km | 1.721.106 | 1.758.079 | 2.002.999 | 99 | 99,91% |

A previsão independente de Consumidores do nível B (moderado 2030: 94.715.778) fica só como resultado independente e auditoria. A fonte canônica interna é a reconciliada (§9).

## 8. Erros retrospectivos

**Desenho comum.** Origens 2023 e 2024, horizonte de **1 ano**, três dobras territoriais por origem (unidade testada fora do treino). Modo point-in-time **sem origem elegível**.

**Erro do modelo usado na projeção:** WAPE mediano por DIST, com o percentil 90 entre parênteses.

| Nível A, por unidade territorial | WAPE mediano (p90) |
|---|---|
| UCBT | 1,27% (5,98%) |
| Transformadores quantidade | 1,36% (3,68%) |
| Transformadores kVA | 2,58% (7,47%) |
| Rede MT | 0,85% (3,69%) |
| Rede BT | 1,15% (4,56%) |

No nível B, Consumidores, por distribuidora: 0,81% (5,80%).

**Ponta a ponta, Consumidores = UCBT + complemento:** 176 células em 96 DIST.

| Variante | WAPE | Comparação pareada com o B escolhido |
|---|---|---|
| Reconciliado | 2,59% | 65 vitórias, 71 derrotas, 40 empates (p = 0,67) |
| B independente escolhido | 2,78% | — |
| Persistência / deriva / CAGR do B | 3,33% / 4,63% / 4,56% | — |

O reconciliado e o B escolhido são **estatisticamente indistinguíveis**; ambos erram menos que os baselines simples. A escolha do modelo foi feita nas **mesmas** origens, o que torna a comparação otimista.

## 9. Reconciliação física

- **Território = empresa:** soma exata para contagens e tolerância de 10⁻³ para km e kVA, em todas as séries.
- **UCBT ⊂ Consumidores:**
  - 101 células violavam a relação na previsão independente; as violações foram preservadas para auditoria.
  - Na reconciliada: **0 violações em 1.545 células (103 DIST × 15 pares únicos ano/cenário)**, inteiros ≥ 0 e cenários ordenados.
  - No histórico, 385/385 fechamentos exatos com a auditoria UC-v3.
- **Fonte canônica interna:** `consumidores_reconciliado` (`FONTE_CANONICA_CONSUMIDORES_INTERNA.json`, SHA-256 da fonte `b715c449…`). O B original nunca é usado como substituto.

## 10. Fontes e hashes

- `reports/nacional/MANIFESTO_PROVENIENCIA.json`: hashes do contrato, do inventário, da conversão dos ZIPs, de cada arquivo final e do código.
- `VERIFICACOES_INTEGRIDADE.json` (`ok: true`):
  - 2.049 agregados do painel conferidos contra os checkpoints;
  - o original da Celesc 2023 é preservado byte a byte;
  - nenhuma alteração pública foi atribuída à execução.
- As saídas da reconciliação, do erro retrospectivo e da cópia compacta dos relatórios são **idempotentes**: SHA-256 idêntico em execuções repetidas, inclusive com sementes de hash diferentes.

## 11. Limitações

- **O histórico não oferece três origens independentes de validação:** há 2 (2023 e 2024); são exigidas 3 para homologar.
- **Não existe backtest point-in-time elegível:** as versões disponíveis em cada origem histórica não foram comprovadas.
- **Horizontes maiores que um ano não foram validados.** As trajetórias 2027–2030 são extrapolação condicional.
- **Cenários não equivalem a intervalos estatísticos de confiança.**
- **Totais nacionais incompletos são identificados como `PARCIAL`**, com cobertura e DIST de fora; uma soma parcial nunca é apresentada como total nacional.
- **Extraordinárias não podem ser publicadas automaticamente** (§13).
- **Experimental, sem homologação:** a ponte da Celesc 2023, a política `INTERVALO_NAO_ANUAL`, a regra de sucessão societária e a liberação do TUC 570.
- **Complemento de consumidores:** só 4 competências por DIST; 15 DIST ficam em persistência por falta de origens.
- **Ambiente local:** o venv local carrega parte dos pacotes de outro ambiente por `.pth`. As versões efetivas ficam no `MANIFESTO_TESTES.json`. O gerador público usa scikit-learn **1.8.0** (`motor_universal/requirements-ml.txt`); com 1.9.1 o HistGradientBoosting diverge do produto publicado.

## 12. Reprodução

Ver `REPRODUCAO_MOTOR_V2.md`. Em resumo:

| Para | Comando | Onde roda |
|---|---|---|
| Suítes sintéticas | `python -m motor_v2.tests.suites` | qualquer máquina; GitHub Actions |
| Emulação do CI | `python -m motor_v2.tests.emular_ci` | máquina local, com `D:\` bloqueado |
| Auditoria completa | `python -m motor_v2.nacional.testes` | só na máquina com a base |
| Regenerar a reconciliação e os relatórios | ver `REPRODUCAO_MOTOR_V2.md` | sem retreino |

## 13. Política de publicação

- **Nada do Motor V2 é publicado.** O dashboard e os produtos públicos não leem `motor_v2/`, e o PR não toca `web/`, `motor_cenarios/`, `output-historico/` nem `output-publicavel/`.
- **Extraordinárias** (`motor_v2/extraordinary.py`):
  - `assert_public_safe` recusa qualquer item não ordinário ou desconhecido que alimente um produto público;
  - `research_path` recusa saída extraordinária sob raiz pública ou fora da raiz de pesquisa.
  Nada extraordinário é publicado automaticamente; isso exige decisão humana e homologação específica.
- **Proteção dos produtos públicos:** `verificacoes.py` reprova qualquer alteração em `web/`, `output-historico/`, `output-publicavel/` ou `motor_cenarios/` que não esteja na baseline versionada (caminho, status git e SHA-256).
- **Fonte canônica de consumidores:** interna. O contrato proíbe publicar, exibir no dashboard e declarar homologação.
- **Publicar** qualquer previsão exigirá decisão humana, homologação científica (≥ 3 origens, point-in-time) e a homologação funcional do dashboard, que é separada (responsabilidade do Codex).

## 14. Fechamento da cobertura (2026-11-01)

Sem retreinar o que já estava válido, sem nova aquisição e sem repetir os candidatos nacionais. Só foram calculadas as séries novas de potência (`potencia_b.py`, cerca de 4 min) e a classificação dos reguladores (`reguladores.py`, cerca de 1 min, leitura de EQRE/UNREMT/CTMT).

| Indicador | 6327239 | Agora |
|---|---|---|
| Universo | 114 DIST × 29 pares (B: 2.850 séries) | 114 × 30 (29 do catálogo + UCBT) = **3.420** combinações |
| Cobertura de processamento | — | **100%** (todas com estado e motivo; `BLOQUEIO_TECNICO` = 0) |
| Combinações com 15 valores | 2.412 (B) + 512 (A) | **2.707** (2.597 com âncora 2025 e 110 `SEM_ANCORA_2025`): 79,2% do universo, **97,1% do aplicável** |
| Pares do catálogo com previsão | 26 de 29 | **28 de 29** (falta só TUC 575 kVA, que é `NAO_APLICAVEL`) |
| DIST com alguma projeção | 103 | **102** (a Energisa Borborema, incorporada em 2023, deixou de ser tratada como empresa ativa) |
| Defeitos de código (classe F) | — | **0** |

Estados finais:
- `PROJETADA_BASELINE`: 1.602;
- `PROJETADA_EXPERIMENTAL`: 995;
- `SEM_ANCORA_2025`: 110;
- `SUCESSAO_SOCIETARIA`: 360 (12 códigos × 30);
- `NAO_APLICAVEL`: 273;
- `DADO_NAO_HOMOLOGADO`: 41;
- `SEM_SEMANTICA_FISICA_HOMOGENEA`: 33;
- `HISTORICO_INSUFICIENTE`: 6.

As métricas liberadas nesta etapa:
- **TUC 570 kVA:** 60 DIST, todas experimentais;
- **reguladores kVA:** 59 DIST com convenção única (55 de potência própria e 4 de passante), **sem total nacional**;
- **transformadores de distribuição kVA por DIST:** 99 DIST, vindas do nível A.

Totais 2030 nesta etapa, todos `PARCIAL`:

| Métrica | Conservador | Moderado | Agressivo |
|---|---|---|---|
| TUC 570 (kVA) | 103.926.264 | 111.442.669 | 127.036.261 |
| TUC 565 (kVA) | 213.286.945 | 216.696.491 | 245.379.290 |
| Consumidores reconciliados | 87.642.247 | 93.460.778 | 106.671.042 |

Os dois últimos são idênticos aos de 6327239.

Os coeficientes de 214 modelos lineares foram recuperados e verificados pela reprodução exata da trajetória. Os detalhes estão em `nacional/METODOLOGIA.md` (§ Cobertura definitiva e métricas de potência), `reports/nacional/MATRIZ_COBERTURA_SERIES.csv`, `AUDITORIA_COMBINACOES_SEM_PREVISAO.csv`, `LACUNAS_VERSUS_6327239.csv` e `COBERTURA_POR_OBJETIVO.csv`.

**Testes:** 256 de 256 na auditoria local (163 sintéticos e 93 locais). Na emulação do CI com `D:` bloqueado, 163 passam com 1 skip herdado.

**Produto para o dashboard:** `exportar_web.py` gera `web/data-motor-v2/` (índice e um JSON por DIST, cerca de 7 MB no total). Esse produto só entra em `public/` numa build de homologação ou preview, pelo portão `web/scripts/motor-v2-gate.mjs`. Produção continua fechada até a autorização final.
