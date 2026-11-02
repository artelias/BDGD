# Entrega final 2026 — Núcleo de Dados BDGD

| Documento | Conteúdo |
|---|---|
| [01 — Relatório executivo](01_RELATORIO_EXECUTIVO_FINAL.md) | Produto, funcionalidades, cobertura, limitações |
| [02 — Matriz completa de modelos](02_MATRIZ_COMPLETA_MODELOS.csv) | 3.420 linhas DIST × objetivo × métrica: estado, motivo, modelo, baseline, erros, histórico e os 15 valores (gerada por `gerar_matriz.py`) |
| [03 — Cobertura nacional final](03_COBERTURA_NACIONAL_FINAL.md) | 114 DIST, os dois indicadores de cobertura, auditoria das 438 combinações, as 10 diferenças contrato × inventário, métricas de potência, totais |
| [04 — Metodologia](04_METODOLOGIA_MODELOS_E_CENARIOS.md) | Modelo × cenário, seleção, equações, coeficientes, variáveis, reconciliação, validação |
| [05 — Integração](05_INTEGRACAO_PRS_E_BRANCHES.md) | Branches, merges, patches A/B/C, sobreposições resolvidas, ordem de merge |
| [06 — Testes e CI](06_TESTES_E_CI.md) | Resultados na árvore integrada, local e GitHub Actions; testes indisponíveis e por quê |
| [07 — Segurança e publicação](07_SEGURANCA_E_POLITICA_DE_PUBLICACAO.md) | Portão do Motor V2, varreduras, N/D, PARCIAL, homologação |
| [08 — Desempenho e UX](08_DESEMPENHO_E_EXPERIENCIA.md) | Tamanhos, tempos, carga sob demanda, responsividade |
| [09 — Limitações e decisões](09_LIMITACOES_E_DECISOES.md) | O que não é contornável e o que cabe decidir |
| [10 — Reprodução](10_REPRODUCAO.md) | Comandos com e sem a base local |

Fonte dos números: `motor_v2/reports/nacional/` (`RESUMO_COBERTURA.json`, `COBERTURA_POR_OBJETIVO.csv`, `MATRIZ_COBERTURA_SERIES.csv`) e `web/data-motor-v2/`.
| [11 — Auditoria de plausibilidade](11_AUDITORIA_PLAUSIBILIDADE_CENARIOS.md) | Outliers, causas, regra do portão, antes/depois, ressalvas |
| [12 — Matriz de plausibilidade](12_MATRIZ_PLAUSIBILIDADE.csv) | As 2.707 séries auditadas: crescimento, razões, limiares, estados e classe |
| [13 — Checklist do release candidate](13_CHECKLIST_RELEASE_CANDIDATE.md) | Critérios de aceite, resultados e estado final |
