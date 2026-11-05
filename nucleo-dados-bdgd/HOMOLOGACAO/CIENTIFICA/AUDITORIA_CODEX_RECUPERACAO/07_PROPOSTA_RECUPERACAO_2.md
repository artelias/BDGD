# 07 — Proposta de protocolo `recuperacao-2` (portabilidade numérica)

**Estado: PROPOSTA.** Não foi aplicada, não substitui a `recuperacao-1` e precisa de aceite humano antes de qualquer execução confirmatória.

**Princípios:**
- **Preserva a versão 1:**
  - nenhum resultado, arquivo ou critério da `recuperacao-1` (`d478e16`) muda;
  - os 711, 1.039 e 1.239 continuam sendo os resultados da versão 1 no ambiente de referência.
- **Escopo restrito:** a proposta só trata da **reprodução entre plataformas**. Não toca em:
  - modelos, variáveis e dados;
  - tolerância de 1,25, diferença mínima de 0,05 p.p./ano, razão [0,5; 3] e percentis;
  - precedência P1–P6.

## 1. Por que a versão 1 não é portável

| Fato (seção da auditoria) | Consequência |
|---|---|
| O WAPE publicado e o gabarito foram gerados no Windows. Lá a reprodução é exata: \|ΔWAPE\| = 0 nos 243 modelos originais, e as duas execuções do zero são idênticas byte a byte | a exigência de \|Δ\| < 1e-9 vale **só** no ambiente de referência |
| `math.log` da UCRT difere do arredondamento correto em 1 ULP em ~0,07% das chamadas, e o glibc difere da UCRT em parte delas. Isso basta para o RF de bancos de capacitores dar \|ΔWAPE\| = 1,3e-6 (reproduzido bit a bit no Windows) | 1e-9 não é atingível entre Windows e Linux para RF; o limite mede a libm, não a ciência |
| O `knn_analogos_otim` (e outros 2 KNN otimizados) tem empates exatos de distância na fronteira da vizinhança | o resultado depende de como a busca desempata; não é reprodutível nem em princípio |
| O HGB é sensível a perturbações que desfazem duplicatas exatas (só no teste de estresse) | registrar como risco; uma plataforma real preserva duplicatas |
| A seleção depende de comparações com limiar (1,25 × WAPE; Q5–Q8; arredondamento meio para cima) | uma decisão perto do limiar pode mudar com ruído de último dígito; isso precisa ser medido, não presumido |

**Evidência empírica:** `04_sensibilidade/` (outra libm; ruído de libm determinístico de 0,1% e 1% das chamadas; estresse de ±1 ULP) e o resumo no parecer `00`.

## 2. Ambiente canônico

- **Números publicados:** são gerados em um único ambiente canônico, registrado com sistema, versões de Python, NumPy, SciPy e scikit-learn, CPU e libm. Hoje é o Windows de `.venv-motor`.
- **Outros ambientes, como o CI Linux:** **verificam**, não regeneram números para publicação.
- **Tolerância de ambiente:** igual à do `--check` público, que já documenta o ruído entre plataformas.

## 3. Critérios de reprodução por camada

| Camada | No ambiente canônico | Em outro ambiente |
|---|---|---|
| R1. Escolhas: modelo agregado por métrica e posição; modelo de cada extremo por série e lado; classe da série | idênticas | **idênticas (tolerância zero)** |
| R2. Valores publicados | idênticos byte a byte | tolerância do `--check`: 0,5% relativo ou 1e-4; contagens com folga de 1 unidade limitada a max(20; 0,5%) |
| R3. WAPE e demais erros | \|Δ\| < 1e-9 (critério da v1, mantido) | \|Δ\| ≤ ε_W, com ε_W = 2e-5: o dobro do maior desvio com outra libm (1,08e-5, RF otimizado). Com ruído 14× o observado, chegou a 3,4e-5; por isso R3 é relatado, não bloqueante |
| R4. Configurações X (S e F contra o registro de 6 decimais) | \|Δ\| ≤ 5e-7 | \|Δ\| ≤ 5e-7 + ε_W |

Se R3 ou R4 falhar fora do ambiente canônico, o resultado é **relatado**, sem bloquear, desde que R1 e R2 passem. Uma falha de R1 bloqueia sempre.

## 4. Certificado de margem (pré-registrado)

Para **cada decisão** com limiar, a execução canônica grava a margem até o limiar:
- competitividade: W_c − 1,25·W_M;
- ordem P2: diferença de WAPE para o próximo candidato;
- Q5: min s·(E_t − M_t);
- Q7: s·(g_E − g_M) − 0,0005;
- Q8: s·(E_2030 − M_2030) − 1;
- Q2–Q4: distância relativa aos limites;
- arredondamento: distância de cada valor bruto ao meio inteiro.

**Regras de fragilidade:**
- **Limiares:** uma decisão é **FRÁGIL** se sua margem estiver abaixo de:
  - δ_W = 1e-4 nas comparações de WAPE;
  - δ_g = 1e-6 em g;
  - δ_rel = 1e-3 relativo nas trajetórias de RF e HGB, e 1e-9 nas demais;
  - 1e-6 do meio inteiro no arredondamento.
- **Decisão frágil:** não muda o resultado da v1, mas é listada e testada em outro ambiente.
- **Teste do certificado:** em outro ambiente, R1 só pode divergir em decisões FRÁGEIS. Uma divergência em decisão não frágil reprova o certificado.

## 5. Correções de determinismo (exigem nova configuração e não são retroativas)

| Item | Proposta | Tratamento |
|---|---|---|
| KNN com empate exato | desempate determinístico por (distância, índice de treino estável) ou inclusão de todos os empatados na fronteira | é uma configuração nova; o `knn_analogos_otim` e os KNN otimizados de chaves e geradores ficam BLOQUEADOS na v1 |
| `log` e `exp` das variáveis | calcular com arredondamento correto (`decimal`, só biblioteca padrão; custo medido de ~2 s por execução nacional) | muda bits das variáveis; reexecutar e comparar com a v1 (seção 6) |
| Q7 sobre valores publicados (O-1) | exigir a diferença mínima também nos valores publicados, como a Q8 já faz | **observação feita depois do resultado** (afeta 1 série conhecida); só entra se aceita como regra nova, nunca retroativamente na v1 |

## 6. Validação da v2 (antes de qualquer uso)

1. Commit deste protocolo, com os valores numéricos acima, **antes** de qualquer execução da v2.
2. **Execução canônica da v2:**
   - sem as correções da seção 5, precisa reproduzir a v1 exatamente (R1–R3 com tolerância zero);
   - com as correções, relata toda mudança de escolha ou de valor em relação à v1;
   - critério de **não mudança material**: 0 mudanças de classe e ≤ 0,5% dos extremos com modelo diferente, cada uma explicada por decisão FRÁGIL.
3. **Execução em Linux (CI ou Codex)**, modo originais: R1 e R2 obrigatórios; R3 e R4 relatados; certificado de margem testado.
4. **Sensibilidade:** ruído de libm de 0,1% e 1% das chamadas, ≥ 5 sementes, nas mesmas condições da auditoria. Nenhuma mudança de escolha em decisão não frágil.
5. **Preservação:** a v1 fica intacta; a v2 grava em diretórios novos, com hashes.

## 7. Fora do escopo

- Novos modelos, novas variáveis, competência 2026.
- Promoção de otimizados, condicionais ou kVA: são decisões D4, D5 e kVA, independentes desta proposta.
- Nenhuma conclusão de homologação: a competência 2025 continua consultada.
