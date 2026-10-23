# Revisão funcional R2 — Métricas, explorações, matriz e evolução histórica (2022–2025)

**Solicitação do responsável em 23/10/2026.** Desenho para o portal *Núcleo de Dados da BDGD*. **Implementar primeiro as melhorias 2025 verificáveis; ativar a evolução anual somente com histórico 2022–2024 reconciliado e perímetros comparáveis à BDGD 2025.** Não treinar modelos de previsão nem apresentar projeções.

**Referência operacional em revisão:** PR https://github.com/artelias/BDGD/pull/4, branch `feat/dashboard-bdgd-2025`. O projeto base está em `feat/nucleo-dados-bdgd-portal`. Não alterar a main, não mudar produção sem release homologado.

## Diagnóstico verificado no código atual

- `web/src/components/pages/Matriz.tsx`: alterna métrica principal/quantidade/registros/distintos e filtra famílias, distribuidora/UF, grupo. **Não oferece escolha múltipla livre de entidades nem recortes técnicos por cubos diretamente na matriz.**
- `web/src/components/pages/Explorar.tsx`: lista **entidades individuais**, com atributos DDA unidimensionais e pares previamente curados, agregação Brasil/grupo/distribuidora. Não tem **conceitos funcionais compostos** (p.ex. transformadores).
- `web/src/lib/facets.ts`: exige cubo exato compatível com os atributos filtrados e métricas existentes; combinações inexistentes corretamente retornam `combinacao_nao_suportada`. A soma por categoria não pode ser assumida disjunta.
- `etl/bdgd2025/75_facetas_exatas.py`: ETL atual gera facetas DDA de 1 dimensão e **pares curados**, em particular SSDAT possui par (`FAS_CON`, `TIP_INST`). Isso não significa que todo campo BDGD é filtrável nem que filtros por **linha/circuito AT** já são suportados.
- `web/src/lib/kpis.ts` e `pages/Metodologia.tsx`: diversas fórmulas `COUNT(*)`, `SUM(COMP)/1000`, `POT_NOM` e descrições técnicas estão expostas em áreas públicas. Reorganizar a documentação conforme dois níveis: texto humano por padrão, demonstração técnica sob demanda.
- `pages/Explorar.tsx` exibe a coluna "Participação" apenas sobre o total das categorias selecionadas. Não calcula a **participação da categoria selecionada no Brasil**, mantendo a mesma métrica, faceta e universo de comparação.
- O PR possui a página `/previsoes/` apenas como planejamento, sem ML. A evolução solicitada é **histórica/descritiva**, NÃO é previsão.
- A referência BI VPE 2024 é metodológica. **O PBIX, suas medidas DAX/Power Query e tabelas de parametrização não estão comprovadamente disponíveis neste GitHub.** Antes de reproduzir métricas proprietárias, procurar o PBIX original no computador/arquivos autorizados e extrair as fórmulas reais. Não adivinhar.

## 1. Catálogo semântico de métricas (requisito central)

**O usuário não quer apenas ver os 43 códigos de entidades.** Criar uma camada de **Indicadores de Negócio** separada das entidades técnicas, filtrável por *família funcional* e com cada métrica audível.

- Catálogo versionado (exemplo de contrato, não lista de métricas aprovadas):
  `metric_id,versao,rotulo_negocio,descricao_curta,unidade,formato,granularidade_base,entidades_origem,joins,criterios_de_inclusao,criterios_de_exclusao,campos_bdgd,ddas_e_mcpse,status_homologacao,cobertura_dist,fonte_normativa,origem_bi_vpe,indicador_aditivo,perimetro_temporal`.
