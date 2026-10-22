# Prompt para Claude — ETL nacional BDGD 31/12/2025

> PROJETO: **Núcleo de Dados da BDGD**. Tarefa exclusiva do Claude no computador: inventariar, baixar, validar, enriquecer e agregar **somente as BDGDs com DATA_BASE = 2025-12-31** disponíveis publicamente. O ChatGPT permanece responsável por frontend, APIs, modelo SQL, GitHub e Vercel. Não substituir uma distribuidora ausente por BDGD de 2024 ou 2026.

## Contexto
Aplicação pública sem login, com mapa de áreas de atuação **ARAT poligonais**, KPIs nacionais, tabela de **todas as entidades BDGD por distribuidora** (colunas), filtros amigáveis **DDA** por ativo, comparação empresa × empresa, grupo × grupo e empresa × grupo. Visual clean, tema claro/escuro, autoria Arthur Henrique Lima. O frontend **nunca** recebe GDB, Parquets brutos, COD_ID individual ou dados pessoais.

Projeto: https://github.com/artelias/BDGD/tree/feat/nucleo-dados-bdgd-portal/nucleo-dados-bdgd
Ler primeiro: `README.md`, `docs/PLANO-GERAL.md`, `database/schema.sql`, `etl/README.md`.
Fonte ANEEL: https://dadosabertos.aneel.gov.br/dataset/base-de-dados-geografica-da-distribuidora-bdgd
Catálogo ArcGIS: https://dadosabertos-aneel.opendata.arcgis.com/search?tags=distribuicao
Manual: https://www.gov.br/aneel/pt-br/centrais-de-conteudos/manuais-modelos-e-instrucoes/distribuicao

IMPORTANTE: O portal oficial informa que a BDGD geográfica é publicada como **File Geodatabase (GDB) por distribuidora**. Pode haver arquivos CSV/ZIP derivados (ex.: UC*_PJ posição de 31/12/2025), mas **eles não substituem o GDB integral**, nem provam que o GDB 2025 existe. Verifique disponibilidade da competência 2025 antes de baixar, sem inventar URLs ou anos-base.

## Critério rígido de inclusão
- Competência obrigatória: `DATA_BASE = 2025-12-31` no arquivo ou metadado confiável, e validar preferencialmente no conteúdo/camada `DATA_BASE`. Data de publicação/atualização do item **não é** DATA_BASE.
- Inclusão: toda empresa/concessionária/permissionária com GDB público acessível, consistente com essa data, sem restringir a 9 empresas Energisa; usar `DIST` oficial como identificador e capturar todas as entidades encontradas.
- Excluir 2024, 2026, 2023 etc. **sem fallback**. Se a empresa não tem BDGD 2025 encontrada, registrar no relatório como `sem_publicacao_2025`, `nao_localizada`, `acesso_restrito`, `download_indisponivel` ou `validacao_falhou`; não exibir 0 ativos por ausência.
- Duplicações ou versões corrigidas da mesma empresa e data: escolher versão oficial homologada mais recente, guardar a trilha de versões, hashes e justificativa. A data-base do site é sempre **31/12/2025**, não 'última de cada empresa'.
- Não concluir que todas as distribuidoras têm arquivo 2025 até que o inventário prove isso. Reportar número de empresas elegíveis e cobertura de maneira transparente.

