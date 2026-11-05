# 00 — Parecer técnico independente: entrega do Codex, extremos publicados e reprodução numérica

**Data:** 2026-11-05.

**Responsabilidades:** o Claude (Opus) define e audita a metodologia; o Codex implementa.

**Estado:**
- **NÃO ASSINADO. EXPERIMENTAL.** Não é homologação científica: a competência 2025 já foi consultada, e os horizontes de 2026 a 2030 não são homologáveis.
- **Nada foi alterado** na RC 1.0 (`dba5fdf`), no PR #22, na produção (`74190e2`), nos dados originais ou na branch do Codex. Não houve merge nem deploy.

**Bases:**
- RC `rc/1.0-20261101@dba5fdf`;
- protocolo `recuperacao-1@d478e16`;
- pesquisa `exp/recuperacao-cenarios-20261104@6ec3b6d`;
- entrega `codex/recuperacao-cenarios-20261105@14f4e61`.

**Ambiente de referência:** Windows 10 19045, Python 3.14.3, NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.8.0. Nada foi instalado. Todos os processos rodaram com uma thread. O pico de memória medido foi de 199 MB, no processo de sensibilidade nacional.

## Respostas objetivas

**1. Os extremos incorretos já publicados foram confirmados?**

**Sim.** No JSON público da RC (`cenarios-motor.json`, blob `9fa6ca1`, idêntico em `6ec3b6d` e `14f4e61`), **1.084 dos 2.495 extremos** violam a ordem ou a diferença material:
- **1.028 são reprovados só pelos valores publicados**, com verificador novo e sem reexecutar modelos:
  - 673 estão do lado oposto ao Moderado: em 602 a inversão vale nos 5 anos, em 71 em 1 a 4 anos;
  - 292 são idênticos ao Moderado nos 5 anos;
  - 61 têm diferença imaterial;
  - 2 são implausíveis.
- **56 têm diferença criada só pelo arredondamento**, porque a trajetória contínua fica a menos de 1 unidade ou de 0,05 p.p./ano do Moderado.
- A soma fecha 1:1 com a auditoria `06` do protocolo.

**Extensão do defeito:**
- 3.015 valores anuais com ordem violada, em 631 séries: 1.933 Agressivos abaixo do Moderado e 1.283 Conservadores acima;
- só **185** das 755 séries "completas" são defensáveis.

**Exemplos** (detalhe em `01_extremos_publicados/EVIDENCIA_ANUAL_RC_dba5fdf.csv`):

| DIST | Ativo / métrica | Ano | Conservador | Moderado | Agressivo | Regra violada |
|---|---|---|---|---|---|---|
| 26 (Energisa AC) | alimentadores / quantidade | 2026–2030 | 128 … 148 | 129 … 154 | 128 … 150 | Q6: A < M nos 5 anos; Q7; Q8 |
| 26 | rede MT / km | 2030 | 21.700,508 | 23.854,595 | 22.415,350 | Q6: A < M nos 5 anos; Q7 |
| 88 | transformadores de medida / quantidade | 2030 | — | 53 | 29 | Q6: A 45% abaixo de M |
| 5160 | reguladores / quantidade | 2030 | 497 | 268 | — | Q6: C 85% acima de M |

**Produção** (`74190e2`, blob diferente): 730 extremos com ordem violada e 921 com contagem não inteira. Só 102 séries completas são defensáveis.

**Conclusão: é um bloqueio de publicação.**

**2. Qual correção aplicar na RC 1.0.1?**

**Opção A: bloquear os extremos incoerentes, mantendo os modelos atuais.**

| | A (bloquear) | B (originais por DIST) |
|---|---|---|
| Completas (todas / sem kVA) | 185 / 170 | 711 / 647 |
| Números novos publicados | 0 | 885 trajetórias |
| WAPE do extremo ÷ Moderado (mediana) | 1,136 | 1,081 |
| Contrato, interface e Metodologia | inalterados (texto da regra) | `cenarios-motor-2`, legenda por série, regra nova |
| Aceite científico | desnecessário (só remove) | necessário |
| Risco de regressão | baixo | médio |