- Calcular indicadores compostos em **ETL local offline** sobre staging GDB/Parquet, não reconstruir por soma de cartões no browser. Publicar apenas fatos agregados e metadados (nenhum COD_ID individual, GDB ou Parquet privado no frontend).
- Três níveis de semântica: (a) **contagem de linhas da entidade**; (b) **contagem distinta de unidades/equipamentos físicos** usando grão e vínculos corretos; (c) **quantidade patrimonial/econômica** condicionada por TUC/A1..A6, classe, tipo, estado, localização e regras do BI. Níveis (a), (b) e (c) não são intercambiáveis.
- **Auditoria do BI VPE 2024 antes de afirmar paridade metodológica:** localizar `BI_BDGD_VPE.pbix` e dependências em locais autorizados; identificar nomes de medidas, DAX, Power Query, filtros fixos, relacionamentos, regras de agregação, critérios TUC/A1..A6, tratamentos de cardinalidade, deduplicação, potência e extensões. Criar planilha/documento `MATRIZ-PARIDADE-METRICAS-VPE-2024.md` com `medida_vpe | entidade(s) | regra | equivalente_bdgd_2025 | validacao | divergencia_metodologica | status`. O BI 2024 **não é gabarito dos valores 2025**, apenas das regras, sujeitas a alterações normativas.
- Revisar os catálogos MCPSE/DDA, TUC, equip./instalação reais do BDGD. Exemplo de **candidato a validar, não uma contagem pronta**: TUC **565** é referência para transformadores de distribuição e pode aparecer em `EQTRMT` associado a `UNTRMT` via `UNI_TR_MT`; TUC **570** pode classificar transformador de força em `EQTRAT` e em alguns `EQTRMT` (versão/regras a confirmar). Atributos de tipo e subclasse (A1-A6, TUC, status) podem mudar a definição final. **Não concluir que COUNT(*) de UNTRMT é automaticamente "transformadores TUC 565"**, nem somar `UNTRMT+EQTRMT`. Manter `DIST + DATA_BASE + entidade + COD_ID` como chaves de escopo e medir cardinalidades/deduplicações.
- TUC **00** ou outros exemplos citados pelo usuário devem ser pesquisados nos campos e medidas reais antes de derivar qualquer filtro. Não hardcodar apenas 565/570, nem presumir que nome da entidade implica TUC; obter frequências reais e catálogo de tradução MCPSE apropriado.
- Para cada indicador definir `business_name` e `technical_footnote`, `explainability`, evidência/versão de regra, universo, data-base, status e alertas. Métricas sem regra comprovada permanecem `não homologadas`, mas podem ser exibidas como dados descritivos de entidade sem vender equivalência ao BI.

### Como mostrar matemática sem poluir interface

- No panorama e cartões: usar linguagem natural e unidade, p.ex. **"Extensão declarada da rede MT"**, sem expressão matemática misturada ao título.
- Ação discreta "**Como é calculado?**" abre um popover/drawer com: finalidade, universo, principais fontes, exclusões, conta em linguagem simples, fórmula técnica (p.ex. `SUM(COMP)/1000`), exemplo numérico *explicitamente fictício*, cobertura, versão/metodologia e links de origem.
- Página **Metodologia > Dicionário de Indicadores** navegável e pesquisável por conceito/métrica, com cópia da regra e fonte auditável, não uma parede de fórmulas.
- Possibilitar acesso técnico com "Ver fórmula / SQL/DAX de referência" **somente quando houver equivalência validada**, sem publicar parâmetros sensíveis do usuário.

## 2. Exploração por conceito de ativo antes da entidade

**Alterar `/explorar/` de "Entidades e DDA" como navegação primária para "Explorar ativos" (ou "Ativos e atributos"), mantendo modo técnico opcional "Ver entidades BDGD".**

### Funil de exploração sugerido

1. Seleção de **categoria de negócio**: Transformadores; Redes; Consumidores; Subestações; Seccionamento/Proteção; Reguladores; Compensação; Medição; Geração; Iluminação/estruturas. Catálogo derivado de entidades reais e regras homologadas, não categorias com números inventados.
2. Após selecionar "Transformadores", oferecer **recortes predefinidos de significado claro**, p.ex. "Transformadores de distribuição" (candidato TUC 565), "Transformadores de força" (candidato TUC 570), "Transformação AT/MT" e "Transformação MT/BT"; habilitar apenas quando métrica TUC + vínculo UN/EQ + unidade e QA estiverem validados. Caso contrário mostrar bloqueio e descrição.
3. Pré-selecionar os atributos de maior utilidade e cobertura (tipo patrimonial, tensão, instalação, área, situação, potência/quantidade), exibindo quais entidades e regras sustentam cada número.
4. Usuário poderá trocar de conceito, métrica, empresa/grupo/Brasil e aprofundar em entidade técnica, voltando sem perder contexto. Tooltip mostra relação entre UN* (instalação) e EQ* (equipamento) e por que números não são somados.
5. Presets são **consultas pré-calculadas e homologadas**, não filtros fictícios no browser. Cada preset recebe `concept_id,metric_id,rule_version,dist,source_coverage,status,dimensions_supported`. Um conceito pode ter várias métricas e limites.
6. No seletor avançado disponibilizar entidade individual para especialistas; o público não deverá precisar conhecer siglas `EQTRMT`, `UNTRMT`, etc.

