# Prompt operacional para Codex — ETL histórico BDGD 2022, 2023 e 2024

## Missão

Atue como engenheiro de dados sênior e desenvolvedor Python especializado em SIG, File Geodatabase, GDAL/pyogrio, DuckDB, validação estatística e GitHub. Execute **neste PC local** a descoberta, download, inspeção, transformação, agregação e auditoria das BDGDs oficiais com datas-base **31/12/2022, 31/12/2023 e 31/12/2024**, de todas as distribuidoras que efetivamente possuam essas competências. Ao finalizar, **publique scripts, contratos, inventários e relatórios não sensíveis em uma branch própria no GitHub**, com commits e PR, e devolva os links para o usuário compartilhar com ChatGPT e Claude.

A BDGD de **31/12/2025 está sendo processada por OUTRO agente/máquina**. NÃO baixar 2025 novamente, NÃO alterá-la, NÃO sobrescrever checkpoints de 2025, NÃO modificar a `main` nem a branch do portal `feat/nucleo-dados-bdgd-portal`. Este trabalho é separado e tem finalidade futura de **séries históricas comparáveis e módulo preditivo**, não de preencher a tela atual com números misturados.

### Repositório a utilizar

- URL: https://github.com/artelias/BDGD
- Branch de referência de especificações: `feat/nucleo-dados-bdgd-portal`
- Diretório do produto: `nucleo-dados-bdgd/`
- Branch que VOCÊ deve criar e usar para seu trabalho: `feat/bdgd-historico-2022-2024` partindo da branch de referência existente. **Não** fazer push de scripts históricos na `main` nem na branch 2025.
- Diretório de código novo, versionável, proposto: `nucleo-dados-bdgd/historico/`
- Documentos obrigatórios: `docs/PLANO-GERAL.md`, `docs/MODULO-PREDITIVO-ML.md`, `docs/CONTRATO-DADOS-2025.md`, `docs/MODELO-FATOS-FACETAS-2025.md`, `etl/README.md`, `etl/validate-publication.mjs`.

Fonte primária: https://dadosabertos.aneel.gov.br/dataset/base-de-dados-geografica-da-distribuidora-bdgd e respectivo repositório ArcGIS da ANEEL. Confirmar URLs na própria API/portal antes de acessar. Não deduzir URLs individuais nem usar download de sites não oficiais. A fonte publica GDB por distribuidora; a origem pode ser ZIP.

## Condição crítica: scripts Python do Claude podem NÃO estar neste computador

O relatório anterior informou scripts `D:\NUCLEO_BDGD_2025\scripts\bdgd_etl.py` e `D:\NUCLEO_BDGD_2025\scripts\run_lote.py` numa máquina Windows. Contudo, ao conferir o GitHub, os arquivos **não estavam versionados** na branch do portal. Este Codex pode estar em **outra máquina**. Portanto:
1. Inspecionar primeiro discos, pasta de trabalho, clones locais, acesso aos scripts 2025, ambiente Python e permissões Git.
2. Se scripts e manifest de 2025 **estiverem presentes e utilizáveis**, ler código e testes, e **reutilizar/parametrizar com cuidado**, sempre copiando para pasta separada e isolando `DATA_BASE` por ano. Não alterar o processo 2025 que esteja rodando.
3. Se scripts não estiverem presentes, NÃO pressupor que existem e NÃO afirmar reutilização. Criar pipeline 2022–2024 a partir de especificações e informações verificadas, documentando claramente essa decisão. Usar ferramentas disponíveis no PC e ambiente isolado.
4. Não solicitar novo login/token via mensagem pública; caso seja necessário autenticar no GitHub, seguir fluxo seguro do `gh auth login` ou credencial existente, sem registrar secrets em código/log.

## Passo 0 — inspeção e segurança

