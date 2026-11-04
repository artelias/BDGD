# 07 — Relatório científico do piloto granular e hierárquico

**Branch:** `exp/piloto-granular-hierarquico-20261104`.

**Linha do tempo:**

| Commit | Gate | Conteúdo |
|---|---|---|
| `d988416` | protocolo congelado | antes de qualquer experimento |
| `abd27a0` | Gate 1 | entradas |
| `9be843b` | Gate 2 | seleção congelada, hash `20c9e59a…`, antes da etapa final |
| (este commit) | Gates 3–5 | avaliação final executada **uma vez** |

**Reprodução** (scikit-learn 1.8.0, pyarrow 26, DuckDB 2.0):

```
python HOMOLOGACAO/CIENTIFICA/PILOTO_GRANULAR/piloto.py entrada
python HOMOLOGACAO/CIENTIFICA/PILOTO_GRANULAR/piloto.py selecao
python HOMOLOGACAO/CIENTIFICA/PILOTO_GRANULAR/piloto.py final
python HOMOLOGACAO/CIENTIFICA/PILOTO_GRANULAR/tabelas_relatorio.py
```

`final` recusa rodar duas vezes e recusa uma seleção alterada depois do hash. Os hashes dos contratos e das entradas estão em `00_MANIFESTO_ENTRADA.json`.

## Resposta direta

**Não, de modo geral. A modelagem territorial e hierárquica não previu a expansão dos ativos melhor que os modelos atuais por distribuidora, de forma que justifique substituí-los.**

- **Exceção:** a potência de transformadores (kVA) atendeu os critérios pré-registrados de validação retrospectiva restrita contra o melhor baseline. O ganho sobre o modelo atual (10,6% de WAPE) **não tem suporte estatístico**, e a métrica é experimental.
- **R² do crescimento:** em nenhuma família a variação relativa anual foi prevista de forma útil. O R² do crescimento por distribuidora fica entre −0,39 e +0,11 para os candidatos, e entre −0,40 e +0,06 para os modelos atuais.
- **Os modelos atuais ficam mantidos.**

## Resultados por família (avaliação final: origem 2024, alvo 2025, configuração congelada)

| Família (nível) | Candidato congelado | WAPE candidato | WAPE modelo atual | WAPE melhor baseline | Ganho vs atual (IC95% da diferença) | R² crescimento (candidato / atual) | R² variação (candidato / atual) | Classe |
|---|---|---|---|---|---|---|---|---|
| Consumidores BT (município) | Ridge global, 5 variáveis | 2,367% | 2,380% (`ridge_painel`) | 2,737% (persistência) | +0,5% ([−0,29; +0,25] p.p.) | −0,385 / −0,400 | 0,138 / 0,135 | **SEM_GANHO** |
| Transformadores, quantidade (município) | Ridge global, 7 variáveis | 0,827% | 0,781% (`knn_analogos`) | 0,778% (CAGR) | −5,8% ([−0,24; +0,30] p.p.) | −0,075 / +0,041 | 0,895 / 0,894 | **SEM_GANHO** |
| Transformadores, kVA (conjunto; **métrica experimental**) | Ridge global, 4 variáveis | 6,42% | 7,18% (`ridge_painel`) | 9,47% (persistência) | +10,6% ([−4,7; +1,3] p.p.); vs baseline [−5,4; −1,6] p.p. | −0,077 / +0,033 | 0,387 / −0,031 | **VALIDADO_RETROSPECTIVAMENTE_COM_RESTRICOES** (ver ressalvas) |
| Rede BT (conjunto) | Hierárquico, 1 variável | 0,837% | 1,135% (`ridge_painel`) | 0,822% (deriva) | +26,3% ([−0,88; +0,43] p.p.) | **+0,112** / −0,098 | −2,46 / −0,82 | **SEM_GANHO** (pior que a deriva) |
| Rede MT (conjunto) | HGB, 4 variáveis | 0,860% | 0,598% (`random_forest_painel`) | 0,628% (deriva) | −43,9% (**[+0,03; +0,49] p.p.**: pior, com significância) | −0,071 / +0,064 | 0,161 / 0,492 | **REJEITADO** (ganho só na seleção) |

O vencedor por métrica (WAPE, MAE, RMSE, viés, R² do estoque, R² da variação, MAE da variação e R² do crescimento), entre candidato, modelo atual e melhor baseline, está em `05b_VENCEDOR_POR_METRICA.csv`. Em h=1, o MAE da variação é igual ao MAE do estoque, porque o estoque de origem é conhecido.

**Prever o tamanho × prever o crescimento.** O R² do estoque fica entre 0,971 e 0,9999 em todos os modelos, inclusive na persistência, e não discrimina nada. O R² do crescimento relativo, a medida que importa para a expansão, fica perto de zero ou negativo. **O crescimento anual por distribuidora continua quase imprevisível com 2022–2025**, também com as variáveis territoriais.

## As 14 respostas