### Campo/atributo faltante e relações espaciais

- Não confundir `atributos presentes na tabela` com `atributos DDA que têm cubo calculado`. Implementar **Inventário de Atributos** por entidade com campos, tipo, descrição, disponibilidade por DIST, vínculo e estado: `filtrável agora`, `requer cubo novo`, `requer junção homologada`, `não publicável`.
- A pergunta "se eu quiser entrar na **linha AT**" é filtro de **contexto elétrico/topológico**, não obrigatoriamente atributo simples de `SSDAT`. Inspecionar `SSDAT`, `CTAT`, `SUB`, `CONJ`, `BAY` e relacionamentos reais de alta tensão por versão. Definir join por `DIST + DATA_BASE + COD_ID/vínculo`, cardinalidade e órfãos; não assumir que CTAT é atributo de SSDAT nem multiplicar segmentos em joins N:N.
- Oferecer **recorte AT**: rede AT total, por área de localização, circuito/linha AT identificada por código/nome público quando permitido, subestação/conjunto vinculado quando homologado, tensão, propriedade, instalação, classe patrimonial TUC e demais campos úteis existentes. Caso dados de linha/circuito fiquem identificáveis, publicar somente identificadores operacionais aprovados de ativos públicos e valores agregados, nunca identificadores individuais de consumidores.
- Se não houver relação válida (ex. chave ausente/órfãos), exibir "filtro de linha AT indisponível por falta de vínculo validado" e cobertura; **não esconder todos os demais filtros** nem extrapolar.
- Adicionar busca dentro dos atributos e exibir "Ver todos os atributos". Mais facetas conjuntas custam CPU/disco; escolher de modo dirigido por interesse e cardinalidade e pré-calcular em ETL por DIST, **sem gerar produto cartesiano universal**. Um backend de agregados sob demanda poderá ser adicionado futuramente se custo/arquitetura autorizados.

## 3. Participação em duas escalas — categoria, grupo e Brasil

Usuário quer responder: **"50% dos ativos do grupo estão no meio rural, mas isso representa apenas 0,1% do rural nacional"**.

Ao escolher uma categoria `c`, métrica `m` e o recorte `s` (empresa/grupo), apresentar lado a lado:

- **Participação interna no recorte**: `v(s,c,m) / v(s,todas_as_categorias,m)`. Ex.: 50% da potência/quantidade **do grupo** em meio rural.
- **Participação do recorte na mesma categoria do Brasil**: `v(s,c,m) / v(Brasil,c,m)`. Ex.: 0,1% da potência rural nacional é do grupo.
- Indicador opcional com rótulo distinto: `v(s,c,m) / v(Brasil,todas_as_categorias,m)`, para "representatividade do rural do grupo no total Brasil". **Não chamar os três percentuais de "participação" indistintamente.**
- Filtro/denominadores devem ter **mesmo exercício 2025, mesma entidade/conceito, mesma métrica, mesmo cubo e dimensões DDA, mesmo status de homologação e cobertura coerente**. Se não forem comparáveis, valor = N/D com razão. Sem denominador/zero, N/D; não exibir infinito.
- Para grupos, membro de DIST não verificado não entra; para categoria de Brasil, usar o universo nacional de DIST com cubo e métrica homologados e **mostrar cobertura** `N de T DIST` (também cobertura ponderada quando houver) e mensagem de parcialidade.
- **Se o cubo contém apenas 2 de 86 DIST de rede**, não mostrar participação "Brasil" como se fosse nacional. Exibir `N/D — cobertura insuficiente para indicador nacional` ou, se for útil, "participação somente nas DIST cobertas" com rótulo explícito e sem comparativo Brasil oficial. Definir gate quantitativo e qualitativo por indicador/categoria, preferindo cobertura completa no universo elegível à métrica.
- Um grupo só pode ser comparado ao Brasil se numerador e denominador estiverem com classes/categorias perfeitamente conciliadas e rollup permitido; categorias sobrepostas não autorizam somar totais. Grupo deve constar no mesmo universo, com interseção auditada.
- A coluna atual "Participação" deve ser renomeada a **"% do grupo/empresa"** ou **"% do Brasil"** de acordo com o escopo, e receber segunda coluna contextual. Se escopo Brasil, apresentar somente "% do Brasil por categoria" para evitar redundância.
- Mostrar gráficos em 100% empilhado + barras absolutas quando unidade aditiva, sempre com cobertura e comparação de denominadores. Sem inferir qualidade operacional apenas pela representatividade.

