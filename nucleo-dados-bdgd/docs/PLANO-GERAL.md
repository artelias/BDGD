# Plano geral — Núcleo de Dados da BDGD

## 1. Objetivo e escopo

Portal nacional, público e sem autenticação, que reaproveite as definições metodológicas do BI VPE de 2024, mas sem exigir paridade de resultados (o portal tem base 2025), incluindo grupo econômico, mantendo a navegação interativa por empresa, família e atributos DDA, e adicionando mapa ARAT nacional.

**Regras de produto**: filtros descritivos (não códigos BDGD), sem dados brutos no browser, **somente `DATA_BASE = 31/12/2025`** para toda distribuidora elegível, sem usar anos anteriores ou posteriores como alternativa, métricas e grandezas explícitas, comparações auditáveis, acessibilidade e tema claro/escuro.

## 2. Restrições não negociáveis

- No frontend apenas endpoints com respostas agregadas e GeoJSON simplificado da ARAT; **nunca** carregar GDB, SHP ou Parquets brutos.
- Nenhum `COD_ID` exposto por padrão. Chaves compostas `DIST + COD_ID` (e `DATA_BASE` no escopo temporal), especialmente em junções.
- Não somar métricas heterogêneas (km, MVA, quantidades) e não somar `DISTINCT COUNT` entre agrupamentos que se sobrepõem.
- Não agregar antes de eliminar N:N indevidos e definir nível de granularidade por fato.
- Não exibir rótulos de domínio sem a versão do catálogo DDA de origem.
- Escopo temporal inicial estrito: **31/12/2025**. Não inserir 2024/2026, mesmo que a empresa só possua esses anos; registrar ausência 2025 como cobertura não disponível.
- Publicação e atualização do arquivo não equivalem à data-base: confirmar `DATA_BASE` no arquivo/metadado e validar conteúdo.
- Grupo econômico é temporal: controlar controlador vigente em cada data-base.

## 3. Stack decidida

| Camada | Produção |
|---|---|
| Web | Next.js + TypeScript + React, Lucide, Tailwind/CSS |
| Gráficos | Apache ECharts |
| ARAT | MapLibre GL + GeoJSON simplificado/tiles |
| Infraestrutura web | Vercel, app público |
| Banco | PostgreSQL + PostGIS gerenciado no Supabase, somente agregados no schema público |
| Backend | Rotas server-side Next.js, validação, filtros paginados, cache |
| ETL | Python, GDAL/OGR, DuckDB, Polars, SQL |
| Orquestração | Pipeline versionado fora do runtime do site (máquina corporativa/runner autorizado) |
| Controle | GitHub, CI com testes de integridade / Vercel Git deploy |
| Armazenamento geográfico | CDN/static para polígonos e tiles publicados |

> Banco Supabase e projeto Vercel não estão provisionados. Não habilitar custos sem aprovação.

## 4. Contratos da API (futura)

- `GET /api/v1/manifest` — snapshot e versões por `DIST`.
- `GET /api/v1/distribuidoras` — empresas e grupos associados à data-base.
- `GET /api/v1/filtros?familia=X&...` — valores DDA, descrições, contagens e cascata.
- `GET /api/v1/kpis?dist=&grupo=&familia=&filtros=...` — métricas nacionais/contextuais.
- `GET /api/v1/ativos?pagina=1&tamanho=50&...` — matriz completa por distribuidora.
- `GET /api/v1/comparacao?tipoA=&idA=&tipoB=&idB=&...` — entidade, valorA, valorB, diferença, percentual.
- `GET /geo/arat/{snapshot}.geojson` (ou tiles) — polígonos oficiais simplificados por empresa, com versão.

Cada resposta inclui `version_id`, `data_base` por distribuidora, `filtro_aplicado`, `unidade`, `advertencias` e `fonte`.

## 5. Modelo analítico

- `dim_distribuidora` (`DIST`, nome, sigla, ativo)
- `dim_grupo_economico` e `bridge_distribuidora_grupo` com validade temporal
- `dim_entidade` (código e designação da BDGD, família e regra de métrica)
- `dim_dominio_dda` (versão, atributo, código interno, descrição amigável)
- `snapshot_bdgd` (DIST, DATA_BASE, origem, checksum, data_ingestao, publicado)
- `fact_ativo_agg` (snapshot_id, entidade; uma linha TOTAL, sem dimensão DDA)
- `fact_facetas_dda` e `facetas_catalogo` (cubos conjuntos por DIMENSÕES DDA, com cobertura, disjunção, métrica e regras de rollup explicitamente validadas)
- `arat_publicada` (snapshot, geometria simplificada por fragmento/polígono, source_checksum)
- `controle_qualidade` (validação, totais de origem/agregado, estado)

