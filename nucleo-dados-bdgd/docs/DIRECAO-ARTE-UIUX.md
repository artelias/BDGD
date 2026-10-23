# Direção de arte e especificação UI/UX — Núcleo de Dados da BDGD

**Status:** requisito obrigatório da Fase A do projeto, definido pelo responsável em 22/10/2026. Objetivo: interface **profissional, minimalista, sofisticada, autoral, com motion design e interações personalizadas**, sem aparência genérica de dashboard gerado automaticamente. **Não sacrificar desempenho, legibilidade ou fidelidade dos dados por animação.** Este documento integra o [PROMPT-CLAUDE-DASHBOARD-2025-DEPOIS-HISTORICO-2022-2024.md](PROMPT-CLAUDE-DASHBOARD-2025-DEPOIS-HISTORICO-2022-2024.md) e o [PLANO-GERAL.md](PLANO-GERAL.md).

## 1. Princípios visuais

- **REFERÊNCIA VISUAL PRINCIPAL: experiência de produto Apple**, especialmente princípios de Apple Maps (mapa protagonista + painel contextual), Apple Health (dados objetivos, tendências e clareza) e macOS/iPadOS (navegação discreta, profundidade leve, refinamento de estados). Usar como **inspiração de qualidade**, sem copiar screenshots, componentes proprietários, marcas, logotipos, interfaces pixel a pixel ou assets protegidos. A identidade final deve ser específica do Núcleo de Dados da BDGD.
- Hierarquia forte, tipografia precisa, ritmos consistentes, composições sob medida por página, espaço negativo intencional, alinhamento óptico, bordas sutis e sombras econômicas.
- Evitar aparência "AI-generated": cartões idênticos em grid infinito, formas/gradientes neon decorativos, blobs, glassmorphism excessivo, ícones desnecessários, muitos badges coloridos, títulos grandiloquentes, texto prolixo, gráficos aleatórios e efeitos em todos os componentes.
- Escolher uma tipografia contemporânea coerente de **licença permitida** (sugestão: **Instrument Sans para UI + IBM Plex Mono somente para códigos/valores técnicos**, se funcionarem bem no render). Usar `font-variant-numeric: tabular-nums` nas tabelas e KPIs. Não subir arquivos de fonte sem licença nem depender de serviços externos proibidos.
- Paleta autoral profissional: fundo neutro levemente quente/frio, textos grafite, superfícies discretamente distintas, **1 acento cromático principal** e cores semânticas limitadas (qualidade/alerta/indisponível). Modo escuro projetado de fato, **não simples inversão de luminosidade**.
- Componentes refinados e compactos, voltados a leitura e exploração de indicadores: tipografia de dados, alinhamento por casas decimais, unidades claras, densidade adequada, truncamentos previsíveis, tooltips verdadeiramente úteis.

## 1.1. Linguagem Apple-inspired — refinada e original

**Requisito do responsável: "algo como um Apple design".** A execução deve transmitir calma visual, precisão tipográfica, hierarquia imediata e microinterações que parecem físicas e naturais; o foco visual continua nos **dados verdadeiros**.

- **Estética:** superfícies off-white/prateadas, fundo cinza muito suave, divisores finos, texto grafite e acento azul ou verde escolhido de forma consistente; dark mode antracite profundo com materiais próprios. Nada de gradientes neon, caixas glass exageradas, sobreposição confusa ou cartões repetidos.
- **Tipografia:** usar stack de sistema `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` com fallback competente (sem redistribuir San Francisco nem fontes proprietárias). Grandes indicadores com algarismos tabulares, rótulos discretos e números fáceis de comparar.
- **Profundidade:** camadas e materiais translúcidos apenas no topo/painéis flutuantes, com fallback sólido, contraste AA e `backdrop-filter` progressivo. Painéis de dados extensos permanecem preferencialmente opacos e altamente legíveis.
- **Mapas:** ARAT 2025 verdadeira como conteúdo principal, contextualizada por um painel lateral/bottom sheet inspirado na dinâmica de Apple Maps; seleção de polígonos, zoom de encaixe e detalhes correlatos fluidos.
- **Interações:** componentes táteis com alvos de pelo menos cerca de 44×44 CSS px para ações principais, foco visível, teclado completo, hover distinto de estado selecionado, menus com geometria consistente e scroll natural.
- **Motion:** transições e springs discretas, easing orgânico, sem bounce caricatural, sem blur pesado em cada mudança. Navegação, sidebar, cards expandidos, modais, filtros DDA, gráficos, mapa e troca A/B devem ter transições próprias **motivadas pela interação**. `prefers-reduced-motion` respeitado.
- **Conteúdo e hierarquia:** estilo Apple não significa interface com pouca informação; compatibilizar uma visão panorâmica respirada com uma matriz densa, filtrável e profissional. A informação extensa deve estar disponível sem afundar o usuário em cartões decorativos.
- **Originalidade:** produzir um sistema de componentes próprio (tamanhos, paleta, gestos, semântica e layout), evitando imitar screenshots e sem usar imagens, trademarks, ícones privativos ou textos de UI da Apple.
- **Critério de avaliação visual:** interface deve parecer um produto premium de engenharia de dados, **não um clone de macOS nem um painel genérico gerado por IA**. Revisar em screenshots reais desktop/tablet/mobile, em temas claro/escuro, antes de homologar.

