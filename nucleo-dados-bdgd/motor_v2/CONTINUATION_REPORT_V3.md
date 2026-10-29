# Motor V2 — generalização e engenharia de features (29/10/2026)

Base `16a2fb5`, mesma branch. Piloto restrito a EPB (6600), EMR (6585) e EAC (26). Sem processamento nacional, sem deploy, sem merge. Os 114 experimentos UCBT não foram recalculados.

## 1. Implementação (código e testes)

| Item | Módulo | O que faz |
|---|---|---|
| Política de cobertura/imputação | `policy.py`, `comparison.py` | `strict` (padrão, comportamento anterior) ou `coverage` (cobertura mínima **no treino** + imputação mediana/média ajustada **só nas linhas de treino**, indicador de ausência opcional). Valor que existe mas falha o gate de liberação/referência não é lacuna: a feature fica inelegível, nunca imputada. Alvo nunca imputado; zero nunca é padrão. Configurável em `feature_policy` e registrada em cada dobra (`explain`) e no resumo. |
| Registro de features | `feature_registry.py` | 8 features com população estatística, unidade, dependências, origem, fonte, regra de disponibilidade, unidades territoriais, ativos elegíveis, `future_policy` e status (`implemented` / `source_not_obtained`). `build()` mede cobertura e disponibilidade (point-in-time vs retrospectiva) no painel; gera `FEATURE_REGISTRY.csv/json` em cada comparativo. |
| Covariáveis futuras 2026–2030 | `future.py` | Cada célula tem uma única proveniência: `official_projection` (só valores marcados `projected`; nenhuma fonte integrada hoje), `scenario_assumption` (id + cenário, vindos de configuração; nunca padrão) ou `engine_estimate` (trajetória própria ou carry-forward estático explícito). Sem fonte: `unavailable`, nunca preenchido. Anos observados (≤ 2025) e fontes em conflito são recusados. |
| Ativos Rede MT e transformadores | `assets.py` | Extratores e executor (`python -m motor_v2.assets --config`) com checkpoints por ano (assinatura = fonte + hash dos Parquets + especificação), guarda de RAM e amostrador de pico. TUC 565; EQTRMT/EQTRAT ligados a UNTRMT/UNTRAT por vínculo 1:1 (EQ e UN nunca somados); unidade = `UN.MUN`; potência = `UN.POT_NOM` (kVA; UNTRAT MVA×1000), pois `EQ.POT_NOM` é código de domínio. Rede MT = `SSDMT.COMP`/1000 por `SSDMT.CONJ` (SSDMT não tem `MUN`; sem inferência espacial). Poisson só em ativos de contagem. |
| Pontes de perímetro | `bridges.py`, `bridges/EPB_EBO_2023.json` | Esquema versionado (sucessão/absorção/divisão) com status. Ponte pendente **coloca em quarentena** (como ruptura, com motivo) os municípios entrantes e sobrepostos no ano efetivo e **recusa** somar registros das duas empresas; `HOMOLOGATED` exige decisão humana registrada e sobreposições declaradas. A ponte EPB←EBO continua `PENDING_HOMOLOGATION`. |
| Recursos | `resources.py` | Guarda de RAM disponível antes de iniciar e pico de RSS/tempo em cada execução. |
| Generalização do comparativo | `comparison.py`, `features.py`, `externals.py` | `asset`, `bridges_dir` e `feature_policy` na configuração; `snapshots`/`load_panel` por ativo; externas municipais ficam indefinidas para unidades não municipais; similaridade `peers_pilot` só por estoque quando o ativo não tem urbanização (continua excluindo empresa sem urbanização quando ela existe). |

**Testes: 66 OK** (37 anteriores + 29 novos em `tests/test_generalization.py`): política estrita/cobertura, estatística ajustada só no treino, indicador de ausência, gate de liberação sem imputação, políticas inválidas; registro e elegibilidade por ativo/unidade; futuras sem invenção, conflitos e anos observados; pontes (quarentena por ano/empresa/status, soma recusada, decisão obrigatória); extratores sintéticos (TUC 565, vínculo não bijetivo, potência retida por cobertura < 98% ou valor inválido, duplicata em SSDMT); painel com quarentena; e dois testes em **Parquets reais** da EAC contra o contrato nacional (trafos TUC 565 = 48.300; Rede MT = 20.705,206 km).

## 2. Execução efetiva

