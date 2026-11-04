# 11 — Candidatos preservados para avaliação confirmatória futura

**Nada aqui é publicado, substitui modelo do produto nem é retreinado nesta etapa.** Os registros servem para a próxima avaliação independente: a primeira competência publicada depois de 2025, como origem nova (por exemplo, origem 2025 → alvo 2026). As configurações abaixo são aplicadas **exatamente como estão**. Qualquer alteração exige um protocolo novo e uma origem ainda não vista.

| # | Família | Candidato | Origem da evidência | Configuração congelada | Por que preservar | Estado |
|---|---|---|---|---|---|---|
| 1 | Potência de transformadores de distribuição (kVA), conjunto × ano | `G-RIDGE` (α = 1,0) com `ln_kva_por_trafo`, `ln_clientes_por_kva`, `ln_kwh_cliente`, `taxa_conexoes`; alvo ln(y_t/y_{t−1}) por conjunto, peso y_{t−1}, winsorização 5–95% | piloto granular, `selecao_congelada.json` (sha256 `20c9e59ac8ae687f803ccb2376b7fcc8bbc647024ae2350759a6360f18cc7a31`), commit `9be843b` | código `PILOTO_GRANULAR/piloto.py` (`Granular("G-RIDGE", …)`) | passou no critério retrospectivo restrito contra o melhor baseline (IC95% [−5,4; −1,6] p.p.); sem ganho significativo sobre o atual; métrica kVA experimental | **EXPERIMENTAL, não publicado** |
| 2 | Rede BT (km), conjunto × ano | `G-HIER` (α = 0,1) com `ln_kwh_cliente` mais intercepto por distribuidora encolhido (Bayes empírico) | mesmo arquivo e commit | idem | único R² do crescimento positivo do piloto (+0,112), com WAPE 26% menor que o atual, mas sem bater a deriva | **candidato confirmatório** |
| 3 | Rede BT (km), distribuidora × ano | **deriva** (passeio aleatório com tendência), `cenarios.py` (sha256 `258322643fa2c28dc1cc53c21f9494cc55962899db20a9639dc6452947f059b1`) | piloto (melhor baseline na etapa final: 0,822% contra 1,135% do Moderado atual na coorte do painel) e backtest do produto (03) | sem parâmetros | candidata a uma **nova comparação independente** com o Moderado atual (`ridge_painel`) | **candidata, sem substituição automática** |

Os modelos atuais por distribuidora (os cinco Moderados do produto avaliados no piloto) ficam preservados sem alteração:

| Família | Moderado |
|---|---|
| Transformadores, quantidade | `knn_analogos` |
| Transformadores, kVA | `ridge_painel` |
| Rede BT | `ridge_painel` |
| Rede MT | `random_forest_painel` |
| Consumidores | `ridge_painel` |

**Regra da avaliação confirmatória**, a ser pré-registrada antes de usar a nova competência:
- treino com as transições até a origem;
- alvo na competência nova;
- mesma coorte, as mesmas exclusões cadastrais e os mesmos critérios de `PILOTO_GRANULAR/01_PROTOCOLO.md` (seção 11);
- nenhum ajuste depois de ver o alvo.

Um candidato só passa a ser elegível para publicação se superar o Moderado atual com IC95% totalmente abaixo de zero **também na origem nova**, e com a aprovação humana.
