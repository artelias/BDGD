# Fórmulas e reconciliação

Implementação única em `confiabilidade/contrato.py` (Python) e `web/src/lib/confiabilidade/calculo.ts` (exibição),
ambas cobertas por testes.

## Indicadores (PRODIST, Módulo 8)

* Conjunto, mês: DEC = Σ DIC ÷ Cc e FEC = Σ FIC ÷ Cc (Cc = consumidores do conjunto no mês). Somar DIC/FIC dá só o numerador.
* Conjunto, ano: soma dos 12 valores mensais apurados. Com menos de 12 meses o ano é marcado como apuração parcial
  (`meses_dec`, `meses_fec`).
* Agregado (distribuidora, grupo, Brasil), mês: média dos conjuntos **ponderada pelo NumCon** de cada mês; anual = soma dos
  meses. Nunca a média simples dos conjuntos. Esse agregado é derivado aqui e pode diferir em centésimos do global ANEEL.
* Desempenho regulatório = apurado ÷ limite anual do conjunto. Os limites são anuais: no recorte mensal o mapa só mostra
  valor absoluto e a opção "% do limite" fica desabilitada.
* Componentes: o apurado é a soma das internas (programada `IP` + não programada `IND`); externas e expurgos aparecem na
  ficha como "não compõe". As parcelas mostradas somam 100% do indicador.

## Zero × N/D

| Situação | Valor publicado |
|---|---|
| Camada da BDGD lida e sem linhas para o conjunto | **0 observado** (ex.: nenhum religador) |
| Camada ausente na carga daquele DIST × ano | **N/D** com o motivo (`camadas_ausentes`) |
| Contagem de consumidores 1–4 por alimentador | **N/D** (suprimido; nunca zero) |
| BT e MT ambos N/D num alimentador | soma **N/D** (nunca 0 + 0) |

N/D fica fora de somas, médias, quantis e ordenações (vai para o fim da lista). Implementado em
`publicar.completar_zeros` e no frontend (`FichaConjunto`, `calculo.ts`), com testes nos dois lados.

## Reconstrução a partir da BDGD (`RECONSTRUIDO_VALIDADO` × `DERIVADO_EXPLORATORIO`)

Para cada conjunto-ano: Σ DIC mensal (e Σ FIC) das unidades consumidoras da BDGD do conjunto ÷ **NumCon oficial** de cada
mês, somado no ano. Também se publica, só como comparação, a versão com o denominador da BDGD (unidades ativas em 31/12).

Critério **experimental** (não é critério de homologação): |reconstruído − oficial| ≤ 0,05 ou ≤ 5% do oficial. O conjunto-ano
só recebe `RECONSTRUIDO_VALIDADO` quando DEC **e** FEC passam. O oficial é sempre a referência; o reconstruído nunca o
substitui.

### Resultado (auditoria A5, `auditoria/RECONCILIACAO_POR_DIST_ANO_INDICADOR.csv`, 748 linhas)

| | Pares | Dentro da tolerância |
|---|---:|---:|
| DEC | 12.170 | 11.454 (94,1%) |
| FEC | 12.170 | 11.336 (93,1%) |
| DEC e FEC juntos | 12.170 | 11.237 (92,3%) |

* 82 combinações DIST × ano × indicador (34 distribuidoras) ficam abaixo de 80% de conjuntos reconciliados; 2023 concentra
  34 delas. As mais frequentes: CEA Equatorial (6), Dmed, Coopersul, Cooperzem e Cerbranorte (5 cada). CEA 2022 tem viés
  médio de −9,06 h no DEC: o DIC cadastrado na BDGD daquele ano não cobre o apurado.
* Cooperativas com 1 conjunto aparecem com 0% quando o único conjunto diverge; a tabela mostra `conjuntos` para pesar isso.
* EPB (6600): 98,5–100% em todos os anos e indicadores. Energisa AC (26): 100% em todos.
* A divergência não altera nenhum valor oficial exibido: ela só define o selo da seção "Reconstrução" da ficha.
