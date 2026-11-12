# Fórmulas e reconciliação

Implementação única em `confiabilidade/contrato.py` (Python) e `web/src/lib/confiabilidade/calculo.ts` (exibição),
ambas cobertas por testes.

## Indicadores (PRODIST, Módulo 8)

* Conjunto, mês: DEC = Σ DIC ÷ Cc e FEC = Σ FIC ÷ Cc (Cc = consumidores do conjunto no mês). Somar DIC/FIC dá só o numerador.
* Conjunto, ano: soma dos 12 valores mensais apurados. Com menos de 12 meses (de DEC **ou** de FEC) o ano recebe o alerta
  `apuracao_parcial` (`meses_dec`, `meses_fec`): o valor é exibido, mas não é comparado ao limite anual nem entra em quebras,
  posições, rankings, pares e contagens "acima do limite". Até a auditoria de 12/11/2026 o alerta só olhava o DEC, e o FEC de
  2025 da Elektro (sem junho na ANEEL, 130 conjuntos) aparecia como anual.
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
mês, somado **nos meses em que o oficial existe** (o mesmo conjunto de meses dos dois lados; desde 12/11/2026). Também se publica, só como comparação, a versão com o denominador da BDGD (unidades ativas em 31/12).

Critério **experimental** (não é critério de homologação): |reconstruído − oficial| ≤ 0,05 ou ≤ 5% do oficial. O conjunto-ano
só recebe `RECONSTRUIDO_VALIDADO` quando DEC **e** FEC passam. O oficial é sempre a referência; o reconstruído nunca o
substitui.

### Resultado (auditoria A5, `auditoria/RECONCILIACAO_POR_DIST_ANO_INDICADOR.csv`, 758 linhas)

| | Pares | Dentro da tolerância |
|---|---:|---:|
| DEC | 12.175 | 11.458 (94,1%) |
| FEC | 12.175 | 11.424 (93,8%) |
| DEC e FEC juntos | 12.175 | 11.325 (93,0%) |

* 83 combinações DIST × ano × indicador (33 distribuidoras) ficam abaixo de 80% de conjuntos reconciliados; 2023 concentra
  34 delas. Antes da correção de 12/11/2026 eram 82: saiu a Elektro 2025 FEC (35% → 100%; era artefato do mês sem FEC
  oficial) e entrou a Cersad 2022 (1 conjunto, que antes não tinha reconstrução por falta de NumCon num mês).
* Diagnóstico das 83 (`auditoria/homologacao/a2_rec_saida.txt`): **49 são distribuidoras de um só conjunto** (uma divergência
  vira 0%); 4 têm DIC/FIC zerado ou quase nulo na BDGD (Coopernorte e Cooperzem 2022, Coopera 2025); nas grandes, a razão
  reconstruído ÷ oficial é deslocada de forma quase uniforme entre os conjuntos (CEA 2022 ≈ 0,90; EDP ES e EDP SP 2023
  ≈ 1,10; Equatorial GO 2025 ≈ 0,87; CPFL Paulista 2025 ≈ 0,94; Celesc 2025 e Copel 2022 ≈ 1,04–1,06), o que aponta para
  diferença de definição ou de cadastro do DIC declarado na BDGD daquela empresa-ano, não para erro no indicador oficial.
  Só 7 combinações se explicam por o DIC da BDGD incluir externas ou expurgos. A cobertura de DIC é 100% em todos.
* Nenhuma combinação invalida o oficial: o oficial bate com o arquivo bruto da ANEEL em 100% dos 12.502 conjunto-anos
  (`auditoria/homologacao/a1_aneel_saida.txt`). A reconstrução mede a coerência da BDGD com o oficial, não o contrário.
* Cooperativas com 1 conjunto aparecem com 0% quando o único conjunto diverge; a tabela mostra `conjuntos` para pesar isso.
* EPB (6600): 98,5–100% em todos os anos e indicadores. Energisa AC (26): 100% em todos.
* A divergência não altera nenhum valor oficial exibido: ela só define o selo da seção "Reconstrução" da ficha.
