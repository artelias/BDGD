# Motor V2 — como reproduzir (2026-10-31)

O Motor V2 é **ferramenta local de pesquisa**, sem passo de deploy. O dashboard e os produtos públicos não leem nada de `motor_v2/`, e nenhum artefato daqui é exigido pelo deploy. Os resultados nacionais continuam **internos e experimentais**, sem homologação científica.

## 0. Onde cada suíte roda (fonte única: `motor_v2/tests/suites.py`)

| Grupo | Suítes | Comando | Onde |
|---|---|---|---|
| `SINTETICAS` | 13 (163 testes) | `python -m motor_v2.tests.suites` | qualquer máquina; GitHub Actions (`motor-v2-sintetico.yml`) |
| `LOCAIS` | 8 (93 testes) | `python -m motor_v2.nacional.testes` (roda **todas** as suítes) | só na máquina com a base local |
| `PUBLICAS` | `test_public_audit` | workflow da web do PR #19 | auditam os produtos públicos reais; chegam com o #19 |
| Dashboard | Node/Playwright | — | Codex; fora do Motor V2 |

`python -m motor_v2.tests.suites --listar` mostra a classificação. `test_suites` reprova:
- arquivo de teste sem grupo;
- nome em dois grupos;
- suíte listada mas ausente;
- workflow que descubra todas as suítes sem filtro.

O runner também reprova uma suíte que não carregue nenhum teste.

## 1. Testes sintéticos (qualquer máquina, Linux inclusive, sem dados locais)

É exatamente o que o CI roda. Sem acesso a `D:\`, à base BDGD ou à rede.

```bash
cd nucleo-dados-bdgd
python3 -m venv .venv-motor-v2
.venv-motor-v2/bin/python -m pip install -r motor_universal/requirements.txt -r motor_universal/requirements-ml.txt duckdb==2.0.0 pyogrio==0.13.0
.venv-motor-v2/bin/python -m motor_v2.tests.suites
```

No Windows, troque `.venv-motor-v2/bin/python` por `.venv-motor-v2\Scripts\python.exe`.

**Emulação do CI na máquina local** (prova de que nenhuma suíte sintética depende de `D:\`):

```bash
python -m motor_v2.tests.emular_ci
```

O emulador:
- copia o código para um diretório temporário fora do disco de dados;
- bloqueia toda leitura sob `D:/` (só o interpretador e seus `site-packages` continuam legíveis, como o venv do Actions);
- verifica que o bloqueio está ativo antes de rodar.

Ele aceita outro comando, por exemplo para avaliar um passo de workflow:

```bash
python -m motor_v2.tests.emular_ci --incluir web/public/data --incluir motor_cenarios -- -m unittest discover -s motor_v2/tests -p test_public_audit.py
```

## 2. Auditoria completa (somente na máquina com a base local)

Depende de `D:\NUCLEO_BDGD_2025` (caminhos fixos no código de `motor_v2/`, que é ferramenta local) e dos resultados nacionais já calculados em `D:\NUCLEO_BDGD_2025\motor_v2\nacional`.

**Interpretador:** `D:\NUCLEO_BDGD_2025\motor_v2\.venv` (Python 3.12.2, scikit-learn 1.9.1, DuckDB 2.0.0, pyarrow 26.0.0). Esse venv carrega parte dos pacotes (DuckDB, psutil) de `D:\NUCLEO_BDGD_2022_2024\.venv` por `.pth`; as versões efetivas ficam em `MANIFESTO_TESTES.json`.

**Gerador público:** `motor_cenarios/cenarios.py` (PR #19) deve rodar com scikit-learn **1.8.0** (`motor_universal/requirements-ml.txt`, por exemplo `D:\NUCLEO_BDGD_2025\.venv-motor`). Com 1.9.1 o HistGradientBoosting diverge do produto publicado.

```bash
cd nucleo-dados-bdgd
D:/NUCLEO_BDGD_2025/motor_v2/.venv/Scripts/python.exe -m motor_v2.nacional.testes
```

Resultado esperado: **256 testes, 256 OK** (163 sintéticos e 93 locais). A matriz fica em `D:\NUCLEO_BDGD_2025\motor_v2\nacional\testes\MATRIZ_TESTES.csv`, com o grupo de cada teste.

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

**Cobertura definitiva e potência (2026-11-01).** Só a classificação dos reguladores e `potencia_b` leem ou ajustam algo novo, e só para as séries de potência:

```bash
$PY -m motor_v2.nacional.reguladores          # convencao propria/passante por registro (EQRE x UNREMT x CTMT), ~1 min
$PY -m motor_v2.nacional.potencia_b           # TUC 570 kVA e reguladores kVA no nivel B, mesma selecao e cenarios, ~4 min
$PY -m motor_v2.nacional.cobertura --verificar-na   # matriz DIST x objetivo x metrica (x ano x cenario); confere NA nos Parquets
$PY -m motor_v2.nacional.exportar_web --saida web/data-motor-v2   # produto compacto do dashboard (portao de homologacao)
$PY -m motor_v2.nacional.consolidar --repo-copy motor_v2/reports/nacional
```

Cada passo é idempotente: executá-lo duas vezes produz arquivos de saída com SHA-256 idêntico.

**Conferências:**
- `VERIFICACOES_INTEGRIDADE.json` com `ok: true`;
- `CONTRATO_HIERARQUIA_CONSUMIDORES.json` com `violacoes_remanescentes: 0` e `pares_por_dist_exigidos: 15`;
- `FONTE_CANONICA_CONSUMIDORES_INTERNA.json` com 1.545 linhas e 103 DIST.

## 4. O que **não** é reproduzido aqui

A extração das publicações BDGD, a montagem do painel e os comparativos de ML (≈ 20 mil candidatos) dependem da base. Medidos na execução nacional, levaram ≈ 2,8 h de extração e ≈ 2,0 h de comparativos na máquina local. Eles foram executados uma vez e **não são repetidos**.

O PR traz apenas o código, os testes, a metodologia e os relatórios compactos (CSV e JSON; nenhum Parquet).

## 5. O que o PR não carrega

- Nenhum Parquet nem arquivo grande: os maiores relatórios têm ≈ 2 MB e, acima de 4 MB, são compactados com `gzip` determinístico.
- Nenhum caminho local é exigido pelo deploy.
- Os Parquets internos (`PROJECOES_*_INTERNO.parquet`, `PROJECOES_CONSUMIDORES_RECONCILIADAS.parquet`) ficam apenas em `D:\NUCLEO_BDGD_2025\motor_v2\nacional`. O equivalente compacto da fonte canônica é `reports/nacional/PROJECOES_CONSUMIDORES_RECONCILIADAS.csv`.
- Nenhum arquivo fora de `motor_v2/` além do workflow sintético: os produtos públicos e o dashboard ficam com os PRs #19 e #20 e com o Codex.
