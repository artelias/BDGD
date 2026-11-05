# RC 1.0.1 — correção dos extremos publicados incoerentes

**Estado:** recomendação e especificação para o Codex. Nada aqui foi aplicado.
- A RC 1.0 (`dba5fdf`), o PR #22 e a produção (`74190e2`) não foram alterados.
- Não houve merge nem deploy.

## 1. Comparação das soluções

Todos os números abaixo vêm da execução nacional no Windows de referência (`win-nacional-originais`), do gabarito científico `recuperacao-1` e da verificação independente dos valores publicados.

| Critério | A. Bloquear os extremos incoerentes | B. Recuperar com originais elegíveis por DIST |
|---|---|---|
| Correção semântica (C ≤ M ≤ A nos 5 anos, diferença material) | **total**: retira os 1.084 reprovados; os 1.411 restantes são aprovados | **total**: 2.296 extremos, todos COERENTE pela Q1–Q9 (1 caso limítrofe, O-1) |
| Séries completas (todas / sem kVA) | **185** / 170 | **711** / 647 |
| Extremos publicados | 1.411 (nenhum número novo) | 2.296 (1.411 mantidos e **885 trajetórias nunca publicadas**) |
| Desempenho: WAPE do modelo do extremo ÷ WAPE do Moderado (mediana) | 1,136 | 1,081 (os 885 novos: 1,049) |
| WAPE local na DIST (mediana) | 0,0287 | 0,0275 (os novos: 0,0252) |
| Rastreabilidade | o modelo do extremo continua sendo um por métrica; o motivo vai em `motivos` por série | o modelo passa a variar por série; exige o campo `extremos` por série e a legenda na tela |
| Contrato e interface | `cenarios-motor-1` mantido; a tela já trata PARCIAL (`completude.ts`); só muda o texto da Metodologia | `cenarios-motor-2`, interface nova (modelo por série), Metodologia nova |
| Mudança de metodologia | nenhuma: aplica o princípio do próprio gerador ("sem modelo que satisfaça a regra, o cenário fica INDISPONÍVEL") | muda a regra de seleção (decisão D2) |
| Aceite científico necessário | não: só retira números | **sim**: publica 885 trajetórias novas; o parecer não está assinado |
| Robustez entre plataformas: decisões a menos de 1e-3 do limiar | 270 de 2.495 (92 são empates exatos, iguais em qualquer plataforma) | 70 de 885 escolhas novas; 48 contagens dependem de um bruto a menos de 1e-8 de x,5 (tendência OLS em geradores) |
| Robustez empírica: 7 cenários realistas de libm (`00`, seção 3.3) | **0 decisões mudaram** | 1 escolha em 885 mudou, só com ruído 14× o observado; 0 valores fora da tolerância do `--check` |
| Risco de regressão | **baixo** | médio |

**Recomendação:**
- **RC 1.0.1: opção A.** É a única que corrige a semântica sem publicar números novos, sem mudar a metodologia e sem depender do aceite científico. Isso respeita a prioridade definida: corrigir os cenários públicos primeiro e só depois buscar cobertura.
- **Opção B: no incremento seguinte** (RC 1.0.2 ou 1.1), num PR separado. Ela já está validada nacionalmente no ambiente de referência e é superior em cobertura e desempenho, mas depende de:
  - decisão D2 e aceite científico do parecer;
  - correção dos defeitos D-1 a D-3 do pacote;
  - verificação R1 em Linux (`07_PROPOSTA_RECUPERACAO_2.md`);
  - regressão completa.

## 2. Especificação da opção A para o Codex

**Ramo e PR:**
- branch nova `rc/1.0.1-20261106`, criada a partir de `rc/1.0-20261101@dba5fdf`;
- PR **em rascunho** com a mesma base do PR #22 (`feat/motor-cenarios-publicacao-20261028`);
- o PR #22 não é tocado: o usuário decide marcá-lo como substituído.

