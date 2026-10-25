# Handoff operacional — recuperação nacional × motor exploratório (25/10/2026)

## Trabalho já realizado por ChatGPT (PR #6)
- Corrigida regex de data de corte em `web/src/lib/previsoes-contrato.ts` (commit `a8fdc797`).
- Criado `web/src/lib/motor-cenarios.ts`: persistência e tendência linear, diagnóstico de elegibilidade, projeções condicionais 2026–2030 e backtest de origem expansiva. Não declara previsão validada.
- Criado `web/tests/motor-cenarios.test.ts` com cenários de sucesso e bloqueios.
- Corrigido SyntaxError em `etl/iasc/prepare_iasc.py` (commit `f3656f39`), identificado nos logs reais do workflow IASC. CI de confirmação pendente.

## Contrato de integração — Claude fornece, ChatGPT consome
Criar artefato versionado (CSV/JSON/Parquet) para TODAS as células de ano × DIST × conceito × métrica:
- `ano` inteiro; `dist` inteiro; `conceitoId`; `metrica`; `unidade`; `valor` numérico ou null.
- `perimetroId`, `regraVersao`, `estado` e `cobertura` (1 somente quando integral e verificável).
- `fonte`, `dataBase`, `perimetroBridgeId` (null se não há ponte).
- `motivo_nd`, `status_homologacao`, `publicacao_id`, `sha256`, `tipo_lacuna`, `data_geracao` como metadados adicionais auditáveis.

Estados aceitos no contrato TS: `observado`, `zero_verificado`, `ausente`, `nao_homologado`, `nao_aplicavel`, `ruptura`.
**Atenção:** `COMPLETO_TECNICO` não é homologação humana. A política de treinamento precisa distinguir aprovação técnica de fonte formalmente homologada; não mapear automaticamente ambos para `fontesHomologadas=true`.
Não transformar N/D em zero, não juntar versões divergentes, não assumir sucessão EPB/EBO. Não contar ENF duas vezes.

## Tarefas do Claude no PR #4
1. Gerar inventário completo das lacunas nacionais 2022–2025, por ativo, ano, DIST, com motivo e etapa exata da falha.
2. Corrigir ETL web, consultas e downloads locais recuperáveis, com checksums e checkpoints novos sem sobrescrever os existentes.
3. Reconciliar agregados e painel balanceado por ativo, sem total nacional fictício.
4. Exportar o contrato de integração acima, com relatório de cobertura antes/depois e exemplos verificáveis.
5. Não editar `web/src/lib/motor-cenarios.ts`, `web/tests/motor-cenarios.test.ts`, `web/src/lib/previsoes-contrato.ts` nem `etl/iasc/**` (responsabilidade PR #6).
6. Informar commit/branch, local do artefato, esquema, total de linhas, percentuais de cobertura e evidências de validação. Não fazer merge ou deploy.

## Limites estatísticos
2022–2025 = quatro pontos anuais por DIST; no máximo um teste temporal com treino inicial de três anos no motor atual. Não chamar essa evidência de validação robusta. Modelos hierárquicos e covariáveis exigem controles de vazamento e análise de viés; compartilhar distribuidoras não cria mais anos observados.

## Estado de CI
No workflow do commit `5c367c33`, o check de frontend terminou com sucesso; o check IASC falhou com `SyntaxError` em `prepare_iasc.py`, corrigido em `f3656f39`. Verificar nova execução antes de alegar CI verde.
