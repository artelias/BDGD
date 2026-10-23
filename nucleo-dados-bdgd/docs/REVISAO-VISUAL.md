# Revisão visual do dashboard BDGD 2025

Capturas reais (Playwright/Chromium, `scripts/shots.mjs`) do app com dados do pacote 2025-12-31, em **desktop 1440×900** e **celular 390×844 (DPR 2)**, temas **claro e escuro**, com `prefers-reduced-motion: reduce` para estabilizar as imagens. Páginas: Panorama, Matriz, Comparador, Entidades e DDA, Metodologia, mais estados (grupo filtrado, distribuidora selecionada, cascata DDA, distribuidora contida no grupo).

## Rodada 1 — layout e hierarquia

| Problema observado | Correção |
|---|---|
| Título da página repetido na barra superior | Título grande no conteúdo; a barra mostra o título só depois de 96 px de rolagem (transição de 220 ms) |
| Títulos internos pesados (até 46 px) | Escala `--fs-display` reduzida para 28–38 px |
| Barras de ferramentas no celular comprimiam seletor e segmentado em caixas vazias | Quebra de linha, controles com largura natural, sem fixação no celular; seletor compacto de 36 px alinhado aos botões |
| Faixa de KPIs com números colidindo (`23.902.8891.210.598 km…`) | Formato compacto (`23,9 mi`, `1,21 mi km`), valor exato em `title` e `aria-label` |
| Lista do mapa sem dizer o que os números significam | Cabeçalho fixo com o indicador ativo; consumidores usam a união de COD_ID |
| Áreas brancas no mapa sem explicação | Nota: distribuidoras ainda não publicadas ou sem BDGD 2025 — ausência, não zero |
| Legenda de grupos em quatro linhas | Chips de 24 px com espaçamento menor |
| Subtítulo da marca truncado na barra lateral | Texto encurtado |

## Rodada 2 — tipografia, estados e microinterações

| Problema observado | Correção |
|---|---|
| **Mapa vazio no build de produção** (canvas com 300 px): a ordem do CSS do MapLibre muda no build e `position: relative` anulava o posicionamento | Largura/altura explícitas de 100% no contêiner; teste E2E de regressão exige altura > 400 px |
| Padrão de hachura do “não confirmado” pedido antes de existir | Imagem e camada adicionadas no evento `load` |
| Prefetch de rotas com 404 no export estático do Next 16 (`__next.<seg>.__PAGE__.txt`) | `postbuild` cria as cópias com o nome esperado pelo roteador |
| Códigos DDA distintos com a mesma descrição exibiam rótulos idênticos | Código acrescentado ao rótulo quando há duplicidade |
| Cubo conjunto calculado para parte das distribuidoras somado sem aviso | Selo “Cubo: X de Y DIST” em toda distribuição DDA |
| Alerta antigo de COD_ID repetido aparecia em distribuidoras válidas pela regra UC v2 | Alertas reavaliados no montador; só permanecem casos com mais de um registro ativado |
| Regras do React Compiler (setState em efeito, refs no render) | Hooks com `useSyncExternalStore` (tema, media queries, preferência da barra), ajuste de estado na renderização quando a prop muda, folha inferior com três apoios medida por `ResizeObserver` |

## Limitações conhecidas

- O selo de dev “Insight” aparece só no `next dev`; não existe no build.
- Rótulos de UF são aproximados (interseção com Natural Earth 1:50 000) e indicados como tal.
- O mapa não é navegável por teclado por natureza; a lista do painel é a alternativa equivalente.
