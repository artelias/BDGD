# 08 — Parecer científico da recuperação dos cenários (preparado para revisão; **não é homologação nem assinatura**)

**Branch:** `exp/recuperacao-cenarios-20261104`. **Protocolo:** `recuperacao-1`, commit `d478e16`, anterior aos cálculos série a série. **Entradas:** as da RC 1.0, sem alteração. O produto publicado é idêntico entre `rc/1.0-20261101@dba5fdf` e a base desta branch. Também entram a otimização `997c4d7` e o dossiê científico `3748c95`.
**Estado de todo resultado:** EXPERIMENTAL. Nada aqui altera a RC, o produto publicado ou algum Moderado. As previsões 2026–2030 continuam **não homologadas**.

## 1. Conclusão

| Pergunta | Resposta |
|---|---|
| Quantas séries podem ter três cenários defensáveis? | **1.419 de 2.202** no registro experimental: **1.081 com os três por modelo** e **338 com pelo menos um extremo condicional**. Sem as métricas em kVA: 1.310 de 2.033, 980 por modelo |
| Quantas tinham antes? | **755 publicadas**, das quais só **185** passam na regra C ≤ M ≤ A com diferença material |
| De onde vem o ganho? | Sobretudo da **seleção série a série com modelos que já existem** (+854 séries), e da regra condicional existente (+200). Os modelos novos acrescentam pouco (+180, quase todos com o quantil condicional) |
| Os modelos novos preveem melhor? | **Não.** Nenhum melhora o WAPE de forma geral nem o R² do crescimento (seção 6) |
| Algum resultado é validado? | **Não.** A escolha dos extremos usa erros que incluem 2025, que já foi consultado. É evidência histórica, exploratória; os horizontes de 2 a 5 anos continuam NÃO HOMOLOGÁVEIS |
| Achado que afeta a RC e a produção | **1.084 dos 2.495 extremos publicados** violam a ordem ou a diferença material. Exemplo: Agressivo de alimentadores da Energisa AC (DIST 26) em 150 contra Moderado 154 em 2030. A produção de 28/10 tem o mesmo defeito |

## 2. Cobertura antes e depois (2.202 séries)

| Estado | Completas | Por modelo | Com condicional | Parciais | Sem previsão |
|---|---|---|---|---|---|
| Publicado (RC 1.0 = produção) | **755** | — | — | 1.206 | 241 |
| Publicado, auditado pela seção 6 do protocolo | **185** | 185 | 0 | 1.776 | 241 |
| Gate B: só os 9 originais, série a série (P1 + P2-O) | **711** | 711 | 0 | 1.250 | 241 |
| Gate B: originais + otimizados (P1 + P2) | **1.039** | 1.039 | 0 | 922 | 241 |
| Gate B completo, sem treino novo (+ B-HIST) | **1.239** | 1.039 | 200 | 722 | 241 |
| Final, com os modelos novos (P1–P6) | **1.419** | 1.081 | 338 | 542 | 241 |

### Quantidades pedidas

| Quantidade | Séries | Observação |
|---|---|---|
| Completas antes | 755 publicadas; **185 defensáveis** | 570 publicadas como completas têm um extremo reprovado |
| Completas depois | **1.419** | registro experimental, não publicado |
| Recuperadas com modelos existentes | **854** | 526 só com os originais e 328 com os otimizados; nenhum modelo novo |
| Recuperadas com a regra condicional existente (B-HIST) | **200** | sem treino; simulação condicional |
| Recuperadas com modelos novos | **180** | 24 com previsão nova (N1 ou N2) e 156 com o quantil condicional (N5) |
| Com cenários independentes (os dois extremos por modelo) | **1.081** | |
| Com cenários condicionais | **338** | 335 mistas, 3 só com condicionais |
| Ainda parciais | **542** | 712 posições: coincidência D 407, lado oposto A2 254, cruzamento C 27, erro B 19, implausível E 5 |
| Ainda bloqueadas (sem previsão) | **241** | G 169, F 66, E 6; **121** teriam Moderado com histórico mínimo de 2 anos (decisão de contrato) |
| Rejeitadas por erro | 11 séries (19 posições) | no Gate A eram 254 posições: os otimizados e os novos resolvem a maioria |
| Rejeitadas por implausibilidade | 5 séries parciais e 6 sem Moderado | mais 2 extremos publicados |
| Rejeitadas por ausência de informação | **235** | competência bloqueada, publicação não localizada, ruptura, zero verificado |
| **Perdas de qualidade** | **161** | séries publicadas como completas que ficam parciais: o extremo publicado é reprovado e não há substituto coerente (subestações 32, alimentadores 28, trafo_forca 27, bancos 19, trafo_dist kVA 18, disjuntores 15, rede AT 9, chaves 7, rede BT 4, rede MT 2) |

