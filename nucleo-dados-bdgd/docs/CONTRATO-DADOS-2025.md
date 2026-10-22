# Contrato de publicação — Núcleo de Dados da BDGD (v1)

**Competência obrigatória:** `2025-12-31`, para TODAS as distribuidoras incluídas. Nenhum fallback de 2024 ou 2026. Esta especificação é o acordo de entrega entre a máquina que processa os GDBs (Claude) e a frente de site/API (ChatGPT).

## Ambientes e responsabilidades
- **ETL offline:** Python, GDAL, DuckDB e Polars. Descoberta/descarga dos GDBs oficiais, validação de `DIST`, aplicação do DDA e dos vínculos IA Builder, agregações, ARAT e QA.
- **Publicação:** exclusivamente arquivos `output-publicavel/2025-12-31/` aprovados, com dados agregados. Não copiar arquivos GDB, parquet de staging, `COD_ID`, dados de pessoas/UCs ou credenciais.
- **Banco/API:** PostgreSQL/PostGIS gerenciado (proposta: Supabase) para armazenamento dos agregados e geometrias ARAT simplificadas; Vercel serve frontend e APIs com respostas paginadas. Provisionamento ainda **não autorizado/realizado**.
- **Frontend:** protótipo atual é ilustrativo. Ao habilitar modo real, falhar fechado quando manifesto não existe/está inválido; **não usar números fictícios como fallback**.

## Estrutura do pacote

```text
output-publicavel/2025-12-31/
  manifest.json
  distribuidoras.csv
  entidades.csv
  grupos_economicos.csv
  dist_grupo.csv
  dda_descricoes.csv
  ativos_agregados.csv           # ou lotes declarados no manifest
  matriz_empresas_2025.csv
  qa_reconciliacao.csv
  geo/arat_2025_<DIST>.geojson   # POLÍGONOS ARAT, não centróides
  schemas/contrato_publicacao.json
  RELATORIO.md
```

Arquivos CSV: UTF-8, separador **vírgula**, cabeçalho na 1ª linha, aspas RFC 4180, números decimais com ponto. Exportação para Excel poderá usar `;` e vírgula decimal, mas **não** no pacote de intercâmbio. Campos e capitalização são obrigatórios.

### `manifest.json` (campos mínimos)

```json
{
  "schema_version": "1.0.0",
  "release_id": "bdgd-2025-12-31-<HASH_OU_VERSAO>",
  "data_base": "2025-12-31",
  "status": "homologado",
  "generated_at": "<ISO-8601 UTC>",
  "dda_version": "<VERSAO_REAL_VERIFICADA>",
  "sources": [{"dist": 6600, "url": "<URL_ANEEL>", "sha256": "<SHA256_64_HEX>", "data_base": "2025-12-31"}],
  "files": {
    "distribuidoras": "distribuidoras.csv",
    "entidades": "entidades.csv",
    "fatos": "ativos_agregados.csv",
    "matriz": "matriz_empresas_2025.csv",
    "arat": ["geo/arat_2025_6600.geojson"]
  },
  "quality": {"status": "aprovado", "source_reconciliation": true}
}
```

Em releases parciais, usar `status: "parcial"` e `quality.status: "em_validacao"`; isso **não** é publicação oficial. Não inventar SHA, fonte, versão do DDA, grupo econômico ou data-base.

### `distribuidoras.csv`
Colunas obrigatórias: `dist,sigla,nome,grupo_economico,data_base,fonte_url,sha256,status`. `dist` numérico; `data_base` exatamente `2025-12-31`; uma linha por `DIST`; grupo econômico e seu vínculo devem ter fonte/validade verificada. Se não confirmado, usar `nao_confirmado`, mas não deduzir grupo.

### `entidades.csv`
Colunas obrigatórias: `entidade,nome_exibicao,familia,metrica,unidade,regra`. Ex.: `SSDMT` com `metrica=extensao_km` somente após homologar a regra; uma entidade não deve aparecer duas vezes.

### `ativos_agregados.csv`
Colunas mínimas: `dist,entidade,data_base,dimensoes_json,quantidade,quantidade_registros,quantidade_cod_id_distinto,extensao_km,potencia_kva,status_qualidade,motivo_qualidade`. `dimensoes_json` é JSON objeto com **códigos de dimensão permitidos** (sem identificadores pessoais/ativos). Valores métricos inexistentes: célula vazia (`NULL`), e NÃO zero. Métrica de comprimento não é contagem de segmentos. `quantidade_registros` e `quantidade_cod_id_distinto` são indicadores distintos e nunca devem ser trocados sem rotular. Para UCBT/UCMT/UCAT, a contagem única não é aditiva entre dimensões sobrepostas: permitir recálculo por `DIST + entidade + COD_ID` no ETL e impedir rollups de contagens distintas sem comprovar partições disjuntas. `status_qualidade` é um de `aprovado`, `alerta`, `bloqueado`, `em_validacao`, `nao_aplicavel`. `motivo_qualidade` é preenchido nos bloqueios. Campos `quantidade`, `extensao_km` e `potencia_kva` não podem ser negativos. Para agregações complexas (médias, distintos), declarar sua semântica em `entidades.csv` e os componentes adicionais com regras homologadas.

