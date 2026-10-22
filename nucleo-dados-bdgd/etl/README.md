# Pipeline de ingestão e publicação — especificação executável futura

## Etapas propostas

1. **Inventariar** recursos ANEEL e admitir **somente DATA_BASE = 2025-12-31**, por `DIST`. Confirmar hash, licença, metadados e disponibilidade das entidades. Distribuidoras sem GDB 2025 ficam fora, com motivo documentado (sem fallback).
2. **Extrair** somente GeoDatabase validada de 2025 com GDAL/OGR em runner controlado e identificar `ARAT` poligonal e entidades do catálogo.
3. **Normalizar** chaves `(DIST, DATA_BASE, COD_ID)`; verificar campos obrigatórios e relações `UN* ↔ EQ*` conforme modelo semântico IA Builder.
4. **Enriquecer** com DDA versionado (`dominio, codigo, descricao`), `TUC`, `A1..A6` quando existirem e vínculo temporal a grupo econômico.
5. **Agregação** por família e dimensões válidas para cada KPI; preservar métricas aditivas, componentes de médias ponderadas e chaves de contagem distinta.
6. **Reconciliação** com bruto por entidade/DIST: quantidade, extensão e potências, tolerâncias documentadas; bloquear versão com erro.
7. **Geometrias ARAT**: `ST_MakeValid`, tratar multipolígonos e buracos; transformar para CRS métrico para simplificação, `ST_SimplifyPreserveTopology`, retornar a 4674; comparar área/cobertura antes e depois; gerar GeoJSON particionado.
8. **Publicação atômica**: inserir novo snapshot como não publicado, publicar agregados e GeoJSON versionado, conferir, então trocar a versão ativa de cada DIST em transação.
9. **Manifesto público**: publicações, versões do DDA, distribuição temporal, contagens de registros, fonte e hash de origem.

## Escopo da carga inicial

Ano-base congelado em **31/12/2025**. O portal não combina empresas com DATA_BASE de outros exercícios. CSVs isolados de unidades consumidoras não são substitutos da GDB completa de 2025. Executar o trabalho local conforme `docs/PROMPT-CLAUDE-ETL-2025.md`.

## Controles de qualidade

- Duplicidades de `DIST+COD_ID` antes da agregação e erros em relações 1:N.
- Regras de nulidade, domínio DDA desconhecido, geometria inválida, percentuais de cobertura da ARAT.
- Totais por distribuidora, ativos e grupos econômicos; alertas de descontinuidade e mudança temporal de controlador.
- Cruzamentos com UF devem respeitar interseção geométrica, não simplesmente atributo `UF` único para distribuidoras multestado.
- Catálogo de publicação só inclui o necessário para o painel público. Nenhuma credencial, UC individual ou identificador pessoal.

## Infraestrutura

Executar ETL fora do ambiente Vercel (runner com armazenamento temporário suficiente para GDB nacionais). O portal Vercel só consulta os resultados já agregados do PostgreSQL e GeoJSON/CDN. O protótipo atual não executa este pipeline.

## Teste obrigatório por amostra

Selecionar 3 distribuidoras de diferentes grupos; calcular relatórios brutos de UCBT, EQTRMT, SSDMT, SUB e ARAT; comparar valores com agregados por todas as dimensões; testar filtros combinados e a comparação grupo×grupo.
