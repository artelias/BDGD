# R3 — Motor de Expansão Elétrica: contrato de implementação
Data: 2026-10-23. Status: especificação, **nenhum modelo treinado**. Sem projeções sintéticas no produto.

## Objetivo
Três saídas independentes e reconciliáveis por DIST/grupo/Brasil, ano e conceito físico: (a) necessidade técnica de expansão, (b) variação do estoque físico de ativos, (c) investimento associado. Distinguir crescimento orgânico, substituição, baixa, transferência, reclassificação e modernização.

## Oito camadas
1. **Fontes e histórico**: BDGD 2022–2025, metadados de publicação, datas-base, CNPJ/DIST, atos de concessão, demanda e mercado externos quando disponíveis. QA e proveniência por célula.
2. **Ontologia física**: conceitos canônicos (transformação MT/BT TUC 565; força TUC 570; redes por tensão; CTMT; subestações; medidores; postes/torres; proteção); instalação e EQ não se somam; unidade de estoque e fluxo explícita.
3. **Grafo elétrico**: nós (SUB, CTMT, transformadores, segmentos, UCs) e arestas por vínculos BDGD documentados. Registrar cobertura de conectividade, componentes órfãos, ambiguidades e ausência; não supor topologia validada só por proximidade espacial.
4. **Demanda**: consumidores, classes, carga coincidente, demanda máxima, densidade e expansão territorial. Fonte temporal *as-of*; geração distribuída pode aumentar ou reduzir picos locais dependendo do perfil.
5. **Capacidade**: potência nominal, reserva, carregamento, limites de engenharia e necessidade de reforço; sem demanda coincidente não inferir saturação de potência nominal.
6. **Economia**: custos unitários e investimentos auditados, CAPEX de expansão versus substituição, restrições de execução, regulação e defasagens de implantação.
7. **Estatística**: baselines, modelos de contagem, regressão regularizada, painel/hierárquico e modelos físico-estatísticos somente após verificação de identificação e histórico. Separar previsão incondicional de simulação condicional.
8. **Publicação**: séries observadas, cenários, fatores, erros, limites, origem e elegibilidade; N/D quando sem base validada.

## Contrato de dados
Chave da série: `(perimetro_id, dist_canonico, ano, conceito_id, metrica, unidade, regra_versao)`.
Campos obrigatórios: `valor`, `status` (observado|ausente|nao_homologado|nao_aplicavel|zero_verificado|ruptura), `fonte`, `data_base`, `cobertura`, `perimetro_bridge_id`, `hash_insumo`.
Features: `feature_id`, `alvo_id`, `dist`, `ano_referencia`, `disponivel_em`, `unidade`, `origem`, `qualidade`, `defasagem`. Proibir variável posterior à origem da previsão e derivados diretos do alvo contemporâneo.
Grafo: `node_id, node_type, dist, ano, entity, cod_id` e `source_id, target_id, edge_type, regra, qualidade, ano`; chaves sempre DIST+COD_ID, nunca COD_ID global.

## Hipóteses de engenharia a testar
- UCBT + demanda coincidente + reserva + densidade territorial -> transformação MT/BT (estoque TUC 565 e potência, alvos distintos).
- Demanda agregada CTMT + capacidade instalada + redundância -> transformação AT/MT e subestações.
- Expansão territorial + novas conexões + densidade -> extensão de rede BT e MT.
- Rede aérea incremental + compartilhamento MT/BT + espaçamento -> estruturas, com separação postes/torres.
- Ramificações + extensão + metas de continuidade -> seccionamento, proteção e automação.
- UCs + renovação tecnológica -> medidores.
A relação entre consumidores e transformadores é mediada por capacidade disponível, carga, simultaneidade e localização; não assumir coeficiente físico constante. Diferenciar crescimento do estoque de volume de instalações/substituições.

## Experimentos
Etapa 0: perfil de completude, coerência temporal, mudanças de perímetro, consistência de grandezas, n de anos por série, rupturas e disponibilidade *as-of*.
Etapa 1: naive, variação absoluta, CAGR (somente cenário), tendências simples; validação rolling-origin quando identificável.
Etapa 2: ablação de features por motor (demanda, capacidade, topologia, qualidade, economia), modelos hierárquicos/regularizados e comparação contra baseline. Não afirmar ganho sem teste.
Etapa 3: reconciliação física e hierárquica, limites de não negatividade, quantis somente calibrados, intervalos e análise de sensibilidade.
Métricas por alvo e horizonte: MAE, viés, WAPE (denominador válido), MASE (escala definida), cobertura de previsões e, quando possível, cobertura de intervalos. Testar fuga temporal, mudanças regulatórias e regressão por DIST.
**Gate:** históricos 2022–2024 ainda não homologados; com 4 pontos anuais não validar horizontes 3–4 nem ML temporal complexo. Não criar previsões públicas sem auditoria.

## Interface planejada
Filtros: DIST/grupo/Brasil, conceito, métrica, horizonte e modo (histórico, previsão validada, simulação condicional).
Gráficos: histórico e previsão com separação visual, bandas se calibradas, decomposição dos fatores, demanda × capacidade, estoque × entradas/baixas, comparativo de modelos e mapa de necessidade. Explicitar unidades e cobertura; nunca usar números fictícios como produção.

## Responsabilidades e interfaces
**Claude (PR #4):** retomar Explorar/Evolução/cubos e homologação histórica no ponto exato da sessão; entregar contratos de conceitos, vínculos e séries comparáveis; não alterar Panorama nem motor estatístico desta branch.
**ChatGPT (PR #6):** especificação e protótipos testáveis de QA de séries, seleção de features, backtesting, gates e contratos de publicação; integrar apenas após recebimento de históricos homologados. Sem tocar ETL histórico, catálogo ou telas de Claude.
**Integração posterior:** PR específico com revisão de diff, testes e aprovação do usuário; nunca merge/deploy automático.