- **Por que A agora:** a A corrige a semântica por completo sem publicar números novos, sem mudar a metodologia e sem depender de um parecer assinado. Isso respeita a prioridade definida: corrigir os cenários públicos primeiro e só depois buscar cobertura.
- **Por que B depois:** a B é melhor em cobertura e desempenho. Ela já está validada nacionalmente no ambiente de referência e fica para o incremento seguinte, num PR separado. Especificação e gabarito em `02_opcoes_rc_1_0_1/`.

**3. Os 60 recuperados pelo Codex estão corretos?**

**Sim.** No Windows, o piloto reproduz byte a byte:
- as trajetórias (`cenarios.csv`), a cobertura e o gabarito do Linux;
- 0 divergências nas 98 séries;
- os 60 são idênticos ao subconjunto de consumidores da execução nacional.

**Preservação e regras:**
- o Moderado e o histórico estão preservados byte a byte;
- a seleção é por DIST, com a precedência e o desempate da referência;
- as regras Q1–Q9 são aplicadas pela função única;
- a ordem vale nos 5 anos.

**4. Qual a causa da divergência de WAPE?**

A causa é a **libm da plataforma**:
- a função `math.log` da UCRT (Windows) e a do glibc (Linux) diferem em 1 ULP em algumas entradas: 24 de 35.522 chamadas diferem do arredondamento correto;
- o Random Forest de bancos de capacitores transforma essa diferença de último dígito numa divisão de árvore diferente.

**Prova:** no Windows, ao trocar só o `math.log` por um log de arredondamento correto, o WAPE fica **0.06005597829053297, igual bit a bit ao valor do Linux**. Os outros 8 modelos não mudam.

**Causas descartadas:**
- dados (hashes iguais);
- código e parâmetros (blob de `cenarios.py` igual);
- estado aleatório (`random_state=42`, `n_jobs=1`);
- versão do scikit-learn (1.8.0 nos dois);
- agregação do WAPE (a mesma função);
- ordem de processamento.

As diferenças de versão de Python, NumPy e SciPy não são necessárias para explicar o caso.

**Origem do valor de referência:** foi gerado no Windows (`d75a29c`). Por isso só o Windows o reproduz com Δ = 0.

**5. O ambiente Windows consegue reproduzir o gabarito?**

**Sim, integralmente.** Execução nacional no modo originais:
- |ΔWAPE| = 0 nos 243 modelos das 27 métricas com séries (o produto lista 29 métricas, 2 delas sem séries);
- escolhas agregadas idênticas;
- 0 divergências contra `02` (2.202 séries) e contra `06` (2.869 linhas);
- saída 0.

Duas execuções do zero, sem cache, em processos separados, saíram **idênticas byte a byte**. Os modos otimizados e condicionais também passam no gabarito no Windows.

**6. Qual a causa das 113 divergências dos otimizados?**

**Uma só:** no Linux, o portão de reprodução S/F bloqueou o `knn_analogos_otim` de consumidores. As posições que ele ocupava no gabarito passaram para outro candidato:
- 36 Agressivos: 36 divergências de modelo, 36 de valor 2030 e 36 de estado;
- 3 de classe e 2 de Q7.

**Por que o KNN otimizado diverge:** ele tem **empates exatos de distância** na fronteira dos 15 vizinhos, com uma única variável e linhas de treino duplicadas:
- os empates aparecem em 25 de 86 consultas da etapa S e em 45 de 88 da etapa F;
- o vizinho incluído depende do desempate da busca: com os mesmos dados, mudar só o algoritmo ou o `leaf_size` move F entre 0,02310 e 0,02336;
- a troca da libm não altera o KNN. A implementação exata do desempate no Linux foi inferida, não observada.

**Consequências para os otimizados:**
- Mais 2 KNN otimizados (chaves e geradores) têm a mesma fragilidade.
- 4 RF otimizados mudam até 1,1e-5 com outra libm.
- Os 104 otimizados reproduzem o registro no Windows.
- **Os otimizados não são liberados:** o `knn_analogos_otim` e os KNN de chaves e geradores ficam BLOQUEADOS, e os demais seguem EXPERIMENTAIS.

**7. Quantos cenários ficaram completos na execução nacional validada?**