**Código** (o mesmo padrão de `aplicar_regra_moderado.py`, que só remove valores):
1. **Novo módulo `motor_cenarios/qualidade_serie.py`**, com a função única das regras Q1–Q9 (porte de `recuperar.checar`) e testes próprios. O pacote experimental `motor_cenarios/recuperacao/` passa a importá-lo, em vez de carregar `recuperar.py`.
2. **Em `cenarios.py`:** na montagem de `series_pub`, depois da regra "extremo só com Moderado":
   - aplicar a função a cada extremo, com E e M contínuos de `prev`, Ê e M̂ publicados e P01–P99 das transições comparáveis 2022–2025;
   - se o estado não for `COERENTE`, não publicar o extremo e gravar `motivos[slot] = "ORDEM_OU_DIFERENCA_NA_SERIE"` e o `estado`.
   - **Não alterar:** `escolher_cenarios`, `TOLERANCIA_ERRO`, `DIFERENCA_MINIMA_PP`, `RAZAO_PLAUSIVEL`, modelos e Moderado.
3. **`motor_cenarios/aplicar_regra_ordem.py`:**
   - aplica a regra ao JSON e ao CSV publicados, **só removendo valores**;
   - os motivos vêm da regeneração;
   - falha sem gravar nada se o resultado divergir do gabarito.
4. **Metodologia (tela e texto gerado):**
   - a ordem C ≤ M ≤ A vale em todos os anos de cada série;
   - o extremo que contradiz o rótulo na série fica indisponível, com o motivo;
   - os extremos não são intervalos de confiança.

**Gabarito obrigatório:** `GABARITO_RC_1_0_1_OPCAO_A.csv` (2.495 linhas).

| Ação | Extremos | Detalhe |
|---|---|---|
| MANTER | **1.411** | |
| RETIRAR | **1.084** | 732 LADO_OPOSTO, 350 COINCIDE, 2 IMPLAUSIVEL |
| — detectáveis só nos valores publicados | 1.028 | |
| — com diferença criada só pelo arredondamento | 56 | exigem a trajetória contínua |

- **Resultado esperado:** 185 completas, 1.776 parciais e 241 sem previsão.
- **Tolerância:** zero divergência de ação.

**Testes obrigatórios** (nenhum desativado):

| Nível | Teste |
|---|---|
| Python | propriedade em **todo** o produto público: cada extremo publicado tem C ≤ M ≤ A nos 5 anos, diferença ≥ 0,05 p.p./ano e, nas contagens, ≥ 1 unidade em 2030 (`verificar_publicado.py` deve dar 0 reprovados) |
| Python | `qualidade_serie.py`: um caso de cada estado e o arredondamento (10,49 × 10,51) |
| Python | gabarito acima linha a linha; `cenarios.py --check` com o produto novo |
| Vitest | motivo `ORDEM_OU_DIFERENCA_NA_SERIE` exibido; completude igual em tela, JSON e CSV |
| Playwright | alimentadores, DIST 26: Agressivo ausente com motivo; consumidores (nenhum extremo retirado) inalterado; CSV baixado igual à tela; celular |

**Portabilidade do CI (Linux):**
- o `--check` regenera no Linux e compara a presença de cada extremo **exatamente**;
- a análise de margem e o ruído realista de libm (`00`, seção 3.3) indicam que as decisões de A são estáveis;
- mesmo assim, o PR precisa passar no CI Linux. Se uma decisão divergir, o PR não é forçado: a decisão é listada e tratada pela `recuperacao-2`.

**Aceite:**
- CI verde no SHA definitivo, nos 5 workflows;
- regressão completa: Python, Vitest e Playwright;
- `verificar_publicado.py` com 0 extremos reprovados no produto novo;
- inspeção humana do preview.

## 3. Produção (`74190e2`)

- **Defeito de ordem:** a produção tem 730 extremos com a ordem violada em algum ano (456 Agressivos e 274 Conservadores).
- **Contagens fracionárias:** tem também 921 extremos com contagem não inteira, defeito já corrigido na RC.
- **Caminho de correção:** publicar a RC 1.0.1, e não remendar a produção (decisão D3).