### Exemplo exclusivamente ilustrativo (não numeração real da BDGD)

`Grupo X, potência de transformadores classificada por área de localização`:
- 50% da potência **do grupo** classificada como rural (participação interna).
- 0,1% da potência **rural nacional** pertence ao grupo (participação na categoria Brasil).
- Se o Brasil não estiver integralmente coberto pelo mesmo cubo, marcar ambas/uma delas conforme a comparabilidade e não rotular "Brasil" sem ressalva.

## 4. Matriz nacional com filtros dinâmicos e hierarquia útil

Atualmente `Matriz.tsx` usa família, grupo e busca de distribuidoras. Propor **controlador de colunas e de linhas**:

- **Colunas por conceito de negócio**, família e **multi-seleção de entidades individuais** (buscar nome/código, marcar favoritos, preset "Essenciais", "Todos", "Redes", "Transformação", "Meu recorte"); indicador de `X/Y` selecionados.
- Métrica por coluna/entidade com unidade, quando homologada; além de modo global métrica principal/quantidade, admitir **colunas calculadas de indicador de negócio** distinto das entidades (ex.: transformador por TUC) apenas com contrato de regra homologado.
- Linhas por Brasil/grupo/DIST opcionais e ordenáveis; grupo só com vínculos verificados. Filtros contextualizados por grupo, UF, distribuidora, cobertura/alerta, conceito e métricas; ligação visual com mapa.
- Se filtros DDA ou atributos forem solicitados na Matriz, o dado deve vir **somente de um cubo aplicável por entidade e DIST**, com status explícito. **Não aplicar um filtro DDA universal à matriz toda** quando só existe para algumas entidades; mostrar "Aplicável a 9 de 43 entidades", optar por ocultar incompatíveis ou manter como N/D.
- Busca de conceitos/metadados (TUC, nome amigável, família) e atalho "Abrir no explorador" para contexto detalhado; presets personalizáveis em estado de URL/localStorage sem armazenamento de dados privados.
- Totais Brasil/grupo apenas de números **aditivos e auditados**, nunca somar `UNTRMT+EQTRMT`, potência com quantidades nem distinct de categorias sobrepostas.
- CSV exporta **exatamente o recorte exibido**, incluindo cabeçalho de `data_base,metrica,unidade,regra,versao,cobertura,status,descricao_filtro` e documenta colunas indisponíveis. Compartilhar filtros via URL.
- UX Apple-inspired: manter tabela premium com colunas congeladas, popover de seleção pesquisável, chips removíveis, foco por teclado, light/dark, mobile scroll e motion discreto.


## 4.1 Decisão adicional APROVADA — Radar com benchmark nacional por indicador

**Deliberação posterior do proprietário:** o gráfico de radar/aranha deve integrar o Comparador como **terceira visualização**, preservando (1) o gráfico atual, aprovado, e (2) as barras espelhadas. Esta decisão **substitui a ressalva anterior de deixar radar para o futuro**. **Não implementar antes da revisão coordenada das telas**; registrar para o Claude na entrega R2.

### Modos de referência

- **Grupo A × Grupo B**: os dois grupos selecionados livremente e comparados no mesmo conjunto de indicadores homologados.
- **Grupo/empresa × Benchmark Brasil**: para **cada indicador** `m`, obter `B_m = MAX_g(v(g,m))` entre os grupos econômicos de 2025 **com fonte verificada, mesmo conceito, método, data-base, unidade e cobertura válida**. Portanto, o benchmark pode ser formado por grupos **diferentes em cada eixo**. O tooltip mostra `nome_do_lider`, `valor_benchmark`, `valor_do_grupo_selecionado`, `proporcao` e `cobertura`; empates são exibidos explicitamente.
- **Grupo/empresa × Brasil total**: opção independente, com total nacional por indicador `T_m = SUM_{DIST elegiveis} v(DIST,m)`; **não confundir com benchmark**. Não somar grupo + suas integrantes duas vezes, e não assumir que membros sem grupo verificado são zero; total Brasil e soma dos grupos podem ter coberturas distintas. A referência "Brasil" no seletor deve deixar claro **"Brasil — total nacional"** ou **"Brasil — líder de cada indicador"**.
- Permitir **empresa × empresa**, **grupo × grupo**, empresa × grupo e empresa/grupo × benchmark quando as grandezas/denominadores forem compatíveis. O benchmark pedido **prioriza líderes entre grupos**, mas pode futuramente oferecer "líder entre distribuidoras" como universo separado e explicitamente rotulado; não misturar rankings de grupos e DIST.

