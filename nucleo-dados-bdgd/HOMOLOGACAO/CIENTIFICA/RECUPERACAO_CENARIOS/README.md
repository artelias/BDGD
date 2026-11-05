# Recuperação científica dos cenários ausentes (experimental)

**EXPERIMENTAL.** Não altera a RC 1.0 nem o produto publicado, e não é homologação científica. O protocolo `04_PROTOCOLO_CANDIDATOS.md` foi commitado em `d478e16`, antes de qualquer cálculo série a série.

| Arquivo | Conteúdo |
|---|---|
| `01_DIAGNOSTICO_LACUNAS.md` | Gate A: causas das 2.150 posições ausentes e auditoria dos 2.495 extremos publicados |
| `02_MATRIZ_SERIES_CENARIOS.csv` | uma linha por série (2.202): histórico, rupturas, Moderado, extremos publicados e o estado de cada um, causas, preenchimento final, gabarito por opção de integração |
| `03_INVENTARIO_MODELOS_EXISTENTES.csv` | originais, otimizados, novos, condicionais e hierárquicos por métrica: reprodução, elegibilidade, competitividade e classe |
| `04_PROTOCOLO_CANDIDATOS.md` | protocolo pré-registrado (`recuperacao-1`) |
| `05_COMPARACAO_RETROSPECTIVA.csv` | por métrica, candidato e etapa: WAPE, MAE, RMSE, viés, R² (estoque, crescimento e variação), WAPE da expansão, robustez e IC95% contra os baselines e o Moderado |
| `06_AUDITORIA_PLAUSIBILIDADE.csv` | regras Q1–Q9 de cada extremo publicado e de cada extremo escolhido, com o estado de todos os candidatos testados |
| `07_COBERTURA_ANTES_DEPOIS.csv` | cobertura nacional, sem kVA, por empresa, por métrica e por família |
| `08_PARECER_CIENTIFICO.md` | Gates B a E, respostas às 12 perguntas e desvios |
| `09_RECOMENDACAO_INTEGRACAO.md` | opções de integração, especificação para o Codex e decisões |
| `selecao_congelada.json` (e `.sha256`) | escolhas feitas na etapa S, congeladas para a confirmação em 2026 |
| `REPRODUCAO.csv`, `MANIFESTO.json`, `RESUMO.json` | verificação da reprodução do produto, SHA-256 das entradas e saídas, contagens do relatório |

Para reproduzir (cerca de 5 min, um processo; scikit-learn 1.8.0, sem dependência nova):

```bash
D:/NUCLEO_BDGD_2025/.venv-motor/Scripts/python.exe HOMOLOGACAO/CIENTIFICA/RECUPERACAO_CENARIOS/recuperar.py HOMOLOGACAO/CIENTIFICA/RECUPERACAO_CENARIOS
D:/NUCLEO_BDGD_2025/.venv-motor/Scripts/python.exe HOMOLOGACAO/CIENTIFICA/RECUPERACAO_CENARIOS/tabelas.py HOMOLOGACAO/CIENTIFICA/RECUPERACAO_CENARIOS motor_cenarios/otimizacao/saida/MATRIZ_MODELOS_OTIMIZADOS.csv
```
