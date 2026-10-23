# Direção de arte — Núcleo de Dados da BDGD

**Conceito.** Um instrumento cartográfico calmo: a área de atuação real é a protagonista, os números aparecem com tipografia de dados e cada valor carrega unidade, cobertura e estado. Referência de *qualidade* em Apple Maps (mapa + painel contextual), Apple Health (números grandes, leitura imediata) e macOS (navegação discreta) — sem copiar componentes, ícones ou layouts.

**Paleta (tokens em `src/app/globals.css`).** Papel neutro levemente quente (`--bg #f4f4f1`, superfícies brancas) e grafite (`--text #1b1b19`). Escuro projetado à parte: antracite `#0d0e10`, superfícies `#15171a`, acento mais claro para contraste. **Um acento** (cobalto `#2b55d6` / `#7d97ff`) para interação e seleção. Estados: aprovado (verde), alerta (âmbar), indisponível (cinza). Comparador: A cobalto, B terracota — oposição sem juízo de valor. Grupos econômicos: 11 matizes de luminância controlada por tema; `não confirmado` é neutro e **hachurado** no mapa.

**Tipografia.** Pilha do sistema (`-apple-system`, `Segoe UI Variable`) com display a 650 e tracking negativo; corpo 15 px; algarismos tabulares em toda tabela e KPI; mono do sistema só para códigos BDGD (`UCBT`, `SSDMT`). Hierarquia por peso e tamanho, não por cor.

**Layout.** Barra lateral recolhível (244 → 68 px) com indicador ativo que desliza; barra superior translúcida com busca ⌘K, data-base e tema; título grande que migra para a barra superior ao rolar. Conteúdo até 1480 px. No celular: barra de abas inferior (alvos ≥ 48 px), folha “Mais” arrastável, mapa com folha inferior de três apoios. Superfícies agrupadas por divisores finos — faixas e tabelas, não grades de cartões.

**Movimento (tokens `--dur-1/2/3` = 140/220/320 ms, `--ease-out` cubic-bezier(.22,1,.36,1)).** Molas curtas (stiffness 380–520, damping 34–40) só onde há física: indicador da navegação, controle segmentado, troca A↔B, folhas inferiores, seleção de entidade. Mapa: contorno de hover com transição de opacidade, enquadramento ao selecionar, realce/esmaecimento por grupo com transição de 320 ms. KPIs contam ≈650 ms uma única vez, após o dado real carregar, com o valor final no rótulo acessível. `prefers-reduced-motion` zera durações e desliga animações de gráfico e contagem.

**Não faremos.** Glassmorphism em tudo (translucidez só em barra superior, painel do mapa e dicas, com fallback sólido); gradientes, neon, blobs ou partículas; grade infinita de cartões iguais; badges coloridos em excesso; números de demonstração como reais; zero no lugar de N/D; percentuais estimados por marginais; centróides ou contornos de UF no lugar da ARAT; scrolljacking.

**Acessibilidade.** Foco visível, teclado completo (⌘K, setas em segmentados e listas, Escape fecha), lista navegável como alternativa ao mapa, rótulos ARIA em gráficos, contraste AA nos dois temas, `lang="pt-BR"`, link “Ir para o conteúdo”.

## Rodadas de revisão visual (screenshots reais, desktop 1440 e celular 390, claro e escuro)

1. **Layout e hierarquia.** Título duplicado (barra + página) → título grande migra para a barra só ao rolar. Títulos internos reduzidos (2,9 → 2,4 rem). Barras de ferramentas encolhiam controles no celular → quebram linha sem fixar; seletor compacto de 36 px alinhado aos botões. Faixa de KPIs com números colidindo → formato compacto (`23,9 mi`) com valor exato na dica e no rótulo acessível. Lista do mapa ganhou cabeçalho com o indicador ativo e nota sobre áreas sem dado (ausência, não zero). Legenda de grupos compactada; subtítulo da marca sem truncar.
2. **Tipografia, estados e microinterações.** Ver `docs/REVISAO-VISUAL.md` (gerado com as capturas da segunda rodada).