### Posições de extremo no registro final

São 1.961 séries com Moderado, logo 3.922 posições.

| Categoria | Posições |
|---|---|
| A, publicado mantido (aprovado na seção 6) | 1.411 |
| A, original escolhido na série | 374 |
| A, otimizado | 1.005 |
| A, novo (N1 ou N2) | 49 |
| B-HIST (condicional, regra existente) | 189 |
| B, quantil N5 (condicional novo) | 182 |
| B, elasticidade N6 | 0 (reprovada nas 6 métricas) |
| Indisponível | 712 |

## 3. Por família

| Família | Séries | Publicadas completas | Defensáveis antes | Gate B | Final | Por modelo | Com condicional | Sem previsão |
|---|---|---|---|---|---|---|---|---|
| Clientes (consumidores, geradores, iluminação) | 295 | 0 | 0 | 116 | 123 | 89 | 34 | 27 |
| Medição (medidores, trafo de medida) | 189 | 0 | 0 | 122 | 160 | 104 | 56 | 23 |
| Estruturas (postes, torres) | 157 | 0 | 0 | 123 | 123 | 116 | 7 | 16 |
| Redes (AT, MT, BT, ramais) | 350 | 230 | 87 | 271 | 304 | 253 | 51 | 28 |
| Transformação | 339 | 147 | 29 | 192 | 223 | 162 | 61 | 44 |
| Seccionamento e proteção | 293 | 137 | 24 | 167 | 183 | 157 | 26 | 43 |
| Subestações e circuitos | 377 | 154 | 25 | 133 | 157 | 97 | 60 | 38 |
| Regulação e compensação | 202 | 87 | 20 | 115 | 146 | 103 | 43 | 22 |

### Por métrica

O detalhe está em `07_COBERTURA_ANTES_DEPOIS.csv`, nível `metrica`.
- **Maiores ganhos:** postes (0 → 91), consumidores (0 → 88), medidores (0 → 88), ramais (0 → 89), trafo_dist/quantidade (0 → 81), reguladores (0 → 78) e trafo de medida (0 → 72).
- **Continuam sem base para um terceiro cenário distinto:**
  - conjuntos (1 de 99);
  - geradores (4 de 98): os dois extremos só convivem na mesma série em 4 casos, e o Agressivo fica indisponível em 68 (em 50 os competitivos ficam abaixo da deriva do Moderado);
  - reatores (0 de 13);
  - seccionalizadores (5 de 32), só com condicionais.

### Por empresa (99 distribuidoras)

- **Fração mediana de séries completas:** 38% publicadas, contra 71% no registro final.
- **Sem nenhuma série completa:** 8 cooperativas (Chesp, Coprel, Certaja, Ceral Anitápolis, Cermoful, Coopercocal, Cetril, Ceral Araruama). Nelas, nenhuma série tem Moderado: a competência 2023 está bloqueada ou falta 2024 ou 2025. Isso é um problema de dados, não de modelo.
- **Sem série defensável antes:** 26 distribuidoras não tinham nenhuma série com três cenários defensáveis.

O detalhe está em `07_COBERTURA_ANTES_DEPOIS.csv`, nível `empresa`.

## 4. Modelos existentes (Gate B)

### Inventário

Detalhe em `03_INVENTARIO_MODELOS_EXISTENTES.csv`.

| Origem | Total | Válido nacional e na DIST | Só na DIST | Só retrospectivo | Rejeitado | Sem evidência |
|---|---|---|---|---|---|---|
| Originais (O), menos os 27 Moderados | 216 | 79 | 7 | 1 | 124 | 5 |
| Otimizados (X) | 104 | 70 | 6 | 1 | 27 | 0 |
| Novos (N1, N2n, N2g) | 81 | 17 | 4 | 0 | 60 | 0 |

