# 08 — Auditoria da implementação do Codex (`14f4e61`)

**Objeto:**
- branch `codex/recuperacao-cenarios-20261105` @ `14f4e6183fe76f32e8606ace4d5d69901b29b105`;
- pacote `motor_cenarios/recuperacao/` e testes `motor_cenarios/test_recuperacao.py`;
- artefatos em `motor_cenarios/experimental/recuperacao/`.

**Protocolo:** `recuperacao-1` (`d478e16`), sem alteração.

**Ambiente de referência:** Windows 10 19045, Python 3.14.3, NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.8.0 (`D:/NUCLEO_BDGD_2025/.venv-motor`), sem nenhuma instalação.

**Ambiente do Codex:** Linux 6.18.57 (glibc 2.41), Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, scikit-learn 1.8.0.

## 1. Resultado

| Item pedido | Verificação | Resultado |
|---|---|---|
| 60 cenários recuperados (piloto, 98 DIST) | piloto reexecutado no Windows; `cenarios.csv`, `cobertura.*` e `gabarito.json` comparados byte a byte com os do Linux; mesmo subconjunto na execução nacional | **Corretos.** Idênticos byte a byte; 0 divergências contra `02`; os 60 são causa I (seleção agregada) |
| Preservação do Moderado | `validar_nacional.py` V1: `moderado`, `hist` e `erro_moderado` iguais ao JSON da RC nas 2.202 séries, nos 3 modos | **Confirmada** (0 diferenças) |
| Seleção por distribuidora | precedência P1 → P2 (O, e X no modo otimizados), ordenação `(WAPE_PRODUTO, complexidade, id)` idêntica à da referência; gabarito nacional | **Confirmada** (0 divergências de modelo, valor 2030 ou classe nas 2.202 séries) |
| Regras Q1–Q9 | `qualidade.checar` valida a estrutura e delega à função única `recuperar.checar`; comparação com as 2.869 linhas sobrepostas de `06`; verificação independente nos valores publicados (V2) | **Corretas.** 0 divergências; 1 caso limítrofe do próprio protocolo (seção 3.2) |
| Testes e hashes | 59 testes (34 novos); hashes de entradas, código e saídas | **Passam** no Windows só com `PYTHONUTF8=1` (defeito D-1); os hashes conferem |
| Vazamento temporal | origens 2023 e 2024 para o erro; projeção da origem 2025; percentis e B-HIST com transições ≤ 2025; configurações X escolhidas na etapa S | **Nenhum vazamento novo.** 2025 continua consultado (exploratório), como já registrado |
| Preservação dos arquivos públicos | `git diff --name-status 6ec3b6d 14f4e61`: 45 arquivos adicionados, 0 modificados ou removidos; `cenarios.py --check` no Windows: 29 métricas OK | **Preservados** |

O piloto original (só originais) passou no gabarito, e no Windows também passa. O piloto com otimizados e B-HIST falhou no Linux por um único motivo, o `knn_analogos_otim` (seção 2). No Windows, os pilotos `otimizados` e `condicionais` passam no gabarito (saída 0). As duas conclusões ficam separadas: a aprovação do piloto original não se estende aos otimizados.

## 2. Divergências do Codex explicadas

| Divergência | Causa demonstrada | Evidência |
|---|---|---|
| WAPE do `random_forest_painel` de bancos de capacitores: 0.06005597829053297 contra 0.0600573022094799 | `math.log` da libm: a UCRT (Windows) e o glibc (Linux) diferem em 1 ULP em 24 de 35.522 chamadas do gerador, e o RF transforma isso em outra divisão de árvore | No Windows, com `math.log` de arredondamento correto (o comportamento do glibc), o WAPE fica **igual bit a bit ao do Linux**. Os outros 8 modelos não mudam (`03_causa_wape/CAUSA_WAPE.json`) |
| 113 campos no piloto com otimizados e B-HIST | o `knn_analogos_otim` (consumidores) foi bloqueado no Linux pelo portão S/F. As 36 posições de Agressivo em que o gabarito o escolheu passaram a outro candidato: 36 de modelo, 36 de valor 2030, 36 de estado, 3 de classe e 2 de Q7 | as 36 trocas de modelo do Linux envolvem todas `knn_analogos_otim`; no Windows a divergência é 0 |
| S e F do `knn_analogos_otim` no Linux | **empates exatos de distância**: k=15 e uma única variável (`int_ln_alimentadores`), com 32 de 88 e 86 de 179 linhas de treino duplicadas e empate na fronteira da vizinhança em 25 de 86 e 45 de 88 consultas. O vizinho incluído depende do desempate da busca | com os mesmos dados, mudar só o algoritmo ou o `leaf_size` move S entre 0,0362021 e 0,0362068 e F entre 0,0231052 e 0,0233629. ±1 ULP muda o WAPE em 20 de 20 réplicas e reprova o portão em 19 de 20. A troca da libm não altera o KNN (`03_causa_wape/`) |