## Tarefa 1 — preparação e inventário (antes de baixar grandes volumes)
1. Inspecionar recursos de PC: SO, Python, GDAL/ogrinfo, DuckDB, espaço em disco, RAM, direitos de acesso, arquivos GDB/Parquet 2025 já disponíveis e catálogos IA Builder existentes. Preferir processamento por empresa e por entidade com disco temporário; nunca carregar a BDGD nacional em RAM.
2. Descobrir itens do ArcGIS Open Data e REST API, paginação completa, filtro tags/nomes `2025-12-31`, tipo GDB/ZIP, distribuidora, DIST. Usar busca na própria API em vez de resultados isolados de buscadores; registrar a consulta e data.
3. Criar `inventario_2025.csv` com: `dist,sigla,empresa,grupo_economico_candidato,data_base_declarada,data_base_validada,item_id,url_item,url_download,formato,versao,publicado_em,atualizado_em,tamanho_bytes,status,motivo,checksum_sha256`.
4. Criar `cobertura_2025.json`: encontradas, baixadas, homologadas, sem acesso, ausentes, rejeitadas, total de DISTRIBUIDORAS consideradas, metodologia. Não preencher empresas ausentes com dados fictícios.
5. **Primeira entrega rápida:** inventário real completo ou parcial com status explícito, antes da extração longa; piloto de no máximo 3 empresas com GDB 2025 validado (de grupos diferentes, se possível).

## Tarefa 2 — download e staging
- Usar download retomável (HTTP Range se suportado), retries limitados, timeouts, SHA-256, detecção de ZIP/GDB corrompidos; limitar concorrência para respeitar rede.
- Não baixar 2024 por engano porque nome do item contém data de upload em 2026.
- Inspecionar cada GDB (`ogrinfo`) para identificar entidades e nomes reais de campos, geometria, EPSG e data-base. Não assumir que nomes pré-definidos sempre existirão.
- Converter para Parquet **somente staging local**, se útil, particionado por `DIST/DATA_BASE/entidade`, com logs e checkpoints. Nunca subir brutos ao GitHub, Vercel ou banco público.
- Adequar para máquina Windows com ~16 GB de RAM (se aplicável): DuckDB streaming/spill em SSD; logs individuais; processamento incremental.

## Tarefa 3 — catálogo IA Builder + DDA
- Localizar **arquivos realmente existentes** do IA Builder: relacionamentos entre `UN*`, `EQ*`, `CONJ`, `CTMT`, `SUB`, catálogos DDA/TUC, regras de `A1..A6` e métricas VPE. Registrar nomes, versões e hashes; não inventar tabelas, campos nem relações.
- Chaves de junção: `DIST + COD_ID` e escopo de snapshot 2025; `COD_ID` não é global. Verificar cardinalidade N:1/1:N/N:N para evitar duplicação de quantidades/quilômetros/kVA. Separar `COD_ID` da publicação.
- DDA: manter mapeamento por `entidade,atributo,codigo,descricao,versao`. Filtros da web devem mostrar **apenas descrições traduzidas**, de acordo com a entidade selecionada; códigos podem ficar apenas na camada analítica.
- Grupo econômico: controlador correspondente à competência 2025, acompanhado da fonte e data de validade. Grupos incertos devem ser marcados `nao_confirmado`, nunca presumidos.
- Medidas: quantidade de itens, extensão (km), potência (kVA/MVA), com unidade explícita. Para médias preservar numerador e denominador. Não somar contagens distintas que se sobrepõem.

## Tarefa 4 — fato agregado público
- Definir grão por entidade: `snapshot_2025 + dist + entidade + combinação de dimensões DDA elegíveis`; documentar cardinalidade e cobertura dos filtros. Uma tabela-matriz de uma linha por `DIST` e uma coluna por entidade deve poder ser reconstruída fielmente.
- Agregar ativos com `GROUP BY`, **não** publicar `COD_ID` nem dados individuais. Gerar colunas `quantidade`, `extensao_km`, `potencia_kva` só onde houver sentido e regra validada; demais métricas opcionais de VPE com metodologia.
- Não misturar unidades em indicador 'total de ativos' sem regra de contagem válida. Quando entidade não existe, valor deve ser `NULL/N/D`, não zero; quando existe e não tem linhas, zero auditado.
- Produzir agregados para todas as entidades confirmadas no manual/GDB — não somente 6 cartões do protótipo.
- Criar dimensão de filtros com descrições DDA e facetas dependentes; considerar cardinalidade/volume para não explodir combinações.

