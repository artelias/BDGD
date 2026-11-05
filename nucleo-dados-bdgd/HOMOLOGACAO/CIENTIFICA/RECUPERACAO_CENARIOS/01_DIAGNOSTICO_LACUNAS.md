# 01 — Diagnóstico das lacunas de cenários (Gate A)

**Branch:** `exp/recuperacao-cenarios-20261104`. **Protocolo:** `04_PROTOCOLO_CANDIDATOS.md` (`recuperacao-1`, commit `d478e16`, anterior a qualquer cálculo série a série).
**Execução de referência:** `recuperar.py`, Windows, Python 3.14.3, scikit-learn 1.8.0, 305 s. Os SHA-256 das entradas e das saídas estão em `MANIFESTO.json`.
**Estado:** EXPERIMENTAL. Não altera a RC 1.0 nem o produto publicado.

A matriz completa, uma linha por série, está em `02_MATRIZ_SERIES_CENARIOS.csv` (2.202 linhas). A auditoria de cada extremo publicado e de cada extremo escolhido está em `06_AUDITORIA_PLAUSIBILIDADE.csv`.

## 1. Resposta curta

As séries ficam sem os três cenários por **três mecanismos de pesos diferentes**:

1. **A regra de seleção do produto é por métrica, não por série** (477 posições). O gerador escolhe o Conservador e o Agressivo pela trajetória **agregada nacional** e aplica o mesmo modelo a todas as distribuidoras. Quando nenhum modelo tem agregado abaixo ou acima do Moderado, a métrica inteira fica sem o extremo, mesmo que, na distribuidora, haja um modelo competitivo e coerente.
2. **Falta de modelo alternativo distinto** (950 posições). Os modelos dentro da tolerância de erro ficam do lado oposto do Moderado (A2), coincidem com ele (D), cruzam-no (C) ou têm erro acima da tolerância (B). Isso é comum quando o Moderado é a persistência, em ativos que quase não mudam (conjuntos, barramentos, reatores, seccionalizadores).
3. **Problemas de dados** (241 séries sem Moderado, com as 482 posições de extremo). Os motivos são:
   - competência 2023 não homologada (`BLOQUEIO_COMPETENCIA`);
   - publicações não localizadas;
   - rupturas cadastrais.

**Achado de qualidade, anterior à RC e já presente em produção.** Dos **2.495 extremos publicados**, **1.084 não passam na regra de ordem e de diferença material** (seção 6 do protocolo):
- **732** ficam do lado oposto ao Moderado em todos os anos: Agressivo abaixo ou Conservador acima;
- **350** coincidem com ele ou diferem menos de 0,05 p.p./ano, ou menos de 1 unidade;
- **2** são implausíveis.

Por isso, das **755** séries publicadas como completas, só **185** têm três cenários defensáveis pela regra C ≤ M ≤ A. O produto em produção (`74190e2`, 28/10/2026) tem o mesmo defeito: 456 Agressivos e 274 Conservadores do lado oposto, comparando os inteiros publicados.

## 2. Universo e posições

| | Séries | Posições ausentes |
|---|---|---|
| Completas (3 cenários publicados) | 755 | 0 |
| Parciais, com 2 cenários | 985 | 985 |
| Parciais, com 1 cenário (só o Moderado) | 221 | 442 |
| Sem previsão | 241 | 723 (241 Moderados + 482 extremos) |
| **Total** | **2.202** | **2.150** |

## 3. Causas das 1.427 posições de extremo ausentes em séries com Moderado

| Código | Causa | Conservador | Agressivo | Total | % |
|---|---|---|---|---|---|
| **I** | elegível e coerente na distribuidora, mas rejeitado pelo critério agregado nacional | 201 | 276 | **477** | 33,4% |
| **A2** | todos os modelos competitivos ficam do lado oposto ao Moderado na série | 257 | 184 | **441** | 30,9% |
| **B** | há modelos elegíveis, mas nenhum com WAPE ≤ 1,25 × o do Moderado | 127 | 127 | **254** | 17,8% |
| **D** | o melhor competitivo coincide com o Moderado (diferença < 0,05 p.p./ano ou < 1 unidade) | 159 | 49 | **208** | 14,6% |
| **C** | o melhor competitivo cruza o Moderado | 20 | 16 | **36** | 2,5% |
| **E** | o melhor competitivo é fisicamente implausível na série | 6 | 5 | **11** | 0,8% |
| A1 | nenhum outro modelo elegível na métrica | 0 | 0 | 0 | — |
| F | nenhum competitivo projeta a série | 0 | 0 | 0 | — |
| J | outra causa | 0 | 0 | 0 | — |

