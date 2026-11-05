# 09 — Recomendação de integração e especificação para o Codex

**Base:** `08_PARECER_CIENTIFICO.md` e a execução de referência `recuperar.py` (protocolo `recuperacao-1`).
**Nada aqui foi aplicado.**
- A RC 1.0 (`rc/1.0-20261101@dba5fdf`) e a produção (`74190e2`) não foram alteradas.
- Não houve merge nem deploy.
- A integração depende de decisão humana e da implementação pelo Codex.

## 1. Decisão urgente: extremos publicados que contradizem o próprio nome

**Fato.** O produto público escolhe o Conservador e o Agressivo pela trajetória **agregada** da métrica e aplica o mesmo modelo a todas as distribuidoras. Na distribuidora, a trajetória pode ficar do lado errado. A auditoria dos 2.495 extremos publicados encontrou:

| Situação | Extremos |
|---|---|
| Do lado oposto ao Moderado em todos os anos (Agressivo abaixo ou Conservador acima) | **732** (458 Agressivos, 274 Conservadores) |
| Iguais ao Moderado, ou diferentes por menos de 0,05 p.p./ano ou de 1 unidade | **350** |
| Implausíveis | **2** |
| **Aprovados** | 1.411 |

- **Exemplo:** alimentadores da Energisa AC (DIST 26), Agressivo 150 e Moderado 154 em 2030.
- **Onde o defeito está:**
  - já está em **produção** desde 28/10/2026, com o mesmo produto: 755 completas, 456 Agressivos e 274 Conservadores do lado oposto, comparando os inteiros publicados;
  - está também na RC 1.0.
- **Por que os testes não pegaram:** nenhum teste da RC verifica a ordem série a série. Os testes de riscos só exigem trajetórias positivas.
- **Consequência:** das 755 séries "completas", só **185** são completas defensáveis.

**Opções**, todas com os modelos e a tolerância atuais e sem treino novo:

| Opção | O que muda | Completas | Esforço | Risco |
|---|---|---|---|---|
| **(a) Filtro** | não publicar o extremo reprovado na seção 6 do protocolo; o motivo vai para a série (`ORDEM_OU_DIFERENCA_NA_SERIE`) | **185** (1.776 parciais) | pequeno: um passo depois da escolha em `cenarios.py`, regenerar o produto, atualizar o `--check` | a cobertura visível cai; nenhum número novo |
| **(b) Série a série, só com os originais** | mantém o extremo publicado quando aprovado; senão, usa o original competitivo de menor WAPE coerente na série | **711** | médio: muda a regra e o texto da Metodologia | o modelo do extremo passa a variar por DIST |
| (c) (b) + otimizados | inclui as configurações da otimização (`997c4d7`) | 1.039 | médio | 40 dos 77 otimizados competitivos pioraram contra o próprio original; são configurações experimentais |
| (d) (c) + B-HIST | inclui a simulação condicional da própria série | 1.239 | médio + interface | exige distinguir na tela as simulações condicionais |

**Recomendação:**
1. **Antes de qualquer publicação em produção do painel de cenários**, aplicar no mínimo a opção **(a)** numa RC 1.0.1. Ela só retira números que contradizem o rótulo, segundo o princípio do próprio gerador: "sem modelo que satisfaça a regra, o cenário fica INDISPONÍVEL".
2. **Se você aceitar a mudança de metodologia**, a **(b)** é preferível. Ela usa só os modelos e a evidência já publicados e chega a 711 séries completas defensáveis.
3. **Quanto à produção atual**, que exibe o defeito desde 28/10, cabe a você decidir se corrige antes da RC.

## 2. Roteiro recomendado