### Normalização obrigatória do radar

- Eixos representam **conceitos e métricas diferentes** (ex.: quantidade de transformadores de força, km de rede MT, potência de transformação); NÃO desenhar valores brutos heterogêneos em um mesmo radial.
- No modo **benchmark**: `radar_percent(A,m) = 100 × v(A,m) / B_m` e `radar_percent(benchmark,m)=100`, somente para `B_m>0`, valores válidos e conceito homogêneo. Exemplo **fictício**: transformadores de força Energisa 1.500 e grupo líder Cemig 2.000 → **75% do benchmark**, com valor absoluto no tooltip.
- Para **grupo A × grupo B**, priorizar a escala nacional de benchmarks por eixo `B_m` como referência **externa idêntica para os dois grupos**, ambos desenhados como proporção da mesma escala. Não normalizar cada grupo por seu próprio máximo (produziria comparação enganosa). Sinalizar se algum grupo escolhido superar benchmark devido a recálculo/cobertura distinta, corrigindo universo antes de exibir.
- Para **Brasil total**, a escala pode ser o valor nacional `T_m`, novamente igual nos dois lados e explicada. Em modo benchmark líderes, usar `B_m` por indicador; nenhum destes percentuais deve ser chamado de participação de mercado sem denominação apropriada.
- Grupos com **cobertura insuficiente**, atributos TUC não homologados, métricas não aditivas, categoria sem universo válido ou denominador zero: exibir N/D e **retirar eixo do radar com indicação visível**, em vez de converter N/D em zero. Não ligar silenciosamente vértices através de lacunas.
- **Mais ativos não significam melhor desempenho/eficiência**. Intitular este modo "**Maior volume por indicador — benchmark nacional**", evitando "`melhor`" no sentido qualitativo; um benchmark de eficiência seria outro estudo com métricas técnicas comparáveis.
- Não somar UN*+EQ* do mesmo objeto, TUC 565/570 não homologados ou categorias DDA sobrepostas para construir benchmark.

### Requisitos de UX

- Terceira opção claramente rotulada `Radar · Benchmark` ao lado do gráfico principal e de `Barras espelhadas` (pode haver segmented control ou tabs).
- Campo **Comparar** e campo **Com** independentes e pesquisáveis, com opções grupo, distribuidora, `Brasil — total nacional`, `Benchmark Brasil — líder por indicador` (conforme regra).
- Seleção de 4 a 8 eixos de negócio (default 5–6), com indicador e unidade no detalhe; tela vazia se não houver mínimo de 3 eixos homologados. Predefinições `Transformação`, `Redes`, `Operação` só se existirem indicadores homologados de interesse.
- Legenda A/B consistente com os cartões (A à esquerda, B à direita), benchmark no tom visual próprio (não fingir ser empresa), hover/foco por eixo mostrando liderança e valores brutos. Animar transição com suavidade e respeitar `prefers-reduced-motion`.
- Alternativa **tabela acessível** com valores, unidade, proporção % e líderes; mobile legível, leitores de tela e exportação CSV do benchmark e da métrica por categoria.
- Exibir a base de comparação `31/12/2025` e a definição do universo de grupos comparados; no futuro a visão histórica só poderá utilizar benchmarks por competência/perímetro corretamente harmonizado.

**Teste mínimo de aceitação (dados sintéticos rotulados):** grupo A com 1.500 transformadores de força, líder com 2.000 → eixo A=75%, eixo benchmark=100%; líder do próximo eixo pertence a outro grupo sem afetar o primeiro; grupo A versus B usa mesma escala por eixo; indisponível → N/D, não 0; `Brasil total` não é `MAX_grupo`. Nenhum número sintético deve chegar ao release público.

## 5. Panorama Brasil — revisão sem poluição visual

