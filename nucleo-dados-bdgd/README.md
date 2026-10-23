# Núcleo de Dados da BDGD — Portal Nacional

Protótipo de uma aplicação pública para explorar ativos da Base de Dados Geográfica da Distribuidora (BDGD), com visual clean, tema claro/escuro, mapa de áreas de atuação, filtros descritivos de DDA, matriz de ativos por empresa e comparador de distribuidoras/grupos econômicos.

> **IMPORTANTE**: este repositório contém somente dados demonstrativos. Os números, datas-base e polígonos do MVP NÃO são dados oficiais. Não utilizar para análises regulatórias.

## Executar o protótipo

Abra `index.html` em um navegador recente, ou hospede a pasta em qualquer servidor HTTP estático:

```bash
python -m http.server 8000
```

Depois abra `http://localhost:8000`. Nenhuma dependência, autenticação, banco, token ou Parquet são necessários para o protótipo.

## Estrutura

- `index.html` — interface acessível com seções Panorama, Ativos, Comparador e Metodologia.
- `styles.css` — design responsivo, visual limpo e paleta claro/escuro.
- `app.js` — dados fictícios determinísticos, mapa poligonal ilustrativo e interações.
- `vercel.json` — cabeçalhos para distribuição estática.
- `database/schema.sql` — desenho inicial do banco PostgreSQL/Supabase.
- `docs/PLANO-GERAL.md` — arquitetura, fases, decisões e critérios de aceite.
- `docs/DIRECAO-ARTE-UIUX.md` — especificação obrigatória de UI/UX premium, identidade visual autoral, animações e microinterações personalizadas, acessibilidade, screenshots e refinamento.
- `docs/MODULO-PREDITIVO-ML.md` — **fase futura** de aprendizado de máquina, classificação e previsões 2026–2029; treinamento ainda não iniciado.
- `docs/PROMPT-CODEX-HISTORICO-2022-2024.md` — **ETL histórico autorizado em paralelo**, na mesma máquina Windows do Claude, sem misturar dados com o dashboard oficial 2025.
- `docs/PROMPT-CLAUDE-DASHBOARD-2025-DEPOIS-HISTORICO-2022-2024.md` — **plano mestre de execução delegado ao Claude**: concluir ETL e dashboard real 2025, GitHub/preview/deploy autorizado e, só depois, ETL histórico 2022–2024 e sucessões empresariais; sem ML.
- `etl/README.md` — especificação da ingestão, extração ARAT, DDA e agregação.
- `docs/MODELO-FATOS-FACETAS-2025.md` — grão dos totais e cubos DDA, sem duplicação de medidas; esquema 1.1.0.
- `docs/PROMPT-CLAUDE-ETL-2025.md` — instruções operacionais completas para processamento local da competência **31/12/2025**.

## Operação final prevista

**Ingestão**: arquivo Geodatabase de cada distribuidora nos dados abertos da ANEEL, validado com o Manual BDGD e PRODIST 10.

**Normalização**: extrair entidades, identificar `DIST` e `DATA_BASE = 2025-12-31` exclusivamente, validar vínculo e cardinalidade, aplicar DDA e grupo econômico.

**Agregação**: Python + GDAL/GeoPandas + DuckDB/Polars; fatos agregados por entidade e dimensões DDA aplicáveis, medidas aditivas e medidas distintas homologadas.

**Áreas de atuação**: a ARAT oficial é geometria poligonal. Publicar GeoJSON simplificado, dividido e indexado por `DIST`, sem geometrias falsas ou pontos; lidar com multipolígonos, sobreposições, buracos, antimeridiano e diferenças de cobertura.

**Banco de consulta**: PostgreSQL gerenciado (Supabase) com PostGIS. Guardar fatos agregados e catálogo semântico; geodados simplificados para mapas. Dados de carga em `private`, somente objetos destinados ao público em `public`.

**API**: Next.js/Vercel Functions, leitura somente de agregados e limites de paginação, validação dos filtros, cache. Dados de importação e segredos **nunca** no navegador.

**Frontend produção**: React + TypeScript + Lucide + MapLibre GL + ECharts. Este protótipo zero-dependência é um marco funcional inicial, não o frontend final.

**Publicação**: GitHub → Vercel com domínio público e sem login. A página nunca fará download de Parquets ou Geodatabases.

## Próximas dependências

1. Disponibilidade de Geodatabases oficiais **com DATA_BASE = 31/12/2025** por distribuidora; não completar lacunas com 2024/2026. ARAT oficial somente dessas mesmas bases.
2. Disponibilidade dos catálogos de vínculos e DDA do IA Builder (não estão neste protótipo).
3. Inventário confiável das páginas, medidas e tabelas do `BI_BDGD_VPE.pbix` e avaliação de replicabilidade.
4. Instância de banco PostgreSQL gerenciado (não provisionada; preços/permissões devem ser aprovados).
5. Projeto Vercel com permissões de criação/deploy.

## Autoria

Desenvolvido por **Arthur Henrique Lima** — **Núcleo de Dados da BDGD**.

## Fontes e atribuição

- ANEEL — Base de Dados Geográfica da Distribuidora (BDGD): https://dadosabertos.aneel.gov.br/dataset/base-de-dados-geografica-da-distribuidora-bdgd
- ANEEL — Manual de Instruções BDGD / PRODIST Módulo 10.
- Licenciamento das fontes de dados: verificar exigências ODbL e atribuição antes da redistribuição dos dados derivados.

Este projeto não é um produto oficial da ANEEL.

- `docs/HARMONIZACAO-SUCESSAO-2022-2025.md` — séries históricas originais e série derivada do perímetro 2025 para incorporar predecessoras sem inflar crescimento; recorte **somente 2022–2025**.
