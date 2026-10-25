# Pendências não recuperáveis — BDGD 2022–2025 (Fase 6)

Universo: 114 códigos de distribuidora × 4 anos × 25 ativos = **11.400 células** (`INVENTARIO_LACUNAS_NACIONAL.csv`). Nenhuma lacuna vem de falha técnica corrigível: os 414 ZIPs locais têm SHA-256 conferido e abrem (`evidencias/integridade_downloads.csv`); não há GDB não processado, falha de ETL nem valor do Parquet ausente do site.

## 1. Não recuperáveis por falta de publicação oficial (275 células · 11 DIST-ano)
O catálogo ANEEL/ArcGIS (1.014 itens, consulta de 25/10/2026, sem itens novos ou alterados desde 23/10) não tem item 31/12 para:

| DIST | Distribuidora | Anos sem publicação | Publicações existentes |
|---|---|---|---|
| 5351 | Ceral Anitápolis | 2022, 2023, 2024 | 2017–2019 e 2025 |
| 7467 | Cemirim | 2022 | 2023–2025 |
| 2351 | Coprel | 2024 | 2016–2020, 2022, 2023, 2025 (o arquivo "2022" tem BASE 06/03/2024 degenerada) |
| 2904 | Cooperaliança | 2024, 2025 | até 2023 |
| 5274 | Ceres | 2024, 2025 | até 2023 |
| 5279 | Cerci | 2024, 2025 | 2022–2023 |

Ação possível: solicitar à ANEEL/distribuidora. Nenhum valor é preenchido.

## 2. Sucessões societárias — não são lacunas (1.150 células)
- **Incorporadas antes de 2022:** CPFL Mococa (70), CPFL Leste Paulista (71), CPFL Santa Cruz antiga (72), CPFL Sul Paulista (73), CNEE (75), CFLO (84), EEB (386) e EDEVP (5217), com última publicação em 2016–2017 e perímetro na CPFL Santa Cruz (69). A RGE (397) publica até 2018, e o perímetro está na RGE Sul (396). A Cejama 6896 vai até 2017 e foi recodificada para 5372.
- **EBO (6611) após 2022 e ENF (6612) após 2022:** incorporadas à EPB (6600) e à EMR (6585). A ENF 2022 já está contida na EMR e fica fora de qualquer soma. A ponte EBO → EPB segue pendente (ver parecer).

## 3. Bloqueio por competência (300 células · 12 DIST-ano)
Os arquivos publicados com BASE de outra competência foram comparados camada a camada com a publicação do ano declarado na BASE (`evidencias/comparacao_gdbs.csv`) e testados pela posição temporal do conteúdo (`evidencias/posicao_temporal_excluidos.csv`):
- nenhum é cópia integral (7 a 39 de 43 camadas idênticas);
- Cermoful, Cetril e Ceral Araruama (2023): o conteúdo é igual ao do ano da BASE (2024), ou seja, são outra versão de 2024 e não existe dado de 2023 no catálogo;
- Chesp, Certaja e Coopercocal (2023): inconclusivo; nos arquivos com título 2022, não há publicação válida de 2021 para comparar;
- Cemig-D 2022: período 01/01–30/11/2022; Celetro 2022: 01/09/2022–31/08/2023; Coprel: datas degeneradas.

Nenhum tem evidência suficiente para reatribuir o ano. **Permanecem excluídos.**

## 4. Ativo não aplicável (623 células)
A entidade não existe no GDB da DIST (por exemplo, distribuidoras sem rede de alta tensão) ou não há segmentos do tipo. N/D, nunca zero.

## 5. Dependem de decisão humana (354 células)
| Causa | Células | Casos |
|---|---|---|
| Republicações divergentes | 325 | 13 pares (2 em 2022, 11 em 2023). As duas publicações de cada par têm intervalo anual 01/01–31/12 e nenhuma tem tag `Extra`; versões distintas do mesmo arquivo anual. A data de criação do item no catálogo (recriação em lote, 10/2025) não comprova substituição oficial. **Nenhuma versão foi escolhida.** |
| BASE inconsistente | 25 | Coprel 2023 (`DAT_INC = DAT_FNL = DAT_EXT = 31/12/2023`) |
| Entidade vazia na origem | 3 | Coopera (UCBT) e Equatorial GO (UGBT/UGAT) em 2025; Certel (EQTRM) em 2025 |
| Publicação incompleta na origem | 1 | Cooperzem, iluminação 2024 (comprovado por identidade de COD_ID) |

## 6. Intervalos não anuais (6 publicações em uso, sem impacto nos valores)
`DAT_FNL` = 31/12, título 31/12, extração logo após o fechamento e demais anos da mesma DIST com 01/01–31/12. Os 25 ativos são estoques referidos ao `DAT_FNL`:
- Equatorial GO 2022 e Amazonas 2022: `DAT_INC` = 01/12 do próprio ano (um mês);
- Enel SP 2022 e 2025, EDP ES 2024 e EDP SP 2024: `DAT_INC` = 01/12 do ano anterior (13 meses).

Explicação plausível: preenchimento do `DAT_INC`. Não há indício de base extraordinária. Permanecem `APTO_COM_RESSALVAS` até decisão.