- Dar prioridade ao mapa ARAT, composição de indicadores verificáveis e navegação por ativos/conceitos, não apenas siglas técnicas.
- Introduzir **seletor resumido de indicador de negócio** para acompanhar mapa/rankings, com métricas fisicamente coerentes e filtro de grupo/empresa preservado.
- Cartão "Participação nacional" no contexto de grupo/empresa, indicando **métrica e denominador**, se houver universo homologado; não tratar participação de território, extensão, potência e quantidade como equivalentes.
- KPIs com subtítulo claro, status de qualidade e "Como é calculado?" a pedido; acesso de um clique para Explorar (preset) e para Matriz (colunas correspondentes).
- Checar coerência de denominação de transformadores: `COUNT UNTRMT` não deve ser automaticamente descrito como contagem TUC 565. Se métrica física/patrimonial do BI for diferente, colocar dois indicadores com nomes corretos ou substituir após homologação.
- Não esconder ausência de 2025 nas empresas sem GDB; nunca utilizar 2024 como fallback no Panorama. Gráficos com valores parciais trazem cobertura e estado da homologação.

## 6. Nova aba "Evolução histórica" — **realizado**, não previsões

Adicionar uma rota `/evolucao/` na barra de navegação **entre Matriz e Comparador** (posição de design pode mudar desde que seja facilmente encontrada). Rótulo curto "Evolução"; título "Evolução histórica dos ativos"; **não juntar à aba /previsoes**.

**O usuário deseja tabela PRONTA de indicadores, com recorte pré-definido por conceito e sem reconstrução de filtros DDA na tela.** Mostrar:
- Tabela com linhas `distribuidora/grupo/indicador` e colunas `2022`, `2023`, `2024`, `2025`, `Δ absoluto 2022→2025`, `variação % 2022→2025` e opcional `CAGR` apenas quando base positiva, todos os anos válidos e métrica aditiva/comparável. Suporte de visualização alternativa por ano em linhas e small multiples de tendência.
- Seletor simples por **empresa ou grupo** e **indicadores pré-homologados** (p.ex. consumidores, redes MT/BT/AT, transformadores de distribuição, potência MT), com mini-tendência e ranking. Evitar filtros técnicos DDA nessa página; usuário escolhe **o que observar**, não precisa construir a métrica.
- Exibir nome, unidade, tooltip simples de significado, cobertura e fonte; `Δ%=(valor2025/valor2022-1)*100` somente quando denominador válido e positivos/cobertura comparável. Se dados ausentes, alteração de regra ou perímetro, N/D.
- Duas visões temporais: **"Conforme publicado"** por DIST e **"Comparável ao perímetro 2025"** com ponte de sucessões, usando [HARMONIZACAO-SUCESSAO-2022-2025.md](HARMONIZACAO-SUCESSAO-2022-2025.md). Caso EPB/EBO, 2022 pode exigir composição de predecessoras e 2023 precisa tratar ano de transição sem dupla contagem. Nunca inferir crescimento de fusão sem harmonização.
- Grupos econômicos com filiação válida **por data-base** para a visão conforme publicado, e `perimetro_grupo_ref=2025` quando comparativo a perímetro de referência; declarar qual visão foi escolhida.
- Variações por entidade com TUC/padrões contábeis mudando entre revisões 2022–2025 devem carregar `metric_version` e `comparavel_2025`. O ano-base é `31/12` de cada competência, e a ferramenta de comparação histórica é descritiva.
- Tabela deve admitir **indicadores diferentes em unidades diferentes** apenas em **linhas separadas**, nunca somar km + kVA + unidades. Exibir setas de tendência como variação observada, não "melhora/piora" sem KPI operacional validado.
- **Ativação progressiva:** enquanto 2022–2024 ainda não estiverem validados, desenvolver rota/componentes com estado vazio editorial "Histórico 2022–2024 em preparação", descrevendo que 2025 já é a base disponível; sem usar valores fictícios como série. Evitar código morto: adicionar testes de leitura do contrato e fixtures sintéticas rotuladas apenas para QA local, não produção.
- Treinamento de ML, cenários preditivos, ranking 2026–2029 e intervalo de confiança continuam totalmente fora desta rodada.

### Contrato de saída temporal proposto (ETL local 2022–2024 + 2025)

`historico_indicadores.csv` (somente agregados públicos após QA):
`ano_base,data_base,dist_origem,dist_referencia_2025,grupo_id,perimetro_tipo,metric_id,metric_version,unidade,valor,status_qualidade,comparavel_2025,regra_sucessao_id,fonte_arquivo,sha256_origem,coverage_flag`.

