# 11 — Auditoria de plausibilidade dos cenários 2026–2030

Código: `motor_v2/nacional/plausibilidade.py` (regras no cabeçalho do módulo). Testes: `motor_v2/tests/test_plausibilidade.py` (16, sintéticos). Artefatos: `12_MATRIZ_PLAUSIBILIDADE.csv` (as 2.707 séries) e, em `motor_v2/reports/nacional/`, `PLAUSIBILIDADE_ALERTAS.csv`, `PLAUSIBILIDADE_RESUMO.json` e `PLAUSIBILIDADE_VALORES_BRUTOS.csv.gz` (valores originais de toda série sinalizada, **fora do produto**).

## O problema

Os totais agressivos de 2030 tinham valores absurdos: torres 124 bilhões (estoque 358 mil), seccionalizadores 2,9 bilhões (27,9 mil), transformadores de medida 246 milhões (746 mil).

**Causa.** O motor (`cenarios.scenarios`) desloca o crescimento log1p anual da trajetória moderada para o **maior crescimento anual observado numa única transição** da própria série e o **compõe por cinco anos**. A triagem do motor só retira uma transição quando o corte transversal a prova atípica **e** persistente. Passos de primeira entrada (0 → n), passos sobre base minúscula e saltos no último ano nunca são confirmados, e entram no envelope. Não houve erro de cálculo: a fórmula foi seguida, e o defeito estava na regra.

| DIST | Série | Histórico | Agressivo 2030 original | Causa |
|---|---|---|---|---|
| 86 Eflul | torres | 0, 0, 0, **66** | 90,5 bilhões (×1,4 bi) | primeira entrada do ativo em 2025: crescimento de 0 é indefinido |
| 5356 Cegero | torres | 0, 0, 0, **56** | 34,3 bilhões | idem |
| 5697 Celesc | seccionalizadores | 31, **1**, 61, 96 | 2,78 bilhões | base 1 em 2023 (reversão excluída), passo 1 → 61 |
| 405 Energisa MT | seccionalizadores | 5, 3, 3, **70** | 125 milhões | salto de 2025 com 5 tipos de ativo da DIST saltando no mesmo ano |
| 370 Roraima | transformadores de medida | 178, 1.638, 1.083, 223 | 14,4 milhões | mudança sistêmica de cadastro em 2023 (6 tipos de ativo) |
| 5707 CEEE Equatorial | transformadores de medida | 10.254, 10.676, 8.861, **48.162** | 228 milhões | salto ×5,4 em 2025 sem janela sustentada |
| 2763 Ceriluz | rede AT (km) | 0,51, 0,75, **19,4** | 1,04 milhão de km | km cadastrados em 2024: histórico insuficiente (moderado bloqueado) |

## Regra do portão (sem teto arbitrário)

1. **Distribuição de referência dos próprios dados.** Janelas de 2 e 3 anos (crescimento log1p anualizado) e passos de um ano, de todas as séries projetadas. Entram **só transições comparáveis**:
   - saem as excluídas pelo motor;
   - saem as com evidência cadastral da fase 4;
   - saem as de sucessão societária;
   - saem as que partem de estoque zero.
   O pool tem três níveis, usando o primeiro com pelo menos 100 janelas: (objeto, métrica, porte) → (unidade, porte) → (unidade). **Quantidades, km e kVA nunca se misturam.** Resultado: 1.226 séries usam o nível objeto/métrica, 1.429 unidade/porte e 52 unidade.
2. **Limiares.** Superior = P99 das janelas (piso 0), inferior = P01 (teto 0), alerta = P95. O crescimento neutro (0) está sempre dentro.
3. **Cenário extremo** (Agressivo para cima, Conservador para baixo):
   - dentro dos limiares → **ACEITO**;
   - fora → se a própria série **sustentou** no sentido do extremo nos últimos 2–3 anos (janela terminando na âncora, início ≥ 10, todos os passos além do passo relevante P90 ou P10, sem transição não comparável), é **CORRIGIDO** para essa taxa demonstrada (`PLAUSIVEL_COM_EVIDENCIA`);
   - senão → **BLOQUEADO**, com a causa classificada.
   A sustentação de queda usa a condição de queda; ela não herda a de alta.
4. Estoque âncora zero → extremos bloqueados (`HISTORICO_INSUFICIENTE`).
5. **Moderado** além dos limiares sem janela própria equivalente (tolerância de 25% para o ajuste do modelo): bloqueia a série inteira (`BLOQUEIO_PLAUSIBILIDADE`) **só se** o motor dessa taxa for evidência não comparável (ruptura, perímetro, base pequena, histórico insuficiente). Se for tendência de modelo, vira **alerta MEDIA** e a série é mantida.
6. **Intensidade** (unidades por consumidor, mesmo cenário e ano, demais distribuidoras): é só **indicador de anomalia** (alerta, nunca bloqueio).
7. UCBT e Consumidores: **só bloqueio, nunca recálculo**; o bloqueio de um bloqueia o outro (Consumidores = UCBT + complemento).
8. **Verificação de cálculo:** o extremo publicado precisa seguir a fórmula do motor a partir do moderado publicado, tolerando o arredondamento físico (±0,5 unidade do moderado, ±1 unidade do resultado). O arredondamento sozinho não é erro. Resultado: **0 erros de cálculo**.

