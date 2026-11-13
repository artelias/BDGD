# Estudo de fatores associados (estatística)

`confiabilidade/estatistica.py` → `web/public/data/confiabilidade/fatores.json` (contrato lido por
`components/confiabilidade/Fatores.tsx`). Observacional e exploratório; semente 20261112; 300 reamostras.
Execução: ~6 min (`.venv-motor`, numpy/scipy/scikit-learn). Rodar duas vezes dá o mesmo resultado (verificado em
12/11/2026: só `gerado_em` muda).

## Regras definidas antes dos resultados

* **Amostra**: conjunto-ano 2022–2025 com DEC e FEC oficiais nos 12 meses, infraestrutura BDGD do mesmo ano, ≥ 100
  consumidores e sem `consumidores_divergentes`. Resultado: 11.381 conjunto-anos, 3.623 conjuntos, 98 distribuidoras.
  Exclusões: sem infraestrutura 324; apuração incompleta 138; consumidores divergentes 595; < 100 consumidores 64.
* **Alvo**: log(indicador + 0,1). **Contexto**: porte, densidade (UC/km²), parcela não urbana, consumo por consumidor.
* **Correlações de Spearman**: bruta; parcial (resíduos em postos após o contexto); dentro da distribuidora-ano
  (escores normais dos postos centrados na distribuidora-ano).
* **Incerteza**: IC 95% por reamostragem de **distribuidoras inteiras** (conjuntos da mesma empresa não são independentes).
* **Modelos**: Ridge (`RidgeCV`) e floresta aleatória, validação cruzada `GroupKFold(5)` por distribuidora (o modelo é
  avaliado em empresas que não viu); efeito fixo de ano; winsorização 1–99% ajustada só no treino; `log1p` nas razões por
  100 km (sem isso o Ridge dava R² fora da amostra −287.895 por razões extremas de redes curtas).
* **Veredito**: `COMPATIVEL` = parcial **e** dentro com IC sem zero no sinal esperado; `NAO_SUSTENTADA` = parcial com IC sem
  zero no sinal oposto, ou |parcial| < 0,05 com os dois IC contendo zero; `INCONCLUSIVA` = demais; `SEM_DADOS` = < 200
  observações. Nenhum resultado fictício: sem dado, o veredito diz isso.

## Hipóteses

| Id | Enunciado (associação, nunca efeito) | Ind. | Bruta | Parcial [IC 95%] | Dentro [IC 95%] | Veredito |
|---|---|---|---:|---|---|---|
| H1 | rede MT por consumidor ↑ ⇔ DEC ↑ | DEC | +0,69 | +0,08 [−0,01; +0,18] | +0,73 [+0,67; +0,79] | inconclusiva |
| H2 | rede MT por alimentador ↑ ⇔ DEC ↑ | DEC | +0,70 | +0,17 [+0,06; +0,25] | +0,69 [+0,64; +0,74] | **compatível** |
| H3 | consumidores por alimentador ↑ ⇔ FEC ↑ | FEC | +0,06 | +0,18 [+0,04; +0,27] | −0,01 [−0,11; +0,08] | inconclusiva |
| H4 | consumidores por transformador (sem sinal esperado) | DEC | −0,62 | −0,09 [−0,19; +0,03] | −0,72 [−0,75; −0,66] | inconclusiva |
| H5 | seccionamento por 100 km ↑ ⇔ DEC ↓ | DEC | −0,52 | −0,01 [−0,21; +0,19] | −0,62 [−0,71; −0,55] | inconclusiva |
| H5b | religadores por 100 km ↑ ⇔ DEC ↓ | DEC | −0,55 | −0,03 [−0,15; +0,15] | −0,50 [−0,61; −0,38] | inconclusiva |
| H6a | densidade ↑ ⇔ DEC ↓ | DEC | −0,70 | −0,35 [−0,46; −0,24] | −0,72 [−0,77; −0,66] | **compatível** |
| H6b | parcela não urbana ↑ ⇔ DEC ↑ | DEC | +0,68 | +0,26 [+0,11; +0,39] | +0,70 [+0,63; +0,75] | **compatível** |
| H7 | variação da infraestrutura 2022→2023 ⇔ variação posterior do indicador 2023→2025 | DEC/FEC | | | | inconclusiva |

