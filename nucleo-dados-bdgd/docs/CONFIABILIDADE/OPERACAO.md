# Operação: comandos, atualização, nova distribuidora

Ambientes (Windows, fora do repositório):

* ETL: `D:/NUCLEO_BDGD_2025/.venv/Scripts/python.exe` (Python 3.12, duckdb, pyarrow, shapely, pyproj).
* Estatística e testes Python: `D:/NUCLEO_BDGD_2025/.venv-motor/Scripts/python.exe` (numpy, scipy, scikit-learn, duckdb).
* Exporte `PYTHONUTF8=1`. Rode tudo a partir de `nucleo-dados-bdgd/` (pacote `confiabilidade`).
* Pasta de trabalho: `D:/NUCLEO_BDGD_2025/confiabilidade` (variável `CONF_TRABALHO`). Nada vai para `C:`.

## Atualização completa (novo arquivo da ANEEL, mesma BDGD)

```bash
PY=D:/NUCLEO_BDGD_2025/.venv/Scripts/python.exe
$PY -m confiabilidade.aneel baixar          # só baixa se o last_modified do CKAN mudou
$PY -m confiabilidade.aneel preparar        # falha (sem gravar) se houver conflitos de valor ou de limite
$PY -m confiabilidade.publicar              # ~45 s; monta em pasta temporária, valida, troca atômica
D:/NUCLEO_BDGD_2025/.venv-motor/Scripts/python.exe -m confiabilidade.estatistica --reamostras 300   # ~6 min
$PY -m confiabilidade.auditoria             # deve terminar com "falhas": []
```

A infraestrutura **não** precisa ser recalculada quando só a ANEEL muda: `infra.py` é idempotente por assinatura (versão do
código + identidade e tamanho dos Parquets lidos) e as 379 cargas DIST × ano já processadas são reaproveitadas.

## Nova competência da BDGD (ex.: 2026)

1. Converter a BDGD do ano pelo pipeline do Núcleo (fora deste módulo).
2. Incluir o ano em `contrato.ANOS` (usado por `aneel.preparar`, `infra`, `publicar` e `estatistica`).
3. Ajustar `infra.resolver_fonte` (hoje: 2025 em `CONF_STAGING_2025`, `DATA_BASE=2025-12-31`; 2022–2024 em
   `CONF_PARQUET_HIST`, conforme a publicação do contrato nacional) para localizar os Parquets do novo ano.
4. `$PY -m confiabilidade.infra --todas` (só as cargas novas ou alteradas são processadas).
5. Geometria: `geo.py` lê a camada CONJ de `DATA_BASE=2025-12-31`; para usar uma delimitação mais nova, troque a data-base
   (caminho e `meta.data_base`) e rode `$PY -m confiabilidade.geo --todas`.
6. `publicar`, `estatistica`, `auditoria`, testes.

## Nova distribuidora (ou distribuidora que faltava)

1. Confirme que os Parquets da BDGD da distribuidora existem (`infra.dists_disponiveis()` lista as que têm
   `conversao.json` em 2025).
2. `$PY -m confiabilidade.infra --dist <DIST>` e `$PY -m confiabilidade.geo --dist <DIST>`.
3. `$PY -m confiabilidade.publicar`. Cada (conjunto, ano) da ANEEL é atribuído à distribuidora primeiro pelo código CONJ da
   BDGD do próprio ano e depois pelo CNPJ do agente; um código isolado que coincide com o de outro agente não transfere o
   conjunto (regra da metade dos códigos). Os casos ficam na auditoria do produto (`aneel_sem_distribuidora`,
   `codigo_de_outro_agente`, `bdgd_fora_da_aneel`).
4. Rode a auditoria e confira a reconciliação da nova empresa em `auditoria/RECONCILIACAO_POR_DIST_ANO_INDICADOR.csv`.
5. Rode a estatística (a amostra muda) e os testes.

## Testes e verificação

```bash
PYTHONUTF8=1 D:/NUCLEO_BDGD_2025/.venv-motor/Scripts/python.exe -m unittest discover -s confiabilidade/tests -t .
cd web && npm run typecheck && npm run lint && npm run test && npm run build
cd web && npm run e2e                                    # suíte completa, ~40 min, serve o out/ na porta 3211
cd web && npx playwright test e2e/confiabilidade.spec.ts # só o módulo
```

Desenvolvimento: `npm --prefix web run dev` (porta 3210 no perfil `bdgd-confiabilidade`). O `node_modules` do worktree
precisa estar **dentro** do worktree (cópia, não junção): o Turbopack não resolve `next` fora da raiz do projeto (causa do
HTTP 500, ver RELATORIO_FINAL.md).