## Tarefa 5 — ARAT poligonal
- Extrair **ARAT oficial da competência 2025** de cada GDB válido e identificá-la por DIST. Se faltar ARAT, marcar no relatório e **não inventar polígonos ou pontos**.
- Tratar geometrias inválidas, polígonos múltiplos, buracos e sobreposições. Simplificar em projeção métrica apropriada preservando topologia, medir diferença de área, entregar **GeoJSON EPSG:4326** versionado e particionado quando necessário. Não usar retângulos, centróides nem limites de UF como ARAT.
- Propriedades mínimas: `dist`, `data_base`, `source_item_id` (sem atributos sensíveis). Garantir hover, seleção e fragmentos multirregião.

## Tarefa 6 — QA e contrato de transferência
Gerar apenas conteúdo APROVADO em `output-publicavel/2025-12-31/`:
1. `manifest.json`: `data_base:'2025-12-31'`, versão de publicação, data de geração, empresas incluídas e excluídas, URLs oficiais, checksums, versão do DDA, QA, esquema de dados e atribuições.
2. `distribuidoras.csv`: dist, nome, sigla, grupo econômico **verificado**, fonte, status e data_base.
3. `entidades.csv`: entidade, nome exibido, família, tipo de métrica, unidade, regra, status.
4. `grupos_economicos.csv` e vínculo temporal `dist_grupo.csv`.
5. `dda_descricoes.csv`: entidade, atributo, código interno, descrição, domínio e versão.
6. `ativos_agregados.csv` (ou lotes por entidade) no grão documentado, e `matriz_empresas_2025.csv` com todos os ativos e N/D explícito.
7. `geo/arat_2025.geojson` ou múltiplos `geo/arat_2025_<dist>.geojson` **com geometria oficial simplificada**.
8. `qa_reconciliacao.csv` e `RELATORIO.md`: contagens originais x agregadas por `DIST/entidade`, auditoria de junções, CRS e simplificação de ARAT, faltas, erros, classificação de privacidade, licenças e resultados.
9. `schemas/contrato_publicacao.json`: campos e tipos exatos de cada arquivo para leitura pelo frontend/API, `schema_version`.

TESTES MÍNIMOS: (a) **100% dos snapshots publicados são 2025-12-31**, (b) cada DIST publicado tem fonte/hash/QA, (c) contagens reconciliadas, (d) ARAT válida ou ausência explícita, (e) todos os filtros DDA usados são suportados pela entidade, (f) empresa×grupo e grupo×grupo não duplicam itens, (g) nenhuma coluna individual/sensível no pacote público, (h) CSVs e GeoJSON validam schema.

## Formato da resposta do Claude
Ao terminar **cada etapa**, informe o que está concluído, a quantidade real de distribuidoras 2025 encontradas, volumes por entidade, URLs consultadas, arquivos produzidos, falhas e próximos itens. Não afirme conclusão nacional caso tenha apenas processado uma amostra. Se 2025 ainda não estiver publicado para determinadas empresas, registre fato verificável, sem trocar por 2024.

**Não criar serviço pago, não publicar produção, não alterar main e não usar credenciais sem instrução explícita.** O ChatGPT fará integração web e banco quando receber os agregados e o relatório.


## Atualização obrigatória após o piloto de 3 GDBs (22/10/2026)

Antes de prosseguir com as outras 96 bases, leia estes documentos mais recentes no MESMO diretório de projeto:

- `docs/DECISOES-PILOTO-2025.md` — decisões vinculantes após o diagnóstico do piloto.
- `docs/CONTRATO-DADOS-2025.md` — pacote interoperável com a aplicação web, incluindo métricas brutas/distintas e campos de QA.
- `database/schema.sql` — esquema atualizado com `quantidade_registros`, `quantidade_cod_id_distinto`, `status_qualidade` e `motivo_qualidade`.
- `etl/validate-publication.mjs` e `etl/tests/smoke.mjs` — validação estrutural de publicação.

