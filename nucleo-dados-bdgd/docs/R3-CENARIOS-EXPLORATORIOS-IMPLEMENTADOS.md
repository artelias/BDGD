# Cenários exploratórios de estoque BDGD — PR #6

**Estado:** aplicação funcional no navegador, **não** previsão validada. Sem merge ou deploy automático.

## Origem e rastreabilidade

- Dados agregados do contrato nacional `output-historico/contrato-integracao/serie_fisica_nacional.csv` do PR #4, commit `8e2eab8`.
- Proveniência por série: quatro IDs de publicação oficial, status de homologação de cada ano, flag `O` (observado) ou `Z` (zero técnico ainda sujeito a checagem independente).
- O blob Git de origem é `ef577d530bfe5c732d2f377f2cea273f79fe663c` (SHA-1 de blob Git, **não** substitui SHA-256 dos ZIPs de origem).
- A série não contém COD_ID, geometria, dado de unidade consumidora nem informação pessoal.
- O arquivo `web/public/data/previsoes/cenarios-exploratorios-2026-2030.json` tem 1.555 séries, 71 distribuidoras, 25 conceitos, quatro anos históricos, cinco cenários anuais e dados de backtest.

## Elegibilidade

Uma série entra **somente** se houver quatro observações 2022–2025 do mesmo DIST/ativo/métrica/unidade/perímetro/regra, `estado` observado ou zero_verificado, cobertura igual a 1, valores não negativos e finitos, sem lacunas, rupturas sinalizadas, duplicidade temporal, predecessora já incorporada ou ponte pendente. Não se preenche N/D por zero. A quantidade de `zero_verificado` vem da matriz técnica; a ausência de registros no GDB é uma evidência que ainda requer auditoria independente.

Não há série comparável suficiente para construir previsão probabilística de longo prazo: o backtest treinou com 2022–2024 e testou em 2025 (**uma origem temporal**). Os anos 2022–2024 não estão homologados humanamente. Portanto não há resultados de `previsao_validada`, intervalos probabilísticos, necessidade técnica nem CAPEX.

## Modelos

- Persistência: repete o valor observado em 2025 em cada ano 2026–2030.
- Tendência linear (pacote 1.0.1): ajusta inclinação e intercepto por mínimos quadrados em 2022–2025; usa `média(y) + inclinação × (ano-alvo − média(ano))`, truncando estoque a zero se o valor algébrico for negativo. A versão 1.0.0 ancorava incorretamente a reta no último observado.
- Erro `MAE` no corte temporal 2025: um erro absoluto, dada uma única origem; não interpretá-lo como estimativa estável de generalização.
- Não somar séries para obter Brasil: cobertura das distribuidoras e mudanças de perímetro tornam a agregação nacional parcial.

## Como reproduzir

Na raiz `nucleo-dados-bdgd`, após incorporar o contrato de dados PR #4:

```bash
node etl/bdgd2025/88_cenarios_exploratorios.mjs --source-commit 8e2eab8 --check
node etl/bdgd2025/88_cenarios_exploratorios.mjs --source-commit 8e2eab8
cd web
npm test -- previsoes-exploratorias-dados.test.ts
```

A primeira linha verifica que o JSON publicado corresponde exatamente ao contrato e à versão do gerador. A segunda regenera os cenários quando a origem for atualizada. **Se o CSV de origem mudar, atualizar o commit de origem e revalidar**; não transportar resultados antigos sem reconciliação.

## Uso no portal

Página `/previsoes`, com seleção por distribuidora, ativo, método e ano, gráfico 2022–2030, CSV por série, backtest e acesso aos identificadores das publicações oficiais.

O CSV diferencia observado, zero técnico e simulação; conserva status de homologação, IDs das publicações, versão e blob de origem. São 792 zeros técnicos nas séries elegíveis, de 1.013 no contrato completo; a verificação independente desses zeros continua pendente. O placar exploratório no corte 2025 é 704 erros menores na tendência, 421 na persistência e 430 empates (tolerância 1e-9); não seleciona nem valida automaticamente um modelo.

O mesmo gerador transporta os 11.400 estados para `web/public/data/historico/estados-contrato.json`, sem modificar o contrato, a matriz ou GDBs. A Evolução exige cobertura nacional completa por ativo/ano; as lacunas do contrato também impedem totais nacionais em 2024–2025. O painel balanceado continua identificado como subconjunto.

**Revisões pendentes:** conferir independentemente os 1.013 zeros técnicos; resolver republicações divergentes, EPB/EBO e outras decisões humanas; obter histórico maior e covariáveis de carga/custos para modelos de demanda e CAPEX.