**711 séries completas**, todas COMPLETA_INDEPENDENTE, no modo originais no ambiente de referência. O restante: 1.250 parciais e 241 sem previsão; sem kVA, 647.

**Extremos:** 2.296 = 1.411 publicados mantidos + 885 originais escolhidos por série.

**Comparação com as bases anteriores:**
- contra a base defensável (185 séries): +526;
- contra a contagem nominal publicada (755): −44. São 333 recuperadas e 377 que deixam de ser completas porque o extremo publicado é reprovado e não há original coerente.

O resultado é igual ao da execução científica de referência (711), sem forçar igualdade: o gabarito foi usado só como oráculo.

**Modos diagnósticos (não liberados):**
- otimizados: 1.039;
- condicionais: 1.239, dos quais 1.039 independentes, 199 mistos e 1 condicional.

**8. Houve perda de qualidade?**

**Não.**
- **Regras:** os 2.296 extremos passam em Q1–Q9, e a validação independente V1–V8 não tem falhas. A única observação é o caso limítrofe O-1: reguladores, DIST 6587, com 0,049 p.p./ano nos inteiros publicados.
- **Desempenho:**
  - a mediana da razão entre o WAPE do extremo e o do Moderado cai de 1,136 para 1,081;
  - o WAPE local mediano cai de 0,0287 para 0,0275.
- **Moderado:** ficou intocado.
- **As 377 séries que deixam de ser completas não são perda de qualidade.** É a remoção de extremos que contradiziam o próprio rótulo, e cada uma tem a causa registrada.

**9. O que pode ser integrado com segurança?**

| Item | Situação |
|---|---|
| Opção A (bloqueio) na RC 1.0.1 | **seguro**, depois da implementação, do gabarito, do CI completo e da inspeção do preview |
| Opção B (originais por série) | **pronto para aceite científico**, não para publicação. Antes: D2, correção de D-1 a D-3, verificação R1 em Linux e regressão completa |
| Otimizados, B-HIST, N1, N2 e N5 | **não**: EXPERIMENTAIS |
| KNN otimizados com empate | **não**: BLOQUEADOS |
| N6 | **não**: REPROVADO |
| kVA | **não**: EXPERIMENTAL |
| Pacote `motor_cenarios/recuperacao/` | **só** como ferramenta experimental, fora do produto |

**10. Qual o próximo commit e PR?**

1. **Este commit:** dossiê de auditoria, execuções no Windows e scripts, em `exp/auditoria-codex-recuperacao-20261105`. O PR, se você quiser, é em rascunho, só de documentação experimental e com base na branch do Codex. Não vai para produção.
2. **Codex, próximo PR (RC 1.0.1):**
   - branch `rc/1.0.1-20261106`, criada a partir de `dba5fdf`, com a opção A conforme `02_opcoes_rc_1_0_1/ESPECIFICACAO_RC_1_0_1.md`;
   - PR **em rascunho** com a mesma base do PR #22, sem tocar no #22;
   - aceite: gabarito de 2.495 linhas, `verificar_publicado.py` com 0 reprovados, CI verde nos 5 workflows, Playwright completo e preview inspecionado.
3. **Codex, na branch experimental:** correção de D-1 a D-3 (encoding, teste de determinismo sem cache, base defensável na cobertura) e bloqueio explícito dos 3 KNN otimizados com empate.
4. **Depois de D2:** PR separado da opção B (RC 1.0.2 ou 1.1).

## Matriz de status por modelo e métrica

O arquivo completo, com justificativa por linha, está em `06_MATRIZ_STATUS_MODELO_METRICA.csv`. Segue o resumo por categoria de candidato.