**Decisão:** prosseguir em lotes pequenos (3–5 empresas), sem consumir toda a RAM/disco. Preservar staging e ZIPs localmente; não subir arquivos individuais. Os totais de UCs são diferentes dos registros brutos, e potência anômala de geração não deve ser corrigida por corte arbitrário. Enviar primeiro os quatro artefatos do inventário/piloto para revisão, depois validar o contrato com dados reais.

Se for possível, usar `pyogrio.open_arrow(..., use_pyarrow=True, batch_size=65536)` para ler batches sem materializar camadas inteiras; configurar memória/threads/tamanho de swap do DuckDB explicitamente, ajustando aos ~8 GB físicos da máquina.

## REGRA ADICIONAL — BI VPE 2024 NÃO É GABARITO DE NÚMEROS 2025

O usuário esclareceu explicitamente: **o Power BI VPE de referência foi feito com BDGD DATA_BASE = 31/12/2024**; o pipeline nacional aqui é **exclusivamente DATA_BASE = 31/12/2025**. Nunca usar o valor numérico de qualquer medida do VPE 2024 como valor esperado para dados 2025 nem interromper downloads/agregações quando houver divergência entre exercícios. Utilizar BI VPE apenas para entender o método de cálculo, medidas, universo, tratamento de entidades e filtros. Validar resultados de 2025 **contra a própria GDB 2025**, com reconciliação direta e auditoria de relacionamentos e chaves. Não misturar 2024/2025 para "fazer bater". Separar no relatório `validacao_metodologica_vpe_2024` de `reconciliacao_origem_bdgd_2025`. Regras e modelos que mudaram de 2024 para 2025 precisam de adaptação e registro da diferença metodológica, nunca ajuste artificial de números.


## ADENDO DE INTEGRAÇÃO — CONTRATO 1.1.0 (TOTAIS + FACETAS)

Após o segundo diagnóstico, o ChatGPT **aceitou sua sugestão de separar** os fatos totais das agregações DDA. Consulte antes de montar o pacote: [MODELO-FATOS-FACETAS-2025.md](MODELO-FATOS-FACETAS-2025.md) e a versão atualizada de [CONTRATO-DADOS-2025.md](CONTRATO-DADOS-2025.md).

1. **Não refazer GDBs por conta desse contrato.** Reaproveitar staging local e checkpoints. Continue a extração nacional em lotes; é possível gerar cubos DDA a partir das partições locais.
2. `ativos_agregados.csv`: uma linha por `DIST×entidade` (`dimensoes_json={}`), sem distinções DDA; matriz é derivada apenas desse arquivo.
3. `ativos_facetas.csv`: grupos independentes por `facet_id` e métricas; `facetas_catalogo.csv`: listas de atributos, unidade, cobertura, disjunção e autorização de rollup; não somar cubos entre si.
4. `COUNT(DISTINCT)` no filtro: contar no conjunto filtrado ou faceta conjunta válida; nunca adicionar distintas de categorias em conflito. Em caso de duplicidade de `COD_ID` com atributos conflitantes, marcar `particao_disjunta=nao` e proibir rollup da métrica; um filtro exato pode ser exibido só se auditado.
5. Para `UG*` e `UNTRMT/EQTRMT`, sem correção automática de `POT_INST`/`POT_NOM`/DDA. Preservar campo e unidade originais no staging privado, bloquear exclusivamente indicador de potência não homologado, mantendo contagens auditadas disponíveis.
6. O contrato de intercâmbio com facetas usa `schema_version=1.1.0`; o piloto antigo `1.0.0` continua aceito só para totais. Executar `node etl/tests/smoke.mjs` e `node etl/validate-publication.mjs <pasta>` no PC e enviar stdout/stderr.
7. Nenhuma comparação quantitativa com BI VPE de 2024. Validar somente com BDGD 2025.

**Não alterar main.** Se for publicar em branch separada, enviar apenas scripts, inventário, relatório, manifest e agregados/ARAT públicos **depois de revisão de privacidade e licença**. Não publicar GDBs, staging Parquet nem segredos.