**Conclusão.** Nenhuma das divergências vem de defeito do código do Codex, de dados diferentes, de versão do código, de parâmetros, de estado aleatório ou da agregação do WAPE:
- o hash das entradas e o blob de `cenarios.py` são iguais;
- `random_state=42` e `n_jobs=1`;
- a mesma função de WAPE.

As duas causas são numéricas e dependem da plataforma:
- **RF:** é a libm; isso está demonstrado.
- **KNN:** é o desempate entre vizinhos à mesma distância. Está demonstrado que o resultado depende desse desempate. A implementação específica que difere no Linux foi inferida, não observada.

O Codex agiu corretamente ao parar no portão e ao não relaxar limites.

## 3. Defeitos e observações da implementação

| # | Severidade | Achado | Correção pedida ao Codex |
|---|---|---|---|
| D-1 | média | `read_text()` sem `encoding='utf-8'` em `test_recuperacao.py` (linhas 124, 125 e 132) e em `fontes.py` (linha 23). No Windows (cp1252), a classe `ContratoReal` dá erro (7 testes) | passar `encoding='utf-8'` em todas as leituras; rodar os testes no Windows sem `PYTHONUTF8` |
| D-2 | média | `DETERMINISMO.json` repetiu a execução **com cache**, o que só prova o determinismo da seleção, não o da reconstrução dos modelos | teste de repetição sem cache. Feito nesta auditoria: duas execuções nacionais do zero no Windows (seção 4) |
| D-3 | média | a cobertura "antes" é a do produto publicado (755 completas), que inclui 570 séries com extremos reprovados. Lido sozinho, "755 → 711 (−44)" parece perda | relatar também a base defensável: 185 completas antes e 711 depois |
| D-4 | baixa | o portão de reprodução de X usa 5e-7, e o protocolo diz "até 1e-6". O 5e-7 foi herdado do `recuperar.py` de referência, que é desvio meu. Como o registro tem 6 decimais, 5e-7 equivale a reproduzir o valor registrado | registrar no relatório; não muda nenhum resultado no Windows |
| D-5 | baixa | `limitar_memoria` só atua em POSIX. No Windows não há limite, e `pico_rss_mib` fica nulo | registrar o pico pelo `psutil`, se já estiver disponível, ou documentar a limitação; não instalar nada |
| O-1 | observação do protocolo | Q7 é aplicada à trajetória contínua. Em reguladores, DIST 6587, o Agressivo recuperado (`ridge_painel_ext`) difere em 0,055 p.p./ano na contínua, mas em 0,049 p.p./ano nos inteiros publicados (411 contra 410 em 2030, e 340 = 340 em 2027) | **não aplicar agora:** o critério não muda depois do resultado. Proposto para a `recuperacao-2` (Q7 também nos valores publicados, como a Q8 já faz) |

## 4. Reexecução no ambiente de referência (Windows)

| Execução | Saída | Gabarito | Completas | Parciais | Sem previsão |
|---|---|---|---|---|---|
| piloto, originais | 0 | 0 divergências (98 séries) | 60 | 28 | 10 |
| piloto, otimizados | 0 | 0 | 80 | 8 | 10 |
| piloto, condicionais | 0 | 0 | 85 | 3 | 10 |
| **nacional, originais** | 0 | 0 divergências (2.202 séries; 2.869 linhas de `06`) | **711** | 1.250 | 241 |
| nacional, otimizados | 0 | 0 | 1.039 | 922 | 241 |
| nacional, condicionais | 0 | 0 | 1.239 (1.039 independentes, 199 mistas, 1 condicional) | 722 | 241 |

**Validação independente (`validar_nacional.py`, V1–V8), nos três modos:**
- 0 falhas de Moderado ou histórico, contrato físico, categorias, competitividade, CSV × JSON, marca kVA e classe;
- uma única observação em V2 (O-1).

**Determinismo:** ver `05_validacao_nacional/DETERMINISMO_SEM_CACHE.json`.

## 5. Parecer sobre o pacote

- **O que está aprovado:** a implementação do Codex para o modo `originais`, no ambiente de referência, como **ferramenta experimental de recuperação**. Ela reproduz o gabarito científico linha a linha.
- **O que não está aprovado:**
  - **não é aprovada para integração** antes de corrigir D-1 a D-3;
  - **não é homologação científica**, porque a competência 2025 já foi consultada;
  - **não autoriza** a publicação nacional sem aceite científico e sem CI completo.
- **Otimizados:**
  - reproduzem no Windows;
  - o `knn_analogos_otim` tem resultado definido por desempate e fica **bloqueado** em qualquer ambiente;
  - os demais seguem **experimentais**, dependendo da decisão D4 e do critério de portabilidade (`07_PROPOSTA_RECUPERACAO_2.md`).