A tabela usa só os 9 modelos originais do gerador e o critério de tolerância do próprio produto, sem nenhum modelo novo. A causa I mede o que se recupera **apenas mudando a seleção** de agregada para série a série.

## 4. Causas das 241 séries sem Moderado

| Código | Causa | Séries | Detalhe |
|---|---|---|---|
| **G** | ruptura ou problema cadastral | **169** | 123 por competência não homologada (`BLOQUEIO_COMPETENCIA`, sobretudo 2023: Chesp, Coprel, Certaja, Cermoful, Coopercocal, Cetril, Ceral Araruama); 46 por ruptura (`alteracao_classificacao` 21, `alteracao_cadastral` 13, sem tipo 6, `sem_evidencia_suficiente` 4, `anomalia_fonte` 2) |
| **F** | falta histórico comparável | **66** | 37 publicações não localizadas; 15 sem registro (potência fora dos portões de qualidade EQ→UN); 12 `zero_verificado`; 2 entidades vazias na origem |
| **E** | Moderado implausível na série | **6** | razão 2030/2025 fora de [0,5; 3] |

**121** dessas séries têm 2 anos contíguos comparáveis, de 2024 a 2025, e um Moderado de painel. Elas teriam Moderado se o histórico mínimo baixasse de 3 para 2 anos (`MODERADO_RECUPERAVEL_SOB_DECISAO_DE_CONTRATO`). Isso não foi aplicado:
- é uma mudança de contrato;
- não há ponto de backtest dessas séries;
- é uma decisão do responsável.

## 5. Seleção ou dados (pergunta 2)

| Grupo | Posições | Composição |
|---|---|---|
| Seleção de modelos | **477** | I |
| Evidência de modelo (não há alternativa distinta e competitiva) | **950** | A2 441, B 254, D 208, C 36, E 11 |
| Qualidade dos dados | **235 Moderados + 470 extremos** | G 169 e F 66 séries |
| Implausibilidade do Moderado | **6 Moderados + 12 extremos** | E |

Somando-se os extremos publicados reprovados (1.084), o problema de **seleção** é maior do que as ausências mostram. A mesma regra agregada que deixa 477 posições vazias publica 1.084 extremos que não representam um cenário mais baixo ou mais alto naquela distribuidora.

## 6. Por métrica

Colunas: Moderado ausente (G/F/E); as causas I a E dos extremos ausentes; e os publicados reprovados (lado oposto / coincidente / implausível).

| Métrica | Séries | G/F/E | I | A2 | B | D | C | E | Publicados reprovados |
|---|---|---|---|---|---|---|---|---|---|
| alimentadores/quantidade | 99 | 7/2/0 | 0 | 0 | 0 | 0 | 0 | 1 | 55/54/0 |
| bancos_capacitores/quantidade | 98 | 9/2/0 | 0 | 0 | 0 | 0 | 0 | 0 | 59/16/0 |
| barramentos/quantidade | 70 | 8/2/0 | 0 | 28 | 0 | 32 | 0 | 0 | 0/33/0 |
| chaves/quantidade | 99 | 11/2/1 | 0 | 0 | 0 | 0 | 0 | 0 | 84/11/0 |
| circuitos_at/quantidade | 38 | 2/1/1 | 16 | 12 | 0 | 6 | 0 | 0 | 2/2/0 |
| conjuntos/quantidade | 99 | 7/2/0 | 1 | 0 | 0 | 89 | 0 | 0 | 21/55/0 |
| consumidores/quantidade | 98 | 8/2/0 | 60 | 26 | 0 | 2 | 0 | 0 | 0/0/0 |
| disjuntores/quantidade | 63 | 7/3/1 | 0 | 0 | 0 | 0 | 0 | 0 | 35/14/0 |
| geradores/quantidade | 98 | 6/2/0 | 64 | 75 | 0 | 11 | 30 | 0 | 0/0/0 |
| iluminacao/quantidade | 99 | 7/2/0 | 4 | 77 | 0 | 9 | 0 | 0 | 8/6/0 |
| medidores/quantidade | 99 | 6/2/0 | 48 | 40 | 0 | 3 | 0 | 0 | 41/10/0 |
| postes/quantidade | 99 | 6/2/0 | 83 | 4 | 0 | 2 | 1 | 2 | 48/3/0 |
| ramais/extensao_km | 99 | 6/2/0 | 54 | 34 | 0 | 2 | 0 | 1 | 30/4/0 |
| reatores/quantidade | 13 | 0/2/0 | 0 | 0 | 22 | 0 | 0 | 0 | 0/0/0 |
| rede_at/extensao_km | 53 | 3/1/0 | 0 | 0 | 0 | 0 | 0 | 1 | 28/0/0 |
| rede_bt/extensao_km | 99 | 6/2/0 | 0 | 0 | 0 | 0 | 0 | 0 | 48/0/1 |
| rede_mt/extensao_km | 99 | 6/2/0 | 0 | 0 | 0 | 0 | 0 | 0 | 70/11/1 |
| reguladores/quantidade | 91 | 7/2/0 | 53 | 15 | 0 | 14 | 0 | 1 | 31/9/0 |
| religadores/quantidade | 99 | 10/3/1 | 34 | 33 | 0 | 10 | 5 | 3 | 6/3/0 |
| seccionalizadores/quantidade | 32 | 2/2/0 | 0 | 0 | 56 | 0 | 0 | 0 | 0/0/0 |
| subestacoes/quantidade | 71 | 5/1/0 | 0 | 0 | 0 | 0 | 0 | 0 | 21/59/0 |
| torres/quantidade | 58 | 3/5/0 | 0 | 33 | 0 | 17 | 0 | 0 | 0/17/0 |
| trafo_dist/potencia_kva (kVA, experimental) | 99 | 3/8/1 | 0 | 0 | 0 | 0 | 0 | 0 | 81/7/0 |
| trafo_dist/quantidade | 99 | 9/2/0 | 0 | 0 | 176 | 0 | 0 | 0 | 0/0/0 |
| trafo_forca/potencia_kva (kVA, experimental) | 70 | 3/7/0 | 27 | 23 | 0 | 10 | 0 | 1 | 14/0/0 |
| trafo_forca/quantidade | 71 | 8/2/1 | 0 | 0 | 0 | 0 | 0 | 0 | 33/36/0 |
| trafo_medida/quantidade | 90 | 14/1/0 | 33 | 41 | 0 | 1 | 0 | 1 | 17/0/0 |