As classes são **hipóteses**: `RUPTURA_CADASTRAL` por mudança sistêmica (≥ 3 tipos de ativo da DIST acima do P95 no mesmo ano) e `EXTRAPOLACAO_EXTREMA_NAO_SUSTENTADA` não foram confirmadas por registro individual. O valor original de toda série sinalizada está preservado no artefato de auditoria.

## Resultado

| | Preliminar (`6a1bb2f`) | Final |
|---|---|---|
| Séries auditadas | 2.707 | 2.707 |
| Alertas | 167 (71 altas, 16 médias, 80 baixas) | 420 (223 altas, 31 médias, 166 baixas) |
| Cenários extremos bloqueados | 72 | **255** |
| Cenários extremos corrigidos | 16 | **25** |
| Séries bloqueadas inteiras | 1 | **4** (Ceriluz rede AT, João Cesa ramais, Equatorial PA seccionalizadores, Ceprag ramais) |
| Séries com os 15 valores | — | **2.484** |
| Séries com Moderado e extremo bloqueado | — | 219 |
| Erros de cálculo | 62 (falso positivo de arredondamento) | **0** |

Classes (por série): extrapolação extrema não sustentada 113, ruptura cadastral 86, plausível com evidência (corrigidos) 25, histórico insuficiente 16, base histórica pequena 6.

O preliminar usava percentis misturados entre métricas, uma regra de teto de intensidade e uma condição de sustentação válida só para alta. As quatro correções feitas nesta etapa aparecem na tabela acima: pools por unidade, intensidade só como alerta, janela simétrica e exclusão de transições não comparáveis do pool.

## Totais agressivos de 2030, antes e depois

| Objeto | Estoque 2025 | Agressivo 2030 original | Agressivo 2030 publicado |
|---|---|---|---|
| Torres | 358.145 | 124.762.219.564 | **400.511** (89 séries com os três cenários) |
| Seccionalizadores | 27.851 | 2.903.339.117 | **17.877** (82 séries) |
| Transformadores de medida | 746.074 | 246.608.707 | **857.018** (82 séries; Moderado 744.039 no mesmo conjunto) |

Os três totais de cada objeto somam **o mesmo conjunto de séries** (as que têm os três cenários publicáveis), para preservar Conservador ≤ Moderado ≤ Agressivo. O Moderado de todas as séries projetadas vem à parte (`total_2030_moderado_todas_as_series`: torres 396.968 em 99 séries; seccionalizadores 28.655 em 98). **Todos os totais são PARCIAL.**

## Ressalvas que permanecem

- **Geradores:** o Agressivo agregado (32,7 milhões, no conjunto comum) é cerca de 8 vezes o estoque de 2025. Cada série está dentro do P99 sustentado do próprio objeto, que é alto porque a geração distribuída cresce de fato, ou foi corrigida pela taxa que demonstrou. Mas somar os extremos individuais produz um **composto**, não um cenário nacional.
  - *Correção de 03/11/2026:* a versão anterior deste documento dizia que o caso estava "sinalizado como alerta de severidade alta (nível nacional)". Esse alerta **não existia** nos artefatos nem na tela (não conformidade NC-ENG-01).
  - Agora o exportador compara o crescimento anual implícito de cada total de extremo com o crescimento nacional observado 2022–2025 **no mesmo conjunto de séries** (`agregado_extremos` no índice).
  - A tela mostra o Moderado como total nacional e os extremos como "soma dos extremos individuais (não é cenário nacional)", com alerta quando a soma sai da faixa observada.
  - Geradores: Agressivo implica 53%/ano contra 28–44%/ano observados.
  - O mesmo efeito de composição aparece em 23 dos 28 totais.
- Os limiares são **percentis empíricos desta amostra** (4 anos, 2022–2025), não limites físicos, e mudam se o histórico mudar. Cenários continuam sendo hipóteses, não intervalos de confiança, e **nenhum modelo é cientificamente homologado**.
- A tolerância de 25% para o ajuste do moderado e o piso de base de 10 unidades são parâmetros do portão (`TOL_MODELO` e `BASE_MINIMA`), não derivados dos dados. Estão no código e neste documento para auditoria.
- A correção reaplica a fórmula do motor sobre o moderado **publicado**: nas contagens pequenas o arredondamento do moderado pode alterar o valor corrigido em poucas unidades.