- Identificar SO, versão Python, CPU/RAM, espaço em disco por unidade, rede e Git/gh; escolher diretório de dados **fora** do clone e em unidade com espaço suficiente. Criar venv específico para processamento histórico com GDAL/pyogrio e DuckDB, pyarrow, shapely/pyproj conforme necessidade.
- Nunca carregar todas as bases nem todos os anos na RAM simultaneamente; priorizar streaming, batches, arquivos colunares locais, spill de DuckDB, índices por `DIST,DATA_BASE,entidade`, e checkpoint por distribuidora/ano.
- Inspecionar arquivos `.gitignore`/Git LFS antes de criar pastas. Nenhum bruto, GDB/ZIP, Parquet de staging ou identificador individual entra no GitHub. Não versionar credenciais ou logs com segredos.
- Não mexer em processos Python em execução, principalmente um eventual ETL BDGD 2025; não encerrar serviços e não elevar privilégios desnecessariamente.

## Passo 1 — inventário nacional ANEEL com paginação e rastreabilidade

1. Consultar o catálogo ArcGIS/Open Data da ANEEL, API REST e suas páginas de detalhe; pesquisar TODAS as publicações GDB para 2022, 2023 e 2024, incluindo revisões. Usar paginação integral, registrar URL/consulta, data e contagem de itens.
2. Montar a lista por `DIST × DATA_BASE` com competência EXATA `2022-12-31`, `2023-12-31` ou `2024-12-31`. **Data de upload do arquivo NÃO é data-base.** Confirmar BASE/`DAT_FNL` ou campo equivalente e `DIST` no GDB antes de classificá-lo como válido. Analisar versão de layout de cada ano e não presumir V11/43 entidades em todo o histórico.
3. Não tomar automaticamente 99 distribuidoras de 2025 como total do histórico. Registrar todas as disponíveis por ano e indicadores de painel longitudinal (interseção 2022–2025 por DIST), sem usar ausência como zero. Detectar fusões, mudanças de código e permanência do controle econômico.
4. Para múltiplos GDB de mesma empresa/competência, preferir versão oficial corrigida mais recente quando isso puder ser comprovado, preservando URLs e hashes de versões anteriores para auditoria.
5. Produzir `inventario_historico_2022_2024.csv`: `dist,empresa,ano,data_base,item_id,url_item,url_download,layout_versao,publicado_em,atualizado_em,tamanho_bytes,download_disponivel,status,motivo,sha256`.
6. Produzir `cobertura_historico_2022_2024.json` e `RELATORIO_INVENTARIO_HISTORICO.md` com números encontrados, elegíveis e faltantes por competência, além de limitações da consulta.

**Primeiro checkpoint de entrega:** inventário verificável antes de downloads grandes. Prosseguir sem exigir confirmação se rede/disk e disponibilidade forem adequados; se algum lote falhar, registrar e seguir os demais.

## Passo 2 — piloto e ingestão resiliente

- Executar um piloto de **3 distribuidoras com GDB disponível nos três anos**, preferencialmente de portes/grupos diferentes e com 2025 já conhecido, mas SEM baixar novamente 2025. Se indisponível, selecionar distribuidoras disponíveis e documentar anos faltantes.
- Baixar ZIP/GDB de 2022, 2023 e 2024 com HTTP Range quando disponível, checksum SHA-256, retomada, retries exponenciais e testes de integridade ZIP.
- Limitar concorrência e memória, usar 2–4 downloads/processamentos no máximo inicialmente, monitorar I/O e armazenamento; permitir cancelamento seguro e retomada automática. GDBs extensos podem descompactar para muitos gigabytes. Não estimar armazenamento total antes do inventário.
- Inspecionar `BASE`, `DIST`, `DAT_INC`, `DAT_FNL`, `DAT_EXT`, nomes e tipos de campos, CRS e camadas presentes. Validar a competência apropriada por item/ano; onde estiver inconsistente, colocar o item em quarentena sem contaminar a base.
- Converter em Parquets particionados locais se necessário, com documentação de versões GDAL/pyogrio, metadados por entidade e contagem GDB↔staging idêntica.

## Passo 3 — semântica e harmonização 2022–2025