1. **Ativos que participaram:** os cinco painéis existentes: `ucbt_quantidade`, `trafo_dist_quantidade`, `trafo_dist_potencia_kva`, `rede_bt_extensao_km` e `rede_mt_extensao_km`. Nenhum foi bloqueado. Geração distribuída e as famílias por DIST ficaram fora, porque não têm painel.

2. **Unidades e transições** (detalhe em `02_COBERTURA_E_EXCLUSOES.csv`):

   | Família | Pares de treino (S / F) | Unidades previstas (S / F) |
   |---|---|---|
   | UCBT (município) | 4.431 / 9.899 | 2.333 / 5.041 |
   | Trafos, quantidade (município) | 3.988 / 9.014 | 1.885 / 5.035 |
   | Trafos, kVA (conjunto) | 2.296 / 3.486 | 892 / 1.124 |
   | Rede BT (conjunto) | 2.343 / 3.691 | 1.037 / 1.288 |
   | Rede MT (conjunto) | 2.526 / 3.900 | 1.221 / 1.314 |

   Por DIST-ano há 3 transições (2022→2023, 2023→2024, 2024→2025), uma origem de seleção e uma origem final. As unidades **não são observações independentes**. O efeito de desenho do diagnóstico 06 vai de 2 a 53, e a inferência reamostra grupos econômicos.

3. **Distribuidoras e grupos avaliados na etapa final:** UCBT 84 DIST / 64 grupos; trafos, quantidade 82 / 64; trafos, kVA 66 / 63; rede BT 69 / 64; rede MT 70 / 64. Na etapa S foram 61–66 DIST, porque a coorte exige comparabilidade nos dois níveis candidatos.

4. **Variáveis selecionadas** (congeladas na etapa S):
   - UCBT: `fracao_urbana`, `ln_trafo_por_cliente`, `ln_kva_por_cliente`, `ln_kwh_cliente`, `eletrificacao`;
   - trafos, quantidade: `ln_kwh_cliente`, `ln_kva_por_trafo`, `cresc_pop_2010_2022`, `eletrificacao`, `fracao_urbana`, `ln_estoque`, `taxa_conexoes`;
   - trafos, kVA: `ln_kva_por_trafo`, `ln_clientes_por_kva`, `ln_kwh_cliente`, `taxa_conexoes`;
   - rede BT: `ln_kwh_cliente`, com o efeito por DIST encolhido;
   - rede MT: `ln_clientes_por_km_mt`, `cresc_pop_2010_2022`, `ln_kwh_cliente`, `taxa_conexoes`.

   Descartada só a `eletrificacao` no conjunto: a população não se particiona por conjunto. Detalhe em `03_MATRIZ_VARIAVEIS.csv`.

5. **Variáveis que de fato acrescentaram informação.** O critério é a importância por permutação na seleção e o ganho fora da amostra sobre o modelo nulo (só intercepto) na etapa final:
   - **trafos, kVA:** perfil de potência por transformador e clientes por kVA (+5,0 e +2,0 p.p. de WAPE na permutação). O Ridge ficou abaixo do nulo também na etapa final (6,08–6,42% contra 7,78%);
   - **UCBT:** fração urbana e transformadores por cliente (+0,85 e +0,81 p.p. na seleção). **Na etapa final o candidato perdeu para o nulo** (2,367% contra 2,317%): a informação não se sustentou;
   - **trafos, quantidade:** energia por cliente e kVA por transformador (+0,55 p.p.). O ganho final sobre o nulo é pequeno (0,804–0,827% contra 0,837%);
   - **redes:** a informação útil veio do **efeito por distribuidora** (persistência do crescimento da empresa), não das variáveis territoriais. O nulo hierárquico fica em 0,860% na BT e 0,683% na MT, contra 1,223% e 0,789% do nulo global;
   - **`taxa_conexoes` (DAT_CON)** teve importância negativa ou desprezível em 4 dos 5 ativos. A pista do diagnóstico (correlação 0,30 na DIST) **não se confirmou** como ganho preditivo na unidade. Na auditoria, a CEEE Equatorial (5707) reescreve a `DAT_CON` de 7,1% das UCs entre fotografias.

6. **Vencedor por métrica** (`05b`):
   - **UCBT:** o candidato vence todas as métricas, por margens mínimas.
   - **Trafos, quantidade:** o baseline CAGR vence WAPE e MAE, e o atual vence o R² do crescimento.
   - **Trafos, kVA:** o candidato vence WAPE, MAE, RMSE, R² do estoque e R² da variação; o atual vence o R² do crescimento; a persistência vence o viés.
   - **Rede BT:** a deriva vence WAPE, MAE e viés; o atual vence RMSE e R² da variação; o candidato vence o R² do crescimento (único positivo, +0,11).
   - **Rede MT:** o modelo atual vence quase tudo.

7. **Ganho de WAPE fora da amostra contra o modelo atual:** UCBT +0,5%, trafos (quantidade) −5,8%, trafos (kVA) +10,6%, rede BT +26,3% (sem vencer a deriva) e rede MT −43,9%. **Nenhum ganho contra o modelo atual tem IC95% totalmente abaixo de zero.**

