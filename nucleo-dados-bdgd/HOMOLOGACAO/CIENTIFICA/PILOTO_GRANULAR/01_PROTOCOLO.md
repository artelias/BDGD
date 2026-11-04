# 01 — Protocolo do piloto granular e hierárquico (congelado antes dos experimentos)

**Branch:** `exp/piloto-granular-hierarquico-20261104`, criada de `homologacao/cientifica-20261103@531b0a9`.

**Este arquivo é commitado antes de qualquer execução experimental.** Os parâmetros estão replicados em `PROTOCOLO` dentro de `piloto.py`, e o código recusa rodar se os dois divergirem (hash do bloco da seção 11). Um desvio posterior é registrado no relatório (`07`) e **não pode** sustentar uma classificação de validação retrospectiva.

**Escopo e restrições:**
- só as competências de 2022 a 2025, nada anterior a 2022, nem como defasagem;
- a RC 1.0 não muda, não há merge nem deploy, e nada é publicado.

## 1. Hipóteses

- **H1 (principal).** Para cada família, um modelo treinado nas unidades territoriais (município ou conjunto), com parâmetros compartilhados entre distribuidoras e agregado à distribuidora, prevê o estoque e a **variação anual** da DIST em 2025 melhor que o modelo atual por distribuidora, na mesma coorte.
- **H2.** Um modelo hierárquico (efeitos globais mais intercepto por DIST encolhido para o global) supera o modelo global puro.
- **H3.** As variáveis territoriais (conexões recentes, energia, perfil urbano, densidade, demografia) acrescentam informação ao modelo nulo granular, que só tem intercepto, e ao modelo nulo hierárquico (intercepto mais efeito por DIST).
- **H0.** Nenhum ganho fora da amostra: os modelos atuais por distribuidora ficam mantidos.

## 2. População-alvo e ativos

Os ativos são os cinco painéis já extraídos (`D:/NUCLEO_BDGD_2025/motor_v2/nacional/painel/<DIST>/<ativo>/<ano>/territorial.parquet`). Os nomes e esquemas foram lidos dos próprios arquivos:

| Ativo (painel) | Métrica e natureza | Unidade-alvo (hipótese) | Sensibilidade de granularidade | Esquema |
|---|---|---|---|---|
| `ucbt_quantidade` | clientes BT ativos (contagem) | município | conjunto | MUN, CONJ, CTMT, ARE_LOC, clientes_ativos, energia_kwh, energia_denominador, conexoes_12m, dat_con_validas |
| `trafo_dist_quantidade` | transformadores TUC 565 (contagem) | município (UN.MUN, vínculo EQ→UN bijetivo) | conjunto | UNIT (=MUN), CONJ, value, rows |
| `trafo_dist_potencia_kva` | kVA dos mesmos transformadores (contínua, **experimental**) | município | conjunto | idem |
| `rede_bt_extensao_km` | km de SSDBT (contínua) | conjunto | — | UNIT (=CONJ), CONJ, value, rows |
| `rede_mt_extensao_km` | km de SSDMT (contínua) | conjunto | — | idem |

A granularidade é escolhida **na etapa de seleção** entre a hipótese e a sensibilidade, pelo critério da seção 9, e fica congelada. O circuito (CTMT) não é unidade-alvo.

Geração distribuída e as famílias por DIST estão **fora deste piloto**, porque não têm painel extraído. Não há extração nova.

## 3. Comparabilidade e exclusões (antes de qualquer variação)

A unidade de exclusão é a transição (DIST, nível, t−1 → t). Cada exclusão é registrada com numerador (unidades e estoque excluídos), denominador e motivo em `02_COBERTURA_E_EXCLUSOES.csv`. Motivos:

