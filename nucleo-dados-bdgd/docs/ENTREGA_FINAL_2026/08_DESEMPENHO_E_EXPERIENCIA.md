# 08 — Desempenho e experiência de uso

Medições feitas na build estática de homologação (`out/`, servida localmente por `serve` com compressão), com o Chromium do painel do navegador, em 2026-11-01.

| Item | Medida |
|---|---|
| Tamanho total de `out/` (homologação) | 54 MB, quase tudo dados agregados versionados; nenhum Parquet |
| Maior chunk JS | 1,07 MB sem compressão (ECharts e MapLibre, carregados sob demanda) |
| HTML das páginas | 23–58 KB |
| Previsões: DOMContentLoaded / load | 371 ms / 1,9 s (local) |
| Previsões: requisições / transferência | 61 / cerca de 1,2 MB |
| Mudança inesperada de layout (CLS) em Previsões | 0 |
| Motor V2: índice | 5 KB transferidos (74 ms) |
| Motor V2: série de uma DIST | cerca de 10 KB transferidos (119 ms); um arquivo por DIST, carregado sob demanda |
| Motor V2: tamanho total do produto | cerca de 7,2 MB (115 JSON); nenhum arquivo acima de 200 KB (teste) |

## Escolhas que mantêm a página leve

- **Nada é treinado no navegador.** O Motor V2 é um produto pré-calculado: índice e um JSON por DIST, carregados só quando a DIST ou o grupo são escolhidos.
- **Grupos econômicos** carregam só os arquivos das DIST do grupo. A soma é feita no navegador e rotulada `PARCIAL` quando falta DIST.
- **Gráficos** usam o ECharts com renderizador SVG e só os módulos necessários; o ResizeObserver redesenha sem recarregar.
- **Sem Parquet no navegador.** Os maiores arquivos de dados continuam sendo as facetas de UCBT e UCMT (cerca de 4 MB e 2 MB sem compressão), servidas com cache de 1 hora (`vercel.json`).
- **Estados de carga e de erro** com repetição ("Tentar novamente") em todas as seções do Motor V2, e N/D explícito para ausência.

## Responsividade

O E2E `e2e/motor-v2.spec.ts` percorre as **sete páginas em 1440, 1024, 901, 900, 768, 390 e 320 px** e exige rolagem horizontal ≤ 1 px. De 901 px para cima, a lateral recolhe com largura real de 244 para 68 px, a coluna principal acompanha e ela volta ao expandir. Até 900 px, a lateral some e aparece a navegação inferior.

Os testes do Codex (`sidebar.spec.ts`, `tema.spec.ts`, `a11y.spec.ts`, projetos `mobile` e `iphone-estreito`) cobrem altura baixa, teclado, armazenamento bloqueado, tema e acessibilidade (axe).

## Limites desta medição

As medidas são locais (loopback). A latência real depende da CDN da Vercel e da rede do usuário. Não houve perfil de memória de longa duração; os testes trocam páginas e filtros repetidamente sem erro no console.