Leitura: ruralidade, densidade e extensão de rede por alimentador mantêm associação depois do contexto e dentro das
empresas. As associações brutas fortes de seccionamento, religadores e rede por consumidor quase desaparecem depois do
contexto: elas acompanham o território (redes rurais longas têm mais equipamentos **e** mais DEC). A causalidade reversa
(religadores instalados onde o DEC já era alto) é plausível e não é separável com estes dados.

**Evolução da infraestrutura (H7 e complementos).** A regra do H7 usa as variações defasadas de quatro razões
(religadores e telecomando por 100 km, rede e consumidores por alimentador): nenhuma tem IC sem zero, mas religadores
por 100 km tem ρ = −0,08 (DEC) e −0,10 (FEC) com IC largo. Até 12/11/2026 o H7 saía "não sustentada"; a auditoria mostrou
que isso contrariava a regra do H1–H6 (não sustentada só com |ρ| < 0,05 e IC com zero) e confundia ausência de evidência
com evidência de ausência. Com a mesma regra, o H7 é **inconclusiva** (`veredito_variacao`, com teste). Fora do conjunto
pré-definido do H7, as variações defasadas de km MT e de consumidores têm IC sem zero; são exploratórias e não mudam o
veredito (escolher a variável depois de ver o resultado seria pesca de significância). Nas variações
**contemporâneas** 2022→2025 das contagens, o aumento de pontos telecomandados (DEC ρ = −0,23 [−0,38; −0,08]; FEC −0,24) e
de religadores (DEC −0,16 [−0,27; −0,01]) acompanha a queda do indicador no mesmo período. Isso é coincidência temporal,
não precedência: não sustenta efeito.

## Capacidade de explicar fora da amostra (R², validação por distribuidora)

| Modelo | DEC | FEC |
|---|---:|---:|
| Contexto (Ridge) | 0,431 | 0,310 |
| Contexto + infraestrutura (Ridge) | 0,456 | 0,330 |
| Contexto + infraestrutura (floresta aleatória) | 0,533 | 0,420 |
| Referência de contexto (floresta aleatória) | 0,485 | 0,365 |

**Comparação equivalente (auditoria de 12/11/2026, `auditoria/R2_PAREADO.json`).** Os quatro modelos usam as mesmas
cinco partições `GroupKFold` por distribuidora (18–20 distribuidoras por dobra, nenhuma no treino e no teste), o mesmo alvo
e as mesmas 11.381 linhas; os R² acima foram reproduzidos exatamente. O ganho da infraestrutura só se lê entre modelos
do mesmo tipo:

| Ganho de R² | DEC [IC 95%] | FEC [IC 95%] | Dobras com ganho |
|---|---|---|---|
| Ridge: contexto → + infraestrutura | +0,025 [−0,052; +0,094] | +0,021 [−0,058; +0,092] | 3 de 5 / 2 de 5 |
| Floresta: contexto → + infraestrutura | +0,048 [+0,003; +0,096] | +0,056 [−0,005; +0,113] | 4 de 5 / 4 de 5 |

IC por reamostragem de distribuidoras sobre as previsões fora da amostra (1.000 réplicas; não inclui a variação do
reajuste). Leitura: o ganho é **pequeno e incerto**; só o da floresta no DEC tem IC acima de zero, e por pouco. A passagem
"0,43 → 0,53" que constava do relatório comparava Ridge com floresta e misturava o efeito da infraestrutura com o do tipo
de modelo (+0,10, dos quais cerca de metade vem da troca de modelo). Importância por permutação (floresta, DEC): rede MT
trifásica 0,167; densidade 0,099; parcela não urbana 0,077; rede MT por alimentador 0,016. Importância mede uso pelo
modelo, não efeito físico; variáveis correlacionadas dividem a importância.

## Referência ajustada (tela Fatores)

`referencias` traz, para DEC e FEC de 2025 (2.865 conjuntos cada), o valor observado, a referência da floresta aleatória só
com contexto treinada **sem a distribuidora avaliada** (R² 0,485 DEC; 0,365 FEC), uma faixa [lo; hi] e o resíduo
(observado − referência). É uma referência de comparação ("acima do esperado para conjuntos com esse perfil"), não uma meta nem um juízo de
eficiência. A tela escolhe a referência do indicador ativo (`Fatores.tsx`).

## Limitações registradas no próprio `fatores.json`

Associação não é causa; clima, vegetação, descargas, idade dos ativos, manutenção e automação efetiva não estão nos dados;
a infraestrutura é a fotografia de 31/12 e o indicador é apurado no ano; quatro anos limitam a leitura temporal; valores da
BDGD são declarados e não homologados; não há validação em dados futuros.
