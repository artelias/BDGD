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
