# Motor V2 — contrato físico, 2021, CONJ e estabilidade (29/10/2026)

Base `df523fa`, mesma branch. Pilotos só em EPB (6600), EMR (6585) e EAC (26). Sem merge, deploy, download, instalação ou processamento nacional. **Nenhuma previsão 2026–2030 foi declarada homologada ou validada.**

## 1. Contrato de natureza física (Prioridade 1)

### Implementado (`motor_v2/metric_contract.py`, só biblioteca padrão)
- Cinco naturezas (`discrete_count`, `continuous_length`, `continuous_capacity`, `continuous_energy`, `ratio`); a natureza vem da unidade e **unidade desconhecida é erro** (também no import de `assets.py`). Conversão de unidade só dentro de uma natureza (MVA→kVA sim; km→kVA e contagens não).
- `raw_prediction` (real, interno) e `physical_prediction` (inteiro ≥ 0 para contagens; decimal inalterado para as demais). Arredondamento **`half_up` declarado**, sobre o valor binário exato (`Decimal`): 2,5→3; 0,49999999999999994→0; o `round()` do Python (meio-para-par, `round(2,5)=2`) não é usado. Também `half_even`, `floor` e `ceil` declaráveis. Previsão negativa ou não finita é **recusada**, nunca truncada.
- Reconciliação territorial → total da distribuidora: maiores restos (Hamilton) em frações exatas, desempate por chave ascendente, soma sempre igual ao total inteiro (inclusive para totais distantes da soma bruta). Cenários: alocação **aninhada** (Conservador ≤ Moderado ≤ Agressivo por território, cada total exato); o arredondamento é monótono, então a ordem física sobrevive ao arredondamento.
- Erros: `error_pair` calcula MAE/RMSE/viés/WAPE **contínuos e físicos** nas mesmas linhas; o erro contínuo nunca é ocultado e **a seleção de modelos continua usando o contínuo**.
- Barreira de publicação: `assert_public_table`/`write_public_csv` (fração em coluna de contagem aborta antes de gravar; célula vazia = N/D).

### Integrado
- Comparativo V2: bloco `physical` por candidato (erro independente, erro reconciliado, totais por origem com `moved_by_reconciliation`), colunas físicas na matriz, `DISTRIBUTOR_RECONCILIATION.csv` **público só com inteiros** e `INTERNAL_DISTRIBUTOR_RAW.csv` com o bruto. Executor v1 (UCBT): `forecast.json/parquet` públicos com `valor` inteiro; bruto em `forecast_internal.json`.
- `motor_cenarios/cenarios.py`, `88_cenarios_exploratorios.mjs`, resumo do motor universal e a camada web (`natureza-fisica.ts`, parsers que **recusam** contagem fracionária, tooltip/tabelas/CSV).

### Auditoria do dashboard (`AUDITORIA_GRAFICOS_NATUREZA_FISICA.md`)
O Motor V2 não está publicado nem consumido por nenhuma página. O problema estava nos produtos já publicados nesta branch:

| Produto | Contagens projetadas | Fracionárias antes | Depois |
|---|---:|---:|---:|
| `cenarios-motor.json` | 16.045 | 11.394 (71%) | 0 |
| resumo do motor universal | 21.490 | 10.986 | 0 |
| cenários exploratórios | 7.550 | 4.638 | 0 |

Tooltip do gráfico com 1 casa decimal, CSV exportado e `number()` com 2 casas eram os pontos visíveis. Extensão (rede MT 21.299,924 km) e potência mantêm decimais.

### Resultados dos pilotos com o contrato (4 execuções, `comparative_v4`)
- **Estabilidade:** 468 candidatos comparados com os pilotos anteriores: **0 diferenças** em métricas contínuas, seleção, vencedores, pontos e origens. O contrato não altera a escolha.
- **Erro físico ≈ contínuo**, como esperado (EPB trafos, ridge compartilhado: MAE 3,711 e 3,711; EMR poisson: 13,566 e 13,573; EAC CAGR: 58,257 e 58,159). **Reconciliação:** o CSV público não tem célula não inteira; o melhor candidato move 0–1 unidade ao reconciliar (máximo entre todos os candidatos: 48 em UCBT, 55 em trafos).
- Modelos com previsão negativa no backtest de `motor_cenarios` (16) não têm erro físico (`fisico_motivo`), em vez de forçar um número.

## 2. Viabilidade de 2021 (Prioridade 2; `reports/plano_2021/`)
Nada foi baixado, consultado na rede ou instalado. Matriz de fontes (catálogo local): EAC 2021 V10 (carimbo 2022-04-01), EMR V10 (2022-06-30), EPB **duplicada** (V10 2022-07-25 e M10 2024-01-19), mais EBO V10 (2022-07-18) e ENF V10 (2022-07-19) para o perímetro; tamanho `DESCONHECIDO` (exige consulta de metadados). 14 riscos classificados (layout V10×V11, duplicata, TUC/MCPSE, identidade UC v3, perímetro EPB←EBO e EMR←ENF, CONJ, vintage, relógio PIT, origens, armazenamento — D: com ≈ 647 GiB —, processamento, reprodutibilidade) e 5 etapas com a autorização exigida em cada uma (metadados → esquema da EAC → conformidade → EMR/EPB/EBO/ENF → reavaliação).

