# Estado de execução — Núcleo de Dados da BDGD

Atualizado pelo Claude durante a Fase A (dashboard e dados 2025). Datas no fuso de Brasília.

## Fase A — BDGD 31/12/2025

| Item | Estado |
|---|---|
| Inventário ANEEL (ArcGIS, paginação completa) | 99 GDB com DATA_BASE 2025-12-31, todos públicos; 15 DIST históricos sem publicação 2025 |
| ETL por DIST (`etl/bdgd2025/run_lote.py`) | em andamento, em lotes de 4, do menor para o maior; checkpoints em `D:\NUCLEO_BDGD_2025\proc\DIST=*\_OK`; nenhuma falha de reconciliação até aqui |
| Facetas exatas e cubos conjuntos (`75_facetas_exatas.py`) | em andamento para os DIST concluídos |
| Pacote 1.1.0 (`80_monta_pacote.py`) | parcial, validado pelo `validate-publication.mjs` (estrutural OK) |
| Grupos econômicos | 11 grupos com fonte oficial (49 DIST); demais `nao_confirmado` |
| Dashboard (`web/`) | Panorama, Matriz, Comparador, Entidades e DDA, Metodologia, Previsões (planejamento); 16 testes unitários e 9 E2E passando; CI verde |
| Vercel | projeto novo `nucleo-dados-bdgd` (Hobby, sem custo), separado do `geoia-data-hub`; previews por push na branch; produção só com release homologado |

## Retomada (comando único)

```bash
cd D:/NUCLEO_BDGD_2025 && .venv/Scripts/python -I scripts/run_lote.py --tam 4 && .venv/Scripts/python -I scripts/75_facetas_exatas.py && .venv/Scripts/python -I scripts/80_monta_pacote.py
```

Depois: `node repo/nucleo-dados-bdgd/etl/validate-publication.mjs output-publicavel/2025-12-31`, `85_assets_web.py`, `npm run build` e `npx playwright test` em `web/`.

## Processo histórico 2022–2024 (Codex)

O runner `historico/run.py --wait` em `D:\NUCLEO_BDGD_2022_2024` processa apenas arquivos pequenos enquanto o ETL 2025 está ativo. Ele aceita parada segura por `STOP_REQUESTED` (checkpoints preservados). A retomada e a pesquisa de sucessões fazem parte da Fase B.