Usar indexação por snapshot, DIST, entidade, JSONB e filtros quentes, com políticas RLS read-only em schema exposto.

## 6. Matriz nacional

Linhas: distribuidoras; dimensões institucionais: grupo econômico, UF, data-base. Colunas: todas as entidades homologadas. Unidade em cada cabeçalho, rolagem horizontal, busca, filtros e CSV. Famílias com unidade km são rotuladas em km, não contagem de segmentos.

## 7. Comparador

Recorte A e B independentes: distribuidora ou grupo. Todas as entidades aparecem em linhas com unidade + valor A + valor B + diferença + variação %. Quociente percentual indisponível quando B=0; quando dados-base diferem, exibir advertência.

## 8. Roadmap

**M0 — Protótipo (iniciado)**: UI pública estática, polígonos *apenas ilustrativos*, filtros, matriz e comparador demonstrativos.

**M1 — Auditoria de fontes 2025**: catálogo nacional `DIST → GDB com DATA_BASE = 2025-12-31`, sem fallback; registrar empresas faltantes, qualidade por entidade, DDA versionado, grupos econômicos e acessos ao IA Builder, levantamento PBIX VPE.

**M2 — ETL homologado**: ingestão incremental, vínculos, DDA, cálculo de medidas, validação de `COD_ID`, publicação de `fact_ativo_agg`.

**M3 — ARAT oficial**: extrair polígono ARAT por `DIST`, dissolver/simplificar sem corromper topologia, publicar com hover e identificação; mapear sobreposições, ilhas e distribuidoras sem ARAT disponível.

**M4 — API e frontend**: banco gerenciado, consulta parametrizada paginada, filtros DDA cascata, React/Next/MapLibre/ECharts, paginação e exportação.

**M5 — Operação**: Vercel público, monitoramento de latência/custo, testes, auditoria de licença, calendário de atualização e documentação.

**M6 — Histórico para ML (futuro, após M5)**: inventariar dados históricos comparáveis, prioritariamente **2022–2025**, com ETL segregado do dashboard oficial 2025, sem mistura de competências.

**M7 — Séries históricas harmonizadas (futuro)**: construir série anual por DIST, entidade e métrica, tratar evolução de DDA/layout, comparabilidade, mudanças de DIST e grupos econômicos com vigência.

**M8 — Modelos preditivos e classificação (futuro)**: comparar baselines com ML, validar por backtesting temporal, classificar trajetórias e projetar **2026–2029** com intervalos de incerteza e regras de coerência empresa/grupo/Brasil.

**M9 — Módulo web preditivo (futuro)**: publicar apenas previsões sumarizadas, qualidade e metadados; nova aba "Inteligência Preditiva", comparativos históricos e futuros, cenários e exportação.

**M10 — Monitoramento e atualização (futuro)**: retreinamento após novas competências homologadas, avaliação de erro real versus previsto, versionamento e alertas de mudanças estruturais.

## 9. Critérios de aceite

- 100% das distribuidoras publicadas correspondem a arquivos oficiais efetivamente validados com `DATA_BASE = 2025-12-31`, e exibem fonte, checksum e cobertura; ausências não se tornam zeros.
- 100% das entidades previstas no escopo ficam visíveis, com ausência explicitamente identificada (nunca zero implícito).
- ARAT oficial é polígono; seleção respeita `DIST` e suporta fragmentos e sobreposição.
- Totais homologados por entidade e empresa têm reconciliação exata ou tolerância previamente aprovada (extensão/geometria).
- DDA legível com domínio/versão válido e filtro aplicável para a família.
- KPI e comparação são matematicamente estáveis com filtros, inclusive zero e valores nulos.
- Zero transferência de Parquet/GDB e zero credenciais de banco no JavaScript entregue ao browser.
- Aplicação sem login, acessível via teclado, funcional em smartphone e com tema persistente opcional.
- Respostas de agregados com cache, paginação e metas de desempenho aferidas em teste de carga antes de SLA público.

## 10. Riscos

- O BI VPE pode conter medidas que dependam de `COD_ID`/distinct ou relacionamento N:N: ajustar granularidade.
- Grupo econômico pode mudar no tempo: não atribuir controlador atual a bases históricas sem justificativa.
- Geometria ARAT pode ter múltiplos fragmentos, buracos e sobreposição; fusão exige decisão de negócio.
- Custo de storage e consultas nacionais; monitorar limites do plano contratado.
- Publicação da BDGD derivada: cumprir licença ODbL e requisitos de privacidade.