| Categoria | Linhas | APROVADO | REPROVADO | BLOQUEADO | EXPERIMENTAL |
|---|---|---|---|---|---|
| O, 9 originais × 27 métricas | 243 | **102** (25 Moderados preservados + 77 originais competitivos, reproduzidos e estáveis) | 124 (não competitivos ou implausíveis) | 6 (5 de reatores, sem evidência suficiente; `hgb_painel` em rede MT, pela mudança de 1 série sob ruído de 1%) | 11 (kVA) |
| X, 4 otimizados × 26 métricas | 104 | 0 | 27 | 2 (`knn_analogos_otim` de consumidores e de chaves, por empate) | 75 (D4) |
| B-HIST (condicional) | 27 | 0 | 0 | 0 | 27 (D5) |
| N1, N2n e N2g (novos) | 81 | 0 | 60 | 0 | 21 (congelados até 2026) |
| N5 (quantil condicional) | 54 | 0 | 26 (não calibrado) | 0 | 28 (congelado) |
| N6 (elasticidade) | 6 | 0 | 6 | 0 | 0 |
| H (hierárquicos do piloto) | 2 | 0 | 0 | 2 (sem contrato DIST) | 0 |
| **Total** | **517** | **102** | **243** | **10** | **162** |

**Originais por modelo** (APROVADO / REPROVADO / BLOQUEADO / EXPERIMENTAL, nas 27 métricas):

| Modelo | APR | REP | BLO | EXP |
|---|---|---|---|---|
| KNN | 22 | 2 | 1 | 2 |
| RF | 18 | 6 | 1 | 2 |
| Ridge | 16 | 8 | 1 | 2 |
| Ridge com externas | 15 | 9 | 1 | 2 |
| Persistência | 13 | 13 | 0 | 1 |
| HGB | 12 | 11 | 2 | 2 |
| Deriva | 3 | 24 | 0 | 0 |
| Tendência OLS | 3 | 24 | 0 | 0 |
| Crescimento geométrico | 0 | 27 | 0 | 0 |

O KNN de geradores tem empate, mas já era REPROVADO por trajetória implausível (78 de 90 séries).

**Como ler a matriz:**
- **APROVADO** quer dizer pronto para integração como fonte de extremo por série no ambiente de referência, sujeito a D2 e ao aceite. **Não é homologação.**
- **O Moderado preservado conta como APROVADO**, exceto em kVA.

## 3. Reprodução numérica e sensibilidade

### 3.1 Ambiente Windows

O Windows reproduz tudo: WAPE com Δ = 0, gabarito, determinismo do zero e o `--check` público (29 métricas).

**Testes do pacote:**
- 59 passam com `PYTHONUTF8=1`;
- sem essa variável, 7 dão erro por `read_text()` sem encoding (D-1).

### 3.2 Causa das divergências

Ver as respostas 4 e 6 e `03_causa_wape/`.

**Limite da emulação por log correto:**
- ela é exata em bancos de capacitores;
- em alimentadores, muda o RF em 6,4e-6, enquanto o Linux não mudou. Ou seja, o glibc coincide com a UCRT nas entradas relevantes dessa métrica.

Em todos os casos, 1 ULP em entradas específicas basta.

### 3.3 Sensibilidade das escolhas (base da proposta `recuperacao-2`)

Comparação com a execução nacional de referência (modo originais, 2.202 séries). Os 9 originais são reconstruídos em cada cenário.

| Cenário | Tipo | Escolha agregada mudou | Máx. \|ΔWAPE\| | Decisões da opção A que mudaram | Opção B: modelo ou classe mudou | Valores fora da tolerância do `--check` | Valores dentro da tolerância |
|---|---|---|---|---|---|---|---|
| outra libm (log/exp corretos) | realista | 0 de 27 | 6,4e-6 | 0 | 0 | 0 | 1 |
| ruído de libm 0,1%, sementes 1–4 | realista | 0 | ≤ 2,2e-7 | 0 | 0 | 0 | 0–1 |
| ruído de libm 1%, semente 5 | realista (14× a taxa observada) | 0 | 3,4e-5 | 0 | 0 | 0 | 18 |
| ruído de libm 1%, semente 6 | realista (14×) | 0 | 8,9e-7 | 0 | **1** (rede MT, DIST 5355: Agressivo `hgb_painel` deixa de ser coerente) | 0 | 7 |
| ±1 ULP aleatório, sementes 1–6 | estresse (desfaz duplicatas) | 0 | ≤ 2,7e-3 (só HGB) | 3–9 | 9–20 | 19–25 | 11–17 |