## 2. Design system implementado em código

Antes de repetir centenas de estilos, definir tokens reais e documentados:
- Cores semânticas para light/dark, superfícies, separadores, foco, hover, status e paleta acessível para séries e grupos.
- Escala tipográfica fluida (headlines, subtítulos, corpo, rótulo, legenda, número KPI), pesos, tracking e métricas em unidades responsivas.
- Espaçamentos com escala coerente, radius por componente, elevações discretas, largura máxima e breakpoints por conteúdo, não por dispositivo suposto.
- Conjunto consistente de ícones **Lucide**, tamanho/traço/área clicável padronizados; não usar emojis como interface.
- Biblioteca de componentes internos reutilizáveis, estados hover/focus/pressed/disabled/loading/empty/error/success; documentação no repositório e ao menos uma página/rota de showcase ou story de componentes (pode ficar fora da produção).

## 3. Layout e navegação

- Identidade "Núcleo de Dados da BDGD" + assinatura **"Desenvolvido por Arthur Henrique Lima"**, sem se apresentar como produto oficial ANEEL.
- Desktop: navegação lateral recolhível com transição delicada, cabeçalho compacto e área de análise ampla; não deixar as tabelas esmagadas pelo menu.
- Mobile: navegação ergonomicamente acessível, sheet/drawer com overlay, filtros em painel de aplicação explícita, tabelas roláveis sem quebrar cabeçalho e sem depender de hover.
- Página Panorama: foco em um **mapa nacional ARAT real** e composição de KPIs/gráficos **não repetitiva**. A seleção no mapa realça distribuidora, filtra estatísticas e expõe contexto verificável.
- Página Matriz: comportamento de ferramenta analítica de alto nível, primeira coluna fixa, cabeçalho sticky, virtualização se necessário, reordenação/ocultação por famílias, densidade otimizada, filtros sem perda de contexto e exportação exata.
- Página Comparador: seleção A/B com linguagem visual de oposição deliberada, detalhes por métrica, diferenciais positivos/negativos semanticamente contextualizados (não assumir que "mais" sempre é melhor).
- Filtros DDA: facetas dependentes, busca com teclado, chips removíveis, resumo de filtros ativos e botão "Limpar"; não apresentar lista universal de dimensões não suportadas.
- Metodologia: leitura editorial, glossário, estados de qualidade claros e links de proveniência ANEEL com contraste/hierarquia.

## 4. Motion e microinterações personalizadas

Criar uma **linguagem de movimento consistente** que ajude a compreender transições de estado, e não apenas efeitos decorativos. `Motion for React` (ou CSS/Web Animations API) só quando a dependência se justificar e não prejudicar manutenção. Sugestões calibráveis:
- Transições de navegação de **180–280 ms**, fades e deslocamentos curtos (4–12 px), easing suave e sem saltos de layout.
- Entrada escalonada **sutil** dos blocos na primeira visita (stagger breve), sem atrasar a leitura dos dados nem recriar efeitos em cada filtro.
- Sidebar colapsável com animação de largura/ícones sem causar jank, foco preservado e nomes acessíveis.
- Painéis de filtro, popovers, tooltips, menus e seletores com expansão/contração elegante, posicionamento responsivo e fechamento por Escape.
- KPIs: contagem animada **apenas quando valor tiver sido realmente carregado e de forma curta**, sem impedir que tecnologia assistiva leia o número correto; atualização com indicação visual sutil da mudança e estado de carregamento.
- Charts: transição entre séries e filtros conservando eixo/escala e contexto; explicação no hover/focus. Não exagerar em rotações, 3D ou efeitos que distorçam comparação.
- Mapa ARAT: hover de polígono real, contorno ativo com transição, fitBounds ao selecionar, tooltip sem obstrução, cores/realce por grupo confiável, clique ↔ painéis/gráficos sincronizados. Não animar geometrias de forma topologicamente incorreta.
- Skeletons de carregamento **sóbrios**; estados vazios/erro com orientação útil e animação mínima; toast informativo para exportação e ações reais.
- `prefers-reduced-motion` respeitado; todos os efeitos não essenciais removíveis. Sem motion forçado ou scrolljacking. Alvo 60 fps para interações normais, preferindo transform/opacity e evitando animações custosas de layout.