### Reprodução

- **Originais:** as 243 configurações foram reexecutadas. Escolhas idênticas, WAPE idêntico ao publicado (diferença 0,0) e trajetórias publicadas reproduzidas. Só 2 contagens, em mais de 16 mil, usaram a folga de 1 unidade do `--check`.
- **Otimizadas:** as 104 configurações reproduziram o WAPE S e F registrados na otimização (|Δ| ≤ 5e-7).

### Vereditos da otimização entre os 77 otimizados competitivos

O que se exige de um extremo é a tolerância de erro, não a melhora sobre o original. Por isso:
- **40** são modelos que **pioraram** contra o original do mesmo algoritmo (`PIOROU_FORA_DA_AMOSTRA`), mas continuam dentro da tolerância do Moderado e da guarda F;
- 24 não tiveram ganho significativo;
- 13 melhoraram.

### Conciliação com o registro de 1.343 séries da otimização

| Situação | Séries |
|---|---|
| Completas na otimização e aqui | 1.255 |
| Completas na otimização, não aqui | 88: lado oposto 41, coincidente 39, ambos 5, implausível 2, cruzamento 1 |
| Completas aqui, não na otimização | 164 |

As diferenças vêm de cinco regras deste protocolo:
- exige diferença de pelo menos 1 unidade nas contagens;
- verifica o crescimento e o salto de 2026 contra o P01–P99;
- limita a regra condicional a P05–P95, onde a otimização usava P01–P99;
- avalia a tolerância pelo WAPE do produto e pela guarda F, em vez de só pela etapa S;
- não substitui o Moderado em nenhuma métrica.

## 5. Algoritmos que mais preenchem extremos, por família

Não houve ganho de capacidade preditiva em nenhuma família. Os algoritmos abaixo são os que fornecem trajetórias coerentes dentro da tolerância de erro:

| Família | Mais usados (posições recuperadas, sem contar os publicados mantidos) |
|---|---|
| Clientes | tendência OLS em geradores (64: 48 Conservadores e 16 Agressivos), KNN otimizado (51, Agressivo de consumidores), B-HIST (33) |
| Medição | KNN otimizado (83), Ridge otimizado (27), quantil 0,2 (25) |
| Estruturas | RF otimizado (64), HGB original (28), Ridge otimizado (25) |
| Redes | HGB otimizado (53), RF otimizado (39), Ridge otimizado (38) |
| Transformação | Ridge otimizado (111), KNN otimizado (57), B-HIST (38) |
| Seccionamento e proteção | HGB otimizado (49), Ridge otimizado (40), RF otimizado (34) |
| Subestações e circuitos | B-HIST (37), RF otimizado (32), KNN otimizado (27) |
| Regulação e compensação | RF original (29), RF otimizado (28), Ridge otimizado (25) |

## 6. Modelos novos (Gate C)

Todas as escolhas foram feitas só na etapa S: φ = 0,8 em 24 de 27 métricas, κ = 3 em 42 de 54. Elas estão congeladas em `selecao_congelada.json` (SHA-256 em `selecao_congelada.sha256`).

| Candidato | Competitivo em | WAPE do produto menor que o do Moderado | IC95% totalmente abaixo do Moderado | IC95% totalmente acima (pior) | R² do crescimento > 0 (etapa F) |
|---|---|---|---|---|---|
| N1, tendência amortecida | 2 de 27 | 1 | 0 | 14 | 3 |
| N2n, crescimento encolhido nacional | 13 de 27 | 5 | 1 (seccionalizadores, com R² do crescimento −0,52) | 6 | 4 |
| N2g, encolhido por grupo econômico | 6 de 27 | 3 | 0 | 9 | 4 |

