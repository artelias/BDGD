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

ETL histórico (runner do Codex) retomado nesta sessão com checkpoints (`run.py --wait --memory-mb 1024`), sem reprocessar 2025.

| Competência | No início da R3 | No fechamento deste handoff (validadas pela regra 2025) |
|---|---|---|
| 2022 | 74/99 processadas | 81 de 102 publicações validadas · 4 com BASE de outra competência · restante em processamento ou revisão |
| 2023 | 62/89 | 55 de 101 validadas · 7 com BASE de outra competência |
| 2024 | 76/97 | 0 de 97 na série (o runner tem 84 itens processados; o adaptador 78 ainda os percorre) |
| 2025 | — | 99/99, homologado |

- **Mesma regra:** `78_conceitos_historico.py` aplica o próprio `77_conceitos.py` ao Parquet histórico, sem cópia de regras.
- **Quebra de classificação:** `79_serie_historica.py` marca quando a parcela sem TUC muda mais de 10 p.p. Exemplo: CEA, chaves de 3.697 em 2022 para 19.131 em 2024, efeito de recadastro e não de crescimento físico.
- **Publicações múltiplas:** com mais de uma publicação válida no ano, a célula fica em revisão pendente, sem escolha automática.
- **Sucessões verificadas nos dados:**
  - EMR ← ENF (2022): os 5 conjuntos da ENF já estão na EMR. A ENF **não é somada**, e a EMR 2022 representa o perímetro (587.601 UCs ativas).
  - EPB ← EBO (2022): conjuntos disjuntos (8 e 67), mas a absorção em 2023 ainda não foi verificada porque a EPB 2023 tem duas publicações. Fica **pendente**.
- **Grupos 2022–2024:** sempre na composição de 2025, identificada na tela.
- **Agregado comparável:** o "painel balanceado" usa só distribuidoras com os quatro anos validados. O "Brasil" só aparece em anos homologados.

**Para completar as séries:** deixar o runner terminar (`D:\NUCLEO_BDGD_2022_2024`, log `logs/run4.stdout.log`); para pausar com segurança, criar `STOP_REQUESTED`. Depois:
```powershell
& D:\NUCLEO_BDGD_2025\.venv\Scripts\python.exe D:\NUCLEO_BDGD_2025\scripts\78_conceitos_historico.py
& D:\NUCLEO_BDGD_2025\.venv\Scripts\python.exe D:\NUCLEO_BDGD_2025\scripts\79_serie_historica.py
node nucleo-dados-bdgd/etl/validate-serie-historica.mjs nucleo-dados-bdgd/output-historico/2022-2025 nucleo-dados-bdgd/web/public/data/historico/serie.json
```
e copiar `D:\NUCLEO_BDGD_2025\output-historico\2022-2025` para o repositório. Também falta resolver as publicações múltiplas (revisão pendente) com critério documentado.

## 5. Testes (local, antes do commit final)

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