- Referência obrigatória: Manual BDGD/PRODIST vigente à data de cada GDB; **NÃO assumir que estruturas, atributos, TUC/A1..A6, DDA ou 43 entidades são idênticos de 2022 a 2025**.
- Os catálogos do IA Builder podem existir em outra máquina. Se estiverem disponíveis, verificar hashes/versões e utilizar o que for compatível. Se ausentes, não inventar domínios; usar documentação pública e marcar `nao_homologado` quando necessário.
- Para chaves e vínculos, usar `DIST + COD_ID` **por entidade e ano**, com verificação de N:N e duplicações. Não criar falsa identidade longitudinal dos ativos sem verificar persistência de COD_ID entre anos.
- Tratar métricas separadas, com mesmo método que foi definido para 2025: `quantidade_registros`, `quantidade_cod_id_distinto`, `quantidade` (somente quando homologada), `extensao_km`, `potencia_kva`. Uma linha TOTAL por `DIST × DATA_BASE × entidade`; facetas DDA separadas e apenas se houver interpretação/cobertura verificáveis. Não misturar fatos e facetas para somar.
- Tratar dados suspeitos do mesmo modo que o piloto 2025: `UG*` e SIGFI: unidade e potência podem ser incompatíveis; `UNTRMT` vs `EQTRMT`: não somar duas visões do mesmo equipamento; `COD_ID` duplicado/conflitante: preservar registros e distintos; `CTMT` órfão: bloquear apenas a faceta/cálculo comprometido.
- Harmonização: por `entidade,metrica,unidade,metric_version,ano`, registrar `comparavel_2025=sim/nao/parcial`, regra de transformação, causa da incompatibilidade e evidência. Não forçar igualdade entre quantitativos 2024 e 2025; BI VPE 2024 é **referência metodológica**, não gabarito quantitativo.
- Grupos econômicos: só vinculados mediante fonte/vigência histórica verificada, nunca inferidos apenas pelo nome. Se não confirmado, `nao_confirmado`.
- Cálculos por circuito/UF e ARAT podem mudar no tempo; opcionalmente gerar ARAT histórico simplificado por ano, quando viável e autorizado em tamanho; **não substituir a ARAT 2025 usada no portal atual**.

## Passo 4 — produto histórico compatível com futura modelagem

Gerar `saida-historica-publicavel/` **apenas com dados agregados e metadados revisados** (o rótulo 'publicavel' não significa publicação automática). Estrutura sugerida:
```text
saida-historica-publicavel/
  inventario_historico_2022_2024.csv
  cobertura_historico_2022_2024.json
  RELATORIO_INVENTARIO_HISTORICO.md
  RELATORIO_QA_HISTORICO.md
  historico_ativos_agregados_2022_2024.csv
  historico_entidades_metricas.csv
  harmonizacao_2022_2025.csv
  qa_reconciliacao_historica.csv
  alertas_qualidade.csv
  grupos_temporais.csv                     # só se confirmado
  manifest_historico.json
  schemas/contrato_historico.json
  geo/arat_historica_<ANO>_<DIST>.geojson  # OPCIONAL, se homologada
```
Cada registro do fato histórico terá, no mínimo,
`dist,ano,data_base,entidade,metrica,valor,unidade,metric_version,status_qualidade,motivo_qualidade,comparavel_2025`.
Ausência de dado = vazio/ND e cobertura explícita; nunca zero artificial. Proveniência por `DIST × ano` com URL oficial, SHA256, versão de layout e QA.

Montar relatório de **painel balanceado por DIST e entidade** para 2022–2025: para 2025 pode usar **apenas informação disponível e homologada**, por exemplo manifest/planilha pública fornecida pelo usuário; se 2025 não estiver acessível, preparar o join 2025 futuro, sem fabricar valores ou baixar 2025. Registrar `ano=2025` como 'aguardando' no índice de comparabilidade caso seja necessário.

**Não treinar modelos ML nesta tarefa.** A etapa atual é construir histórico comparável; treinamento e forecast 2026–2029 serão tarefas posteriores do Claude e ChatGPT, depois de auditoria.