- **N5, regressão quantílica condicional:** calibrada nas etapas S e F em 14 de 27 métricas para cada lado. Preenche 182 posições. É uma simulação condicional, sem erro retrospectivo próprio e sem calibração para h > 1.
- **N6, elasticidade à carga:** reprovada nas 6 métricas. O IC95% de β na amostra S (2022 → 2023) inclui zero em todas. Medidores têm β = 0,26 (IC95% [0,10; 0,51]) na amostra completa, mas [−0,26; 0,79] na S; rede BT tem 0,14, com [0,04; 0,30] na completa e IC que inclui zero na S. Com 3 transições, a relação entre a expansão da rede e a carga não é estimável de forma estável.

**R² do crescimento na etapa F (mediana):**

| Conjunto | Mediana | Positivos |
|---|---|---|
| Moderados | −0,02 | 7 de 27 |
| Originais competitivos | −0,02 | 28 de 87 |
| Otimizados competitivos | −0,04 | 20 de 77 |
| Novos competitivos | −0,22 | 5 de 21 |

**WAPE da expansão** (erro em relação à variação observada; a persistência vale 1,00):
- Moderados: mediana 0,86;
- originais competitivos: 0,81;
- otimizados competitivos: 0,84;
- novos competitivos: 0,75. A amostra é pequena e o resultado, exploratório.

**Resultado:** os modelos novos **não melhoram o WAPE de forma geral nem o R² do crescimento**. Servem para preencher 24 séries com um extremo por modelo. O ganho do Gate C vem quase todo do quantil condicional, que é uma simulação e não uma previsão.

## 7. Qualidade (Gate D)

| Verificação | Resultado |
|---|---|
| Ordem C ≤ M ≤ A nos 5 anos (contínua e publicada) | 100% dos extremos do registro final |
| Diferença material | 100%: ≥ 0,05 p.p./ano e, em contagens, ≥ 1 unidade em 2030 |
| Plausibilidade | 100%: razão 2030/2025 em [0,5; 3]; crescimento e salto de 2026 no P01–P99 da métrica |
| Valores | não negativos; contagens inteiras; km e kVA contínuos |
| Inversão de direção no 1º ano | 21 de 1.799 extremos novos: todos Conservadores com queda inicial dentro do P01–P99, legítimos como cenário |

**Fora do alcance desta auditoria:**
- **Níveis territoriais:** não se aplicam, porque o produto público é por DIST.
- **Soma nacional:** nenhuma foi criada.
- **UN e EQ:** seguem o contrato, sem somas.
- **Telas, JSON e CSV:** a coerência entre eles fica para a implementação do Codex (09).

## 8. Vazamento e limites da evidência

- **Uso de 2025.** A tolerância dos extremos usa o WAPE do produto, que inclui pontos com alvo em 2025. Esses pontos já foram usados na escolha do Moderado, na otimização e no dossiê. A guarda F (2024 → 2025) também já foi consultada. **Nenhuma melhora é declarada confirmada.**
- **Escolhas novas.** φ, κ e o mínimo de pares do N5 foram escolhidos só na etapa S. A calibração do N5 e a guarda F usam a etapa F, já consultada, e por isso são exploratórias.
- **Configurações otimizadas.** As variáveis e os hiperparâmetros vêm da etapa S, e os pontos S entram no WAPE do produto, com viés otimista em 1/3 dos pontos. A guarda F limita esse efeito, mas não o elimina.
- **Confirmação futura.** A regra série a série e as escolhas congeladas devem ser avaliadas na primeira competência posterior a 2025 (origem 2025 → alvo 2026), sem nenhum ajuste.
- **Horizontes de 2 a 5 anos:** NÃO HOMOLOGÁVEIS COM A EVIDÊNCIA ATUAL.
- **Natureza dos cenários.** Os extremos por modelo são "simulação comparada retrospectivamente". Os condicionais são "simulação condicional". Nenhum deles é intervalo de confiança.

## 9. Desvios de execução (registrados)

1. **Depuração.** Depois do commit do protocolo, houve uma execução em 2 métricas (consumidores e rede BT) num diretório temporário. Ela revelou um defeito de preenchimento: as colunas do Gate B ficavam vazias nas séries sem previsão. O defeito foi corrigido sem mudar nenhum parâmetro. A execução completa reproduziu a de depuração nessas 2 métricas, com 0 diferenças.
2. **Saída.** A primeira execução completa gravou em `saida/`. Para a entrega, a execução foi refeita gravando direto nesta pasta, com colunas extras de gabarito por opção de integração (só originais, originais + otimizados, Gate B). O `RESUMO.json` das duas execuções é idêntico.
3. **Tolerâncias de reprodução.** Nenhum desvio. O WAPE é idêntico ao publicado, e as trajetórias ficam dentro da tolerância do `--check`.

