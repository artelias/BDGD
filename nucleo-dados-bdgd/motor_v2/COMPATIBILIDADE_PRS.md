# Motor V2 — compatibilidade com os PRs #17, #18, #19 e #20 (2026-10-31)

Análise sobre as cabeças **atuais** dos PRs, buscadas em 2026-10-31 (`refs/pull/N/head`):

| PR | Branch | Cabeça |
|---|---|---|
| #17 | `feat/motor-cenarios-publicacao-20261028` | `f0ad962` |
| #18 | `feat/metodologia-modelos-por-empresa-20261028` | `74190e2` |
| #19 | `fix/natureza-fisica-contagens-inteiras-20261029` | `09cd749` (avançou desde 30/10: `b60f3ae` e `09cd749`) |
| #20 | `fix/alternancia-tema-claro-escuro-20261029` | `10be0e0` (avançou desde 30/10: `33d84b7`, `5cf4e1d` e `10be0e0`) |

Nenhuma dessas branches foi alterada.

**Método:**
- simulação de merge sem tocar árvore alguma (`git merge-tree --write-tree`);
- validação executável da árvore combinada (entrega + #19), num worktree temporário destacado e descartado ao fim.

## 1. Branch de entrega do Motor V2

O PR usa a branch **`feat/motor-v2-entrega-20261031`**, criada a partir do #18 (`74190e2`). Ela contém **somente** `nucleo-dados-bdgd/motor_v2/**` e `.github/workflows/motor-v2-sintetico.yml`.

A branch de trabalho `feat/motor-v2-granular-territorial` fica preservada, com todo o histórico (`badfd24`). Ela carregava, de commits anteriores, 25 arquivos fora de `motor_v2/`:
- **16 são hoje idênticos ao #19.** Ficam com o #19.
- **9 divergem do #19:**
  - 7 dos oito conflitos originais: `motor_cenarios/cenarios.py`, `motor_cenarios/test_publico.py`, quatro arquivos de `motor_cenarios/saida/` e `web/public/data/previsoes/cenarios-motor.json` (o oitavo conflito era `motor_v2/tests/test_metric_contract.py`);
  - `motor_cenarios/saida/BACKTEST_MODELOS_POR_HORIZONTE.csv`, que só a branch do Motor V2 alterava;
  - `web/src/lib/cenarios-motor.ts`, que mesclava sem conflito.

Nenhum deles entra na entrega; ver §3.

Dentro de `motor_v2/`:
- **`metric_contract.py` e `__init__.py`** são usados pelo código do Motor V2 e são **idênticos byte a byte** ao #19: o merge é limpo em qualquer ordem.
- **`test_metric_contract.py`** agora é idêntico ao do #19. Os 7 testes que só o Motor V2 tinha foram para `test_metric_contract_motor_v2.py`, sem perda: 25 + 7 = 32.
- **`audit_public_products.py` e `test_public_audit.py`** só auditam produtos públicos reais e pertencem ao #19. Saem da entrega e chegam com o #19, já classificados como `PUBLICAS` em `tests/suites.py`.

## 2. Matriz

| | Relação | Conflitos simulados | Verificação executável | Veredicto |
|---|---|---|---|---|
| **Motor V2 × #17** | ancestral | 0 | — | Compatível; #17 entra antes. |
| **Motor V2 × #18** | ancestral (base do PR) | 0 | auditoria completa sobre a base #18: 245/245 | Compatível; #18 entra antes ou é a base. |
| **Motor V2 × #19** | irmão | **0** (eram 8 na branch de trabalho) | árvore combinada: runner sintético 152/152 com `D:\` bloqueado; `test_public_audit` 3/3; testes do `motor_cenarios` OK | **Compatível no texto; incompatível no CI do #19 até aplicar o patch C** (§4). |
| **Motor V2 × #20** | irmão, só `web/` | 0 | — | Compatível em qualquer ordem. |
| #19 × #20 | irmãos | 0 | — | Compatíveis. |
| (Motor V2 + #19) × #20 | — | 0 | — | Compatíveis. |

Os testes do dashboard (Node, Playwright) não foram executados aqui; são responsabilidade do Codex.

## 3. Resolução dos oito conflitos com o #19

**Princípio: uma única implementação do contrato físico público, a do #19.** O Motor V2 não leva a sua cópia antiga. O que ele tinha de complementar vira patch **sobre** o #19, testado.

| # | Arquivo | Natureza | Resolução |
|---|---|---|---|
| 1 | `motor_v2/tests/test_metric_contract.py` | teste do contrato | **Eliminado:** arquivo idêntico ao #19; extras em `test_metric_contract_motor_v2.py`. |
| 2 | `motor_cenarios/cenarios.py` | gerador do produto público | **#19 prevalece:** histórico e `base_2025` inteiros, `contagem_publica`, folga de 1 unidade limitada (`FOLGA_MAXIMA`), `comparar_produtos`. Do Motor V2 entram só os complementos, como patches A e B. |
| 3 | `motor_cenarios/test_publico.py` | teste público | **#19 prevalece;** o teste do erro físico vai junto com o patch B. |
| 4–7 | `motor_cenarios/saida/{CENARIOS_…, MANIFESTO.json, MATRIZ_MODELO_POR_METRICA.csv, TABELA_FINAL_METRICA_DISTRIBUIDORA.csv}` | **produtos derivados** | **Nunca mesclar à mão:** ficam os do #19. Se o patch B for aceito, regenerar com `cenarios.py` (scikit-learn 1.8.0) e aprovar `--check`. |
| 8 | `web/public/data/previsoes/cenarios-motor.json` | **produto derivado** (dashboard) | Idem; regenerar só se o patch B for aceito. |

**Complementares × incompatíveis**

| Alteração | Classe | Evidência |
|---|---|---|
| #19: histórico inteiro, `base_2025` inteira, folga limitada, `test_tolerancia` | adotada (implementação única) | — |
| **Patch A:** `--internal-dir`, valor contínuo bruto em diagnóstico interno | **complementar, sem efeito público** | 7 arquivos públicos regenerados idênticos com e sem a opção; `--check` OK com scikit-learn 1.8.0 (29 métricas; 2 de 16.045 contagens na folga de 1); recusa gravar sob `web/`, `motor_cenarios/saida`, `output-*` |
| **Patch B:** `fisico()`, erro pós-arredondamento (`mae_fisico`, `wape_fisico`, `vies_fisico`, `fisico_motivo`) ao lado do contínuo | **complementar e aditivo, com efeito público** | sem os campos novos, o JSON regenerado é idêntico; CSVs idênticos; 168 modelos de contagem ganham o erro físico e 16 o motivo de previsão negativa; contínuos não ganham o campo; o teste novo passa com o produto regenerado e reprova com o atual (por desenho) |
| Versão antiga do Motor V2 de `main`/`verificar`: histórico não convertido em inteiro, `base_2025` fora do gate e comparação `--check` sem a folga limitada de contagens | **incompatível; descartada** | substituída pela do #19 |
| Texto público de `tres_cenarios`: #19 "Três cenários **validados** retrospectivamente" × Motor V2 "comparados em backtest" | **incompatível (semântica)** | decisão humana e do Codex (UI). O Motor V2 não declara validação. |
| Status público `simulacao_validada_retrospectivamente` no CSV do #19 | mesma questão semântica | decisão humana |

Patches em `integracao/pr19/`, gerados com `git format-patch` e conferidos com `git am --3way` sobre o #19 puro, sem conflito:
- `0001` = A;
- `0002` = B, que também exige tipar os campos em `web/src/lib/cenarios-motor.ts`, arquivo do Codex;
- `0003` = C (CI, §4).

## 4. CI: separação de suítes

**Problema.** O #19 acrescenta a `nucleo-bdgd-web.yml` o passo `python -m unittest discover -s motor_v2/tests -v`. Hoje, no #19 isolado, são 2 arquivos. Com o Motor V2 na árvore, o passo descobre também as suítes locais.

**Medido na árvore combinada** com `D:\` bloqueado (`emular_ci`):
- passo atual: 248 testes, **5 erros**;
- passo proposto (patch C, só `-p test_metric_contract.py` e `-p test_public_audit.py`): 25 + 3 testes, todos OK.

**Separação implementada na entrega** (`motor_v2/tests/suites.py`, fonte única):

| Grupo | Suítes | Onde roda |
|---|---|---|
| `SINTETICAS` | 12 (152 testes) | GitHub Actions, `motor-v2-sintetico.yml` → `python -m motor_v2.tests.suites` |
| `LOCAIS` | 8 (93 testes) | auditoria completa local, `python -m motor_v2.nacional.testes` |
| `PUBLICAS` | `test_public_audit` (PR #19) | workflow da web do #19 |
| Dashboard | Node/Playwright | Codex (fora do Motor V2) |

**Salvaguardas** (nenhum teste foi enfraquecido):
- `test_suites` reprova arquivo de teste sem grupo, nome em dois grupos, suíte listada e ausente, ou workflow com descoberta sem filtro.
- O runner reprova suíte que não carregue nenhum teste.
- `emular_ci` aborta se o bloqueio de `D:\` não estiver de fato ativo.

## 5. Ordem de integração recomendada

1. **#17 → #18** (ancestrais).
2. **#19 com o patch C** (CI), e com A e B se aprovados. Se B for aceito: regenerar os produtos derivados com scikit-learn 1.8.0, aprovar `--check` e tipar o TS (Codex).
3. **#20** (qualquer posição).
4. **Motor V2** (`feat/motor-v2-entrega-20261031`). Merge limpo antes ou depois de #19 e #20.

Se o Motor V2 entrar antes do #19 sem o patch C, o workflow da web do #19 passa a falhar (§4).