| Versão | Conteúdo | Condição |
|---|---|---|
| RC 1.0.1 | opção (a), ou (b) se a mudança de metodologia for aceita | implementação do Codex; regressão completa (Python, Vitest e Playwright, sem desativar testes); CI verde no SHA definitivo; inspeção humana do preview |
| 1.1 | opções (c) e (d), com rótulo de categoria na interface | revisão humana da otimização e deste parecer; texto da Metodologia; regressão completa |
| depois da competência 2026 | candidatos novos N1 e N2 e o quantil N5 | confirmação na origem 2025 → 2026 com as escolhas congeladas (`selecao_congelada.json`), sem ajuste; ver a seção 5 |
| decisão de contrato | Moderado para as 121 séries com 2 anos contíguos | aceitar Moderado de painel sem ponto de backtest próprio na série |

**Não recomendado:**
- elasticidade à carga (N6): reprovada;
- substituir algum Moderado;
- promover as métricas em kVA;
- qualquer rótulo de "previsão validada".

## 3. Especificação para o Codex

### 3.1 Escopo e ramo

- **Ramo:** novo, a partir de `rc/1.0-20261101`. Sugestões: `fix/ordem-extremos-por-serie-20261105` para (a) e `feat/cenarios-serie-a-serie-20261105` para (b).
- **PR em rascunho.** Sem merge e sem deploy de produção.
- **Reutilizar, sem duplicar a lógica:**
  - `motor_cenarios/cenarios.py`: `executar_metrica` e `escolher_cenarios` não mudam; o filtro ou a escolha por série entram depois, na montagem de `series_pub`;
  - as regras Q1–Q9 e o estado do candidato de `recuperar.py` (`checar`), movidos para um módulo único, por exemplo `motor_cenarios/qualidade_serie.py`, com testes;
  - `motor_v2/metric_contract.py` para a publicação física.
- **Não alterar:** `TOLERANCIA_ERRO`, `DIFERENCA_MINIMA_PP`, `RAZAO_PLAUSIVEL`, os modelos, as variáveis e o Moderado.

### 3.2 Contrato do produto (`cenarios-motor.json`, `schema_version` → `cenarios-motor-2`)

- **Por série** (`series[DIST]`), novo campo `extremos`:

  ```json
  {
    "conservador": {"modelo": "…", "categoria": "A_PUBLICADO_MANTIDO|A_ORIGINAL|A_OTIMIZADO|B_HIST", "regra": "serie_a_serie"},
    "agressivo": {"modelo": "…", "categoria": "…", "regra": "serie_a_serie"}
  }
  ```

  Os campos `conservador` e `agressivo` com os 5 valores continuam como estão.
- **`motivos`:** ganha os códigos de causa do protocolo (`I`, `A1`, `A2`, `B`, `C`, `D`, `E`, `F`, `G`, `H`) ou `ORDEM_OU_DIFERENCA_NA_SERIE`, com texto para o usuário.
- **`cenarios` por métrica:** permanece com o significado atual (modelo agregado) ou é renomeado para `cenarios_agregados`. A Metodologia precisa explicar a diferença.
- **CSV público:** colunas `modelo_serie`, `categoria` e `motivo`. As contagens continuam inteiras.

### 3.3 Interface

- **`web/src/lib/completude.ts`:** mantém COMPLETA, PARCIAL e SEM_PREVISAO.
- **Painel "Cenários de expansão por métrica física":**
  - mostra o modelo de cada extremo da série na legenda ou na dica;
  - indica "simulação condicional" quando a categoria começa por B (só nas opções d e seguintes);
  - mostra o motivo de cada extremo ausente.
- **Metodologia:**
  - descreve a regra série a série;
  - diz que a ordem C ≤ M ≤ A vale em todos os anos de cada série;
  - explica que os extremos não são intervalos de confiança;
  - lembra que os horizontes de 2 a 5 anos não são homologados.
- **Total nacional dos extremos:** continua rotulado como soma de extremos individuais (NC-ENG-01).

### 3.4 Testes obrigatórios (nenhum pode ser desativado)