**Padrões:**
- **Seleção dominante (I):** consumidores, postes, ramais, medidores, reguladores, geradores e religadores. Nelas, o produto não publica um dos extremos, mas existem modelos competitivos coerentes série a série.
- **Moderado = persistência** (barramentos, conjuntos, iluminação, reatores, seccionalizadores, trafo_forca kVA). A alternativa coincide com o Moderado ou fica do lado oposto. Em conjuntos, o melhor competitivo coincide com o Moderado em 89 das 99 séries, porque o número de conjuntos quase não muda. Um Conservador distinto não tem base.
- **Erro excessivo (B):** em trafo_dist/quantidade (176 posições), o KNN do Moderado tem WAPE 1,11%. O melhor outro original, o Random Forest, tem 1,40%, acima da tolerância de 1,38%. Reatores e seccionalizadores têm amostras pequenas.
- **Publicados reprovados:** concentram-se onde o produto tem os três cenários na métrica: chaves 84, trafo_dist kVA 81, rede MT 70, bancos 59, alimentadores 55, rede BT 48. O modelo extremo escolhido pelo agregado fica do lado errado em boa parte das distribuidoras.

## 7. Por família e por empresa

| Família | Séries | Completas publicadas | Completas defensáveis (antes) |
|---|---|---|---|
| Clientes (consumidores, geradores, iluminação) | 295 | 0 | 0 |
| Medição (medidores, trafo de medida) | 189 | 0 | 0 |
| Estruturas (postes, torres) | 157 | 0 | 0 |
| Redes (AT, MT, BT, ramais) | 350 | 230 | 87 |
| Transformação | 339 | 147 | 29 |
| Seccionamento e proteção | 293 | 137 | 24 |
| Subestações e circuitos | 377 | 154 | 25 |
| Regulação e compensação | 202 | 87 | 20 |

Por empresa, 99 distribuidoras:
- a mediana da fração de séries completas publicadas é 38%;
- **26 distribuidoras não têm nenhuma série com três cenários defensáveis antes**;
- 8 cooperativas ficam sem nenhuma previsão em todas as séries, porque a competência 2023 está bloqueada ou falta 2024 ou 2025.

O detalhe por empresa está em `07_COBERTURA_ANTES_DEPOIS.csv` (nível `empresa`).

## 8. Limitações do diagnóstico

- **Escopo da causa I:** a causa I usa a tolerância de erro do produto (WAPE ≤ 1,25 × o do Moderado). Esse WAPE inclui pontos de 2025, já consultados na escolha do Moderado. A causa mede a regra, não uma validação.
- **Ordem da precedência das causas:** a ordem COERENTE > IMPLAUSIVEL > CRUZA > COINCIDE > LADO_OPOSTO foi fixada no protocolo. Outra ordem mudaria a divisão entre E, C, D e A2, mas não o total.
- **Potência (kVA):** as métricas em kVA continuam experimentais e não homologáveis (dossiê científico). Elas aparecem marcadas na matriz.
