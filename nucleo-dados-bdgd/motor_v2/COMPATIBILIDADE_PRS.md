# Motor V2 — compatibilidade com os PRs #17, #18, #19 e #20 (2026-10-30)

Análise **somente leitura**, feita sobre as branches remotas buscadas em 2026-10-30. Nada foi mesclado nem alterado nas branches dos outros PRs.
Método: grafo de ancestrais (`git merge-base`), listas de arquivos por PR (`git diff --name-status`) e simulação de merge sem tocar a árvore de trabalho (`git merge-tree --write-tree`).

## 1. Estrutura da pilha

```
main ── … ── #16 fix/limpeza-paineis-seletores ── #17 feat/motor-cenarios-publicacao ──┬── #18 feat/metodologia-modelos-por-empresa ── Motor V2 (13 commits)
                                                                                       ├── #19 fix/natureza-fisica-contagens-inteiras   (1 commit)
                                                                                       └── #20 fix/alternancia-tema-claro-escuro        (4 commits)
```

- A branch do Motor V2 **descende** de #17 e #18 (e de #16). O PR do Motor V2 deve usar como base a branch do **#18** (`feat/metodologia-modelos-por-empresa-20261028`), seguindo a convenção de PRs empilhados já usada em #17–#20. O diff do PR fica restrito aos 13 commits próprios.
- #19 e #20 saem do #17 **em paralelo**: não contêm o #18 nem o Motor V2.

## 2. Matriz

| PR | Relação com o Motor V2 | Arquivos próprios | Sobreposição com o Motor V2 | Conflito de merge (simulado) | Veredicto |
|---|---|---|---|---|---|
| #17 Motor de Expansão: cenários e integridade do contrato nacional | **Ancestral** (base da pilha) | 50 vs #16 | nenhuma a resolver | não | Precisa entrar antes. Sem ele o Motor V2 não aplica. |
| #18 Metodologia por distribuidora, métrica e modelo | **Ancestral** (base direta do PR) | 3 vs #17 | nenhuma a resolver | não | Precisa entrar antes (ou ser a base do PR). |
| #19 Contagens inteiras e contrato de natureza física no dashboard | **Irmão divergente** (mesma origem #17) | 32 | 20 arquivos idênticos; **12 divergentes** | **sim: 8 arquivos** | **Incompatível sem decisão** (ver §3). |
| #20 Alternância estável tema claro/escuro | Irmão independente | 3 (`web/`) | nenhuma | não (nem com #19) | Compatível. Pode entrar em qualquer ordem. |

Conflitos entre os próprios #19 e #20: nenhum.

## 3. #19 × Motor V2 — o que colide

A branch do Motor V2 carrega **40 arquivos fora de `motor_v2/`** (web, `motor_cenarios`, `etl`, `motor_universal`), herdados dos commits anteriores `d6729d3` e `f2bb937`. O commit único do #19 (`c544e7b`, "independente do Motor V2") foi extraído da mesma linha de trabalho e **diverge** dela:

| Arquivo | Estado | Observação |
|---|---|---|
| `motor_v2/__init__.py`, `metric_contract.py`, `audit_public_products.py`, `tests/test_public_audit.py` | idênticos | Sem conflito. |
| `motor_v2/tests/test_metric_contract.py` | **conflito** | O Motor V2 é superconjunto (281 contra 215 linhas; o #19 não tem nada que falte aqui). Resolver com a versão do Motor V2. |
| `motor_cenarios/cenarios.py` | **conflito** | Implementações complementares do mesmo contrato. #19: `contagem_publica` (histórico publicado como inteiro, nunca `123.0`) e tolerância de ±1 em contagens inteiras na comparação `--check`. Motor V2: `fisico()` (erro físico no backtest) e diagnóstico interno `INTERNAL_RAW_PREDICTIONS.csv`. Exige **união manual** das duas. |
| `motor_cenarios/test_publico.py` | **conflito** | Mesma união manual (+11/−17). |
| `motor_cenarios/saida/*` (3 arquivos) e `web/public/data/previsoes/cenarios-motor.json` | **conflito** | Saídas **geradas**. Não mesclar à mão: resolver o código e regenerar com `cenarios.py … --check`. |
| `motor_cenarios/relatorio.py`, `web/src/lib/cenarios-motor.ts` | mescla automática | Diferenças pequenas (+6/−1, +1/−2). |
| `.github/workflows/nucleo-bdgd-web.yml`, `docs/homologacao-natureza-fisica/HOMOLOGACAO.md` | só no #19 | Entram sem conflito. |

### Risco de CI que a mescla cria (sem conflito textual)

O #19 acrescenta ao `nucleo-bdgd-web.yml` o passo `python -m unittest discover -s motor_v2/tests -v`, que roda **todas** as suítes de `motor_v2/tests`. No #19 isolado são 2 arquivos. Com o Motor V2 incorporado serão 19 arquivos de teste (18 já versionados e a nova suíte de erro retrospectivo), vários dos quais exigem `D:\`, DuckDB, pyogrio e a base local, e o ambiente desse workflow só instala `motor_universal/requirements-ml.txt`. **O passo passaria a falhar.** A correção é restringir o passo às duas suítes de produtos públicos (`-p test_metric_contract.py` e `-p test_public_audit.py`), como já faz o workflow sintético do Motor V2 por lista explícita. Essa alteração fica no #19 (ou num commit de reconciliação); **não foi feita aqui**.

## 4. Ordens de integração possíveis

| Ordem | Efeito | Avaliação |
|---|---|---|
| **A (recomendada).** #17 → #18 → #19 → #20 → Motor V2 | Motor V2 rebaseado depois do #19. Nos arquivos públicos adota-se a versão do #19, e o que só existe no Motor V2 (`fisico()`, diagnóstico interno) vai para um PR pequeno à parte ou é descartado por decisão sua. O diff do Motor V2 fica **só em `motor_v2/` + workflow sintético**, sem tocar produtos públicos. | Deixa o PR do Motor V2 com zero alteração em produtos públicos. Exige a decisão do §5. |
| B. #17 → #18 → Motor V2 → #19 | #19 passa a conflitar com o que já está na base (8 arquivos, §3) e o passo de CI acima quebra. | Mais retrabalho no PR menor. |
| C. Motor V2 mantido como está, antes de qualquer outro | Carrega as 40 alterações públicas junto. | Contraria "não tocar produtos públicos" e mantém o conflito. |

## 5. Decisões que dependem de você

1. **Divergência #19 × Motor V2 em `motor_cenarios/cenarios.py`.** Unir as duas (histórico inteiro do #19 + erro físico e diagnóstico interno do Motor V2) ou adotar só a do #19.
2. **Escopo do PR do Motor V2.** Manter a branch como está (inclui as 40 alterações públicas) ou, após o #19, reduzir o diff a `motor_v2/` + workflow (recomendado).
3. **Restrição do passo de CI do #19** às duas suítes públicas antes da incorporação do Motor V2.

## 6. Não avaliado

Não foram executados testes do dashboard (Node, Playwright) nem builds das branches #19 e #20. A compatibilidade acima é de **código e árvore de arquivos** (merge simulado), não de execução integrada. O PR #15 (`fix/ux-panorama-evolucao-comparador-clean`) fora da lista pedida **não** é ancestral do Motor V2 (13 commits próprios) e não foi analisado.
