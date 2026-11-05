# Auditoria da entrega do Codex e desbloqueio dos cenários (2026-11-05)

**EXPERIMENTAL e não assinado.** Não altera a RC 1.0 (`dba5fdf`), o PR #22, a produção (`74190e2`) nem os dados originais, e não é homologação científica. Não houve merge nem deploy.

**Base:**
- branch `exp/auditoria-codex-recuperacao-20261105`, criada a partir de `codex/recuperacao-cenarios-20261105@14f4e61`;
- protocolo `recuperacao-1` (`d478e16`), sem alteração.

**Ambiente de referência:** Windows 10 19045, Python 3.14.3, NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.8.0 (`D:/NUCLEO_BDGD_2025/.venv-motor`). Nada foi instalado.

| Arquivo | Conteúdo |
|---|---|
| `00_PARECER_AUDITORIA.md` | parecer independente e respostas às 10 perguntas |
| `01_extremos_publicados/` | verificação independente, só sobre os valores publicados, dos 2.495 extremos da RC e da produção: por série e lado (`EXTREMOS_PUBLICADOS_*`), por ano (`EVIDENCIA_ANUAL_*`) e por métrica |
| `02_opcoes_rc_1_0_1/` | comparação A × B, especificação da RC 1.0.1 e gabarito da opção A (2.495 linhas) |
| `03_causa_wape/` | causa da divergência de WAPE (libm) e do KNN otimizado (empates de distância) |
| `04_sensibilidade/` | outra libm, ruído realista de libm, estresse de ±1 ULP, configurações X e margens das decisões |
| `05_validacao_nacional/` | validação independente V1–V8 dos produtos nacionais e determinismo sem cache |
| `06_MATRIZ_STATUS_MODELO_METRICA.csv` | status APROVADO, REPROVADO, BLOQUEADO ou EXPERIMENTAL por modelo e métrica |
| `07_PROPOSTA_RECUPERACAO_2.md` | proposta de protocolo de portabilidade (não aplicada) |
| `08_AUDITORIA_IMPLEMENTACAO_CODEX.md` | achados sobre o código do Codex (D-1 a D-5, O-1) |
| `*.py` | scripts da auditoria, que só leem; as saídas vão para estas pastas |

As execuções do pacote do Codex no Windows ficam em `motor_cenarios/experimental/recuperacao/win-*`:
- **Pilotos:** completos.
- **Execuções nacionais:** só os artefatos leves. `produto.json`, `inventario.json` e `elegibilidade.csv` têm até 26 MB e não foram versionados; os SHA-256 deles estão em `proveniencia.json` e se reproduzem com os comandos abaixo.

Para reproduzir, a partir de `nucleo-dados-bdgd`, com `OMP_NUM_THREADS=1` e `PYTHONUTF8=1`:

```bash
D:/NUCLEO_BDGD_2025/.venv-motor/Scripts/python.exe -m motor_cenarios.recuperacao --modo originais --nome <novo-nome>
D:/NUCLEO_BDGD_2025/.venv-motor/Scripts/python.exe HOMOLOGACAO/CIENTIFICA/AUDITORIA_CODEX_RECUPERACAO/verificar_publicado.py dba5fdf <pasta> RC_dba5fdf
D:/NUCLEO_BDGD_2025/.venv-motor/Scripts/python.exe HOMOLOGACAO/CIENTIFICA/AUDITORIA_CODEX_RECUPERACAO/validar_nacional.py motor_cenarios/experimental/recuperacao/<novo-nome> <saida.json> originais
```