## Passo 5 — QA obrigatório e testes automáticos

- Testar data-base para cada registro/entidade conforme as especificações de 2022/23/24; DIST íntegro; GDB íntegro; contagem GDB↔Parquet (se convertido); totalização por entidade sem duplicidade de junção; nulidade vs zero; checagem de unidades/DDA; sanidade e cobertura das ARAT caso produzidas.
- Escrever testes `pytest` ou `unittest` para validação histórica, legibilidade CSV/JSON, compatibilidade de schema, retomada e cálculo de atributos de cobertura. Usar o validador JS do portal somente onde a sua competência rígida 2025 fizer sentido: **não adaptar/afrouxar `validate-publication.mjs` para permitir 2022–2024 na saída pública 2025**. Criar validador separado em `historico/validate_historico.py`.
- Testar piloto de 3 e depois escalar em lotes de 4 (ou menos se RAM/disco exigir), sem perder checkpoints. Não declarar 'todos' sem conferir contagem dos itens realmente processados e casos em quarentena.
- Gerar relatório de diferenças por ano, por DIST e entidade, com séries incompatíveis marcadas como `nao_comparavel` — **não alterar a origem para "fazer bater"**.

## Passo 6 — integração e comunicação com GitHub

- Clonar `artelias/BDGD` se necessário, verificar login GitHub e configurar remoto; criar branch **`feat/bdgd-historico-2022-2024` a partir da branch `feat/nucleo-dados-bdgd-portal`**.
- Usar `git status` para não sobrescrever mudanças alheias, revisar `.gitignore`, e garantir que dados históricos grandes e sensíveis nunca sejam rastreados. Versionar **código**, documentação, scripts de ambiente, testes, arquivo de configuração exemplo, inventário sem dados privados, relatórios de cobertura e pequenos agregados **somente após aprovação de privacidade/licença**.
- Se o inventário ou agregados públicos forem grandes, **não** fazer push dos arquivos grandes ao GitHub; registrar caminho local e produzir manifesto/checksums e um pacote pequeno representativo. GDB, ZIP originais, Parquet de staging, dados individualizados, perfis de UC e segredos permanecem locais.
- Fazer commits atômicos com mensagens descritivas, enviar branch ao remoto e **abrir Pull Request para a branch `feat/nucleo-dados-bdgd-portal`**, sem merge automático nem mudanças em `main`. Se o repositório for público, nenhum dado ainda não aprovado/individualizado pode ser anexado ao PR. Se não tiver permissão, registrar o motivo e emitir comandos/diff para publicação manual; não fingir que enviou.
- Enviar link da branch e PR; listar SHA do commit e arquivos criados, lista de distribuidores/anos concluídos, alertas, QA, próximos passos, tamanho em disco, histórico disponível para 2025 e caminhos locais para o operador.

## Ordem de execução e status final

1. Inventário → piloto três distribuidores → reuso/composição do ETL histórico → lotes por ano/DIST → harmonização/QA → publicação do código e resultados não sensíveis em branch → PR → relatório final.
2. Se a sessão Codex atingir limite ou interromper, preservar estado e **deixar um único comando determinístico de retomada** que salte registros com checkpoint e revalide status. Não declarar a execução nacional concluída.
3. Informar para ChatGPT e Claude a URL real da branch/PR e contrato histórico. Relatar separadamente `2022: N/T`, `2023: N/T`, `2024: N/T`, empresas ausentes, erros, QA e séries comparáveis.
4. Não pedir autorização para passos técnicos rotineiros já autorizados neste prompt (inventariar, baixar fontes públicas e processar localmente), mas **não criar infraestrutura paga, não alterar main, não enviar dados brutos/sensíveis e não fazer deploy**.

**Importante:** a seleção 2022–2024 é para projeto preditivo posterior. A versão atual do site permanece ancorada **exclusivamente em 2025**. Os dados históricos não passam automaticamente a ser dados oficiais do portal, nem o primeiro treinamento está autorizado nesta tarefa.
