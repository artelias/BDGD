# 08 — Recomendação para a próxima etapa

## Decisão recomendada

1. **Manter os modelos atuais por distribuidora nas cinco famílias.** Nenhum candidato granular superou o modelo atual com suporte estatístico na avaliação final. Na rede MT, o candidato foi significativamente pior.
2. **Não fazer uma expansão territorial ampla do Motor V2** (extração nacional de novas entidades ou migração dos modelos para município/conjunto) com base neste piloto. A granularidade aumentou a informação transversal, mas não a previsibilidade do crescimento anual: o R² do crescimento ficou entre −0,39 e +0,11.
3. **Potência de transformadores (kVA): mantê-la como candidata experimental, sem substituir.**
   - O Ridge por conjunto passou no critério retrospectivo restrito contra o melhor baseline (IC95% [−5,4; −1,6] p.p.).
   - Mas não superou o modelo atual com significância, o R² do crescimento é −0,08 e a métrica kVA não é homologada.
   - Ele vale como **teste confirmatório** na próxima competência publicada (2026), com a configuração congelada **sem nenhuma alteração** (`selecao_congelada.json`, hash `20c9e59a…`). Essa seria a segunda origem independente.
4. **Rede BT:** o modelo hierárquico (persistência do crescimento da DIST, encolhida, mais energia por cliente) teve o único R² do crescimento positivo (+0,11) e WAPE 26% menor que o atual, mas não bateu a deriva simples.
   - Recomendação: **avaliar a deriva como Moderado da rede BT** no produto, em processo próprio, porque ela foi o melhor baseline na etapa final (0,822% contra 1,135% do atual).
   - O hierárquico fica como candidato confirmatório em 2026.

## Expansão controlada: só um teste barato se justifica

| Opção | Justificativa | Custo | Recomendação |
|---|---|---|---|
| Geração distribuída (UGBT) por município | é o ativo de maior crescimento relativo; é heterogêneo por município; o Moderado atual é a deriva (WAPE 6,6% na etapa final) | extração de 1 a 5 min (10,8 milhões de linhas) e cerca de 2 min de modelagem | **pode ser feito** com o mesmo protocolo, congelado antes, se o objetivo for testar uma família onde o erro atual é alto |
| Postes (PONNOT) | erro atual baixo (0,56%), estoque muito persistente | 10 min a 1,5 h | não recomendado |
| Variáveis novas de UCBT (carga instalada, classe) | UCBT não teve ganho; as variáveis territoriais não se sustentaram fora da amostra | cerca de 2,5 h | não recomendado |
| Circuitos (CTMT) | reconfiguração domina a variação (diagnóstico 06) | — | não usar como alvo |

## Informações que fariam diferença (não disponíveis hoje)

O limite está na evidência temporal e na falta de sinais antecedentes, não no algoritmo nem na granularidade:

1. **Novas origens temporais:** cada competência publicada a partir de 2026 dá uma avaliação independente adicional. Com 3 origens, o protocolo permite o nível "homologado para o horizonte".
2. **Indicadores antecedentes de demanda**, com data de disponibilidade:
   - pedidos de ligação e de aumento de carga;
   - obras e planos de expansão das distribuidoras;
   - fila de conexão de geração distribuída;
   - licenças de construção ou lançamentos imobiliários por município.
3. **Pontes cadastrais homologadas:** renumeração de conjuntos (15–17 DIST em 2023→2024), município da Celesc 2023 e anomalia do 7019. Recuperariam cerca de 20% das DIST no nível conjunto.
4. **Identidade contínua das UCs e DAT_CON estável** entre fotografias. Na CEEE Equatorial, 7,1% das datas são reescritas. Sem isso, as conexões recentes não servem como sinal limpo.
5. **Área servida validada por conjunto**, para a densidade territorial (hoje indisponível).

## O que continua proibido

- Substituir previsões do produto ou publicar estes modelos.
- Usar competências anteriores a 2022.
- Aplicar pontes sem homologação.
- Usar o alvo de 2025 para reajustar qualquer modelo deste piloto. Qualquer novo ajuste precisa ser avaliado numa origem nova.
- Declarar homologação científica para 2026–2030.