`catalogo_indicadores.csv`: as regras do item 1.

`evolucao_manifest.json`: `schema_version,anos=[2022,2023,2024,2025],fontes,metric_version,cobertura_por_ano,release_historico,qa,data_publicacao`.

`eventos_sucessao_distribuidoras.csv`, `ponte_perimetro_2025.csv`, `regras_comparabilidade_historica.csv` e `qa_sucessao.csv` referenciados pelo contrato de sucessões existente.

Manter banco opcional; agregados públicos versionados podem ficar em JSON estático compacto por indicadores/ano, sem GDB/Parquet/CPF/COD_ID individual exposto.

## 7. Plano de entrega e prioridades (não travar ETL 2025)

### R2-A — design & métricas 2025 (prioritário, pode seguir durante ETL)
1. Criar auditoria BI VPE 2024 e catálogo de indicadores/presets; documentar regra e status sem inventar TUC.
2. UI "Como é calculado?" e dicionário de métricas, sem remover rigor/metodologia atual.
3. Explorer por conceito com transformação/unidades/equipamentos/TUC; modo técnico por entidade preservado.
4. Adicionar participação interna × participação na mesma categoria Brasil com cobertura correta, no Explorer e Panorama.
5. Estender Matriz com seleção livre de colunas/entidades e presets; preservar fato-base e opção de facetas homologadas.
6. Rever área AT/SSDAT/CTAT/relacionamentos e priorizar filtros com cobertura/uniões válidas; produzir novos cubos apenas após QA e conforme recurso de máquina disponível.
7. Implementar E2E/contrato e revisão visual (desktop/celular, light/dark, teclado, reduced motion) com screenshots e checklists de aceitação.

### R2-B — histórico 2022–2025 (após extração/harmonização)
8. Processar e homologar 2022, 2023, 2024 e integrar com pacote 2025, com distinção entre original e perímetro comparável.
9. Gerar métricas prefiltradas por ano/empresa/grupo, versionar manifesto e teste de continuidade de 2022–2025.
10. Ativar página Evolução histórica com tabela, variações observadas e cobertura. Validar EPB/EBO como exemplo, sem extrapolar outras sucessões sem fonte.

### R2-C — release
11. Testar impacto do novo painel no `output: export` do Next.js 16, rotas estáticas, prefetch, worker MapLibre, CSS do mapa, navegabilidade mobile e acessibilidade; adicionar regressões E2E.
12. Publicar códigos/testes/docs em branch derivada de `feat/dashboard-bdgd-2025` ou no branch autorizado do Claude, **sem força de push, sem merge automático e sem trocar main**. Abrir issue/PR vinculado e manter `previsoes` apenas como planejamento.
13. Site em preview (público somente quando homologado), sem aumento de custo. Nenhuma dependência de deploy para concluir código/testes.

## 8. Critérios mínimos de aceite testáveis

- [ ] Cada cartão oferece compreensão em linguagem simples e fórmula técnica acessível de maneira opcional, com fonte e versão.
- [ ] Selecionar **Transformadores** mostra presets funcionais verificados, e `TUC 565` não é somado automaticamente a unidade + equipamento.
- [ ] Visão de entidade individual ainda existe e permite acesso a todos atributos **catalogados**, diferenciando os realmente filtráveis.
- [ ] `SSDAT` oferece recursos AT filtráveis que tenham vínculo/QA sustentados, ou informa precisamente o motivo de impossibilidade, sem mostrar opção falsa.
- [ ] Para categoria rural e grupo selecionado, a tabela tem **% dentro do grupo** e **% do rural do Brasil**, com denominadores explícitos e invariância matemática testada.
- [ ] Cubo parcial (p.ex. 2/86 DIST) **nunca** vira participação nacional sem aviso ou N/D; cobertura numérica e status são verificáveis.
- [ ] Matriz permite seleção livre de entidades/colunas e presets, e o CSV corresponde integralmente ao filtro aplicado.
- [ ] Evolução tem somente dados observados 2022–2025, pré-filtrados e auditados, e distingue série publicada x perímetro referência 2025.
- [ ] Variações/participações com denominador zero, incompatível ou dados incompletos retornam N/D com motivo.
- [ ] Unit test + E2E + CI passam, com tratamento de mobile, foco e motion reduzido; app não apresenta números fictícios como oficiais.

**Autoria:** Arthur Henrique Lima. **Data:** 23/10/2026.
