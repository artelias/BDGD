# 14 — Correções finais de release (RC 1.0)

Base: `rc/1.0-20261101@a7df5e2`. Quatro defeitos visíveis, corrigidos na origem e cobertos por testes. Nenhum teste foi removido ou enfraquecido. Os números publicados não mudaram: só valores inconsistentes foram retirados, e campos novos foram acrescentados.

## 1. Cenários incompletos na tela de Previsões

**Auditoria.** A matriz `14_COMPLETUDE_CENARIOS.csv` (gerada por `gerar_completude.py`) traz, por produto, distribuidora, ativo e métrica, a completude, os cenários publicados e o motivo de cada ausente.

| Causa | Produto público (produção) | Motor V2 (homologação) |
|---|---|---|
| Os 3 cenários existem | 755 séries | 2.484 séries |
| Extremo bloqueado: Motor V2 pelo portão de plausibilidade; produto público pela faixa física 2030/2025 ∈ [0,5; 3] da série | 308 cenários extremos | 219 séries parciais, 4 bloqueadas inteiras |
| Regra de seleção da métrica: nenhum modelo dentro de 1,25× o WAPE do Moderado com trajetória abaixo/acima dele | 1.593 cenários extremos (métricas `somente_moderado`, `somente_baseline`, `dois_cenarios`) | não se aplica |
| Front escondendo cenário válido | **0** (os testes conferem todas as séries: o cenário exibido é exatamente o publicado) | **0** |
| Exportador com estado inconsistente | **8 extremos publicados sem o Moderado** em 6 séries (DIST 6072: chaves, circuitos AT, disjuntores, potência de trafos de distribuição, trafos de força; DIST 5363: religadores). A tela ainda mostrava o estado **da métrica** ("Três cenários comparados em backtest") para séries parciais | 0 |

Totais por série: produto público 755 completas, 1.206 parciais, 241 sem previsão (histórico curto ou trajetória implausível); Motor V2 2.484 / 219 / 4.

**Correção da regra de publicação** (`motor_cenarios/cenarios.py`): Conservador e Agressivo são definidos em relação ao Moderado, então numa série sem Moderado publicável nenhum extremo é publicado (`SEM_MODERADO_NA_SERIE`). Toda ausência de um cenário cujo modelo existe na métrica passa a ter motivo por série (`motivos`):
- `TRAJETORIA_IMPLAUSIVEL_NA_SERIE`;
- `HISTORICO_CONTIGUO_INSUFICIENTE`;
- `MODELO_SEM_PROJECAO_NA_SERIE`.

A regra foi aplicada ao produto publicado por `motor_cenarios/aplicar_regra_moderado.py`: 8 extremos removidos e 247 séries com motivos. Os demais números publicados ficaram preservados, e `cenarios.py --check` foi aprovado (29 métricas; 16.010 contagens; 2 na folga de 1 unidade). O parser da web e o teste Python recusam extremo sem Moderado.

**Correção da tela.** Há uma regra única de completude (`web/src/lib/completude.ts`) para os dois produtos:
- **COMPLETA:** os 3 cenários publicados.
- **PARCIAL:** o Moderado publicado e um ou os dois extremos não publicados, cada um com o motivo.
- **SEM_PREVISAO:** a projeção não é exibida ("Cenários incompletos: previsão não publicada"); só o histórico e o motivo.

Os mesmos dados alimentam:
- **cards:** cenário não publicado desativado e marcado "Não publicado neste recorte"; o motivo fica no `title` e na faixa;
- **faixa de completude:** "Previsão parcial · 1 de 3 cenários publicados (Moderado)";
- **gráfico:** só os cenários publicados; o `aria-label` traz a completude;
- **tabela:** colunas só dos publicados, legenda com a completude, nenhuma célula "Indisponível";
- **CSV:** colunas `…_nao_publicado` e `completude_cenarios`/`cenarios_publicados` em toda linha;
- **KPI nacional do Motor V2:** "X com os três cenários · Y parciais · Z bloqueadas".

Num grupo, um cenário só é publicado quando todas as distribuidoras o têm. A seleção da métrica nacional continua visível, rotulada como tal ("Seleção na métrica nacional: …").

