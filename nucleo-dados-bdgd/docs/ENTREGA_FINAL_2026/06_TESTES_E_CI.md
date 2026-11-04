# 06 — Testes e integração contínua (árvore integrada)

Todos os resultados abaixo são da branch `integracao/produto-final-20261101`, exceto quando indicado. Nenhuma verificação foi removida ou enfraquecida para passar.

## Python e estatística

| Bateria | Onde | Resultado |
|---|---|---|
| Auditoria completa do Motor V2 (`python -m motor_v2.nacional.testes`) | local, com `D:` | **256 de 256 OK** (163 sintéticos, 93 com dados locais) |
| Suítes sintéticas (`python -m motor_v2.tests.suites`) | local | 163 de 163 OK |
| Emulação do Actions com `D:` bloqueado (`python -m motor_v2.tests.emular_ci`) | local | 163 OK, 1 skip herdado |
| `motor-v2-sintetico.yml` | GitHub Actions | **success** na integração ([run 41349501062](https://github.com/artelias/BDGD/actions/runs/41349501062)) e na entrega ([run 41349392320](https://github.com/artelias/BDGD/actions/runs/41349392320)) |
| Novos testes de cobertura e potência (`test_cobertura`, 11) | todos os acima | OK: estados, classes A–G, regra de liberação, convenção dos reguladores, ruptura kVA × unidades |
| Gerador público (`motor_cenarios`, 24 testes, incluindo o erro físico do patch B e o diagnóstico interno do patch A) | local (sklearn 1.8.0) e Actions | OK |
| `cenarios.py --check` (regeneração idêntica, tolerância de plataforma) | local e Actions | OK: 29 métricas, 16.045 contagens, 2 na folga de 1 unidade |
| Contrato físico (`test_metric_contract` 25) e auditoria pública (`test_public_audit` 3, `audit_public_products`) | local e Actions | OK: 0 contagens fracionárias ou negativas nos produtos públicos |
| Reconciliação hierárquica, idempotência e hashes | local (dentro dos 256) | OK: 0 violações, 15 pares por DIST, `VERIFICACOES_INTEGRIDADE` ok |
| `motor_universal --check-web` | Actions (Linux) | OK. No Windows difere só no último dígito de ponto flutuante (mesmo `experiment_id`); o resumo publicado é do runner Linux |

## Front-end

| Bateria | Onde | Resultado |
|---|---|---|
| ESLint | local e Actions | 0 problemas |
| TypeScript (`tsc --noEmit`) | local e Actions | 0 erros |
| Vitest | local | **176 de 176** (21 arquivos), incluindo `motor-v2.test.ts` (15: contrato do produto, regras de soma e CSV, portão em 4 ambientes) |
| Build de produção (portão fechado) | Actions | OK; o passo reprova se `out/data/motor-v2` existir ou se `PROJETADA_EXPERIMENTAL` aparecer |
| Build de homologação | local, Actions e preview da Vercel | OK; o log da Vercel registra "MOTOR V2: build de homologação" |
| Validadores ETL (smoke, pacote 2025-12-31, série histórica, homologação web, contrato nacional, cenários exploratórios, auditoria PR6, assets web) | local e Actions | OK (260 assets; 11.025 células; 11.400 linhas do contrato) |
| Playwright, bateria completa (321 testes: desktop, Android e iPhone estreito emulado) | local, build `d98fe1a` | **312 passaram, 9 falharam**. As 9 eram dois defeitos dos próprios testes, corrigidos abaixo; os testes do Motor V2 (10) e de layout em 7 larguras passaram |
| Playwright, rodada dos specs corrigidos ou novos na build final | local | inventário 12/12; homologação da Matriz ok; `matriz-fonte` ok; `panorama-comparador-fontes` ok; `motor-v2` 11/11; `sidebar` ok |
| Playwright no CI Linux | Actions | 1º run (`d98fe1a`) e 2º run (`35684cd`): falha. Com o reporter `github`, o 2º run mostra uma **única** falha, `matriz-fonte.spec.ts:14` (o seletor do alerta, corrigido em `56f0d1a`); todos os outros testes passaram. **Run final em `6c72c57`: success**, todos os passos, incluindo o E2E completo ([run 41355080905](https://github.com/artelias/BDGD/actions/runs/41355080905)) |

### Defeitos encontrados nos testes e corrigidos (sem enfraquecer as asserções)

| Teste | Causa | Correção |
|---|---|---|
| `inventario-controles.spec.ts` (Codex, `de225f5`), 9 rotas | laço sobre `locator('details:not([open]) > summary').all()`: o localizador preguiçoso deixa de apontar para o `<details>` assim que ele abre | marcar o alvo antes do clique; a mesma exigência (cada resumo abre o próprio `<details>`) |
| `homologacao-funcional.spec.ts`, ordenação da Matriz | linhas lidas logo após o clique, antes da nova ordem (estado gravado na URL) | esperar `aria-sort` e a ordem com `expect.poll` |
| `matriz-fonte.spec.ts` (Codex, não publicado) | `getByRole("alert")` também encontra o anunciador de rotas do Next | filtrar pelo texto do alerta |

### Defeito de interface anterior a esta integração (P2, documentado)

O layout raiz envolve o `AppShell` num `<Suspense>`. Com o agendamento de revelação do React 19 (`$RC` → `$RV`), a hidratação pode deixar uma **cópia não hidratada da página** dentro de `<div hidden id="S:0">`, no fim do `<body>`.
- **Impacto:** a cópia é invisível e ignorada por leitores de tela, mas duplica ids (`#conteudo`, `data-testid`) no DOM e quebra seletores estritos que contam elementos ocultos.
- **Reprodução:** o mesmo ocorre na build da cabeça do Codex `de225f5`, na página Previsões, segundos depois da carga.
- **Correção recomendada (não aplicada nesta entrega, por exigir uma regressão completa do shell):** tirar o `useSearchParams` do caminho que suspende no layout raiz, ou isolar o Suspense nos componentes que leem a URL.
- **Nesta entrega:** os testes do Motor V2 consideram só elementos visíveis.

## Testes indisponíveis ou limitados pelo ambiente

- Os testes que leem a base em `D:` (93) rodam só nesta máquina; não são disfarçados de portáveis.
- Safari em aparelho físico não foi testado; o projeto `iphone-estreito` emula viewport, toque e agente no Chromium.
- No Windows, o `serve` usado pelo Playwright caiu com `EMFILE` depois de 129 testes na primeira rodada local; todas as falhas seguintes eram de conexão. A rodada foi repetida com `scripts/servir-estatico.mjs`.

## Release candidate 1.0 (`rc/1.0-20261101`)

| Bateria | Resultado |
|---|---|
| Auditoria local completa do Motor V2 | **275 de 275 OK** (179 sintéticos, 93 locais, 3 públicos) |
| Emulação do Actions com `D:` bloqueado | 179 OK, 1 skip herdado |
| `test_plausibilidade` (16 sintéticos: crescimento sustentado, primeira entrada, renumeração, estoque zero, base pequena, queda sustentada, arredondamento, erro de cálculo verdadeiro, unidades separadas) | OK |
| ESLint / TypeScript | 0 / 0 |
| Vitest | **182 de 182** (contrato do Motor V2 com cenário bloqueado ou corrigido, outliers auditados, totais sobre o mesmo conjunto) |
| `e2e/hidratacao.spec.ts` (15: sete páginas em desktop e mobile, parâmetros da URL, tema, lateral, console) | 15 de 15 |
| GitHub Actions, `motor-v2-sintetico.yml` | success ([run 41445552399](https://github.com/artelias/BDGD/actions/runs/41445552399)) em `ae3ef26` |
| GitHub Actions, web (lint, tipos, testes, contratos, build de produção e de homologação, E2E completo) | **success** ([run 41445552427](https://github.com/artelias/BDGD/actions/runs/41445552427)) em `ae3ef26` |

O resultado do Playwright local completo e o CI do commit final estão em `13_CHECKLIST_RELEASE_CANDIDATE.md`.

### Defeito P2 do React (ids duplicados): corrigido

- **Causa.** O `<Suspense>` na raiz do layout envolvia o `AppShell`. Esse limite não é necessário (o shell só usa `usePathname`; as páginas que leem a URL já têm o próprio `Suspense`). No prerender estático ele virava um segmento adiado: `<template id="B:0">` vazio mais `<div hidden id="S:0">` com a página inteira, revelado por script. Quando a hidratação do React 19 assumia o limite antes do reveal agendado, a página era renderizada de novo no cliente e a cópia do servidor ficava retida no `<body>`, com ids e landmarks duplicados.
- **Correção.** O `Suspense` da raiz saiu de `app/layout.tsx`.
- **Prova.** O HTML de `/previsoes/` e `/evolucao/` deixou de ter `S:0`. `/matriz/`, `/explorar/` e `/comparar/` mantêm o `S:0` e o `B:0` no HTML estático, por causa do `Suspense` da própria página com `useSearchParams`, mas o DOM hidratado fica sem `S:0`, sem ids duplicados e com um único `#conteudo` (medido nas sete páginas, 6 s depois da carga). A regressão confere o DOM, não os seletores. Os seletores do `motor-v2.spec.ts` continuam filtrando por elementos visí& veis, o que agora é só uma salvaguarda.

## Correções finais de release (03/11/2026)

Ver `14_CORRECOES_FINAIS_RELEASE.md`. Nenhum teste foi removido ou enfraquecido. O `natureza-fisica.spec.ts` lia a coluna do Moderado do CSV pela posição; com as colunas novas (`observado`, completude), a coluna passou a ser localizada pelo cabeçalho, e a exigência de contagem inteira continua valendo para toda coluna numérica.

| Bateria | Onde | Resultado |
|---|---|---|
| Motor V2, auditoria local completa (`python -m motor_v2.nacional.testes`) | local, com `D:` | **281 de 281** (179 sintéticos, 93 locais, 9 públicos) |
| Emulação do CI com `D:` bloqueado | local | 179 OK, 1 skip herdado |
| Gerador público (`motor_cenarios`, 25 testes, incluindo o novo `test_extremo_nunca_sem_moderado_e_ausencia_com_motivo`) | local (scikit-learn 1.8.0) | OK |
| `cenarios.py --check` depois da regra "extremo só com Moderado" | local | **OK**: 29 métricas, 16.010 contagens, 2 na folga de 1 unidade |
| Produto web do Motor V2 (`test_produto_web_v2`, novo, 6 testes) | local | OK: inteiros JSON, completude 2.484/219/4, agregado nacional dos extremos |
| ESLint, TypeScript | local | 0, 0 |
| Vitest | local | **196 de 196** (22 arquivos; novo `release-correcoes.test.ts` com 14) |
| Playwright completo (351 testes) | local, build com as correções | **347 de 351**: as 4 falhas eram o defeito do teste descrito acima |
| Playwright, specs afetados, na build final (`natureza-fisica`, `release-correcoes`, `motor-v2`, `cenarios-motor`, `mapa-tema`) | local | **33 de 33** antes do último ajuste de texto; rerodados depois dele (ver relatório) |
| CI Linux (web, com E2E completo, e sintético) no commit final | GitHub Actions | ver o relatório final |

Novos testes de regressão:
- `e2e/mapa-tema.spec.ts`: 10 alternâncias com leitura de pixels do canvas, desktop e mobile;
- `e2e/release-correcoes.spec.ts`: completude em cards, gráfico, tabela e CSV; Evolução sem decimais; contagens sem notação compacta; lateral; agregado nacional de geradores;
- `web/tests/release-correcoes.test.ts`;
- `motor_v2/tests/test_produto_web_v2.py`;
- teste novo em `motor_cenarios/test_publico.py`.

## Integração do PR #21 (04/11/2026)

O PR #21 retira o painel "Explorar cenários 2026–2030". A experiência pública de cenários passa a ser só o painel principal, "Cenários de expansão por métrica física". Os dados exploratórios continuam publicados e validados no CI.

Para não perder ressalvas do painel retirado:
- a Coopera (DIST 5370) continua selecionável e bloqueada em consumidores;
- as observações cadastrais da distribuidora e do ativo selecionados aparecem no painel principal.

Oito specs que dependiam da interface retirada foram **adaptados, não desativados**:

| Spec | O que verificava | Como fica |
|---|---|---|
| `auditoria-pr6` | filtros, métodos e anos; CSV de zeros; rótulos do gráfico; falha de carga; visual e teclado no celular | os mesmos aspectos no painel principal, sobre `cenarios-motor.json`, mais a ausência do painel retirado. Os zeros técnicos do produto exploratório seguem no Vitest |
| `motor-universal` | título do painel exploratório antes da carga sob demanda | título do painel principal, mais a ausência do retirado |
| `natureza-fisica` | card, tabela e CSV do painel exploratório | o produto exploratório continua publicado com contagens inteiras; a exibição por natureza física é auditada no painel principal pelos 4 casos do mesmo arquivo |
| `previsoes-integracao` | ordem resultados × ressalvas; celular | painel principal antes da ressalva longa (posição medida); celular sem rolagem |
| `publicacoes-previsoes` | mesmo valor no gráfico, na tabela e no CSV | idem no painel principal (DIST 26, alimentadores) |
| `qa-final` | filtros e exportação no iPhone; alvo de carga da página | idem no painel principal |
| `reconciliacao` | Coopera bloqueada com ressalva | idem no painel principal (incluindo "Observações e ressalvas dos dados", 225) |
| `riscos-cenarios` | avisos da tendência exploratória (truncamento no zero, quatro zeros técnicos) | nenhuma trajetória publicada chega a zero; DIST 39 (reatores, zeros técnicos) não é oferecida; a lógica dos riscos segue no Vitest (`risco-cenarios.test.ts`) |

Também foi atualizada a asserção da Coopera em `cenarios-motor.spec.ts`: ela era "ausente da lista" e passa a ser "presente, bloqueada, sem tabela e sem CSV".

Resultados no SHA da integração: ver `HOMOLOGACAO/ENGENHARIA/02_EVIDENCIAS_TESTES.md`.