Duas conclusões que mudam a expectativa: (a) **2021 isoladamente não garante 3 backtests elegíveis**: adicionaria no máximo a origem 2022 e só se a transição 2021→2022 passar layout, TUC, identidade, perímetro, cobertura e ruptura; (b) **o relógio point-in-time do motor é inatingível**: 0 de 19 competências (2021–2025 das três empresas) foram geradas antes do fim do próprio ano, então 2021 não cria nenhum ponto point-in-time. Definir o relógio por data de publicação é decisão de projeto, não tomada aqui. O mínimo de 3 origens não foi reduzido.

## 3. Continuidade de CONJ (Prioridade 3; `reports/conj/`, `bridges/conj/`)
`conj_bridge.py` usa a continuidade dos circuitos (CTMT) como portadora de evidência (SSDMT km e clientes UCBT, fluxo antigo→novo), com NOME e área do CONJ apenas como apoio, e classifica cada código (`one_to_one` só com fluxo mútuo ≥ 90% em km **e** clientes, `carved_from`, `merge`, `new_circuits`, `persisting_changed`, `insufficient_evidence`). Quatro propostas versionadas, todas `PENDING_HOMOLOGATION`, `decision: null`.
- **EAC 2024:** continuidade de circuitos 99,8%, então a evidência é forte. Não é só renumeração: o 12590 TAQUARI (4.864 km) foi **repartido** em 17306 TAQUARI (58%), 17311 ACRELÂNDIA (26%), 17309 FLORESTA (10,5%) e 4,7% para o 12594; o 12597 TANGARA em 17307 (64%) e 17310 ALTO ALEGRE (30%); o 12596 SÃO FRANCISCO em 17308 (89%). Os três com nome mantido têm área 8–40% menor que a do código antigo. Cobertura: 23,8% do km com evidência forte, 76,2% parcial, 0% insuficiente.
- **EPB 2023:** 8 códigos novos, ≥ 95% de circuitos inéditos e 7 deles com nome presente nos conjuntos da EBO 2022 — consistente com a absorção já identificada nos municípios (hipótese, não homologada). Continuidade de circuitos 94,4%.
- **EMR 2023 e EPB 2024:** novos códigos e 9–18 conjuntos "persistentes alterados" (≥ 5% do km vindo de outro conjunto ou de circuitos novos; limiar conservador, também captura simples inclusão de circuitos).
- Efeito sobre o motor (Rede MT, modo reconciliado, **2 origens**): com as pontes como quarentena (nada assumido) a EAC passa de 1 para 2 origens (15→21 pontos) e a EPB de 1 para 2 (75→124), e os baselines deixam de ser degenerados. Ganho do melhor ML sobre o melhor baseline: EAC +12,7%, EPB +40,8%, EMR −13,9%. Ainda abaixo do mínimo de 3 origens: nenhum resultado é validado.

## 4. Estabilidade do motor (Prioridade 4)
Persistência, deriva, CAGR e ML seguem nos mesmos pontos de teste (conferido), seleção independente por DIST × ativo × métrica, nenhuma data, origem ou limiar foi alterada. Retomada e hashes preservados: 12 agregados UCBT + checkpoints `585da4d176babebf`; 114 checkpoints `90169fb05589f3ba`; extração `assets-1` `4c148fdf7951e9fc`; os pilotos v3 continuam em disco.

## 5. Testes
**152 testes `motor_v2` OK** (110 anteriores + 42: contrato 28, CONJ/plano 14). `motor_cenarios`: 13 OK (+ regeneração `--check`, auditoria independente `auditoria_pr6.py` e verificação do gerador exploratório). Web (checkout LF com `node_modules`): `tsc` e `eslint` limpos; `vitest` nos 5 arquivos afetados: 35 de 36 (a falha é artefato da sincronização temporária, hash do contrato de outro checkout). **Não executei** a suíte completa do vitest, o build nem o Playwright.

## 6. Pendências
- Aquisição de 2021 depende das aprovações listadas (metadados, download, decisão sobre a duplicata da EPB); PIT exige decisão metodológica.
- Homologação humana das 4 pontes de CONJ e da EPB←EBO; limiar de 5% para "persistente alterado" é de engenharia.
- `motor_universal`: 2 testes falham antes e depois (hash do contrato no manifesto), e `experiment_id`/`code_version` do resumo precisam ser regenerados após rebase em um contrato íntegro.
- Verificação visual do dashboard (Playwright) e a suíte web completa não foram executadas; nada foi publicado em produção.
- Erro físico indisponível para modelos com previsão negativa; reconciliação por total de um modelo da própria distribuidora (em vez da soma territorial) não foi avaliada.
