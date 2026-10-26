# Integração da QA estatística após a auditoria independente do Codex

**Referência:** PR #6 atualizado pelo Codex, commit `1f4e3246` (25/10/2026). **Alteração isolada:** branch `feat/chatgpt-qa-cenarios-reconciliados-codex`.

## Por que esta segunda versão é necessária

O Codex corrigiu o modelo de tendência linear para regressão de mínimos quadrados ordinários **com intercepto** e republicou os cenários como `cenarios-bdgd-exploratorios-1.0.1`. Também passou a usar `toCSV`, a incluir estado do zero técnico, homologação, métrica, IDs de publicação e SHA do contrato, além de aprimorar acessibilidade.

O PR #7 antigo foi criado sobre o commit `cfad5559` e não pode ser integrado sem alterações: usa a projeção anterior ancorada no último valor e um CSV menos auditável. A presente branch parte diretamente do `1f4e3246` e preserva **integralmente** essas correções do Codex.

## O que muda, sem recalcular dados

A biblioteca `web/src/lib/risco-cenarios.ts` calcula **apenas avisos heurísticos** sobre a série apresentada:

- pelo menos um zero classificado tecnicamente na série original: **205 séries**;
- os quatro históricos iguais a zero técnico: **190 séries**;
- zero em 2025 depois de algum valor histórico positivo: **4 séries**;
- regressão OLS **com intercepto** estima valor negativo em algum ponto 2026–2030 e este é truncado em zero: **11 séries**;
- estoque linear estimado para 2030 pelo menos o dobro do observado de 2025: **65 séries**;
- estoque linear estimado para 2030 no máximo 30% do observado em 2025: **13 séries**.

As categorias se sobrepõem; não somar seus totais. Os resultados são sobre as 1.555 séries já elegíveis do contrato BDGD, não sobre todas as 2.850 combinações nem sobre os 11.400 registros nacionais.

A previsão com intercepto tem a forma `media_y + inclinacao*(x-media_x)`; não substitua por `ultimo_observado + inclinacao*horizonte`. Um zero previsto por truncamento é **matemático**, não `zero_verificado` na origem.

## Integração não destrutiva ao CSV do Codex

O CSV original do Codex tem o cabeçalho:

```csv
ano,valor,classe,metodo,dist,conceitoId,unidade,metrica,status_homologacao,publicacao_id,verificacao_independente_zero,versao_dados,commit_origem,blob_sha_origem
```

Esta atualização preserva todas as 14 colunas, sem reordenar ou reclassificar valores, e acrescenta apenas `avisos_estatisticos` como 15ª coluna. As linhas 2022–2025 recebem string vazia para riscos do futuro, e as linhas 2026–2030 recebem os códigos das ressalvas pertinentes à série e ao método, separados por `|`. Todos os dados de proveniência ficam intactos.

## Validação e handoff

- `web/tests/risco-cenarios.test.ts`: regressões com valores fixos e contagens completas para a versão 1.0.1.
- `web/e2e/riscos-cenarios.spec.ts`: cenários DIST 87 (bancos de capacitores) e DIST 39 (reatores), exportação com estado, fontes e avisos, além de viewport mobile.
- Não altera GDB, ZIP, dados oficiais, o contrato ETL, as séries calculadas nem o modelo do Codex.
- Sem decisão regulatória, merge ou deploy de produção. A publicação permanece em prévia de PR.

**Coordenação:** esta branch substitui funcionalmente o PR #7 antigo; o Codex não precisa refazer sua auditoria nem atualizar a regressão novamente.