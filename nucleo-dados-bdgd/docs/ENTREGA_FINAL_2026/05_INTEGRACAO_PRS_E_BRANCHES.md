# 05 — Integração dos PRs, branches e patches

## Branches

| Branch | Cabeça | Papel |
|---|---|---|
| `integracao/produto-final-20261101` | ver `git log` (esta entrega) | **branch composta**: interface do Codex + #17–#20 + Motor V2 + patches A, B e C + integração web do Motor V2 |
| `feat/motor-v2-entrega-20261031` | `12f8808` | Motor V2: só `motor_v2/**` e o workflow sintético, sobre o #18 |
| `feat/motor-v2-granular-territorial` | `badfd24` | histórico de trabalho preservado (não alterado) |
| `codex/qa-frontend-homologacao-20261031` | `de225f5` | homologação funcional do Codex (não alterada; o worktree dele não foi tocado) |
| #17 `feat/motor-cenarios-publicacao-20261028` | `f0ad962` | não alterado |
| #18 `feat/metodologia-modelos-por-empresa-20261028` | `74190e2` | não alterado |
| #19 `fix/natureza-fisica-contagens-inteiras-20261029` | `09cd749` | não alterado |
| #20 `fix/alternancia-tema-claro-escuro-20261029` | `10be0e0` | não alterado |

## Como a branch composta foi montada

1. **Base:** a cabeça do Codex `de225f5`, que já reúne #17 e os cherry-picks de #18, #19 e #20, além das correções e testes de QA dele (lateral LAT-01/02, filtros FIL-01, inventário INV-01/02, tema).
2. **Merges de #18, #19 e #20** (`3e3f1b2`, `78b414b`, `3deb515`) para registrar a ancestralidade dos PRs. A árvore ficou **idêntica** antes e depois de cada merge: o conteúdo já estava presente.
3. **Patches sobre o contrato do #19**, aplicados com `git am --3way`:
   - **A** `f119950`: diagnóstico interno contínuo (`--internal-dir`), sem efeito público; gravar sob `web/`, `motor_cenarios/saida`, `output-publicavel` ou `output-historico` é recusado;
   - **C** `8a9156b`: o workflow da web roda só as duas suítes públicas de `motor_v2/tests`; as que exigem `D:` ficam fora do Actions;
   - **B** `19d3858`: erro físico pós-arredondamento (`mae_fisico`, `wape_fisico`, `vies_fisico`, `fisico_motivo`) ao lado do contínuo, só em contagens.
4. **Merge do Motor V2** (`54c3722`, depois `cdc4f13`) sem conflitos.
5. **Produto público do patch B** (`5a47161`):
   - regenerado pelo gerador oficial com scikit-learn 1.8.0;
   - os **valores já publicados foram preservados** e só os 184 objetos ganharam os campos novos (`motor_cenarios/preservar_publicado.py`);
   - status `simulacao_validada_retrospectivamente` → `simulacao_comparada_retrospectivamente`;
   - `cenarios.py --check` aprovou: 29 métricas, 16.045 contagens comparadas, 2 dentro da folga de 1 unidade;
   - os tipos TS dos campos novos foram acrescentados.
6. **Motor V2 no dashboard** (`db6aeff`, `d467b79`), com portão de homologação.
7. **CI:** o workflow da web passa a disparar na branch de integração. Ele roda uma build de produção que **falha se o Motor V2 aparecer** e uma build de homologação só para o E2E. O workflow sintético do Motor V2 também dispara na integração.

## Pilha anterior do dashboard (#4 a #16): dependências reais

A pilha aberta é `#4 → #6 → #8 → #9 → #10 → #11 → #12 → #13 → #14 → #16 → #17 → {#18, #19, #20}`. Conferi por ancestralidade git (`merge-base --is-ancestor`) que a cabeça de cada um desses PRs está contida na branch composta.

