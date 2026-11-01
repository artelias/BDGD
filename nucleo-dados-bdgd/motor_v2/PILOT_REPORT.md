# Piloto controlado de UCBT — 28/10/2026

Execução completa: `D:/NUCLEO_BDGD_2025/motor_v2/runs/e37812185a2af670`.

| DIST | Empresa | 2022 | 2023 | 2024 | 2025 |
|---|---|---:|---:|---:|---:|
| 6600 | EPB | 1493479 | 1694626 | 1665108 | 1897891 |
| 6585 | EMR | 586611 | 571557 | 560820 | 600066 |
| 26 | EAC | 274522 | 264468 | 272668 | 294711 |

Contagens de UCBT ativas pela chave COD_ID + PN_CON, cobertura de identidade 100%. Conflitos territoriais: EPB/2022=16; EMR/2023=1; demais células=0. A precedência UC-v3 foi aplicada e os conflitos permanecem no QA. Não interpretar variações como expansão física sem análise de perímetro/sucessão.

Nenhum fold retrospectivo elegível: os arquivos históricos disponíveis foram publicados/revisados em outubro de 2025; a competência 2025 foi disponibilizada em setembro de 2026. Não foram usados como se estivessem disponíveis em 2023/2024. Persistência é fallback, não vencedor estatístico. Há 45 linhas exploratórias (3 empresas × 5 anos × 3 cenários neutros), sem intervalos probabilísticos. Ano 2026 é projeção intranual condicionada ao corte de outubro/2026.

O bundle `bdgd-parquet-2` foi escrito e relido com os validadores existentes, com objetivo UCBT explicitamente separado de consumidores totais. A primeira execução com chave COD_ID isolada foi invalidada em `runs/4d49451d3c35e349/SUPERSEDED.json`.

Testes: 9 testes V2 + 8 testes existentes de contrato Parquet aprovados. O ambiente dedicado tem versões fixadas em requirements.lock.txt. Os originais e a produção não foram alterados. O treinamento nacional não foi executado.

## Limites desta entrega

Infraestrutura e piloto UCBT funcionam de ponta a ponta. Não estão concluídos: integração da busca granular com seleção nacional/pares/individual, binomial negativa/hierárquico/duas etapas, ablação/permutação, validação da continuidade de UCs, extratores de todo o catálogo no executor e ingestão oficial externa versionada. Os adapters adicionais e o módulo de busca são componentes preparatórios; não representam as fases C e o ML completo concluídos. Ver README para o estado preciso de cada componente.
