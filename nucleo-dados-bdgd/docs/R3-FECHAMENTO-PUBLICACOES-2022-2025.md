# Fechamento técnico — inventário de publicações BDGD 2022–2025

Data de referência: 25/10/2026. Base: PR #4, commit `8e2eab8`, a partir da matriz `auditoria/fase4/MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv` e do inventário `auditoria/fase6/INVENTARIO_LACUNAS_NACIONAL.csv`. Interface e dados derivados: PR #6.

## O significado de "em quarentena"

O painel antigo exibia 4 arquivos em 2022 e 7 em 2023 como se fossem etapas genéricas de processamento. Aqueles números são obsoletos e não representam a situação atual da auditoria. O inventário atual lista e identifica os 414 itens oficiais; cada item traz DIST, empresa, competência, DAT_FNL da BASE, versão e URL ArcGIS.

| Ano | Versão em uso | Pacote 2025 | Versões divergentes pendentes | Arquivos excluídos por competência | Uma versão do par em uso | Total |
|---|---:|---:|---:|---:|---:|---:|
| 2022 | 94 | 0 | 4 (2 pares) | 6 | 1 | 105 |
| 2023 | 82 | 0 | 22 (11 pares) | 8 | 1 | 113 |
| 2024 | 97 | 0 | 0 | 0 | 0 | 97 |
| 2025 | 0 | 99 | 0 | 0 | 0 | 99 |
| **Total** | **273** | **99** | **26** | **14** | **2** | **414** |

**Conclusão da recuperação técnica:** não há ZIP oficial não processado ou corrompido identificado pelo trabalho da Fase 6. Os 14 arquivos excluídos têm DAT_FNL incompatível com a competência-alvo (incluindo 30/11/2022 para o ciclo 31/12/2022). Não devem ser reclassificados apenas pelo título do catálogo. Não são uma fila de recuperação: exclusão técnica concluída.

As 26 versões divergentes pertencem a 13 pares DIST/ano, com todos os itens e comparações conservados em `web/public/data/historico/pares-divergentes.json`. Seis pares não alteram os totais dos 25 conceitos; sete alteram pelo menos um total. A versão mais recente **não** foi adotada automaticamente; o comparativo técnico oferece evidência, não homologação.

Há, separadamente, **11 combinações DIST/ano sem publicação localizada** no catálogo oficial, equivalentes a 275 células (11 × 25 conceitos), e anomalias como entidades vazias em GDB. Sem dados oficiais adicionais, a categoria correta é N/D, não zero.

## Estados e decisões

- **Em uso:** entrou na série de referência do ETL. Não implica que todas as 25 células da publicação sejam observadas/homologadas. Em especial, Coprel 2023 mantém ressalva de BASE inconsistente.
- **Excluído por competência:** dados presentes, mas não atribuíveis à data-base-alvo; já excluídos da série. Encerrado tecnicamente.
- **Par divergente pendente:** duas versões conflitantes sem evidência formal inequívoca de substituição; ficam bloqueados os indicadores dependentes, com motivo e fontes.
- **Ausência de publicação:** inexistência no inventário oficial pesquisado, requer resposta oficial; não é quarentena técnica nem valor zero.
- **Entidade vazia:** não prova zero. Pode ser N/D mesmo quando o ETL tem 0 registros.
- **Homologação:** `COMPLETO_TECNICO` não corresponde a aprovação humana. N/D e zero devem permanecer distintos.

## Entregas executadas no PR #6

1. `web/public/data/historico/publicacoes-auditadas.json`: 414 publicações e 11 combinações não localizadas, com origem e status.
2. `web/public/data/historico/pares-divergentes.json`: 13 pares e impactos, sem seleção de versão.
3. `web/src/components/pages/PublicacoesAuditadas.tsx` e `ParesDivergentes.tsx`: filtros por ano, estado e distribuidora/arquivo, explicações e links oficiais.
4. `web/src/components/pages/Evolucao.tsx`: quadro ligado à Evolução e retirada da mensagem obsoleta de quarentena.
5. Testes unitários e E2E em `web/tests/publicacoes-auditadas.test.ts` e `web/e2e/publicacoes-previsoes.spec.ts`.

## Limites inegociáveis

Não decidir publicação oficial quando evidências são inconclusivas. Não criar ano histórico, não substituir ausência por zero, não alterar dados GDB ou Parquet originais e não gerar total Brasil com cobertura incompleta. Não homologar as 13 republicações, EPB/EBO e Coprel 2023 sem decisão formal.

**Critério de conclusão técnico:** disponibilizar inventário exato e filtro de todos os casos, relatórios reprodutíveis, build e testes de CI verdes e preview de navegação no ambiente Vercel. O fechamento de pendências regulatórias depende de decisões externas e não pode ser simulado como solução computacional.