### `matriz_empresas_2025.csv`
Uma linha por `DIST`, com coluna `dist`, `data_base` e as colunas das métricas **com unidade explícita** para cada entidade (por exemplo, `UCBT__quantidade`, `SSDMT__extensao_km`). Unidades diferentes não devem ser somadas. Ausente/não homologado: célula vazia + registro de cobertura; zero apenas se realmente auditado. A matriz deve reconciliar com o fato agregado no nível de DIST + entidade + métrica.

### `dda_descricoes.csv`
`versao,entidade,atributo,codigo_interno,descricao,dominio`. Código pode ficar na camada técnica, mas a interface **exibe descrição**. Facetas apenas nas entidades onde fazem sentido, sem lista universal falsa.

### `geo/arat_2025_<DIST>.geojson`
GeoJSON FeatureCollection com Feature Polygon ou MultiPolygon obtida **exclusivamente** da ARAT BDGD 2025. CRS de publicação WGS84/EPSG:4326 (longitude, latitude), convertendo corretamente a origem. Propriedades mínimas `dist` e `data_base`. Se a empresa não tiver ARAT, registrar ausência e NÃO inventar um polígono. Simplificar com tolerância declarada, preservar topologia e medir alteração de área; evitar artefatos de geometria, limites de UF substitutos e sobreposições indevidamente fundidas.

### `qa_reconciliacao.csv`
`dist,entidade,metrica,valor_origem,valor_agregado,diferenca,tolerancia,status`, com status `ok`, `falha` ou `nao_aplicavel`. A emissão de `status=homologado` depende de reconciliação aprovada, com metodologia por métrica. Distintos precisam de validação de partições disjuntas.

## Semântica de API
- `GET /api/v1/manifest`: release e escopo verificado.
- `GET /api/v1/kpis?grupo=&dist=&familia=&filtros=...`: grandezas e fontes.
- `GET /api/v1/ativos?pagina=1&tamanho=50&...`: matriz de entidades por empresa, incluindo ausências explícitas.
- `GET /api/v1/comparacao?tipoA=grupo&idA=...&tipoB=dist&idB=...`: linhas por entidade com unidades e cálculo A-B; porcentagem não existe se B=0.
- `GET /api/v1/filtros?entidade=...`: filtros descritivos aplicáveis e suas contagens.
- `GET /api/v1/arat?dist=...` ou CDN versionada: polígonos reais.

Respostas incluem `release_id`, `data_base`, `fonte`, `unidade`, `status_cobertura`, `advertencias` (quando necessárias). APIs retornam **só resultados públicos agregados**.

## Critérios de homologação automática e manual
1. Em TODOS os registros com `DATA_BASE`, valor exatamente `2025-12-31`.
2. Cada `DIST` no fato/matriz/ARAT deve existir no manifesto/catálogo de distribuidoras.
3. Nenhuma linha agregada contém `COD_ID`, `NUM_CDC` ou identificador pessoal; a lista de campos bloqueados deve ser ampliada por análise de privacidade.
4. Cada `DIST` publicado tem proveniência `URL`, SHA-256 da fonte e evidência de validação 2025.
5. Não usar 0 para entidade ausente. `N/D` é estado próprio.
6. QA de totalizações com tolerâncias documentadas; falha bloqueia publicação do indicador afetado, sem transformar métrica ausente/bloqueada em zero. KPIs nacionais só incluem medidas homologadas e deixam claro a cobertura.
7. Entidade reporta unidade e fórmula; KPI só agrega grandezas homogêneas.
8. ARAT corresponde a geometria poligonal oficial; sem centroide artificial.
9. License/ODbL e atribuição ANEEL revisadas antes de publicação.
10. No front, **se não houver dados oficiais**, mostrar "Demonstração", nunca números de simulação como reais.

## Primeira entrega do Claude
Enviar primeiro `inventario_2025.csv`, `cobertura_2025.json`, `RELATORIO.md` e uma amostra validada. O ChatGPT fará revisão e indicará modificações antes de ampliar a ingestão nacional.

## Versões e governança
Incrementar `schema_version` ao mudar o formato. Registrar `release_id`, versão do DDA, hash da fonte, hora de ingestão, testes, versão do código e responsável. Imutabilidade dos snapshots homologados e troca atômica do snapshot ativo.

Responsável pela aplicação: Núcleo de Dados da BDGD — desenvolvido por Arthur Henrique Lima.

## Regra de comparabilidade com o BI VPE (2024)

O BI VPE já existente utiliza **31/12/2024**; este portal usa **31/12/2025**. O BI anterior serve somente de **referência metodológica** (definições, fórmulas, indicadores, filtros e estrutura), nunca como gabarito quantitativo para o ano de 2025. Diferenças entre as quantidades 2024 e 2025 são esperadas e **não podem bloquear** a publicação de dados 2025 que reconciliem com seus próprios GDBs.

No relatório QA, manter `validacao_metodologica_vpe_2024` e `reconciliacao_origem_bdgd_2025` como registros distintos; o segundo é critério obrigatório de números. Para um KPI, homologar fórmula/escopo e reconciliar agregação e fonte **da mesma competência 2025**. Auditoria de mudanças 2024→2025 seria projeto separado, sem misturar dados no portal inicial.