1. ruptura: no histórico do painel (`result.json`, `rupture`) ou no contrato nacional, para o conceito correspondente (UCBT → `consumidores`, os trafos → `trafo_dist`, as redes → `rede_bt`/`rede_mt`), no ano t ou t−1;
2. sucessão societária, origem ou destino (`eventos_sucessao.csv`), quando a data efetiva cai em t−1 ou t;
3. recodificação municipal pendente: Celesc (5697) em 2023, para os níveis municipais nas transições 2022 → 2023 e 2023 → 2024;
4. anomalia municipal do DIST 7019 em 2023: mesmas transições, níveis municipais;
5. chave instável: menos de 95% do estoque em unidades presentes nos dois anos, em qualquer sentido. Isso inclui a renumeração de conjuntos (17 DIST em 2023 → 2024) e vale só para o nível afetado;
6. painel ausente no ano: DIST-ano sem extração;
7. código territorial inválido (vazio, `0` ou município sem 7 dígitos): o estoque fica em `SEM_CODIGO`, fora dos pares de treino, e é projetado por persistência na agregação.

Nenhuma ponte é aplicada e nada é imputado. Unidades que entram (0 → n) ou saem não são pares de crescimento; entram só como margem extensiva no erro da DIST.

## 4. Separação temporal (sem uso de 2025 antes da avaliação final)

| Etapa | Treino (pares t−1 → t) | Previsão | Uso |
|---|---|---|---|
| **S, seleção** | t ≤ 2023 (2022 → 2023) | 2024, a partir de 2023 | variáveis, algoritmo, hiperparâmetros e granularidade |
| **F, final** | t ≤ 2024 (2022 → 2023 e 2023 → 2024) | 2025, a partir de 2024 | **só avaliação**, uma vez, com a configuração congelada na etapa S |
| **E, espacial** | pares 2022 → 2023 dos grupos econômicos de treino | 2023 dos grupos econômicos retidos (validação cruzada agrupada, 5 dobras) | generalização para grupos não vistos, no **mesmo ano**; não prova capacidade de prever anos futuros |

**Controle de vazamento:**
- toda variável é medida na fotografia de t−1, a competência de origem, ou é estática, com divulgação até a origem:
  - IBGE: Censo 2022 divulgado em 31/08/2023;
  - PIB municipal 2021 divulgado em 15/12/2023;
  - população 2010 e estimativa 2021;
- na etapa S as variáveis do IBGE são de conhecimento na origem (31/12/2023). Os pares de treino com variáveis de 2022 usam atributos estáticos do município, não informação do ano-alvo;
- `conexoes_12m` vem da própria fotografia: UCs ativas com `DAT_CON` em (data-base − 1 ano, data-base]. Não se usa conexão de 2024 para prever 2024;
- a auditoria da seção 10 mede, numa amostra, se a competência seguinte reescreve a `DAT_CON` de registros antigos;
- nenhuma defasagem de crescimento: em t−1 = 2022 ela exigiria 2021. Crescimento contemporâneo de outros ativos é proibido, porque é futuro em relação à origem.

## 5. Variáveis candidatas (por ativo, na unidade e em t−1)

Definições e estado de cada variável em `03_MATRIZ_VARIAVEIS.csv`.

- **Comuns**, quando há UCBT na unidade:
  - `ln_estoque`;
  - `taxa_conexoes` = conexoes_12m / clientes;
  - `ln_kwh_cliente` (energia anual ÷ clientes com energia);
  - `fracao_urbana` (clientes em ARE_LOC = UB);
  - `ln_pib_pc_2021`, `cresc_pop_2010_2022` (anualizado) e `eletrificacao` = clientes / população 2022 (município). No conjunto, essas três são médias ponderadas pelos clientes da interseção município × conjunto em t−1.
- **UCBT:** as comuns, mais `ln_trafo_por_cliente` e `ln_kva_por_cliente` (do painel de trafos, mesma unidade).
- **Trafos (quantidade):** as comuns, mais `ln_clientes_por_trafo` e `ln_kva_por_trafo`.
- **Trafos (kVA):** as comuns, mais `ln_kva_por_trafo` e `ln_clientes_por_kva`.
- **Rede BT (conjunto):** as comuns, mais `ln_clientes_por_km_bt`, `ln_trafo_por_km_bt` e `ln_razao_mt_bt`.
- **Rede MT (conjunto):** as comuns, mais `ln_clientes_por_km_mt`, `ln_trafo_por_km_mt` e `ln_razao_bt_mt`.

Potência em kVA: só UNTRMT kVA / UNTRAT MVA × 1000 via vínculo EQ→UN bijetivo. EQ.POT_NOM é código de domínio e não é usado. EQ e UN nunca são somados.