| Fora da integração | Situação | Decisão |
|---|---|---|
| **#15** `fix/ux-panorama-evolucao-comparador-clean-20261028` (`8cd7a44`, 13 commits) | Implementação **concorrente** da mesma correção que o #16: avisos dos KPIs do Panorama, limpeza da Evolução com o inventário numa rota técnica, Picker `inlineMenu` do Comparador. Os dois partem do #14 no mesmo dia; a pilha seguiu pelo #16. Mesclar o #15 conflita em 9 arquivos e duplicaria a implementação | **Não incorporado.** Recomendo fechar o #15 como superado pelo #16 (decisão humana) |
| `feat/nucleo-dados-bdgd-portal` (`ae9d149`) | Um commit de documentação (prompt R3) posterior à abertura do #4 | Sem efeito no produto |

## Sobreposições resolvidas (uma implementação por contrato)

| Tema | Implementação final |
|---|---|
| Contrato físico público (contagens inteiras, folga de 1 unidade, auditoria pública) | **#19**; o Motor V2 não tem cópia concorrente (`test_metric_contract.py` idêntico ao do #19, mais `test_metric_contract_motor_v2.py`) |
| Gerador público de cenários | `motor_cenarios/cenarios.py` do #19 + A + B; regenerado pelo processo oficial |
| Diagnóstico contínuo do Motor V2 | patch A (`--internal-dir`), fora das raízes públicas |
| Tema claro/escuro | versão do Codex = #20 (merge sem alteração de árvore) |
| Metodologia por empresa | #18 (motor V1 público) + nova ficha do Motor V2 (`MetodologiaMotorV2.tsx`) |
| Previsões | motor público V1 (`CenariosMotor`) inalterado nos números + seção do Motor V2 atrás do portão |
| Produtos derivados | regenerados pelo gerador e conferidos pelo `--check`; nenhum mesclado à mão |

## Integração do trabalho do Codex

Durante esta etapa, a branch do Codex ficou em `de225f5`. O worktree dele (`wt-qa-frontend`) tem alterações **não publicadas** e foi apenas lido, nunca escrito:
- `Matriz.tsx`;
- `e2e/matriz-fonte.spec.ts` e `e2e/panorama-comparador-fontes.spec.ts`;
- documentos de homologação.

A correção da Matriz que estava em andamento ali foi **portada sem alteração** para esta branch, com os dois testes de dados dele (commit `f0eaa45`). Ela bloqueia a exportação do CSV enquanto a fonte de uma coluna filtrada carrega ou falhou e mostra o alerta de fonte indisponível. Como o diff de `Matriz.tsx` é idêntico, o merge futuro do commit dele será limpo.

Quando ele publicar novos commits, o caminho é fazer o merge de `origin/codex/qa-frontend-homologacao-20261031` nesta branch e repetir as baterias de `06_TESTES_E_CI.md`. Os defeitos já corrigidos por ele (LAT-01 P1, LAT-02, FIL-01, INV-01 P0, INV-02 P1, QA-01) estão nesta integração com as regressões dele.

## Ordem de merge recomendada para a branch principal

#17 → #18 → #19 (com A, C e B) → #20 → Motor V2 → interface do Codex. Equivale a fazer o merge desta branch composta, que já resolveu tudo e passou nas baterias. **Nenhum merge na branch principal nem deploy de produção foi feito**: dependem de autorização.

## Release candidate (`rc/1.0-20261101`)

Partiu de `81263e0` (que continua intacta em `integracao/produto-final-20261101`) e acrescenta, sem reescrever histórico: o portão de plausibilidade, a integração dele ao produto, a correção do defeito P2 do React, os documentos do Codex que estavam só no worktree dele (`DEFEITOS.md`, `HOMOLOGACAO_FUNCIONAL_FINAL.md`, `INTEGRACAO_CI.md`, `gerar_matriz.py`) e os documentos 11 a 13.

**Codex.** A branch `codex/qa-frontend-homologacao-20261031` continua em `de225f5`. O worktree dele tem as mesmas alterações que já estavam integradas (o diff de `Matriz.tsx` é idêntico ao porte do commit `f0eaa45`) e nada novo desde 31/10. O worktree dele não foi alterado.
