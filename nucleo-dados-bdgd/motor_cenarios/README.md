# Motor de Expansão Elétrica — cenários Conservador | Moderado | Agressivo

Executa modelos estatísticos e de aprendizado de máquina sobre o estoque físico BDGD 2022–2025 (contrato nacional) e publica, por ativo e métrica, trajetórias 2026–2030 em três cenários. Os cenários são interpretações de modelos validados com a mesma origem temporal, não nomes de algoritmos. Nada é treinado no navegador.

## Reproduzir

A partir de `nucleo-dados-bdgd` (Python ≥ 3.11, `motor_universal/requirements*.txt`):

```sh
# 1) Variáveis internas (só na máquina com os Parquets; não reabre ZIP/GDB). Saída versionada em motor_cenarios/entrada/.
python motor_cenarios/extrair_features.py output-historico/contrato-integracao/serie_fisica_nacional.csv motor_cenarios/entrada
# 2) Variáveis externas IBGE: respostas brutas do SIDRA (URLs no manifesto) → CSV municipal enxuto com SHA-256 do bruto
python motor_cenarios/preparar_externas.py <dir_com_json_do_sidra> motor_cenarios/entrada
# 3) Modelos, backtest, cenários e produto web
python motor_cenarios/cenarios.py output-historico/contrato-integracao motor_cenarios/entrada motor_cenarios/entrada motor_cenarios/saida web/public/data/previsoes/cenarios-motor.json
python motor_cenarios/relatorio.py web/public/data/previsoes/cenarios-motor.json motor_cenarios/saida
# CI: testes e regeneração idêntica (escolhas de modelo e estados exatos; números com tolerância de 0,5% para variação de ponto flutuante entre plataformas)
python -m unittest discover -s motor_cenarios -p 'test_*.py'
python motor_cenarios/cenarios.py output-historico/contrato-integracao motor_cenarios/entrada motor_cenarios/entrada motor_cenarios/saida web/public/data/previsoes/cenarios-motor.json --check
```

## Entradas

| Arquivo | Conteúdo | Origem |
|---|---|---|
| `entrada/uc_por_municipio.csv` | UC ativas (SIT_ATIV=AT) por DIST × ano × município (atributo `MUN` da UC) | Parquets UCBT/UCMT/UCAT da publicação em uso no contrato |
| `entrada/energia_uc.csv` | Energia declarada das UC (ENE_01..12, MWh) por DIST × ano | idem |
| `entrada/potencia_trafos_tuc.csv` | Potência por TUC 565/570/575 via EQ→UN (cada unidade uma vez), com cobertura do vínculo e diagnósticos | EQTRMT→UNTRMT (kVA), EQTRAT→UNTRAT (MVA×1000) |
| `entrada/externas_ibge_municipal.csv` | População 2010 e 2022 (Censos), estimativa 2021 e PIB municipal 2021 | IBGE/SIDRA; URLs, datas de divulgação e SHA-256 em `externas_ibge_manifesto.json` |

Somente agregados por DIST/município; nenhum COD_ID ou registro individual.

## Saídas (`saida/`)

`MATRIZ_MODELO_POR_METRICA.csv`, `BACKTEST_MODELOS_POR_HORIZONTE.csv`, `CENARIOS_CONSERVADOR_MODERADO_AGRESSIVO.csv`, `VARIAVEIS_INTERNAS_EXTERNAS.csv`, `QUALIDADE_POTENCIA_EQ_UN.csv`, `TABELA_FINAL_METRICA_DISTRIBUIDORA.csv`, `RELATORIO_MODELOS_EXECUTADOS.md`, `MANIFESTO.json` (SHA-256 de entradas, código e saídas). Produto web: `web/public/data/previsoes/cenarios-motor.json`.

## Método (resumo)

- Alvo: estoque físico por DIST × ativo × métrica; segmento contíguo de observações positivas terminando em 2025, cortado em ruptura; projeção exige ≥ 3 anos.
- Candidatos: persistência, deriva, tendência OLS, crescimento geométrico; Ridge, Ridge com externas, KNN de análogos (k=9, mediana), Random Forest e HistGradientBoosting em painel sobre o log-crescimento anual com variáveis em t−1 (alvo winsorizado 5–95% só no treino).
- Backtest com origem móvel 2023 (h=1,2) e 2024 (h=1), mesmos pontos para todos; WAPE, MAE, RMSE, viés, MdAPE e estabilidade.
- Moderado = menor WAPE entre plausíveis; Conservador/Agressivo = menor/maior crescimento agregado entre plausíveis com WAPE ≤ 1,25× o moderado e diferença ≥ 0,05 p.p./ano. Sem candidato ⇒ indisponível.
- Sem intervalos probabilísticos; sem totais nacionais projetados; estoque não identifica necessidade técnica nem CAPEX.