O que esta etapa **não** faz é preencher cenários ausentes. Ampliar a cobertura com modelos defensáveis (R² fora da amostra, seleção de variáveis, otimização dos candidatos próximos) é trabalho separado, numa branch própria, que não substitui esta RC.

## 2. Contagens com decimais

Origem dos decimais encontrados:
1. **JSON público do Motor V2:** 41.027 contagens gravadas como `36241.0` (histórico, âncora, cenários e totais nacionais). O exportador (`motor_v2/nacional/exportar_web.py`) agora grava inteiros JSON. Uma contagem fracionária é erro de contrato (`_inteiro`), nunca arredondada. O produto foi regenerado e é semanticamente idêntico ao anterior (0 arquivos com diferença), mais o campo `completude_cenarios`.
2. **Gráfico da Evolução:** o eixo das contagens não tinha `minInterval`, então o ECharts podia escolher marcas fracionárias numa série pequena (por exemplo 1 → 2 subestações). O rótulo usava `fmt()`, com 2 casas para valores não inteiros. Isso foi identificado no código; o teste novo confere a série 1 → 2 da DIST 95 na build corrigida. Agora o eixo de contagem usa marcas inteiras (`minInterval: 1`) e `fmtEixo`, que nunca rotula uma marca fracionária.
3. **`fmt()` genérico** formatava contagem fracionária com 2 casas ("12,5"). Agora mostra "valor inválido" e registra o erro no console (os testes E2E reprovam erro de console), sem arredondar em silêncio.
4. **Notação compacta:** contagens apareciam como "12,5 mil" e "1,2 mi" em cards, barras, listas e rótulos (`fmtCompact`/`fmtUnitCompact`). Agora contagens saem inteiras com separador de milhar ("12.500"); extensão e potência continuam compactas.

Confirmado nos dados: inventário, cubos, fatos, série histórica, cenários públicos, motor universal e exploratórios já publicavam contagens inteiras. Os testes agora reprovam qualquer regressão (Vitest `release-correcoes.test.ts`, Python `test_produto_web_v2`, `test_publico`). N/D continua N/D, e km/kVA mantêm decimais.

## 3. Informações laterais

A lateral mostrava "Data-base 31/12/2025", "99 GDBs processados" e "15 publicações 2025 não localizadas", que foram removidas. A lateral mantém só a navegação e a autoria. A data-base continua no cabeçalho. GDBs processados e publicações não localizadas ficam em **Metodologia e qualidade** (seção Fonte e competência, mais o estado por distribuidora em Cobertura).

## 4. Tema claro/escuro no mapa

**Reprodução.** Depois de um clique no tema, a página ficava escura e o mar e o continente continuavam claros (e o inverso no clique seguinte). As áreas de atuação mudavam corretamente.

**Causa exata.** O `ThemeProvider` gravava `data-theme` no `<html>` num `useEffect` do provedor. O React executa os efeitos dos filhos antes dos do pai, então o efeito de recoloração do mapa (filho) lia as variáveis CSS (`--map-water`, `--map-land`, `--map-line`) ainda do tema anterior. Enquanto isso, as cores das ARAT vinham do valor novo do React. O mapa ficava sempre um tema atrasado no fundo. O mesmo atraso afetava `chartTokens()` dos gráficos ECharts.

**Correção.**
- O `ThemeProvider` grava `data-theme` num `useLayoutEffect`. Todos os efeitos de layout rodam antes dos efeitos comuns, então mapa e gráficos já leem o tema novo.
- O mapa não recolore se o DOM não estiver no tema pedido.
- O mapa expõe o tema e a cor de fundo pintados (`data-tema`, `data-fundo`) para teste.
- Não há remontagem, filtro CSS nem nova instância.

**Teste** (`e2e/mapa-tema.spec.ts`, desktop e mobile), com 10 alternâncias seguidas e depois recarga. A cada alternância confere:
- o tema pintado pelo mapa e a cor de fundo igual à variável CSS do tema atual;
- os **pixels renderizados no canvas**: nenhum pixel com as cores de base do outro tema;
- 1 canvas MapLibre só e os controles de zoom presentes;
- console sem erros.

## Testes

Ver `06_TESTES_E_CI.md` (seção Correções finais de release).