## 10. Respostas às 12 perguntas

1. **Por que faltam três cenários em tantas séries?**
   - A regra do produto escolhe os extremos pelo agregado nacional e os aplica a todas as distribuidoras: são 477 posições recuperáveis só mudando a seleção.
   - Em 950 posições não há alternativa competitiva e distinta: lado oposto 441, erro 254, coincidência 208, cruzamento 36, implausibilidade 11.
   - 241 séries não têm Moderado por problema de dados.
   - Além disso, 1.084 extremos publicados não representam um cenário mais baixo ou mais alto na distribuidora.
2. **Quantas ausências decorrem de seleção, e quantas de dados?**
   - **Seleção:** 477 posições de extremo, mais os 1.084 publicados reprovados, que têm a mesma origem.
   - **Evidência de modelo:** 950.
   - **Dados:** 235 séries sem Moderado (G 169, F 66), com os seus 470 extremos.
   - **Moderado implausível:** 6.
3. **Quantas podem ser recuperadas sem treinar nada?**
   - **711** séries completas só com os 9 originais escolhidos série a série;
   - **1.039** com os otimizados já executados;
   - **1.239** somando a regra condicional existente.
   - Antes eram 755 publicadas, das quais 185 defensáveis.
   - Isso exige reexecutar as mesmas configurações, porque as trajetórias das séries não eram persistidas. A reprodução é bit a bit.
4. **Quantas exigem novos modelos?** **180**: 24 com N1 ou N2 e 156 com o quantil condicional N5.
5. **Quais algoritmos funcionam melhor por família?** Nenhum prevê melhor o crescimento. Os que mais fornecem extremos coerentes dentro da tolerância estão na seção 5: Ridge e KNN otimizados em transformação e medição, HGB e RF otimizados em redes e proteção, e tendência OLS em geradores.
6. **Os modelos novos melhoram o WAPE?** Não, em geral. O N2n tem WAPE menor que o Moderado em 5 de 27 métricas e é significativamente melhor só em seccionalizadores, que têm amostra pequena. O N1 é pior com significância em 14 métricas.
7. **O R² do crescimento melhora?** Não. A mediana dos novos competitivos é −0,22, contra −0,02 dos Moderados.
8. **Quantas séries passam a ter três cenários matematicamente defensáveis?** **1.081** com os três por modelo, ou **1.419** contando os condicionais. É registro experimental: com 1.081, a regra da seção 6 vale em todos os anos, e com 1.419, também com simulações condicionais rotuladas.
9. **Quantas continuam bloqueadas e por quê?**
   - **241 sem previsão:** por dados (G 169, F 66) e por Moderado implausível (E 6); 121 delas dependem de uma decisão de contrato.
   - **542 parciais:** o melhor candidato coincide com o Moderado (281 séries), fica do lado oposto (254), cruza (15), tem erro excessivo (11) ou é implausível (5). Uma série pode ter mais de uma causa.
10. **Quais resultados são apenas experimentais?** Todos. Nenhum extremo é previsão validada. As escolhas novas ficam congeladas para confirmação com a competência 2026.
11. **Impacto na Metodologia e na interface:**
    - **Metodologia:** a regra muda de agregada para série a série, com o modelo de cada extremo indicado por distribuidora.
    - **Interface:** exibir a categoria de cada extremo (modelo alternativo ou simulação condicional), a garantia de ordem C ≤ M ≤ A e o motivo de cada posição bloqueada. O total nacional segue rotulado como soma de extremos individuais.
    - **Correção:** corrigir os 1.084 extremos publicados que violam a ordem (09).
12. **Alterações recomendadas para integração futura:** ver `09_RECOMENDACAO_INTEGRACAO.md`. A decisão sobre o defeito de ordem é a mais urgente.

## 11. Assinaturas

Não registradas. Este parecer é preparado para revisão humana e não constitui aceite nem homologação.
