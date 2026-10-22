# Decisões técnicas após piloto Claude — BDGD 31/12/2025

**Origem destas informações:** relatório textual encaminhado pelo usuário em 22/10/2026, referente a execução local do Claude em `D:\NUCLEO_BDGD_2025`. **Não se trata de auditoria independente dos arquivos**; os artefatos, hashes e logs completos ainda precisam ser compartilhados e verificados.

## Cobertura relatada
- 114 DISTRIBUIDORAS históricas no ArcGIS, **99 GDB públicos 2025**, **15 sem publicação 2025**; 1.014 itens GDB somando todas as competências; volume de download relatado 31,65 GB.
- Três pilotos: Energisa Acre (`DIST=26`), CEA Equatorial (`DIST=31`), CPFL Santa Cruz (`DIST=69`). GDBs ZIP íntegros, BASE com data 31/12/2025, `DIST` consistente, 43 camadas por GDB, ARAT presente.
- 6,53 milhões de linhas no piloto; 8 testes do pipeline relatados como passando; não equivalem a homologação nacional.
- PC: 7,9 GB RAM, D: com ~882 GB livres; Python 3.14 global, venv isolado com GDAL/pyogrio/DuckDB em D:; processamento deve preservar limite de memória.

## Decisões autorizadas para continuação
1. **Continuar outros 96 downloads/processamentos por lotes de 3–5 distribuidoras** (começar menores). Limitar concorrência e uso de memória, conferir espaço mínimo seguro (>150 GB livres e >2x o tamanho temporário estimado da maior distribuidora antes de iniciar cada lote); capturar logs, checksums e progresso. Não sobrescrever entregas validadas; não publicar GDB/Parquet brutos. Se houver falta de disco, lentidão excessiva, erro de integração ou download restrito, pausar e documentar o lote.
2. **Consumidores:** publicar `quantidade_registros` e `quantidade_cod_id_distinto` separadamente para UCBT, UCMT e UCAT, por `DIST + entidade + COD_ID`. KPI principal de UC será contagem distinta **somente após** validar coerência intraentidade, ausência de nulos/chaves conflitantes e disjunção entre entidades. Se houver sobreposição entre UCBT/UCMT/UCAT, usar união de chaves distintas `(DIST,COD_ID)` sobre famílias de UC antes do `GROUP BY`, ou apresentar KPIs individuais sem somar, com método explícito. **Não** descartar duplicatas no bruto para forçar reconciliação.
3. **Potência de geração UG*:** manter original no staging privado; **não aplicar corte/cap** de 75 kW, nem corrigir automaticamente. Investigar semântica do campo, domínio DDA, unidade, fator de conversão, distribuição e vinculação por ativo. Geração total **não homologada** deve permanecer `NULL/N/D` e não 0 no pacote público, com `motivo_qualidade`. A contagem de UG* pode ser publicada somente se auditada. O parâmetro <=75 kW é definição legal de **microgeração**, mas não é necessariamente limite de todas as classes de UG*/sistemas na BDGD. Separar UGBT/UGMT/UGAT e classificação micro/minigeração validada.
4. **CTMT na CEA Equatorial:** filtro por circuito `CTMT` fica `indisponivel_por_qualidade` para o `DIST=31` até resolver cobertura. Não bloquear contagens independentes sem vício. Guardar numerador, denominador e percentual de órfãos por relacionamento.
5. **Transformação:** `EQTRMT` e `UNTRMT` representam visões relacionadas; não somar kVA/contagens entre elas sem regra canônica, sob risco de duplicidade. Investigar divergência de 19% em potência no piloto CPFL Santa Cruz.
6. **DDA:** `TSIST` ausente, 21 referências sem tabela de domínio, 2 arquivos do KNOWLEDGE_LOCK ausentes; registrar versão/hash e não converter rótulos de domínios ausentes em descrições inventadas. Exibir `N/D` no protótipo real para o campo sem mapeamento.
7. **ARAT:** comparar polígono de origem com GeoJSON simplificado, CRS transformado para EPSG:4326, geometria válida, fragmentos, sobreposições e diferença relativa de área; a coincidência com área geográfica da UF não é prova suficiente.
8. **Grupo econômico:** não publicar agrupamento suposto por nome. Encontrar cadastro controlador válido para 31/12/2025 com fonte; estados `nao_confirmado` não entram em soma de grupos, mas continuam no agregado por empresa.

## Critérios de avanço
- **Lote processado** exige validação de BASE, DIST, GDB, ARAT, checksum, agregações e reconciliação; falhas isoladas ficam em quarentena.
- **Publicação de dados oficiais** exige validar o `docs/CONTRATO-DADOS-2025.md` e executar `node etl/validate-publication.mjs output-publicavel/2025-12-31`. O validador é verificação estrutural inicial, não substitui homologação dos vínculos e fórmulas do VPE.
- Citar todas as fontes; preservar planilha de cobertura das 15 distribuidoras sem arquivo GDB 2025 para que não sejam apresentadas como zero.
- Não implantar Supabase/Vercel, não gerar custos e não alterar `main` sem aprovação específica; projeto web demonstrativo permanece separado do pipeline.
- Verificação externa regulatória: [ANEEL — MMGD](https://www.gov.br/aneel/pt-br/assuntos/geracao-distribuida/) e [Lei 14.300/2022](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2022/lei/l14300.htm).

**Próxima transferência Claude → ChatGPT:** `inventario_2025.csv`, `cobertura_2025.json`, `RELATORIO_COBERTURA_2025.md`, pacote-piloto sanitizado, código de ETL (sem segredos) e evidências de QA, pelo GitHub em branch própria ou arquivo anexo. **Não adianta enviar caminhos D:\ locais como se eu pudesse acessá-los daqui.**

## Correção de referência numérica do BI VPE

O usuário esclareceu que o **BI VPE é de 2024**, e **não** deve bater numericamente com a carga do portal baseada em **2025**. Portanto, os resultados do BI VPE são consultados apenas para reproduzir/avaliar **método, fórmula, definições de métricas, dimensões e regras**, ajustados quando necessário para o layout 2025. Não comparar os números de 2025 com os resultados do BI VPE como condição de aceite. A reconciliação obrigatória é `GDB 2025 → agregados 2025 → matriz e KPIs 2025`. Caso um KPI VPE 2024 dependa de cálculo que não se aplica ao layout atual, documentar a incompatibilidade e homologar a versão 2025 sem forçar igualdade histórica.