8. **R² do crescimento por DIST (candidato):** UCBT −0,385, trafos (quantidade) −0,075, trafos (kVA) −0,077, rede BT +0,112 e rede MT −0,071.

9. **Modelos que pioraram:**
   - rede MT: HGB rejeitado, melhor que o atual na seleção e pior na final, com significância;
   - trafos (quantidade): o candidato já perdia na seleção e perdeu na final;
   - o modelo hierárquico piorou UCBT e trafos em todas as etapas (o choque de crescimento da DIST em 2022→2023 não se repete);
   - no teste espacial (grupos não vistos, mesmo ano), os granulares de UCBT e kVA ficaram piores que a persistência (`espacial_E.csv`).

10. **Famílias que passaram nos critérios:** só **trafos (kVA)**, como `VALIDADO_RETROSPECTIVAMENTE_COM_RESTRICOES`: IC95% contra o melhor baseline de [−5,4; −1,6] p.p., 66 DIST, 63 grupos e sensibilidades mantidas.

    Ressalvas que impedem usá-lo como substituto:
    - a métrica kVA é experimental, sem homologação do contrato;
    - o ganho sobre o modelo atual não é significativo;
    - o R² do crescimento é −0,08;
    - o viés é de +4,6%, menor que o do atual (+5,9%), mas alto.

11. **Continuaram experimentais ou sem ganho:**
    - UCBT, trafos (quantidade) e rede BT: `SEM_GANHO`;
    - rede MT: `REJEITADO`.

    Os modelos atuais por distribuidora ficam mantidos nas cinco famílias.

12. **Extrair outras entidades se justifica?** **Não como expansão.** A granularidade não trouxe ganho nas famílias com painel, e os limites vêm da evidência temporal e dos choques comuns por DIST, não da falta de variáveis. Ver `08` para o único teste barato que faria sentido (geração distribuída).

13. **Custo de ampliar para o país inteiro.** Os cinco painéis já são nacionais (97–99 DIST por ano). No piloto:
    - etapa S: 473 s e pico de 315 MB;
    - etapa F: 306 s e pico de 363 MB;
    - Gate 1: 78 s;
    - artefatos: menos de 1 MB por arquivo; cache em D: (vazio).

    Ampliar para outras entidades custaria, pela vazão da extração anterior (diagnóstico 06):
    - UGBT: 1 a 5 min;
    - PONNOT: 10 min a 1,5 h;
    - campos novos de UCBT: cerca de 2,5 h;
    - mais cerca de 2 min de modelagem por ativo.

    O gargalo é a evidência, não a computação.

14. **Limitações que impedem a homologação plena:**
    - uma só origem final independente e só o horizonte de 1 ano, sem nenhuma avaliação de 2 a 5 anos;
    - choques comuns por distribuidora e ano (ICC de 0,28–0,55 em UCBT), que um painel de 3 transições não identifica;
    - renumeração de conjuntos (15–17 DIST em 2023→2024) e pendências municipais (Celesc 2023, 7019), que reduzem a coorte;
    - `DAT_CON` reescrita em parte das distribuidoras e identidade da UC não contínua (8–20% dos identificadores somem entre fotografias);
    - nenhuma variável antecedente de demanda (pedidos de ligação, obras, planos de expansão);
    - métrica kVA não homologada;
    - o modelo atual foi escolhido pelo produto também com o alvo de 2025 (seleção não cega para ele, ver 01 científico), o que favorece o atual na comparação.

## Auditoria (Gates 4 e 5)

- **Restrições físicas:**
  - 0 contagens fracionárias e 0 valores negativos;
  - o total de cada DIST é a soma das previsões inteiras das unidades (reconciliado por construção);
  - EQ e UN nunca são somados.
- **Vazamento:**
  - a etapa S roda com o carregador limitado a 2024 (`Dados(ano_max=2024)`, com asserção);
  - a seleção foi congelada e commitada antes da etapa F;
  - `final` foi executado uma vez.
- **Coorte única:** em cada família, candidato, modelo atual e baselines usam exatamente as mesmas DIST.
- **Comparação independente com o produto:** a reexecução do modelo atual reproduz o backtest independente do produto (`exp/otimizacao-modelos-20261103`, `PONTOS_AVALIACAO.csv`, origem 2024 → 2025) com diferença mediana de 0,01% a 0,2% nas previsões, nas DIST em que o alvo do painel é igual ao do contrato (trafos 61, kVA 47, rede BT 69, rede MT 70). UCBT não tem equivalente no contrato.
- **Sensibilidade:** sem a DIST de maior contribuição e sem as 5% maiores variações, as conclusões se mantêm nas cinco famílias.

## Desvios do protocolo

- A medição de memória do Gate 1 falhou: a chamada ctypes estava errada e foi corrigida antes do Gate 2. Isso não afeta resultados.
- Nenhum desvio de critério, variável, hiperparâmetro ou coorte depois da etapa S.
- Os hashes dos arquivos versionados foram calculados sobre o conteúdo com quebra LF.
