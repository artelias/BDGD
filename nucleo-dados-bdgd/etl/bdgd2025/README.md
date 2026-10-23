# ETL BDGD 31/12/2025 — pipeline local

Pipeline que gera o pacote público `output-publicavel/2025-12-31/` (contrato **1.1.0**) a partir dos File Geodatabases oficiais da ANEEL com `DATA_BASE = 2025-12-31`. Roda em máquina local (Windows, ~8 GB RAM, HD para staging). Nada bruto sai da máquina: GDB, ZIP e Parquet ficam no staging privado.

## Etapas e scripts

| Ordem | Script | O que faz |
|---|---|---|
| 1 | `01_inventario.py` | Varre a API ArcGIS do órgão (owner `aneel_aneel`, todos os itens File Geodatabase, paginação completa). |
| 2 | `02_sonda_download.py` | HTTP HEAD em `/sharing/rest/content/items/<id>/data`: tamanho real, `Accept-Ranges`. |
| 3 | `03_gera_inventario.py` | `inventario_2025.csv` + `cobertura_2025.json` (99 GDB 2025, 15 DIST históricos sem 2025). |
| 4 | `run_lote.py` + `bdgd_etl.py` | Por DIST, com checkpoint: download retomável + SHA-256 + teste do ZIP → validação `BASE.DAT_FNL = 31/12/2025` e `DIST` em todas as camadas → Parquet de staging (lotes de 65.536 linhas) → `DATA_BASE` linha a linha → totais, vínculos IA Builder, DDA, regras de UC/potência, ARAT → reconciliação com leitura independente do GDB. Falhas vão para quarentena (`_FALHA.json`) sem parar o lote. |
| 5 | `75_facetas_exatas.py` | Facetas DDA de 1 dimensão + cubos conjuntos curados (2 dimensões) com somas em `DECIMAL(38,6)` — categorias reconciliam exatamente com o total. |
| 6 | `80_monta_pacote.py` | Pacote 1.1.0: fato-base, facetas + catálogo de rollup, matriz, distribuidoras, grupos com fonte, DDA, QA, homologação por métrica, ARAT, manifesto com checksums. Aplica a **regra UC v2**. |
| 7 | `85_assets_web.py` | JSON compacto para o site a partir do pacote validado (sem acesso ao staging). |

Pilotos históricos (superados por `bdgd_etl.py`) estão em `piloto/`, para auditoria.

## Regras implementadas

- **Competência única** 2025-12-31; DIST sem GDB 2025 fica `sem_publicacao_2025` (nunca preenchido com outro ano).
- **UC v2:** `COUNT(DISTINCT COD_ID)` é a quantidade homologada quando não há COD_ID nulo, `SIT_ATIV ∈ {AT, DS}` e no máximo um registro ativado por COD_ID (repetições AT+DS são histórico de estado no ano). Fora disso: quantidade N/D, registros e distintos publicados.
- **Potência:** `UNTRMT.POT_NOM` (kVA), `UNTRAT.POT_NOM` (MVA × 1000), `EQ*.POT_NOM` via DDA `TPOTAPRT`. Unidade e equipamento nunca são somados; divergência > 5% e `POT_NOM` aparentemente em MVA viram alerta (valor preservado).
- **Geração UG\*:** contagem publicada; potência N/D (POT_INST sem semântica comprovada; SIGFI; > 75 kW em BT). Sem corte artificial.
- **Filtros:** vínculo `*.CTMT/SUB/CONJ` com > 5% de órfãos → filtro `indisponivel_por_qualidade` para o DIST.
- **ARAT:** somente a entidade ARAT do GDB; LAEA local (equivalente) para medir e simplificar com tolerância adaptativa (≤ 100 m, |Δárea| ≤ 0,1%), saída EPSG:4326.
- **Grupos:** `config/grupos_2025.json` — controlador vigente em 31/12/2025 com fonte; sem fonte → `nao_confirmado` (fora de somas de grupo).

## Execução

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
set BDGD_ROOT=D:\NUCLEO_BDGD_2025          # staging local
set BDGD_KNOWLEDGE=C:\GEOIA\GEOIA_DATA_HUB\knowledge   # catálogos IA Builder (relacionamentos, DDA M10, schema Rev.5)
.venv/Scripts/python -I run_lote.py --tam 4          # retoma do checkpoint; pula DIST com _OK
.venv/Scripts/python -I 75_facetas_exatas.py
.venv/Scripts/python -I 80_monta_pacote.py
node ../validate-publication.mjs %BDGD_ROOT%/output-publicavel/2025-12-31
.venv/Scripts/python -I 85_assets_web.py %BDGD_ROOT%/output-publicavel/2025-12-31 ../../web/public/data <natural_earth_dir>
```

Requisitos de recurso: lotes de 3–5 DIST do menor para o maior; o driver pausa se o disco livre ficar abaixo de 150 GB ou de 6× o maior ZIP do lote. DuckDB com `memory_limit=3GB`, `threads=2` e spill em disco.
