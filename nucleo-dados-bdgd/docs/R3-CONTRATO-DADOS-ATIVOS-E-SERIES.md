# R3 — Contrato de dados: ativos, cubos, inventários e séries 2022–2025

**Responsável pelo esquema:** Claude (PR #4, branch `feat/dashboard-bdgd-2025`). **Consumidores:** Explorar, Matriz, Comparador e Evolução (PR #4); Panorama e Motor de Expansão Elétrica (ChatGPT, PR #6). Este documento define as dependências de integração. O PR #6 **não precisa recalcular nada**: basta ler os arquivos e usar as funções abaixo.

## 1. Catálogo semântico único

- Fonte: `etl/bdgd2025/config/conceitos_2025.json`, copiado no pacote (`output-publicavel/2025-12-31/conceitos/catalogo.json`) e no índice web (`index.json → conceitos`).
- `conceitos`: entidades de origem, vínculos, dimensões (DDA/MCPSE/IBGE), medidas e cubos.
- `ativos`: recortes nomeados (id, nome, conceito, filtro, medida, explicação, cálculo técnico, ressalva). São os mesmos ids da Matriz, do Comparador e da Evolução.
- `kpis_padrao`: os **10 KPIs** pedidos para o Panorama, na ordem `consumidores, rede_mt, rede_bt, rede_at, trafo_dist, trafo_forca, subestacoes, alimentadores, medidores, iluminacao`.
- `menu`: navegação por conceitos clicáveis do Explorar.

## 2. Totais por ativo (2025)

- Pacote: `ativos_totais.csv` (`dist, data_base, ativo, conceito, medida, unidade, valor, status, motivo`).
- Web: `index.json → ativosTotais[ativo][medida] = [[dist, valor, status, motivo], …]`; status `a` aprovado, `l` alerta, `b` bloqueado, `n` ativo inexistente.
- API: `totalAtivo(ds, id, dists, medida?)` em `web/src/lib/ativos.ts` devolve `{v, n, nd, ausentes, total, alerta, partial}`, com a mesma semântica de `Dataset.aggregate`.
- O validador do pacote recalcula os 2.562 totais a partir dos cubos e confere os ativos de entidade única com o fato-base R2.

**Dependência para o Panorama (ChatGPT):** o KPI de consumidores do R2 (`lib/kpis.ts`, união de COD_ID pela regra v2, com 14 distribuidoras N/D) foi substituído no catálogo pela **regra UC v3**:
- **Unidade:** chave (COD_ID anonimizado SHA-256, PN_CON), somente `SIT_ATIV = AT`, unida entre UCBT/UCMT/UCAT.
- **Resultado:** 90.252.218 unidades ativas nas 99 distribuidoras, nenhuma N/D. Evidências em `qa_uc_regra_v3.csv` e na seção 4.

Para os 10 KPIs, recomenda-se ler `ativosTotais` por `totalAtivo(ds, id, dists)` em vez de `kpiValue`. `lib/kpis.ts` e `Panorama.tsx` não foram alterados pelo Claude.

## 3. Cubos por conceito (filtros exatos)

- Pacote: `conceitos/cubos.csv` (`dist, conceito, cubo, entidade, chave(JSON na ordem das dimensões), quantidade, extensao_km, potencia_kva`).
- Web: `conceitos/<conceito>.json`, com dicionário de códigos por dimensão, rótulos, `a1PorTuc` e linhas `[dist, …índices, …medidas]`. Na potência, `-1` significa medida não aplicável àquela entidade (ex.: transformador de medida). Não é zero nem N/D.
- Motor: `web/src/lib/cubo.ts` (`agregar`, `agregarPorDist`, `distribuicao`, `porDistPorCategoria`, `participacao`). Um recorte só é respondido por um cubo que contenha todas as dimensões filtradas. Nunca há multiplicação de percentuais.

## 4. Regra UC v3 (evidências)

- COD_ID de UC publicado pela ANEEL como SHA-256 (64 hex) em 2022, 2023, 2024 e 2025: hash igual significa código igual.
- Copel (2866): registros "Ativada" repetidos têm o mesmo ponto de conexão, município, alimentador e data de conexão, mudando só a classe. É a mesma UC e conta uma vez (5.152.731).
- DIST 5160: repetições com ponto de conexão (99,5%), alimentador (81%) e data (99,4%) diferentes. São ligações distintas sob o mesmo código e contam pela chave (1.219.651).
- Distribuidoras sem repetição: v3 = códigos distintos ativados.

## 5. Inventários (conectividade elétrica 2025)

- `inventario/subestacoes.csv`, `alimentadores.csv`, `circuitos_at.csv`, `conjuntos.csv`, e na web `inventario/<dist>.json`.
- Cada objeto tem código e nome de infraestrutura publicados na BDGD e contagens por vínculo oficial: UC/UG/SSD/PIP pelo campo do registro; EQ* pela instalação UN* deduplicada por código.
- Linhas `SEM_VINCULO` / `SEM_CODIGO` mantêm os totais auditáveis.

## 6. Séries 2022–2025 (insumo do Motor de Expansão)

Pasta `output-historico/2022-2025/` (validada por `etl/validate-serie-historica.mjs` no CI) e `web/public/data/historico/serie.json`:

| Arquivo | Conteúdo |
|---|---|
| `serie_ativos_original.csv` | DIST × ano × ativo, publicação original: valor (só se `validado`), estado, motivo, comparabilidade (`comparavel` / `quebra_classificacao`), item ArcGIS e SHA-256 da fonte, versão da regra |
| `serie_ativos_perimetro_2025.csv` | mesma grade no perímetro de 2025 (predecessoras somadas só com prova de disjunção por CONJ e absorção no ano seguinte); comparabilidade `quebra_perimetro` quando há evento |
| `populacao_conceitos.csv` | população de cada conceito e parcela sem TUC do MCPSE por DIST/ano (base da marca de quebra de classificação) |
| `eventos_sucessao.csv`, `ponte_perimetro_2025.csv`, `qa_sucessao.csv` | EPB(6600) ← EBO(6611) e EMR(6585) ← ENF(6612), com fontes oficiais e prova por conjuntos |
| `cobertura_por_ano.csv`, `manifest.json` | publicadas, validadas e pendentes por ano; ano `homologado` só sem pendências |

**Estados:** `validado`, `ausente` (ativo inexistente: N/D, nunca zero), `campo_ausente`, `bloqueado`, `revisao_pendente` (mais de uma publicação válida no ano), `nao_processado`, `competencia_divergente`, `sem_publicacao`.

**Para previsões:** usar somente células `validado` e `comparavel`. Tratar `quebra_classificacao` e `quebra_perimetro` como quebra estrutural, não como crescimento. Equipamentos (ativos TUC) e instalações (UNTRMT/UNTRAT no fato-base) ficam em linhas separadas e nunca são somados. Grupos econômicos em 2022–2024 usam a composição de 2025, identificada como tal.

## 7. Arquivos sob responsabilidade de cada PR

- **Claude (PR #4):** catálogo, ETL 77/78/79/80/85, validadores, `lib/{cubo,ativos,escopo,matriz,comparador,evolucao}.ts`, Explorar, Matriz, Comparador, Evolução, `e2e/r3.spec.ts`.
- **ChatGPT (PR #6):** `Panorama.tsx` e estilos, `lib/kpis.ts`, `lib/panorama-r3.ts`, IASC, Previsões, Metodologia e Design.
- **Compartilhados com mudança mínima:** `e2e/app.spec.ts` (o PR #4 removeu os testes do Explorar/Matriz/Comparador/Evolução R2 superados e os substituiu em `e2e/r3.spec.ts`), `e2e/a11y.spec.ts` (rotas), `lib/types.ts` e `lib/data-context.tsx` (apenas acréscimos).
