# Motor de Expansão Elétrica — protocolo de variáveis econômicas
Data: 2026-10-23. Status: hipóteses pré-registradas; nenhum coeficiente estimado.

## Dois mecanismos diferentes
**Demanda:** atividade econômica, renda, indústria, demografia e tarifa -> consumo/demanda máxima -> capacidade e topologia -> necessidade técnica de ativos.
**Oferta de investimento:** juros reais, WACC regulatório, inflação de equipamentos, câmbio, CAPEX aprovado/realizado e ciclo regulatório -> timing, substituição, expansão e estoque observado.
Não interpretar correlação contemporânea entre PIB e estoque de transformadores como causalidade direta.

## Features candidatas e fontes a verificar
- PIB real estadual e valor adicionado setorial: IBGE (contas regionais); deflacionar, verificar defasagem de publicação.
- Produção industrial e comércio: IBGE PIM-PF e PMC, quando representativas do território.
- População/domicílios e urbanização: IBGE; mudanças metodológicas e geografia.
- Emprego e renda real: IBGE PNAD Contínua / Novo CAGED conforme granularidade e disponibilidade histórica.
- IPCA: IBGE; custos de obras podem exigir índices setoriais apropriados, com documentação.
- Selic, taxas reais, câmbio: Banco Central SGS; distinguir taxa observada de cenário futuro.
- Tarifas, WACC e investimentos regulatórios: ANEEL; diferenciar valores homologados, anunciados e executados.
- Mercado de energia, GD, demanda e consumo por classe: ANEEL/EPE quando disponíveis.
Nunca misturar preços nominais com quantidades reais sem deflator e ano-base explícitos.

## Especificação e validação
1. Construir painel por DIST-ano, mapeando exposição estadual via perímetro de concessão; não imputar PIB de uma UF inteira a concessões multi-UF sem pesos documentados.
2. Definir data de disponibilidade (*as-of*) de cada indicador e defasagens 1–2 anos; impedir vazamento de revisões e informações publicadas depois da origem.
3. Comparar ablações: baseline físico sem macro; + macro de demanda; + macro de investimento; + ambos. Usar splits temporais e mesmos conjuntos de DISTs, cobertura e alvos.
4. Considerar elasticidades, interações, não linearidade e multicolinearidade; regularização/hierarquia só com dados suficientes.
5. Comparar MAE, viés, MASE e cobertura, além de estabilidade do sinal, interpretação física e ganho contra baseline.
6. Se ganho não for robusto, manter variáveis como contexto ou cenário condicional, **não** forçar inclusão no modelo preditivo.
7. Para horizonte futuro, exógenas precisam de trajetória conhecida na origem ou cenário externo versionado. Não usar PIB realizado futuro como entrada de previsão retrospectiva.
8. Com 2022–2025 e históricos ainda não homologados, não alegar validação de elasticidades ou efeitos macroeconômicos.

## Equações conceituais
Demanda: log(D_it) = alpha_i + beta' X_economico_it-lag + theta' X_eletrico_it-lag + epsilon_it.
Necessidade técnica: N_it = f(demanda_pico, capacidade_disponivel, reserva, topologia, restricoes).
Investimento/execução: I_it = g(N_it, custo_real, custo_capital, orçamento, ciclo_regulatorio, defasagens).
Estoque: A_i,t+1 = A_it + entradas_expansao + entradas_substituicao - retiradas_substituicao - outras_baixas.
Não confundir projeção estatística de estoque com cálculo de necessidade ou cenário de investimento.

## Critério de aprovação
A variável econômica só passa a preditora quando possui disponibilidade histórica auditada, comparabilidade territorial e temporal, ausência de vazamento e melhoria estável fora da amostra. Sem isso, mostrar em análise exploratória/sensibilidade com rótulo adequado.