**Filtros**, só no treino S:
- disponibilidade ≥ 50% dos pares;
- desvio-padrão > 1e-9;
- |r| > 0,95: fica a primeira da lista.

## 6. Modelos

O alvo de treino é g = ln(y_t / y_{t−1}) por unidade pareada, com peso y_{t−1} (alinhado ao WAPE) e winsorização a 5–95% ajustada no treino. A previsão por unidade é ŷ_t = y_{t−1}·exp(ĝ).

**A. Referências por DIST**, sobre os totais do painel, na mesma coorte:
- persistência;
- deriva;
- CAGR (crescimento geométrico de uma transição);
- **modelo atual** = o algoritmo do Moderado do produto em produção para o conceito, reexecutado com o mesmo código de `motor_cenarios/cenarios.py` (`Motor.prever`, as mesmas variáveis e hiperparâmetros) sobre a série do painel:

| Ativo | Modelo atual |
|---|---|
| Trafos, quantidade | `knn_analogos` |
| Trafos, kVA | `ridge_painel` |
| Rede BT | `ridge_painel` |
| Rede MT | `random_forest_painel` |
| UCBT | `ridge_painel` (Moderado de `consumidores`, o conceito mais próximo) |

Também entram, como contexto, todos os outros candidatos por DIST do produto.

**B. Granulares:**
- nulos:
  - `G-NULO`: intercepto global;
  - `H-NULO`: intercepto global mais efeito por DIST encolhido, sem variáveis;
- `G-RIDGE` (α ∈ {0,1; 1; 10});
- `G-HIER`: o Ridge com as variáveis selecionadas mais intercepto por DIST encolhido por Bayes empírico. A variância entre DIST τ² e a dentro σ² são estimadas por momentos ponderados nos resíduos de treino, com 10 iterações de *backfitting*. Uma DIST sem treino recebe efeito 0;
- `G-HGB` (max_depth ∈ {2; 3} × learning_rate ∈ {0,05; 0,1}; 150 iterações; min_samples_leaf 20);
- `G-RF` (300 árvores; min_samples_leaf ∈ {5; 20} × max_features ∈ {0,5; 1,0});
- `G-KNN` (k ∈ {15; 50}, mediana dos vizinhos).

Todos usam imputação pela mediana do treino e padronização. **Ordem de custo:** nulos, Ridge, hierárquico e HGB primeiro. RF e KNN só rodam numa granularidade se, na etapa S, o melhor granular até ali tiver WAPE_S ≤ 1,25 × o melhor de referência por DIST.

**Agregação à DIST:**
- ŷ_DIST = Σ ŷ_u sobre todas as unidades com estoque em t−1, mais o estoque `SEM_CODIGO` por persistência;
- contagens: cada ŷ_u é arredondada meio para cima, e o total é a soma dos inteiros, ou seja, reconciliado;
- km e kVA: sem arredondamento;
- valores sempre ≥ 0 (exp);
- nenhuma dupla contagem: cada ativo é somado só no próprio painel.

## 7. Métricas (etapas S e F; DIST e unidade)

**Na DIST:**
- WAPE do estoque, MAE, RMSE e viés relativo;
- R² do estoque;
- **R² da variação anual** Δ = y_t − y_{t−1} e **MAE de Δ**;
- **R² do crescimento** ln(y_t / y_{t−1});
- erro físico (WAPE depois do arredondamento, contagens);
- ganho de WAPE sobre o melhor baseline e sobre o modelo atual;
- contagem de grupos, DIST e unidades avaliadas.

**Na unidade:** WAPE e R² do crescimento das unidades pareadas.

R² não é definido com n < 5 ou SST = 0, e nunca é trocado por 0. R² negativo é relatado. Prever o **tamanho** do estoque (WAPE e R² do estoque) e prever o **crescimento** (R² de Δ e do crescimento, MAE de Δ) são relatados separadamente.

## 8. Incerteza

- **Bootstrap por grupo econômico:** 2.000 réplicas, semente 20261104. Uma DIST sem grupo é o próprio grupo.
- **IC95%:** percentil da diferença de WAPE na DIST (candidato − melhor baseline; candidato − modelo atual), reamostrando grupos inteiros com todas as suas DIST. Nunca se reamostram unidades.
- **n efetivo** das unidades: relatado (efeito de desenho pelo ICC intra-DIST), não usado como n de teste.

