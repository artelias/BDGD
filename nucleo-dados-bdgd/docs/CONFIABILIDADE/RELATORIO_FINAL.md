# Relatório final: retomada e conclusão do módulo de Confiabilidade

Data: 12/11/2026 · Repositório `artelias/BDGD` · Branch `feat/inteligencia-confiabilidade-dec-fec-20261111`
Commit inicial `c234089` → final indicado no fim deste documento. **Sem merge e sem deploy.** RC `rc/1.0-20261101`,
produção, Motor de Expansão e bases BDGD originais não foram tocados; as 379 cargas da BDGD não foram reexecutadas.

## 1. P0: HTTP 500 em `/confiabilidade`

**Causa comprovada** (log do servidor Next.js 16.4.2 / Turbopack, não presumida): `web/node_modules` do worktree era uma
**junção** para o `node_modules` da worktree da RC. O Turbopack resolve o caminho real, que fica fora da raiz do
workspace, e falha com `Could not find the Next.js package (next/package.json)`; em seguida, `ENOENT … build-manifest.json`.
Todas as rotas davam 500, não só `/confiabilidade`; o código do módulo não era a causa.

**Correção** (de ambiente, fora do git): removida só a junção (o diretório de destino, compartilhado, ficou intacto) e
copiado o `node_modules` da RC para dentro do worktree, com o mesmo `package-lock.json` (SHA-256 `1d27d560f5ac8a3a…`
idêntico), sem download e sem alterar instalações de outros worktrees. Next 16.4.2 confirmado.

**Correção de código no mesmo commit** (`1ea2c61`): o enquadramento da distribuidora rodava antes do `load` do MapLibre;
agora o mapa avisa `onPronto` e o enquadramento espera por ele.

**Critérios do P0**: HTTP 200, página renderiza, índice carrega, sem exceção no servidor nem erro fatal de console,
sobrevive a recarga completa: verificados no navegador e cobertos pelo e2e (teste "P0" de `confiabilidade.spec.ts`: status 200, recarga com estado na URL, sem erro de console e sem id duplicado).

## 2. Validação dos dados (auditoria A1–A6, `auditoria/AUDITORIA_PRODUTO.json`, `falhas: []`)

* A1 manifesto: 204 arquivos, 0 divergentes de SHA-256/tamanho.
* A2 chaves: 12.502 (DIST, CONJ, ano) únicas; nenhum conjunto em duas distribuidoras no mesmo ano.
* A3 contrato: anos 2022–2025, contagens inteiras, nada negativo, `demonstrativo: false`.
* A4 piloto: EPB (6600), ESE (6587) e Energisa AC (26) com transformadores, km MT e km BT iguais ao portal; consumidores
  com diferença pequena e explicada (+22, +10, −4).
* A5 reconciliação DIC/FIC × oficial (critério experimental 5%): DEC 94,1%, FEC 93,1%, ambos 92,3%; 82 combinações
  DIST × ano × indicador abaixo de 80%, listadas no CSV.
* A6 geometria: 3.147 conjuntos de 2025, 3.147 polígonos.
* Dados demonstrativos e reais nunca se misturam: o produto só tem estado oficial ou derivado; testes falham se aparecer
  `DEMONSTRATIVO_SINTETICO`.

## 3. Problemas encontrados e corrigidos nesta retomada

| # | Problema | Correção | Commit |
|---|---|---|---|
| 1 | HTTP 500 em todas as rotas (junção de `node_modules`) | cópia local com lockfile idêntico | ambiente + `1ea2c61` |
| 2 | Mapa não enquadrava a distribuidora da URL | `onPronto`/`mapaPronto` | `1ea2c61` |
| 3 | Rolagem da página presa no mapa | `cooperativeGestures` | `b93a8db` |
| 4 | Contagens N/D quando a camada fora lida e não tinha linhas (ex.: 3.213 conjunto-anos sem regulador de tensão `reg_eq`, 95 sem rede BT) | zero observado × N/D (`completar_zeros`) e produto republicado | `b93a8db` |
| 5 | Alimentador com BT e MT N/D exibia 0 consumidores | soma mantém N/D | `b93a8db` |
| 6 | Legenda dos gráficos sobre o nome do eixo | legenda abaixo do gráfico | `b93a8db` |
| 7 | ESLint (react-hooks): set-state em efeito, memoização manual | `useMemo` derivado, callbacks reestruturados | `b93a8db` |
| 8 | Ridge com R² fora da amostra −287.895 | `log1p` nas razões por 100 km + winsorização ajustada no treino | `a8ab0d0` |
| 9 | Diferença relativa calculada para métricas em % | `rel = null` para `pct` | `a8ab0d0` |
| 10 | Ficha somava componentes externas na "parcela do DEC" (115%) | apurado = internas (identidade 100% verificada); externas "não compõem"; `aneel.py` registra a identidade correta | `444d62d` |
| 11 | Evidências das hipóteses com ponto decimal e pontuação trocada | vírgula decimal; `fatores.json` regenerado (determinístico) | `444d62d` |
| 12 | Celular: 7 linhas de filtros antes do mapa | filtros em 2 colunas (300 → 246 px); mapa na primeira tela | `444d62d` |
| 13 | Celular: clicar na lista não mostrava a ficha (abaixo da lista) | rolagem até a ficha só em layout de uma coluna, respeitando movimento reduzido | `444d62d` |
| 14 | Texto "reconciliada em 11.237" ambíguo | "DEC e FEC reconciliados ao mesmo tempo" | `444d62d` |
| 15 | Nacional (~1 MB) baixado ao abrir a página | carregado só quando a escala "Conjuntos do Brasil" é usada | `8626c60` |