## 11. Separação obrigatória entre BI VPE 2024 e BDGD 2025

**Esclarecimento do responsável pelo projeto em 22/10/2026:** o BI VPE de referência foi construído com a BDGD **DATA_BASE = 31/12/2024**, ao passo que este portal utilizará **exclusivamente DATA_BASE = 31/12/2025**. **Não existe critério de aceite de igualdade numérica entre os dois exercícios.**

- **Validar estrutura e metodologia com o BI VPE 2024:** definições de KPIs, fórmulas, filtros, unidades, classificação de entidades, regras DDA e semântica de relacionamentos. Ajustar normas/layout para 2025 quando houver evolução.
- **Validar quantitativamente com a BDGD 2025:** contagens e medidas da própria GDB com competência 31/12/2025, vínculos, chaves `DIST + COD_ID`, reconciliação de registros versus contagens distintas, extensões/potências e totalizações entre grupos.
- **Nunca bloquear um release ou uma distribuidora porque os números de 2025 divergem dos indicadores de 2024.** Divergência histórica pode motivar investigação, mas não é falha automática de QA.
- Não criar um backfill 2024 nem misturar competências no portal para satisfazer a paridade com VPE.
- Evidenciar no relatório de qualidade duas categorias separadas: `validacao_metodologica_vpe_2024` e `reconciliacao_origem_bdgd_2025`. A primeira verifica regras, a segunda números e integridade de 2025.

## 12. Evolução posterior: Inteligência Preditiva e previsões 2026–2029

**Incluída no escopo, mas não iniciada.** O portal público atual continuará usando exclusivamente `DATA_BASE=31/12/2025`; séries históricas anteriores serão adquiridas e processadas **em módulo separado após o dashboard 2025 estar pronto**, com métricas temporalmente harmonizadas.

Objetivo: gerar previsões de crescimento por **distribuidora, grupo econômico e país**, por entidade, unidade e métrica, com classificação da trajetória histórica, comparativos futuros A/B, cenários e intervalos de incerteza para **2026, 2027, 2028 e 2029**. São **projeções estatísticas**, nunca dados reais da ANEEL.

Treinamento/inferência fora do website, com **Python e DuckDB em máquina local autorizada (CPU)**. O site receberá apenas CSV/JSON ou tabelas PostgreSQL de **previsões sumarizadas e aprovadas**; não é necessário fazer upload de modelo treinado, GDBs históricos, Parquets privados ou COD_ID. A solução poderá inicialmente usar assets JSON estáticos se os agregados forem pequenos.

**Restrição científica:** a única competência 2025 não é série temporal; não treinar/apresentar ML de crescimento quadrienal somente com esse snapshot. Para inferência temporal é necessário histórico de anos comparáveis (**2022–2025** como janela de referência, ou **2023–2025** somente para análises exploratórias se 2022 for incompatível), com mudanças de layout/DDA, fusões de distribuidoras e vigência de grupos econômicos documentadas. Onde não houver histórico suficiente, mostrar `previsao_indisponivel`, sem fabricar confiança ou resultados. Comparar com modelos-base e utilizar validação temporal retrospectiva, não divisão aleatória dos anos.

**Documento normativo completo:** [MODULO-PREDITIVO-ML.md](MODULO-PREDITIVO-ML.md) — granularidade e fontes, classificação, backtesting, hierarquia distribuidora/grupo/Brasil, formatos públicos, experiência no dashboard, critérios de aceite e roadmap M6–M10.


**Regra de janela histórica (atualizada em 22/10/2026):** devido às mudanças do Manual BDGD ao redor de 2021/2022, começar **somente com 2022, 2023, 2024 e 2025** no estudo de previsão. Não ampliar automaticamente para 2019–2021. O Manual Revisão 1 tem vigência em 02/01/2022, mas ainda é preciso reconciliar versões, métricas, chaves e DDA entre 2022–2025. Se 2022 não passar na validação, pode-se explorar 2023–2025 para descrição/cenários, sem prometer treinamento preditivo robusto. Quatro pontos anuais por série não são quatro milhões de pontos temporais: mesmo com muitas empresas e ativos, validação de horizonte 3–4 anos permanece frágil. Treinamento pooled/hierárquico só se houver ganho verificável sobre baselines. Para projeções 2028/2029 sem backtest adequado, apresentar limitações, premissas ou marcar indisponível.

**Prioridade vigente:** terminar M1–M5, sem atrasar download, reconciliação, ARAT e construção do dashboard oficial 2025. Não realizar download de histórico ou criação de infraestrutura paga sem autorização específica.