## 5. Interações e experiência de dados

- O usuário poderá selecionar distribuidora no mapa, ler cartões correlacionados, navegar da matriz para o detalhamento e abrir o comparador com seleção pré-preenchida.
- URLs compartilham filtros/seleções sem expor informação individual; histórico do navegador, back/forward e recarga preservam a navegação.
- Busca global ou busca contextual eficiente por sigla/DIST/nome, sem pressionar o usuário a conhecer códigos.
- Escolher unidade da métrica por contexto e mostrar fórmulas, data-base, fonte e status; nunca exibir "N/D" como 0 nem esconder empresas sem dado sem aviso.
- Alternância claro/escuro persistente, respeitando inicialmente preferência do sistema. Exportações nomeadas com data-base e filtros relevantes.
- Cuidado especial com população de 99 distribuidoras, catálogo de 43 entidades e filtros DDA: tabelas com virtualização ou paginação, aria/teclado, responsividade e performance real.

## 6. Acessibilidade e desempenho

- WCAG 2.2 AA como referência de projeto: contraste AA em texto e visualizações, foco visível, sem navegação por cor apenas, teclado completo, labels e tooltips acessíveis.
- `prefers-reduced-motion: reduce`, mínimo de animações para leitores sensíveis; skeleton não deve vibrar eternamente.
- Mapas: seleção acessível também por lista/tabela, pois geometria não é teclado-first por padrão. Indicadores não dependem exclusivamente de mapa.
- Mobile real: testar larguras de **360/390, 768/1024 e 1440/1920 px**; desktop sem rolagem horizontal de página, apenas dentro da tabela quando intencional.
- Lazy loading de MapLibre/ECharts quando fizer sentido; geometria simplificada/tiles para proteger payload; nenhum download do GDB; vitals monitorados. Não adicionar pacote grande para implementar apenas um pequeno efeito.
- Testar `loading/empty/error/partial data` e mudanças rápidas de filtro sem conteúdo errado/flash de dados fictícios.

## 7. Processo e entregáveis obrigatórios de design

1. Estabelecer uma **direção de arte escrita de uma página**, com tipografia, paleta, layout, composição, motion tokens e decisões negativas ("não faremos").
2. Implementar componentes visuais **reais e testáveis**, não apenas um design mockado ou screenshot.
3. Gerar e inspecionar **screenshots reais** da aplicação em desktop e smartphone, **light/dark**, nas páginas Panorama, Matriz, Comparador e Exploração DDA. Revisar alinhamento, contraste, hierarquia e densidade. Se tiver Playwright/browser, automatizar snapshots e fluxos.
4. Executar manualmente ou automatizar testes: entrada/saída de sidebar, ARAT hover/select, filtros em cascata, export, comparação A/B, keyboard navigation, dark mode e redução de movimento.
5. Fazer ao menos **duas passagens de refinamento visual**: (a) layout e hierarquia; (b) tipografia/espessuras/estados/microinterações. Registrar mudanças específicas e limitações restantes.
6. Concluir quando as páginas parecerem parte de **um produto intencional** e oferecerem informação real auditada, e não um conjunto desconexo de cartões.
7. Publicação na Vercel **não é dependência de UX**: se o deploy falhar por permissão, rodar a aplicação local, executar screenshots/testes, fazer push do código e fornecer instruções de deploy. Não parar o desenvolvimento ou reduzir a qualidade.

**Gate:** considerar a Fase A incompleta se só existir estrutura técnica sem design refinado, se animações forem meramente decorativas, se os gráficos/ARAT não forem interativos, ou se a interface não funcionar/for ilegível em smartphone.

## 8. Limites éticos e funcionais

- Não inventar dados, grupos ou dimensões para preencher telas; a identidade visual deve funcionar igualmente com `N/D` e cobertura parcial.
- Não confundir inferência com dados oficiais e não usar "smart insights" fabricados. Animação não mascara valores nem substitui fonte/regra de cálculo.
- Evitar dependência de outras marcas e assets protegidos; imagens ilustrativas só se exigidas pelo produto, não stock genérico.
- Sem treinar ML nesta etapa; previsões ficam no backlog e não são exibidas como dados reais.

**Rótulo de qualidade desejada:** `visual premium, editorial, autoral, minimalista e sofisticado, com microinterações discretas e úteis; não template e não estética genérica de IA`.