## 4. Inspeção visual

Desktop (1440 × 900) e celular (375 × 812), tema escuro e claro, com **EPB (6600)** e **Energisa AC (26)**, perfis
distintos (75 conjuntos no litoral/sertão × 15 conjuntos amazônicos com redes longas):
* Mapa: panorama Brasil, distribuidora, conjunto; DEC/FEC; ano; mês; % do limite (desabilitado no mês, com motivo);
  legenda por quintis e regulatória; hover (dica do conjunto); clique; zoom; volta ao Brasil; distribuidora vizinha clicável.
* Ficha (KPIs, acumulado, anual × limite, componentes, reconstrução, infraestrutura, alimentadores), comparador EPB × EAC
  com CSV, benchmarking (pares, perfil, ranking), Fatores, Metodologia, estados N/D (sem polígono, sem infraestrutura,
  supressão).
* Observação: no painel do navegador do app, quando oculto, o `requestAnimationFrame` é suspenso e o mapa não termina o
  `load`; não é defeito da página (no Chromium do Playwright o mapa fica pronto). Hover, clique e zoom foram por isso
  verificados no e2e.

## 5. Estatística

Ver MODELOS_ESTATISTICOS.md. Compatíveis com os dados: H2 (rede MT por alimentador ↑ ⇔ DEC ↑), H6a (densidade ↑ ⇔ DEC ↓),
H6b (ruralidade ↑ ⇔ DEC ↑). Inconclusivas: H1, H3, H4, H5, H5b. Não sustentada: H7 (precedência temporal). R² fora da
amostra por distribuidora: DEC 0,43 (contexto) → 0,53 (contexto + infraestrutura, floresta); FEC 0,31 → 0,42. Nenhuma
afirmação causal.

## 6. Testes novos

* Python: `confiabilidade/tests/test_confiabilidade.py`, 22 testes.
* Vitest: `web/tests/confiabilidade.test.ts`, 20 testes.
* Playwright: `web/e2e/confiabilidade.spec.ts`, 9 desktop + 1 `@mobile`: P0 com recarga, fluxos do mapa, ficha,
  comparador, benchmarking, fatores, metodologia, tema e celular.
* Detalhe em TESTES_E_DESEMPENHO.md. Nenhum teste existente foi desativado ou alterado.

## 7. Desempenho

Carregamento por distribuidora. No desktop todas as telas ficam prontas em até 2,5 s. No celular, com 4G emulado,
CPU 4× mais lenta e servidor sem compressão (pior caso), os tempos vão de 3,4 s a 13,3 s. O arquivo nacional deixou de
ser baixado ao abrir a página. A recomendação seguinte (quebras nacionais no `indice.json`) depende de uma republicação
controlada. Tabelas em TESTES_E_DESEMPENHO.md.

## 8. Evidências da execução final (12/11/2026, worktree `D:\NUCLEO_BDGD_2025\wt-confiabilidade`)

| Verificação | Comando | Resultado |
|---|---|---|
| Tipos | `npm run typecheck` | saída 0 |
| Lint | `npm run lint` | saída 0, sem avisos |
| Vitest (suíte inteira) | `npm run test` | 23 arquivos, **216/216** |
| Build de produção | `npm run build` | saída 0; `/confiabilidade` estática |
| Build de homologação | `NEXT_PUBLIC_MOTOR_V2=homologacao npm run build` | saída 0 |
| e2e (suíte inteira, build de homologação, como a CI `nucleo-bdgd-web.yml`) | `PW_BASE_URL=http://127.0.0.1:3232 npx playwright test` | **361/361**, saída 0, 28,6 min |
| e2e do módulo após o último teste (P0 com recarga) | `npx playwright test e2e/confiabilidade.spec.ts` | **10/10** |
| Python | `python -m unittest discover -s confiabilidade/tests -t .` | **22/22** |
| Auditoria do produto | `python -m confiabilidade.auditoria` | A1–A6, `falhas: []` |
| Estatística | `python -m confiabilidade.estatistica --reamostras 300` | saída 0, 356 s, reexecução idêntica |

Execuções que **não** valem como evidência e por quê:
* `npm run e2e` com o `serve` padrão: o servidor caiu com `EMFILE` (Windows) aos 128 testes; os 233 seguintes deram
  `ECONNREFUSED`.
* Suíte sobre o build de **produção**: 355 passaram e 6 falharam, todos do Motor V2 (`motor-v2.spec.ts`,
  `release-correcoes.spec.ts`). Eles exigem o build de homologação, porque o portão `motor-v2-gate.mjs` remove
  `/data/motor-v2` em produção; no build de homologação passam. Comportamento esperado, sem relação com o módulo.

**Isto não é CI verde.** Os resultados acima são execuções locais no Windows. A CI do GitHub não foi disparada nem
observada nesta retomada.

## 9. Pendências

1. Homologação humana do conteúdo regulatório (componentes, expurgos, limites) e da leitura das hipóteses.
2. Republicação controlada para pôr as quebras nacionais no `indice.json` (desempenho no celular).
3. Na próxima `aneel preparar`, a proveniência passa a registrar a identidade correta das componentes.
4. Merge e deploy só com autorização expressa. Nenhum dos dois foi feito.
