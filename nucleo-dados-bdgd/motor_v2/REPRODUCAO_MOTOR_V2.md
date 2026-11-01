# Motor V2 — como reproduzir (2026-10-30)

O Motor V2 é **ferramenta local de pesquisa**, sem passo de deploy. O dashboard e os produtos públicos não leem nada de `motor_v2/`, e nenhum artefato daqui é exigido pelo deploy. Os resultados nacionais continuam **internos e experimentais**, sem homologação científica.

## 1. Testes sintéticos (qualquer máquina, Linux inclusive, sem dados locais)

É o que o CI roda (`.github/workflows/motor-v2-sintetico.yml`, 11 suítes, 150 testes). Sem acesso a `D:\`, à base BDGD ou a rede.

```bash
cd nucleo-dados-bdgd
python3 -m venv .venv-motor-v2
.venv-motor-v2/bin/python -m pip install -r motor_universal/requirements.txt -r motor_universal/requirements-ml.txt duckdb==2.0.0 pyogrio==0.13.0
for t in test_hierarquia test_erro_retrospectivo test_auditoria_final test_nacional test_baselines test_conj_plan test_future \
         test_metric_contract test_public_audit test_temporal test_vintage; do
  .venv-motor-v2/bin/python -m unittest discover -s motor_v2/tests -p "$t.py" -v
done
```

No Windows, troque `.venv-motor-v2/bin/python` por `.venv-motor-v2\Scripts\python.exe`.

## 2. Auditoria completa (somente na máquina com a base local)

Depende de `D:\NUCLEO_BDGD_2025` (caminhos fixos no código de `motor_v2/`, que é ferramenta local) e dos resultados nacionais já calculados em `D:\NUCLEO_BDGD_2025\motor_v2\nacional`. Interpretador: `D:\NUCLEO_BDGD_2025\motor_v2\.venv` (Python 3.12.2, scikit-learn 1.9.1, DuckDB 2.0.0, pyarrow 26.0.0).

```bash
cd nucleo-dados-bdgd
D:/NUCLEO_BDGD_2025/motor_v2/.venv/Scripts/python.exe -m motor_v2.nacional.testes
```

Resultado esperado: 243 testes, 243 OK. A matriz fica em `D:\NUCLEO_BDGD_2025\motor_v2\nacional\testes\MATRIZ_TESTES.csv`.

## 3. Regenerar a reconciliação e os relatórios (sem retreinar nada)

Estes passos **só leem** os resultados nacionais já calculados. Não treinam modelos, não repetem os candidatos de ML e não tocam produtos públicos.

```bash
cd nucleo-dados-bdgd
PY=D:/NUCLEO_BDGD_2025/motor_v2/.venv/Scripts/python.exe
$PY -m motor_v2.nacional.hierarquia           # reconciliação UCBT ⊂ Consumidores; falha se houver violação ou par ausente/duplicado
$PY -m motor_v2.nacional.erro_retrospectivo   # erro ponta a ponta (diagnóstico, não validação)
$PY -m motor_v2.nacional.fonte_canonica       # declara o contrato da fonte canônica interna
$PY -m motor_v2.nacional.verificacoes         # integridade, hashes e produtos públicos
$PY -m motor_v2.nacional.consolidar --repo-copy motor_v2/reports/nacional   # cópia compacta para o repositório
```

Cada passo é idempotente: executá-lo duas vezes produz arquivos de saída com SHA-256 idêntico.

**Conferências:** `VERIFICACOES_INTEGRIDADE.json` com `ok: true`; `CONTRATO_HIERARQUIA_CONSUMIDORES.json` com `violacoes_remanescentes: 0` e `pares_por_dist_exigidos: 15`; `FONTE_CANONICA_CONSUMIDORES_INTERNA.json` com 1.545 linhas e 103 DIST.

## 4. O que **não** é reproduzido aqui

A extração das publicações BDGD, a montagem do painel e os comparativos de ML (≈ 20 mil candidatos) levaram, medidos na execução nacional, ≈ 2,8 h de extração e ≈ 2,0 h de comparativos na máquina local, e dependem da base. Eles foram executados uma vez e **não são repetidos**. O PR traz apenas o código, os testes, a metodologia e os relatórios compactos (CSV e JSON; nenhum Parquet).

## 5. O que o PR não carrega

- Nenhum Parquet nem arquivo grande: os maiores relatórios têm ≈ 2 MB e, acima de 4 MB, são compactados com `gzip` determinístico.
- Nenhum caminho local é exigido pelo deploy.
- Os Parquets internos (`PROJECOES_*_INTERNO.parquet`, `PROJECOES_CONSUMIDORES_RECONCILIADAS.parquet`) ficam apenas em `D:\NUCLEO_BDGD_2025\motor_v2\nacional`. O equivalente compacto da fonte canônica é `reports/nacional/PROJECOES_CONSUMIDORES_RECONCILIADAS.csv`.