| Nível | Teste |
|---|---|
| Python | propriedade em **todo** o produto: para cada série publicada, C ≤ M ≤ A nos 5 anos, nos valores publicados; diferença ≥ 0,05 p.p./ano; contagens com diferença ≥ 1 unidade em 2030 |
| Python | `qualidade_serie.py`: casos de cada estado (COERENTE, LADO_OPOSTO, COINCIDE, CRUZA, IMPLAUSIVEL) e de arredondamento (10,49 contra 10,51) |
| Python | **gabarito** da opção escolhida contra `02_MATRIZ_SERIES_CENARIOS.csv` (abaixo) |
| Python | `cenarios.py --check` com o produto novo (mesma tolerância de plataforma) |
| Vitest | rótulos de categoria e motivos; completude igual entre tela, JSON e CSV |
| Playwright | alimentadores, DIST 26: o Agressivo não fica abaixo do Moderado (ou fica ausente, com o motivo); uma série recuperada pela opção (b), por exemplo consumidores com Agressivo; o CSV baixado igual à tela; celular |

**Gabarito por opção** (colunas de `02_MATRIZ_SERIES_CENARIOS.csv`):

| Opção | Por série e lado | Classe esperada |
|---|---|---|
| (a) | o extremo publicado continua só se `{lado}_estado_publicado == COERENTE` | `completude_defensavel_antes` |
| (b) | `{lado}_so_originais_modelo` e `{lado}_so_originais_2030` | `classe_gateB_so_originais` |
| (c) | `{lado}_originais_otimizados_modelo` e `_2030` | `classe_gateB_originais_e_otimizados` |
| (d) | `{lado}_gateB_modelo` e `_2030` | `classe_gateB` |

A tolerância é de 0 diferenças de modelo ou de categoria. Nos valores, vale a folga de 1 unidade do `--check`, entre plataformas.

### 3.5 Aceite

- **Auditoria independente:** o Claude reexecuta `recuperar.py` contra o produto novo e exige 0 extremos publicados reprovados na seção 6.
- **Regressão completa no SHA definitivo:** Python (281 + gerador), Vitest e Playwright completo, com CI verde.
- **Inspeção humana do preview.**
- **Gabarito:** a implementação do Codex reproduz o gabarito da opção escolhida linha a linha.

## 4. Decisões que dependem de você

| # | Decisão | Recomendação |
|---|---|---|
| D1 | Corrigir os 1.084 extremos publicados que violam a ordem antes de publicar a RC | **Sim**: opção (a) no mínimo |
| D2 | Adotar a seleção série a série (b) e mudar o texto da Metodologia | Sim, na RC 1.0.1 ou na 1.1 |
| D3 | Corrigir a produção atual (`74190e2`), que já exibe o defeito | Decisão sua; a correção segue o mesmo caminho da RC |
| D4 | Aceitar as configurações otimizadas como candidatas a extremo (c) | Só na 1.1, depois de revisar a otimização |
| D5 | Publicar as simulações condicionais (B-HIST, quantil) com rótulo próprio (d) | Só com a interface que distingue a categoria |
| D6 | Histórico mínimo de 2 anos para o Moderado de painel (121 séries) | Não agora: falta evidência retrospectiva na série |
| D7 | Manter N1, N2 e N5 congelados até a competência 2026 | Sim |
| D8 | Assinar ou não este parecer | — (não assinado) |

## 5. Confirmação futura

Será pré-registrada antes de usar a competência 2026. Regras:
- **Configurações:** as de `selecao_congelada.json` (SHA-256 em `selecao_congelada.sha256`), aplicadas como estão.
- **Treino e alvo:** treino com as transições até 2025; alvo em 2026, com h=1.
- **Pontos e critérios:** os mesmos pontos e critérios deste protocolo.
- **Ajustes:** nenhum ajuste depois de ver o alvo.
- **Regra de promoção:** um candidato novo só pode virar extremo publicado se continuar competitivo e coerente na nova origem.