**Conclusão:**
- **Escolhas agregadas e opção A:** sob ruído realista de plataforma, não mudam em nenhum dos 7 cenários.
- **Opção B:** mudou 1 escolha em 885, e só com uma taxa de ruído 14 vezes maior que a observada. Essa série fica listada como frágil, e o modelo foi marcado BLOQUEADO na métrica (rede MT, HGB) até a `recuperacao-2`.
- **Exigência de 1e-9 para o WAPE:** é incompatível com o RF fora do ambiente que gerou os números. Mas as escolhas, que são o que importa cientificamente, são estáveis.

**Leitura:**
- **Cenários realistas** (outra libm; ±1 ULP determinístico por argumento em 0,1% ou 1% das chamadas de `log` e `exp`):
  - medem o que outra plataforma faria;
  - mantêm as escolhas agregadas em 27 de 27 métricas.
- **Cenário de estresse** (±1 ULP com sinal aleatório em cada entrada):
  - desfaz duplicatas exatas, o que nenhuma plataforma faz;
  - expõe só o HGB, cuja discretização depende de valores repetidos;
  - os outros 8 originais mudam menos de 1e-12.

**Margens das decisões** (`04_sensibilidade/MARGENS_RESUMO.json`):
- **Opção A:** 270 das 2.495 decisões estão a menos de 1e-3 do limiar. Dessas, 92 são empates exatos entre persistência e KNN, iguais em qualquer plataforma.
- **Opção B:** 70 das 885 escolhas novas estão a menos de 1e-3. Além disso, 48 contagens de geradores (tendência OLS) têm o valor bruto a menos de 1e-8 de x,5 e podem variar 1 unidade entre plataformas; isso fica coberto pela folga do `--check`.

### 3.4 Otimizados (`04_sensibilidade/SENSIBILIDADE_X.csv`)

| Algoritmo | Configurações | Reproduzem no Windows | Mudam com outra libm (> 1e-9) | Mudam sob estresse |
|---|---|---|---|---|
| Ridge | 26 | 26 | 0 | 0 (< 2e-16) |
| RF | 26 | 26 | 4 (até 1,08e-5) | 0 |
| HGB | 26 | 26 | 0 | 15 |
| KNN | 26 | 26 | 0 | 3 (os empates: chaves, consumidores, geradores) |

## 4. Desvios e limites desta auditoria

1. **Exatidão da emulação do Linux:** foi exata em bancos (bit a bit), não em geral. Ela não substitui uma execução Linux: R1 em Linux continua pendente.
2. **Desempate do KNN:** a dependência do desempate está demonstrada no Windows. A implementação específica do Linux foi inferida.
3. **Matriz de status:** foi definida nesta auditoria, depois dos resultados, mas só reúne portões já existentes (reprodução, competitividade, coerência, kVA e as decisões D4, D5 e D7) mais a estabilidade sob ruído realista. Não muda nenhum critério de aprovação da `recuperacao-1`.
4. **Desvio meu (D-4):** o `recuperar.py` de referência usa 5e-7 no portão de X, e o protocolo diz 1e-6. Não muda nenhum resultado.
5. **O-1:** caso limítrofe registrado, não aplicado (o critério não muda depois do resultado).
6. **Testes web:** não rodei Vitest nem Playwright. O commit do Codex não toca em `web/`, e a interface da RC 1.0.1 ainda não existe.

## 5. Decisões que dependem de você

| # | Decisão | Recomendação |
|---|---|---|
| D1 | Corrigir os 1.084 extremos antes de publicar | **Sim: opção A na RC 1.0.1** |
| D2 | Adotar a seleção por série (opção B) | Sim, no incremento seguinte, depois do aceite e de R1 em Linux |
| D3 | Produção `74190e2` (ordem e contagens fracionárias) | Corrigir publicando a RC 1.0.1, sem remendar a produção |
| D4 | Otimizados | Manter EXPERIMENTAIS; os 3 KNN com empate BLOQUEADOS |
| D5 | B-HIST | EXPERIMENTAL, só com interface que distinga a simulação condicional |
| D9 | Aceitar a proposta `recuperacao-2` (`07`) | Sim, antes de qualquer execução confirmatória em Linux |
| D10 | Assinar este parecer | — (não assinado) |