## 9. Seleção (etapa S) e congelamento

- Variáveis por modelo: ordem por importância por permutação na validação S, no G-RIDGE com todas as variáveis. A importância é o aumento do WAPE da DIST agregada, com 5 repetições e semente 42. Entram prefixos de até 8, e a busca para depois de 2 prefixos sem melhora. RF, HGB e KNN usam a mesma ordem de prefixos.
- Critério: **menor WAPE_S da DIST agregada**. No empate até 1e-6, fica o modelo mais simples (nulo < Ridge < hierárquico < HGB < RF < KNN) e a granularidade da hipótese.
- Congelamento: **um único candidato granular por ativo** (algoritmo, granularidade, variáveis, hiperparâmetros). Ele é gravado em `selecao_congelada.json` com hash, e o hash é commitado antes da etapa F. A etapa F avalia **só esse candidato** para a decisão. Os demais aparecem em `05` como exploratórios e não entram em aprovação.

## 10. Auditoria de DAT_CON (amostra, sem extração massiva)

Para 3 DIST (26, 6600 e 5707), com DuckDB e projeção de colunas em uma DIST por vez:
- conta, na fotografia de 2024, as UCs ativas com `DAT_CON` em 2023;
- compara com `conexoes_12m` da fotografia de 2023;
- mede a fração das UCs da fotografia de 2023 (identidade COD_ID + PN_CON) cuja `DAT_CON` muda na fotografia de 2024.

Uma reescrita relevante (> 5%) torna `taxa_conexoes` suspeita, registrada como limitação. Ela não muda os modelos depois do fato.

## 11. Critérios de decisão (fixados agora; avaliados só na etapa F, no candidato congelado)

```
PROTOCOLO_DECISAO = {
  "melhoria_competitiva": "WAPE_F <= 0.95 * WAPE_F(modelo atual) na mesma coorte; WAPE_F <= WAPE_F(melhor baseline); restricoes fisicas atendidas; |vies_F| <= |vies_F(modelo atual)| + 0.01; R2 de variacao e crescimento relatados",
  "validado_retrospectivo_restrito": "melhoria_competitiva E IC95% bootstrap por grupo de (WAPE candidato - WAPE melhor baseline) inteiramente < 0 E >= 20 DIST e >= 12 grupos E conclusao mantida sem a DIST de maior contribuicao absoluta a diferenca E conclusao mantida sem as 5% maiores variacoes relativas observadas",
  "rejeicao": "piora fora da amostra; ganho so na etapa S; violacao fisica; informacao futura; transicao nao comparavel; ganho sem suporte estatistico quando a classificacao o exige",
  "melhor_baseline": "menor WAPE_F entre persistencia, deriva e CAGR na mesma coorte",
  "teto": "nenhuma homologacao cientifica plena para 2026-2030; 1 origem final independente"
}
```

Classes por ativo:
- `VALIDADO_RETROSPECTIVAMENTE_COM_RESTRICOES`;
- `MELHORIA_COMPETITIVA_EXPERIMENTAL`, que cumpre a melhoria competitiva sem suporte estatístico;
- `SEM_GANHO`, com os modelos atuais mantidos;
- `REJEITADO`;
- `BLOQUEADO`, com motivo.

## 12. Limites computacionais e regra de parada

- Ambiente: Windows, 8 GB de RAM, 4 núcleos, dados em D:.
- Derivados e cache ficam em `D:/NUCLEO_BDGD_2025/piloto_granular_cache/`, fora do C:.
- Leitura: só os painéis existentes, por DIST e por coluna. O DuckDB, só na auditoria da seção 10, roda com `memory_limit = 2GB` e `temp_directory` em D:.
- Execução em um processo, sem paralelismo (`n_jobs = 1`).
- Registro de tempo, memória máxima do processo (Windows PeakWorkingSet) e tamanho dos artefatos.
- Orçamento por ativo e granularidade: no máximo 60 ajustes na etapa S.
- **Parada:** se, depois de nulos, Ridge, hierárquico e HGB, nenhum candidato tiver WAPE_S ≤ 1,25 × a melhor referência, RF e KNN não rodam. A etapa F roda uma única vez por ativo.