- **Extração** (36 tarefas: 3 empresas × 3 ativos × 4 anos): os valores reproduzem exatamente o contrato nacional; cobertura do vínculo EQ→UN = 100% em todas; nenhuma potência inválida. Pico 0,14 GiB, 49 s. Retomada: 36/36 reutilizados em 7,7 s; Parquets idênticos aos da execução original.
- **Recursos:** a máquina tem 7,9 GiB e estava com ~1 GiB livre (Edge/Opera/ChatGPT). Não encerrei aplicativos seus. Como as extrações são pequenas, usei DuckDB 1 GB, 1 thread e piso de RAM 0,6 GiB (registrado em `assets_pilot.json`); o guarda original (3 GiB) abortou a execução antes de ajustar.
- **Comparativos** (4 execuções × 6 pares empresa/modalidade): `trafo_qty_strict`, `trafo_kva_strict`, `rede_mt_strict`, `trafo_qty_coverage`. Retomada do comparativo de Rede MT: 54 s recalculando (assinatura mudou com o código) e 9 s com 96/96 reutilizados; números idênticos entre execuções.
- **Preservação:** hashes iguais antes e depois para os 12 agregados + checkpoints UCBT (`585da4d176babebf`) e os 114 checkpoints do comparativo anterior (`90169fb05589f3ba`).

## 3. Resultados experimentais (retrospectiva reconciliada; **não operacionais**; 2 origens; nenhum modelo validado)

Escore robusto = MAE médio por origem + desvio. "Persistência" = estoque defasado.

| Ativo | Empresa | Persistência (robusto / WAPE) | Melhor exploratório | Robusto / WAPE |
|---|---|---|---|---|
| Trafos (qtd) | EPB | 8,9 / 2,8% | poisson compartilhado | 4,2 / 1,3% |
| Trafos (qtd) | EMR | 22,5 / 2,2% | ridge compartilhado | 13,8 / 2,0% |
| Trafos (qtd) | EAC | 164,4 / 7,4% | poisson individual (44 pts) | 68,0 / 2,9% |
| Trafos (kVA, experimental) | EPB | 930,8 / 9,7% | ols individual | 587,4 / 6,1% |
| Trafos (kVA, experimental) | EMR | 835,5 / 4,3% | elastic net peers | 329,4 / 1,6% |
| Trafos (kVA, experimental) | EAC | 3116,9 / 9,6% | ridge compartilhado | 1404,2 / 3,7% |
| Rede MT (km) | EPB | 8,3 / 1,2% | ols individual | 3,1 / 0,5% |
| Rede MT (km) | EMR | 6,8 / 1,0% | persistência | 6,8 / 1,0% |
| Rede MT (km) | EAC | 101,6 / 4,8% | ols compartilhado (24 pts) | 90,0 / 3,7% |

Leitura: estoques crescentes tornam a persistência um baseline fraco; qualquer modelo com tendência a supera. **Uma deriva/CAGR por município seria o baseline justo e ainda não está no comparativo V2** (existe no motor de cenários). Por isso não interpreto esses ganhos como evidência de variáveis explicativas. As externas foram selecionadas em parte dos folds (população, PIB, crescimento intercensitário), sem prova de efeito. Point-in-time continua bloqueado (0 previsões elegíveis; vintages não comprovadas). Sem intervalos de confiança.

A variante `trafo_qty_coverage` saiu **idêntica** à estrita porque a cobertura municipal das externas é 100% nesses dados; a imputação só foi exercitada nos testes com lacunas sintéticas. A quarentena da ponte EPB←EBO atuou em 9 municípios de 2023 (6 entrantes + 3 sobrepostos), sem alterar o total auditado (70.539). A elevação de ~10% nos trafos da EPB em 2022→2023 vem da mesma absorção; o modelo só vê os municípios comparáveis.

## 4. Pendências científicas e técnicas

- Baseline de deriva/CAGR por município e comparação com a persistência no V2.
- Duas origens (mínimo configurado 3, não reduzido); sem vintages históricas verificáveis do BDGD e das externas, logo sem validação operacional.
- Potência kVA é experimental (derivada fora do contrato homologado; vale só para TUC 565; 570/575 e reguladores não tratados). Rede MT usa `CONJ` como unidade: continuidade dos códigos de conjunto entre anos não auditada.
- Fontes de DEC/FEC (precisam do vínculo CONJ→MUN), SAMP, EPE, PDD e migração seguem não obtidas; `future.py` não possui nenhuma projeção oficial integrada. Geração de covariáveis futuras está implementada e testada, mas não foi usada para projetar 2026–2030.
- Ponte EPB←EBO pendente de homologação humana; o UCBT do piloto anterior não aplicou a quarentena (afeta 3 municípios sobrepostos com 21 clientes da EBO; efeito desprezível) e não foi recalculado.
- Executor UCBT original continua separado do executor de novos ativos; unificá-los exige recalcular o piloto UCBT.
- Nada foi executado fora de EPB, EMR e EAC.
