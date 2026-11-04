# Homologação funcional do dashboard BDGD

**Parecer parcial em 31/10/2026.** A barra lateral passou a manter o comando de expansão ao alcance do usuário em janelas baixas. Antes da correção, em 1024 × 400, a borda inferior do botão ficava a 597,5 px do topo. A regressão mede tanto a largura da lateral quanto o início da coluna de conteúdo. As duas coordenadas passam de 244 para 68 px ao recolher e voltam a 244 px ao expandir.

Os testes usam a exportação estática e os contratos versionados da release `bdgd-2025-12-31-v1-99d-2f6fa3879a-rec1`. As expectativas dos novos testes de dados são calculadas a partir dos cubos, índices e contrato nacional, separadamente do código de agregação da interface. Um teste anterior ao conserto do inventário reproduziu a conversão de `null` em zero ao buscar a subestação Aporema.

| Página | Evidência funcional examinada |
|---|---|
| Panorama | Mapa, seleção de grupo e distribuidora, retorno ao país, expansão do ranking, KPIs e explicação de cálculo. O escopo nacional indica cobertura parcial. |
| Explorar ativos | Mudança de categoria, TUC, entidade, característica e unidade. Cada teste de característica seleciona códigos no navegador, recalcula o total no cubo de origem, recarrega a página e limpa o recorte. Na EPB, o filtro de situação retorna 1.902.125 unidades ativadas e 241.340 desativadas. |
| Matriz nacional | Distribuidoras, UF, grupo, busca, ordenação, transposição, seleção de ativos e exportação são verificadas no fluxo `homologação matriz`. Cada DIST e valor exportados são comparados com `ativosTotais` na amostra de consumidores. |
| Comparador | Lados A/B, grupos, troca, abas de gráficos, modo espelhado, radar, referências e CSV. A matriz registra o alcance das asserções de cada fluxo. |
| Evolução histórica | Quatro anos, recortes, quebras e fontes de publicação. O contrato de consumidores informa **1.698.731** para EPB em 2023 e **8.215.027** para Enel SP em 2025. Para Coopera em 2025, o valor é vazio, com estado `nao_homologado`. O subtotal de 225 tem finalidade explicativa. |
| Previsões | Três produtos públicos existentes, estados sem trajetória, natureza física, formatos de tabela, tooltip e CSV. A ordenação dos cenários do motor publicado usa crescimento agregado e pode inverter na empresa. WAPE do painel e diagnóstico individual têm interpretações distintas. |
| Metodologia e qualidade | Âncoras de navegação e seletores de empresa, ativo/métrica e cenário. A troca das três empresas foi conferida com histórico, valores de 2030 e nome do modelo do JSON. A documentação informa ausência de intervalos calibrados e limites de rastreabilidade dos coeficientes. |

## Integridade e alcance

A validação estrutural leu 260 assets JSON e a homologação web conferiu 11.025 células, 9.044 delas com valor validado. O contrato nacional tem 11.400 linhas, distribuídas por 114 DIST, quatro competências e 25 conceitos. Os 13 pares de republicações passaram no validador. A auditoria de produtos públicos encontrou zero contagens negativas ou fracionárias nos quatro produtos examinados. Esses controles verificam os produtos versionados. A aprovação regulatória dos ativos é outra decisão.

A matriz de testes inclui os controles observados no navegador e as ações efetivamente executadas. Um teste de inventário identifica a existência de um controle. A sua aprovação funcional exige uma asserção sobre o resultado. Os campos sem evidência individual suficiente permanecem discriminados no CSV. A lista de inventário usa busca e mostra até 400 linhas na tela. A exportação inclui o recorte completo e a interface não oferece um botão de próxima página nesse componente.

[Matriz de testes](MATRIZ_TESTES_INTERFACE.csv) · [Defeitos e condições de reprodução](DEFEITOS.md) · [Integração e execução de CI](INTEGRACAO_CI.md)
