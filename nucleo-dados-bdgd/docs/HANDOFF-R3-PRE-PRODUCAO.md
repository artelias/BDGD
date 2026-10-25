# Handoff R3 — pré-produção (Claude → auditoria ChatGPT)

**Data:** 23/10/2026 · **Responsável pelo produto:** Arthur Henrique Elias de Lima · **Escopo do Claude na R3:** Explorar Ativos, Matriz Nacional, Comparador, ETL complementar/cubos e Evolução Histórica. Panorama, IASC/destaques, Previsões, Metodologia e Design ficaram com o ChatGPT (PR #6), conforme a divisão registrada no PR #4 e na issue #5. **Nada foi publicado em produção.** Sem merge em `main`, sem force push, sem promoção de deploy e sem alteração em outros projetos Vercel.

## 1. PR, branch e commits

| Item | Valor |
|---|---|
| PR | https://github.com/artelias/BDGD/pull/4 (rascunho) · base `feat/nucleo-dados-bdgd-portal` |
| Branch | `feat/dashboard-bdgd-2025` (ponto de partida R3: `d54f7d3`) |
| Commits R3 | `bf5310f` ETL R3 (cubos por conceito, UC v3, inventários) · `e1ea395` Explorar R3 · `086adfb` Matriz R3 · `b88291f` Comparador R3 · `54baa30` Evolução R3 · commit final com séries atualizadas, contrato de dados e este handoff (ver `git log`) |
| Contrato de integração com o PR #6 | `docs/R3-CONTRATO-DADOS-ATIVOS-E-SERIES.md` |

## 2. ETL 2025 complementar

- **Catálogo semântico único** (`etl/bdgd2025/config/conceitos_2025.json`): 17 conceitos, 26 ativos nomeados, 10 KPIs padrão e menu por conceito físico. É a fonte de Explorar, Matriz, Comparador e Evolução.
- **`77_conceitos.py`:**
  - Monta um cubo conjunto **exato** por conceito (GROUP BY de todas as dimensões). Qualquer combinação de filtros sai da soma de linhas de um mesmo cubo, sem multiplicar percentuais.
  - Os atributos de instalação (localização, município, alimentador, subestação, conjunto, nível) chegam aos equipamentos pela tabela UN* **deduplicada por código**. Código ambíguo vira `AMBIGUO`, e equipamento sem destino vira `SEM_VINCULO`, ambos como categorias explícitas.
  - Cada cubo é reconciliado com o total da fonte.
- **Regra UC v3:**
  - **Unidade:** chave (COD_ID anonimizado SHA-256, PN_CON), somente `SIT_ATIV = AT` (DDA TSITATI: Ativada), unida entre UCBT/UCMT/UCAT.
  - **Resultado:** 90.252.218 unidades ativas nas 99 distribuidoras, nenhuma N/D. A regra v2 descartava 22 tabelas, às vezes por uma única repetição.
  - **Evidências:** Copel (repetições = mesma UC com troca de classe) e DIST 5160 (ligações distintas sob o mesmo código), detalhadas no contrato de dados.
- **Inventários por vínculo oficial:** 7.792 subestações, 27.883 alimentadores, circuitos AT e 3.147 conjuntos, cada um com seus ativos associados (UCs ativas, transformadores e potência, rede MT/BT/AT, chaves, religadores, disjuntores, reguladores, capacitores, IP, geradores, barramentos e bays).
- **Pacote:** `output-publicavel/2025-12-31` com `conceitos/`, `ativos_totais.csv`, `inventario/`, `qa_uc_regra_v3.csv` e `qa_conceitos.csv`. Release `bdgd-2025-12-31-v1-99d-2f6fa3879a`, status **homologado**, todos os critérios verdadeiros (inclui `conceitos_r3_em_todas`).
- **Validador:**
  - Recalcula os **2.562 totais por ativo** a partir dos cubos.
  - Exige que todos os cubos de um conceito somem o mesmo total.
  - Reconcilia os ativos de entidade única com o fato-base R2.

Totais nacionais (2025):

| Ativo | Total |
|---|---|
| UCs ativas | 90.252.218 |
| Rede MT | 3.146.152 km |
| Rede BT | 1.750.884 km |
| Rede AT | 146.559 km |
| Transformadores de distribuição (TUC 565) | 6.103.972 |
| Transformadores de força (TUC 570) | 9.659 |
| Transformadores de medida (TUC 575) | 746.074 |
| Chaves (TUC 160) | 5.268.771 |
| Religadores (TUC 345) | 207.693 |
| Disjuntores (TUC 210) | 30.918 |
| Reguladores | 49.670 |
| Bancos de capacitores (TUC 125) | 42.844 |
| Medidores | 105.036.802 |
| Postes | 55.835.576 |
| Torres | 358.145 |
| Iluminação pública ativa | 21.126.745 |
| Geradores ativos | 3.927.337 |

**Decisões de população** (documentadas no catálogo e no "Como é calculado?"):
- Medidores, reguladores e iluminação: toda a tabela, porque a própria entidade já é o ativo.
- Chaves, disjuntores, religadores, capacitores e transformadores: TUC do MCPSE. Os equipamentos sem TUC ficam visíveis como "Código … (sem correspondência no MCPSE)" e em "Outros dispositivos". A auditoria de TUC 000 continua adiada.
- Postes e torres: `TIP_PN` do DDA, que concorda com TUC 255 e A1 01/02 e também cobre postes com TUC 000.

## 3. Telas (checklist)

| Tela | Estado | Observação |
|---|---|---|
| Explorar Ativos | OK | Conceito clicável primeiro (21 itens de menu), sem escolher tabela. Tipos TUC/A1/DDA descobertos nos dados. Quantidade e potência separadas, filtros com combinação só quando há cubo exato, gráfico e tabela com unidade. Escopo Brasil / Grupo (todas ou algumas DIST) / várias DIST. Participação no escopo e no Brasil com denominadores homogêneos. "Onde estão instalados" para transformadores. Inventário de SUB/CTMT/CTAT/CONJ com ativos associados e CSV. Visão técnica R2 por entidade no modo avançado. Perdas e balanço mantidos |
| Matriz Nacional | OK | Colunas = ativos com nome de negócio e unidade própria. Sem controles globais de medida. Filtro e medida alternativa dentro de cada coluna (mesmo motor do Explorar). Seleção múltipla com favoritos, grupo, DIST, UF, chips, ordenação, transposição e CSV com recorte, unidade, status, motivo e regra |
| Comparador | OK | Abas Tabela / Gráficos / Radar num único espaço, com só a aba ativa renderizada. Gráfico de diferença (%) e barras espelhadas preservados. O ativo e as características escolhidas valem para A, B e benchmarks (Brasil, maior grupo, maior distribuidora, lado B), recalculados no recorte. Mais de 100% permitido |
| Evolução histórica | PARCIAL (dados) / OK (experiência) | Três modos de escopo, multi-DIST, linhas ou mapa de calor, valores ou índice 100, publicação original ou perímetro 2025, variação, CAGR e ano a ano só quando definidos, tabela e CSV com o estado de cada ano. Valores 2022–2024 aparecem apenas para células validadas |
| Panorama, IASC, Previsões, Metodologia, Design | fora do escopo do Claude | PR #6 (ChatGPT). Dependências de dados descritas no contrato |

## 4. Evolução histórica — estado real

ETL histórico (runner do Codex) retomado com checkpoints, sem reprocessar 2025. Na estabilização, o limite do DuckDB caiu para 768 MB (`run.py --wait --memory-mb 768`, log `logs/run5.stdout.log`), porque a reserva de RAM de 1.024 + 384 MB travava o runner em `RESOURCE WAIT`.

| Competência | No início da R3 | Fechamento do processamento (24/10/2026) |
|---|---|---|
| 2022 | 74/99 processadas | 95 de 102 validadas · 5 com BASE de outra competência · 2 pares sem equivalência (decisão humana) |
| 2023 | 62/89 | 83 de 101 validadas · 7 com BASE de outra competência · 11 pares sem equivalência (decisão humana) |
| 2024 | 76/97 | 97 de 97 validadas · status `completo_tecnico` (validação automática completa, **sem** homologação humana) |
| 2025 | — | 99/99, homologado |

**Nenhum item em falha.** Todos os itens publicados foram processados ou têm motivo documentado (`qa_itens_auditoria.csv`, por ano/DIST/item: registros, hash do pipeline, origem ArcGIS, SHA-256 da fonte, estado na série e motivo).

**Memória:** 8 itens grandes (Enel SP 390 e Neoenergia Coelba 47 em 2022–2024; Cemig-D 4950 em 2023–2024) estouravam 768 MB na checagem de vínculos órfãos (`NOT IN` sem uso de disco). A consulta foi reescrita como `LEFT JOIN` contra chaves `DISTINCT`, com resultado idêntico, conferido em 2 distribuidoras de controle. Mesmo assim, esses itens só concluíram com DuckDB a 1.536 MB, necessidade registrada nos `failure.oom_*.json` preservados. A correção ficou em `pipeline_antijoin.py` (cópia em `etl/bdgd2025/historico_patch/`). O `pipeline.py` original segue intacto, porque o runner valida o hash dele em cada checkpoint. Checkpoints: 261 do original (`d1811842211b`) e 40 do `pipeline_antijoin.py` (`e348a1afa64d`), todos íntegros. Uma tentativa de alterar o `pipeline.py` levou o runner a reprocessar tudo; foi interrompida após 3 itens pequenos (Cersad), já registrados com o novo hash.

**Equatorial GO 2022 (6072):** o ZIP traz dois GDBs (`Enel_GO_…` e `Equatorial_GO_…`). `equivalencia_gdb_duplo.py` comprovou equivalência integral nas 43 camadas (esquema, contagem, atributos e geometria). O item foi processado com o GDB do controlador vigente, e a escolha está registrada em `gdb_escolhido.json` (evidência: `evidencia_6072_gdb_duplo.json`).

**Consistência temporal** (`qa_consistencia_temporal.csv`): de 5.904 pares ano-a-ano validados, 238 têm variação acima de 50% ou indo a/de zero. Destes, 20 são explicados por quebra de classificação marcada e 218 ficam para revisão: geradores (GD em expansão), ativos de contagem pequena e transformadores de medida. **Por isso nenhuma competência histórica é declarada homologada**; 2024 está completo tecnicamente, com sinais a revisar. A classificação dos 238 sinais está em `qa_sinais_temporais_classificados.csv`: 56 são variação real plausível (expansão da GD), 25 são alteração de classificação (quebra marcada ou parcela sem TUC mudando mais de 5 p.p.), 1 é sucessão societária (EPB), 2 são anomalia da fonte (Equatorial GO e Coopera, consumidores 2024→2025) e 154 não têm evidência suficiente (77 com base menor que 50 unidades e 77 a verificar, por exemplo Enel CE com +65% de consumidores em 2025, Cooperzem com iluminação oscilando 5.040 → 1.545 → 5.249 e Elektro com rede AT caindo 77% em 2023). A classificação é indicativa e nenhum valor foi corrigido.

**Status do ano (`cobertura_por_ano.csv`, `manifest.json`, `serie.json`):** `homologado` exige decisão humana registrada (hoje só 2025); `completo_tecnico` indica todas as publicações elegíveis validadas pelas regras automáticas; `parcial` indica que há pendências. O antigo `homologado_tecnico` foi substituído por `completo_tecnico`, e o validador agora rejeita o rótulo antigo e qualquer ano histórico marcado como `homologado`. Na tela, o agregado Brasil continua aparecendo em anos `homologado` ou `completo_tecnico` (`anoCompleto()` em `lib/evolucao.ts`), e o rótulo exibido é "completo (validação automática)".

- **Mesma regra:** `78_conceitos_historico.py` aplica o próprio `77_conceitos.py` ao Parquet histórico, sem cópia de regras.
- **Quebra de classificação:** `79_serie_historica.py` marca quando a parcela sem TUC muda mais de 10 p.p. Exemplo: CEA, chaves de 3.697 em 2022 para 19.131 em 2024, efeito de recadastro e não de crescimento físico.
- **Publicações múltiplas (regra revisada pelo responsável em 24/10/2026):** totais idênticos nos 26 ativos **não** provam equivalência. Duas publicações do mesmo DIST/ano só são tratadas como uma quando o SHA-256 é igual ou quando `equivalencia_duplicatas.py` comprova, entidade por entidade, que coincidem: esquema, número de registros, identidade dos COD_ID, impressões por grupo de atributos (identidade, TUC/MCPSE, DDA, vínculos CTMT/SUB/CONJ/PAC/UNI_TR e demais), registro completo e geometria (WKB lido do GDB original). O OBJECTID é ignorado. A impressão de cada conjunto é (n, soma mod 2^64, XOR) de blake2b-64 por registro. Sem prova integral, a célula fica em `revisao_pendente` para decisão humana, e o detalhe vai para `qa_publicacoes_multiplas.csv` e `proc/ANO/DIST/equivalencia_duplicatas.json`. Enquanto algum item do par não foi processado, a célula fica `nao_processado`; nunca se usa uma publicação isolada do par.
- **Sucessões verificadas nos dados:**
  - EMR ← ENF (2022): os 5 conjuntos da ENF já estão na EMR. A ENF **não é somada**, e a EMR 2022 representa o perímetro (587.601 UCs ativas).
  - EPB ← EBO (2022): conjuntos disjuntos (8 e 67), mas a absorção em 2023 ainda não foi verificada porque a EPB 2023 tem duas publicações. Fica **pendente**.
- **Grupos 2022–2024:** sempre na composição de 2025, identificada na tela.
- **Agregado comparável:** o "painel balanceado" usa só distribuidoras com os quatro anos validados. O "Brasil" só aparece em anos homologados.

**Para completar as séries:** deixar a cadeia terminar (`D:\NUCLEO_BDGD_2025\logs\cadeia_historico.log`; memória e erros DuckDB em `logs\monitor_historico.log`). Para pausar com segurança, criar `D:\NUCLEO_BDGD_2022_2024\STOP_REQUESTED`. Depois, copiar `D:\NUCLEO_BDGD_2025\output-historico\2022-2025` e `web/public/data/historico/serie.json` para o repositório e rodar `validate-serie-historica.mjs`. Para refazer manualmente, a ordem é: `duplicatas_historico.py` (venv do histórico, `--memory-mb 768`), `78_conceitos_historico.py`, `equivalencia_duplicatas.py`, `79_serie_historica.py` e o validador.

## 5. Testes (local, antes do commit final)

Rodada de estabilização (24/10/2026, árvore deste commit): ESLint e TypeScript sem erros · Vitest 57/57 · smoke do contrato OK · validador 2025 OK (somente avisos conhecidos de rollup de potência EQTRAT) · release dos assets igual ao manifesto, `data_base` 2025-12-31 · validador da série histórica OK · build OK · Playwright + axe 45/45. A rodada anterior está abaixo.

| Etapa | Resultado |
|---|---|
| ESLint / TypeScript | sem erros |
| Vitest | 57/57 (motor de cubos, participação dupla, medida inaplicável, radar genérico 75%/125%/37,5%, evolução: base zero, quebra, painel balanceado, soma sem parcial) |
| Smoke do contrato, validador 2025 (R3) e validador da série histórica | OK |
| Build estático | OK (9 rotas) |
| Playwright + axe | 45/45 (desktop e celular; acessibilidade em 7 rotas claro/escuro; R3: 21 conceitos do menu, consistência Explorar = Matriz = Comparador no mesmo recorte, participação dupla, combinação sem cubo bloqueada, inventário e CSVs, abas do Comparador, benchmark recalculado com filtro, Evolução sem valores fabricados) |

## 6. Capturas
`docs/screenshots/r3/`: Explorar (transformadores; religadores rurais na Energisa; alimentadores da CEA), Matriz com colunas filtradas, Comparador (radar filtrado e barras espelhadas) e Evolução (multi-DIST e mapa de calor do grupo), em desktop e celular, claro e escuro.

## 7. Erros e limitações conhecidos
- Paridade com o BI VPE: não avaliada (PBIX ausente), sem bloqueio.
- Município: disponível nos conceitos com o campo `MUN` (consumidores, geradores, IP, estruturas e equipamentos via instalação). Redes não têm o campo.
- Geradores: sem fonte e tipo de sistema (TSIST ausente do DDA M10) e sem potência homologada.
- Potência de transformadores de força: N/D em 28 distribuidoras (código sem correspondência no DDA TPOTAPRT).
- Nomes de linhas AT com caractere perdido na conversão de origem aparecem com "·".
- `e2e/app.spec.ts` foi alterado de forma mínima, removendo testes R2 superados que viraram `e2e/r3.spec.ts`. Pode haver conflito simples com o PR #6, que também editou esse arquivo.

## 8. Segurança e privacidade
- Somente agregados. Nenhum COD_ID de consumidor ou gerador, endereço, CPF ou credencial.
- Os inventários publicam código e nome de infraestrutura (subestação, alimentador, circuito, conjunto), que são dados públicos da BDGD. Fica como decisão explícita para o auditor.
- Nenhuma dependência nova instalada nem recurso pago criado.
- A skill externa sugerida (ECC/search-first) **não** foi instalada; a política Search First foi seguida manualmente.

## 9. Preview, CI e rollback
- Projeto Vercel `nucleo-dados-bdgd` (`prj_yO3RCoffttr3LSnLP5quAyU26uej`), somente preview, proteção inalterada. URL da branch: https://nucleo-dados-bdgd-git-feat-dash-7286b5-arthurhenriqueelias-6367.vercel.app
- Preview de `54baa30` (`dpl_47Z52ZjmY3GFu8tmg5mU7oTXUov1`) READY e verificado com navegador autenticado em 8 rotas R3: nenhuma resposta 4xx/5xx, nenhum erro de console, release homologado servido. Os previews dos commits seguintes saem automaticamente na mesma URL da branch.
- CI: workflow `nucleo-bdgd-web.yml` com gates obrigatórios do pacote 2025 e da série histórica.
- Rollback: não promover o preview. O último estado R2 é `d54f7d3`.

### 4.1 Teste real da equivalência integral (24/10/2026)
A auditoria apontou `struct_pack()` com argumentos posicionais em `digital()`. No DuckDB 2.0.0 instalado, a forma posicional roda quando os argumentos são colunas simples, mas depende da inferência de nomes e não escapava identificadores nem o caminho. Foi substituída por `struct_pack("col" := "col", …)`: colunas em ordem alfabética, aspas internas duplicadas em `ident()` e caminho com aspas simples escapadas em `literal()`. O esquema passou a ser comparado sem depender da ordem das colunas.

Teste com dados reais da DIST 11825 (`etl/bdgd2025/tests/teste_equivalencia_real.py`), numa raiz isolada já apagada. Em todos os casos o SHA-256 dos arquivos é diferente:

| Caso | O que muda | Resultado |
|---|---|---|
| A | publicações reais 2023 × 2024 | **divergente**, 111 diferenças em identidade, TUC, DDA, vínculos, demais atributos e geometria |
| B1 | mesmo GDB reempacotado (outro ZIP) | **equivalente** |
| E | colunas do Parquet em outra ordem, mesmo conteúdo | **equivalente** |
| C | TUC de 1 registro de EQTRMT trocado | **divergente** só em `EQTRMT.grupo_tuc_mcpse` e `EQTRMT.registro` |
| D | 1 ponto de PONNOT deslocado 1e-6° | **divergente** só em `PONNOT.geometria` |
| B2 | GDB reescrito pelo GDAL, sem edição | **divergente** só na geometria de 10 camadas. As coordenadas mudaram ~1e-9° ao serem regravadas na grade de precisão do GDB, ou seja, é mudança real de bytes da geometria. A regra estrita exige revisão humana nesse caso |

## 10. Compatibilidade com o PR #6 (sem merge)
- Simulação feita com `git merge-tree --write-tree` entre esta branch e `feat/chatgpt-r3-panorama-iasc-previsoes` (`4db9cc9`, base comum `d54f7d3`): **nenhum conflito textual**. O único arquivo editado pelos dois lados é `web/e2e/app.spec.ts`, mesclado automaticamente.
- Árvore combinada testada num worktree descartável, já removido, sem commit em nenhuma branch: TypeScript e ESLint sem erros · Vitest 66/66 · build estático OK · Playwright + axe **41/45**.
- As 4 falhas também acontecem **no PR #6 sozinho** (`4db9cc9`) e não nesta branch sozinha, e o job "Lint, tipos, testes, build e E2E" do PR #6 está em falha no GitHub:
  - axe `dlitem` (serious) em `/metodologia/`, claro e escuro: `#modelo-matematico … > dt` fora de `<dl>` em `Metodologia.tsx`;
  - `map-ready` fica `false` no Panorama (testes "mapa ARAT, KPIs e seleção" e "clique fora das áreas volta ao Brasil").
- Dependências entre as frentes: o PR #6 consome `public/data/2025-12-31/*` (pacote 2025 inalterado) e não lê `conceitos/`, `inventario/` nem `historico/serie.json`. As rotas `/explorar`, `/matriz`, `/comparar` e `/evolucao` são deste PR e funcionam na árvore combinada.

## 11. Arquivos que precisam de decisão humana
| Arquivo | Decisão |
|---|---|
| `output-historico/2022-2025/qa_duplicatas_reconciliadas.csv` (tabela única dos 15 pares; detalhe em `qa_publicacoes_multiplas.csv` e `proc/ANO/DIST/equivalencia_duplicatas.json`) | 2 pares com competência única válida (Cerci 2022, Coprel 2023): nada a decidir. 13 divergentes: escolher a publicação ou manter fora da série. Em 6 deles (Energisa TO, RO, Sul-Sudeste, SE e PB e EDP ES, todos 2023) a diferença está só em registros e atributos e não muda nenhum dos 26 totais; os outros 7 mudam totais (Cedrap 2023: 14 ativos; Eflul 2023: 4) |
| `output-historico/2022-2025/qa_sucessao.csv` (`EPB_EBO_2023`) | Inclusão da EBO 2022 no perímetro da EPB. Depende do par de publicações da EPB 2023 |
| `cobertura_por_ano.csv` (`competencia_divergente`: 2022 = 5, 2023 = 7) | Arquivos publicados com BASE.DAT_FNL de outra competência. Ficam fora, a menos que haja republicação |
| `web/public/data/2025-12-31/inventario/*.json` | Publicação de códigos e nomes de SUB, CTMT, CTAT e CONJ (dado público da BDGD, nenhum dado de consumidor) |
| **Ressalva** do pacote 2025, Equatorial GO (6072), consumidores = 23.203 | No GDB oficial de 31/12/2025, a UCBT tem 3.449.443 registros com `SIT_ATIV='DS'` (desativada) e 13.492 com `'AT'`; a UCMT tem 9.711 `AT` e 61 `DS`. Em 2024 eram 3,47 mi UCs ativas. A regra UC v3 conta só `AT`, então o número segue a regra, mas indica provável erro de cadastro da distribuidora. **O valor não foi alterado.** Decidir: manter com alerta visível, marcar `bloqueado` ou consultar a ANEEL ou a distribuidora. Afeta o total Brasil 2025 de consumidores e a série. Caso semelhante: Coopera 28.141 → 225 |
| `qa_sinais_temporais_classificados.csv` (238 sinais, 218 sem quebra marcada) | Revisar antes de homologar 2022–2024, priorizando as 2 anomalias da fonte e os 77 casos sem evidência com base relevante. Correção: Energisa PB (6600) 2023 **não é zero**; é uma célula `revisao_pendente`, porque o ano tem duas publicações válidas divergentes e falta a decisão humana (uma versão anterior deste handoff dizia "= 0" por erro de leitura) |
| PR #6: `Metodologia.tsx` e Panorama (mapa) | Corrigir as 4 falhas de E2E/axe do PR #6 antes da integração (frente do ChatGPT; não alterada aqui) |

## 12. Decisões humanas para homologar 2022 e 2023
1. **Publicações múltiplas divergentes** (`qa_duplicatas_reconciliadas.csv`): escolher uma publicação ou excluir o DIST/ano da série. 2022: Eflul (86) e Copel-Dis (2866). 2023: Energisa TO (32), Eflul (86), Energisa RO (369), EDP ES (380), Energisa MS (404), Energisa Sul-Sudeste (5216), Cerci (5279), Cedrap (5381), Energisa Minas Rio (6585), Energisa SE (6587) e Energisa PB (6600). Nos 6 pares em que os 26 totais coincidem, a escolha não altera o painel.
2. **Sucessão EPB ← EBO (2022):** depois da escolha da publicação da EPB 2023, confirmar se a EBO 2022 entra no perímetro 2025 da EPB (conjuntos disjuntos 8 e 67; absorção ainda não verificada).
3. **Competência divergente** (2022: 5; 2023: 7, entre eles Cemig-D 2022): aceitar a exclusão desses DIST/anos, ou buscar republicação na ANEEL. Sem isso, o agregado Brasil 2022/2023 permanece incompleto e só o painel balanceado é comparável.
4. **Sinais temporais** (`qa_sinais_temporais_classificados.csv`): aceitar ou recusar os 154 casos sem evidência suficiente, a começar pelos 77 com base relevante, e confirmar as 25 alterações de classificação como quebra de série.
5. **Critério do agregado Brasil 2022–2023:** publicar apenas o painel balanceado ou exigir cobertura completa.

## 13. Fase 5A — Evolução integrada à matriz de homologação (24/10/2026)
- **Dados:** `etl/bdgd2025/86_homologacao_web.py` gera `web/public/data/historico/homologacao.json` a partir dos artefatos versionados em `auditoria/fase4/`, sem reprocessar GDB nem alterar checkpoints. O asset traz o estado de publicação de cada uma das 11.025 células (25 ativos × 441 DIST-ano), os agregados Brasil e painel balanceado, a proveniência por publicação (item ArcGIS, versão, BASE, tag `Extra`, SHA-256), os sinais temporais, os 13 pares e as pontes. Os textos de apresentação são legíveis; a matriz continua sendo a fonte de verdade.
- **Gate:** `etl/validate-homologacao-web.mjs` (no CI) confere o SHA-256 das fontes, o estado de cada célula, que nenhuma célula não publicável tenha valor, que o Brasil 2022–2023 nunca apareça como total, que somas e painel batam com as células publicáveis (excluída a ENF 2022) e que os 13 pares sigam `PENDENTE`.
- **Página Evolução:**
  - seleção de família e ativo;
  - escopos Brasil, Grupo e Distribuidoras, com comparação de até 8 linhas;
  - Brasil e painel balanceado vindos da matriz;
  - selos de estado e ressalvas;
  - natureza das variações (expansão física × mudança cadastral × classificação × anomalia);
  - cobertura e qualidade por estado e parcela sem TUC;
  - proveniência até o catálogo ANEEL;
  - decisões pendentes, com a recomendação técnica marcada como "não é homologação";
  - sucessões com a evidência de absorção EPB ← EBO;
  - CSV com estado, motivo e publicação.
- **Recortes por TUC/atributos 2022–2024:** não exibidos, porque os cubos históricos não foram homologados. A página indica Explorar (2025).
- **Capturas:** `docs/screenshots/fase5/`.
