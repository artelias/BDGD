> **INSTRUÇÃO ATUALIZADA DE RELEASE (23/10/2026):** a revisão R2 e o limite de ações Vercel agora são regidos por [PROMPT-CLAUDE-EXECUCAO-R2-ATE-PREVIEW.md](PROMPT-CLAUDE-EXECUCAO-R2-ATE-PREVIEW.md). **O Claude NÃO deve publicar nem promover produção.** Deve entregar PR, CI, QA e preview para que o ChatGPT faça auditoria e publicação apenas mediante comando posterior explícito do proprietário. Essa regra prevalece sobre quaisquer instruções antigas deste documento que autorizassem deploy em produção automaticamente.

# PROMPT MESTRE CLAUDE — entregar dashboard BDGD 2025 e, após publicação, continuar ETL histórico 2022–2024

**Instrução do proprietário do projeto:** execute as etapas abaixo, com código, testes, GitHub e publicação de site quando puder ser feita com segurança e sem custo adicional. Você está no mesmo PC Windows que executa BDGD 2025 e que foi usado pelo Codex para piloto 2022–2024. **Não construa nem treine modelos preditivos nesta execução.**

**Modelo sugerido ao proprietário:** Claude Opus 5.5 — Alto para arquitetura, DDA, QA e eventos societários; Claude Sonnet 5.5 — Médio para geração de código, ETL repetitivo e correções rotineiras. O modelo escolhido não altera prioridades nem etapas.

## 0. Estado real conhecido e repositório

- GitHub do projeto: https://github.com/artelias/BDGD
- Branch de desenvolvimento atual do portal: `feat/nucleo-dados-bdgd-portal`; preservar a `main`.
- Web demonstrativa existente: `nucleo-dados-bdgd/index.html`, `styles.css`, `app.js`; mapa e indicadores ainda **fictícios**, visualização não regulatória. Protótipo não é site de produção.
- Documentos de leitura obrigatória:
  - `nucleo-dados-bdgd/README.md`
  - `nucleo-dados-bdgd/docs/PLANO-GERAL.md`
  - `nucleo-dados-bdgd/docs/CONTRATO-DADOS-2025.md` (fatos totais vs cubos DDA, schema 1.1.0)
  - `nucleo-dados-bdgd/docs/MODELO-FATOS-FACETAS-2025.md`
  - `nucleo-dados-bdgd/docs/DECISOES-PILOTO-2025.md`
  - `nucleo-dados-bdgd/docs/HARMONIZACAO-SUCESSAO-2022-2025.md`
  - `nucleo-dados-bdgd/docs/MODULO-PREDITIVO-ML.md` (**apenas planejamento, sem treinamento**)
  - `nucleo-dados-bdgd/docs/PROMPT-CODEX-HISTORICO-2022-2024.md` (continuidade após conclusão do site).
- Tarefas: https://github.com/artelias/BDGD/issues/1 (2025), https://github.com/artelias/BDGD/issues/3 (histórico), https://github.com/artelias/BDGD/issues/2 (previsões **futuras**).
- Mesmo computador: `D:\NUCLEO_BDGD_2025` (scripts `scripts\bdgd_etl.py`, `scripts\run_lote.py`, inventário, staging, checkpoints, agregados e ARAT), `D:\NUCLEO_BDGD_2022_2024` (trabalho piloto histórico iniciado pelo Codex, verificar conteúdo real). **Não presumir** completude de qualquer pasta.
- Disco D: HD de ~1 TB para dados grandes, C: SSD de ~500 GB com pouco espaço livre. RAM ~8 GB. Não rodar dois ETLs pesados em paralelo; enquanto download/conversão 2025 ocorre, desenvolver UI/API/testes e inspecionar contratos com consumo de memória controlado.
- A inspeção remota mais recente não mostrou o `bdgd_etl.py` ou `run_lote.py` versionados no GitHub. **Inclua o código limpo (sem dados locais nem segredos)** em uma pasta ETL apropriada na branch do projeto.

## OBJETIVO EM DUAS FASES SEQUENCIAIS

**FASE A — AGORA, enquanto 2025 ainda baixa:** concluir pipeline e dashboard público real, GitHub, preview, validação e publicação **somente quando dados de 2025 estiverem aprovados**. Esta fase é a prioridade inegociável.

**FASE B — SOMENTE DEPOIS de concluir Fase A, publicar código/site/relatório de 2025 e conferir QA:** assumir o histórico iniciado pelo Codex, retomar o ETL de **31/12/2022, 31/12/2023 e 31/12/2024** sem reiniciar dados já baixados, e pesquisar todas as sucessões/incorporações relevantes de distribuidoras. Construir séries brutas e comparáveis ao perímetro 2025. **NÃO iniciar Machine Learning nem previsões.**

### Gate formal entre fases

Só inicie a Fase B quando:
1. Todas as distribuidoras 2025 elegíveis estiverem concluídas ou exceções individuais/quarentena devidamente documentadas, sem afirmar cobertura 100% indevidamente.
2. Pacote público 2025 `schema_version=1.1.0` (ou 1.0.0 temporário com **facetas indisponíveis declaradas**) gerado, reconciliado, sanitizado e validado; grupos com fontes comprovadas.
3. Dashboard **integrado a resultados reais 2025**, testado, e site publicado com URL verificável em infraestrutura autorizada **ou** impedimento de publicação explicitamente documentado com preview funcional e instruções de permissão.
4. Código, instruções, testes, contratos e relatório do release registrados no GitHub em branch/pull request, sem mudar `main` inadvertidamente.
5. Os scripts históricos puderem ser executados sem afetar o ETL 2025; se ainda estiver em curso, prioridade do 2025.

Se publicação estiver bloqueada por autenticação/permissão, **não inventar URL publicada** e não descartar progresso; concluir todas as demais entregas possíveis, registrar o impedimento e então continuar a fase B se os dados 2025 tiverem sido totalmente homologados e enviados ao GitHub.

## FASE A1 — inventário e retomada BDGD 2025, sem rebaixar arquivos

1. Verifique o estado dos processos ativos, checkpoint, `inventario_2025.csv`, `cobertura_2025.json`, scripts, logs e armazenamento em `D:\NUCLEO_BDGD_2025`. Relatórios anteriores indicaram 99 fontes GDB com data-base 31/12/2025 e dezenas de distribuidoras concluídas, porém você deve conferir o estado **atual**, não confiar em fotografias antigas.
2. Se o processo Python 2025 estiver rodando, **não abra outro run_lote**. Caso tenha terminado, verifique total, falhas/quarentena, GDBs, HASH, BASE/`DAT_FNL`, `DIST`, ARAT, entidades e reconciliações.
3. Corrija somente falhas legítimas, preservando originais e checkpoints. Não misture competências e não tratar alertas de QA como sucesso automático nem como falhas fatais de todo o release.
4. Investigue anomalias já relatadas: UCBT repetida/conflitante na Energisa AC; CTMT órfã na CEA; SIGFI em UG* com `POT_INST` sem semântica comprovada; diferenças `UNTRMT.POT_NOM` vs `EQTRMT`, DDA potenciais inconsistentes. Não fazer corte automático ou "acertar" o GDB original. Bloquear indicadores específicos se não homologáveis e expor N/D.
5. Reconciliar resultados GDB 2025→staging→fatos totais→matriz→KPIs e facetas aprovadas. **BI VPE é de 2024 e serve somente de referência metodológica**, não gabarito quantitativo de 2025.

## FASE A2 — contrato, fatos, facetas, grupos e ARAT para publicação

- Manter **uma linha por `DIST × entidade × data_base=2025-12-31`** em `ativos_agregados.csv`, `dimensoes_json={}`. `quantidade`, `quantidade_registros`, `quantidade_cod_id_distinto`, `extensao_km`, `potencia_kva` com unidade e estado QA; matriz por DIST gerada **só** do total-base; entidades não presentes/indicador bloqueado = nulo/N/D, não zero falso.
- Em separado, `ativos_facetas.csv` e `facetas_catalogo.csv` na versão 1.1.0, identificando `facet_id`, dimensões DDA conjuntas, código↔descrição por entidade/versão, cobertura, disjunção, qualidade, permissão de rollup por métrica. **Não somar histogramas DDA sobrepostos nem COUNT(DISTINCT) sem partições comprovadamente disjuntas.** Para múltiplos filtros DDA, usar cubo conjunto compatível, jamais produto de percentuais marginais.
- Investigar e homologar grupo econômico/controlador por `DIST` **na competência 2025**, com fonte verificável e vigência. Se não comprovado, `nao_confirmado`, e evitar falsos agrupamentos.
- ARAT 2025: usar exclusivamente poligonais reais da entidade ARAT de cada GDB, convertidas para EPSG:4326 com ordem de coordenadas correta, simplificação topológica auditada e perda de área medida; multipolígonos, buracos e sobreposições tratados. Não usar centroide, retângulo, contorno de UF ou regiões inventadas.
- Criar manifesto e pacote `output-publicavel/2025-12-31/` conforme contrato; log de cobertura 99 elegíveis, ausências, status por DIST e campo; licença/atribuição ANEEL, privacidade, checksums e amostras QA.
- Rodar `node etl/tests/smoke.mjs` e `node etl/validate-publication.mjs <pasta_do_pacote>` com stdout/stderr no relatório; se houver defeitos do validador, corrigir com testes de regressão, nunca enfraquecer critérios para fazer os dados "passarem". Se o contrato de 1.1.0 mudar, versionar e atualizar frontend/testes.
- Publicar SOMENTE agregados sanitizados. **Não** subir GDBs/ZIPs/Parquets brutos de UC, `COD_ID`, CPFs, identificadores de consumidores, token ou credenciais para GitHub, Vercel, Supabase ou browser. Não publicar dados de amostra fictícios como reais.

## FASE A3 — desenvolvimento do dashboard REAL e responsivo

Converter o protótipo HTML demonstrativo em aplicação profissional, conforme `PLANO-GERAL.md`, preferencialmente **Next.js + TypeScript + React + Lucide + MapLibre GL + ECharts**. Avaliar viabilidade de manter aplicação estática bem construída como passo intermediário caso o provisionamento do banco esteja bloqueado, mas entregar código testado e arquitetura expansível. Não apagar recursos funcionais da interface anterior antes de substituí-los por equivalentes.

**Identidade do site: `Núcleo de Dados da BDGD`, atribuição no rodapé `Desenvolvido por Arthur Henrique Elias de Lima`.** **O padrão de UI/UX exigido é premium, minimalista, sofisticado e autoral, com motion design e microinterações personalizadas**, sem aparência genérica de template ou de painel gerado por IA. Essa é uma exigência de aceitação, não sugestão estética. **LEIA E EXECUTE INTEGRALMENTE**: [DIRECAO-ARTE-UIUX.md](DIRECAO-ARTE-UIUX.md). Nele estão especificados design tokens, tipografia, paleta light/dark própria, composição sob medida, animações, comportamentos do mapa e gráficos, acessibilidade, screenshots e rodadas de refinamento.

Páginas / seções mínimas:

**1. Panorama Brasil**
- Data-base única 31/12/2025, quantidade verificada de distribuidoras cobertas/ausentes, inventário de entidades, grupos com fonte, status de homologação, botão metodologia/fonte ANEEL.
- KPIs com número, unidade, definição e cobertura/denominador; cartões filtráveis; distribuição por grupo, por empresa, por família, rankings, barras e gráficos de distribuição.
- Mapa nacional MapLibre com ARAT **poligonal oficial** por DIST, cores por grupo econômico verificado, hover, seleção, zoom, legenda, busca de distribuidora e detalhes. Para `nao_confirmado`, cor neutra e explicação. Evitar mapa de pontos como substituto.
- Cobertura incompleta explicitada; 15 sem publicação 2025 no inventário (conforme levantamento anterior, revalidar). Não representar ausência como zero.

**2. Matriz nacional de ativos**
- **Todas as entidades BDGD** encontradas/homologadas (43 no layout V11 onde aplicável), não apenas 6 KPIs. Linhas por DIST e empresa; colunas por entidade com código + nome e unidade. Transposição/pivot ou agrupamento por famílias, scroll horizontal, coluna congelada, busca, ordenação, filtros, paginação/virtualização, CSV, metas de performance.
- Permitir alternar métricas válidas: quantidade, quantidade de registros, COD_ID distintos, km, kVA quando disponíveis. Não somar `UNTRMT` e `EQTRMT` como entidades independentes no mesmo KPI de transformadores.
- Filtros de grupo, empresa, família, entidade e valores DDA descritos; explicar filtros não suportados e indicadores bloqueados.

**3. Comparador avançado**
- A e B independentes: empresa×empresa, grupo×grupo, empresa×grupo. Exibir por entidade e métrica: A, B, diferença absoluta, variação percentual (N/D se denominador=0) e cobertura/número de empresas. Evitar dupla contagem e totais intergrupos inconsistentes.
- Permitir seleção de métricas/entidades, ordenação e busca, gráficos comparativos, exportar e compartilhar URL com parâmetros sanitizados. Comparações sempre da mesma data-base 2025.

**4. Exploração por entidade / DDA**
- Selecionar entidade, reconhecer atributos técnicos aplicáveis, apresentar nomes e descrições do DDA e não códigos sem contexto; facetas em cascata.
- Visualização por distribuição de fases, localização urbana/rural, instalação, tensão e atributos TUC/A1..A6 **apenas quando existirem e forem validados para a entidade**. Não inventar domínio/descrição. Quando não houver cubo conjunto, mostrar `combinação indisponível`, não cálculo aproximado.

**5. Metodologia e qualidade**
- Proveniência ANEEL, lista de DISTs incluídos/excluídos, `DATA_BASE=2025-12-31`, regras de contagem, cardinalidade, unidade, dicionário e versões DDA, erros/alertas, indicador homologado/não homologado, licença e créditos.
- Deixar claro o BI VPE 2024 é referência metodológica e **não** referência numérica.

**6. Inteligência Preditiva — FUTURA APENAS**
- Registrar no roadmap/menu opcional como `Em planejamento`, sem apresentar resultados calculados, sem treinar ML, sem usar dados 2022–2024 no dashboard 2025.

Ao lado de cada KPI e exportação incluir fonte, status e data-base. **Nenhum número real pode ter fallback silencioso para amostras fictícias.** Quando sem dados, apresentar estado vazio/indisponível.

### A3.0 — Direção principal definida pelo responsável: experiência inspirada na Apple

**A principal referência visual desejada é o padrão de acabamento da Apple.** Referenciar princípios de Apple Maps, Apple Health e macOS/iPadOS, **sem copiar os produtos**. Criar uma aplicação de dados própria, com layout de aparência calma e premium, fundo e superfícies neutras, bordas quase imperceptíveis, tipografia de sistema com hierarquia editorial, acento cromático comedido, clareza das métricas e efeitos de profundidade leves apenas onde fizerem sentido.

**O requisito não é só usar um tema semelhante.** Desenvolva animações fluidas e microinterações sob medida nos filtros, menus, navegação, painéis do mapa ARAT, seleção de empresa/grupo, gráficos e comparador; respostas imediatas, transições físicas discretas, painéis contextuais semelhantes no comportamento (não na cópia visual) ao Apple Maps, atenção à ergonomia de smartphone e suporte a redução de movimento. **Evite aparência genérica de IA, templating de cards, glassmorphism exagerado, neons, bordas decorativas e animações gratuitas.**

Design e funções precisam atingir a mesma qualidade **mesmo sem deploy na Vercel**: rodar, revisar screenshots e interações em desktop/mobile e light/dark, refinar e versionar o resultado localmente no GitHub. [Especificação visual completa](DIRECAO-ARTE-UIUX.md).

### A3.0.1 — Biblioteca opcional de microinterações recomendada pelo responsável

Consultar **https://21st.dev/** ao implementar componentes interativos com React/TypeScript/Tailwind. O site oferece código e demonstrações de botões, menus, componentes animados e padrões de UI. Selecionar criteriosamente recursos que sejam úteis para a navegação e exploração da BDGD; usar como inspiração ou adaptar componentes individuais, **não importar templates completos** nem descaracterizar a proposta Apple-inspired, minimalista, sofisticada e autoral.

Leia a seção de integração em [DIRECAO-ARTE-UIUX.md](DIRECAO-ARTE-UIUX.md). Antes de copiar qualquer implementação, conferir **licença do componente, dependências, acessibilidade, responsividade, custo de bundle, suporte a `prefers-reduced-motion` e conformidade com o design system**. Evitar animações gratuitas, partículas, shaders/WebGL decorativos e superfícies chamativas que disputem atenção com os dados. Não instalar serviços pagos nem chaves 21st.dev.

 
### A3.1 — Critério obrigatório de design refinado

Antes de classificar o dashboard como concluído:
- Entregar **direção de arte** com paleta, tipografia, hierarquia, grids e regras de interação, evitando glassmorphism/gradientes/neons genéricos, cards repetitivos e aparente template de IA.
- Implementar **microinterações sob medida** nas transições de páginas, menu lateral, mapa ARAT real, filtros DDA em cascata, seletores, estados carregando/vazio/erro, tooltips, comparador e gráficos; movimentação elegante e informativa (aprox. 180–280 ms para transições pequenas), com `prefers-reduced-motion` respeitado.
- Testar e **inspecionar screenshots reais** do produto nas quatro páginas principais, desktop/mobile, temas light/dark; executar **duas rodadas de revisão visual** e corrigir espaçamentos, alinhamento, tipografia, interatividade e contraste.
- A aparência deve ser de um **produto de dados profissional e singular**, não um mockup estático nem template pronto; a animação nunca pode comprometer precisão, performance ou acessibilidade.
- A impossibilidade de fazer deploy na Vercel **não reduz o escopo de design**: o produto precisa funcionar localmente com a experiência completa.

## FASE A4 — backend, GitHub, infraestrutura e publicação

1. Escolher a menor arquitetura operacional adequada. Para matriz agregada 99 DIST × ~43 entidades + catálogo e ARAT otimizada, **avaliar começar com arquivos JSON/GeoJSON públicos versionados + CDN**, evitando dependência de banco sem necessidade; para facetas grandes ou consultas complexas, **PostgreSQL/PostGIS** e API read-only server-side (Supabase é proposta, não obrigação). Justificar custo, limites e segurança.
2. **Vercel:** criar projeto **novo** para Núcleo de Dados da BDGD no escopo autorizado do proprietário. Não reutilizar/modificar o projeto existente `geoia-data-hub`. A integração anterior pelo ChatGPT retornou `403 forbidden` ao criar novo projeto; você pode inspecionar autenticação/escopo com CLI oficial ou interface e tentar no plano gratuito. Se faltar autorização, registrar claramente qual permissão do usuário é necessária, sem simular sucesso. Não criar recursos cobrados/upgrade/serviço pago sem aprovação explícita.
3. **GitHub:** versionar toda implementação, docs, testes, configuração de deploy, variáveis-exemplo sem segredos e workflow CI na branch `feat/nucleo-dados-bdgd-portal` ou criar branch curta derivada e PR direcionado a ela. Nunca reescrever trabalho remoto/force push; conferir `git status`, remotos, locks e divergência de commits antes de pull/push. `main` intocada até revisão/merge autorizado.
4. **CI:** executar lint, typecheck, build, testes de contrato/QA e smoke E2E (desktop/móvel, mapa ARAT, filtros, export CSV, light/dark, comparador, estados N/D), validar políticas de segurança e uso de segredos. Corrigir erros. Documentar comandos de execução local/reprodução.
5. **Deploy:** publicar preview para testar; somente promover o site com os agregados oficiais homologados e sem conteúdo sensível. Abrir site pelo navegador e validar rotas, links, assets, dados, comportamento de filtros e download/exportação. Verificar URL/HTTP status para não afirmar site disponível sem evidência. Se possível, configurar domínio padrão Vercel sem custo.
6. Sem dados finalizados, pode publicar **demo explicitamente marcada**, isolada de produção, apenas para avaliação visual; nunca rotular demo como painel oficial. Se produção estiver bloqueada, entregar preview, código no GitHub, documentação e lista precisa de bloqueadores.
7. Entregáveis de Fase A: URL verificável (preview e produção se possível), branch/commits/PR, captura/relatório de testes, manifesto do release, lista de QA, endpoints ou assets, plano de operação e comando de reexecução do ETL.

## FASE B — DEPOIS DA FASE A: histórico 2022–2024 e sucessões

**Apenas após cumprir o gate da Fase A**, retomar o trabalho **já iniciado pelo Codex no mesmo PC**, sem apagar suas mudanças. Localizar `D:\NUCLEO_BDGD_2022_2024`, scripts, venv, inventário, checkpoints, pilotos, branch local ainda não enviada e relatório. O Codex atingiu limite de uso, mas relatou:
- Inventário inicial: **102 distribuidoras com GDB 2022**, **101 com GDB 2023**, **97 com GDB 2024** (números informados, precisam revalidar versões/competências).
- ~109,1 GB ZIPs no inventário incluindo versões duplicadas.
- Primeiro piloto Cocel DIST 7883 de 2022: 286.963 linhas em 42 entidades, 143 reconciliações aprovadas, mas métricas físicas ainda não homologadas.
- Havia compatibilidade DuckDB corrigida, testes de regressão, piloto Cersad/Cerpalo em andamento. Não presumir que ambos terminaram.
- Branch `feat/bdgd-historico-2022-2024` pode existir **localmente**, mas não apareceu no GitHub na última verificação. Conferir antes de criar outra.

### B1. Integridade e extração de todas as competências
- Competências únicas: **2022-12-31, 2023-12-31, 2024-12-31**. **Não baixar 2020 nem 2021**; preservar separada a base 2025. Inventariar GDB por DIST/ano, versões oficiais corrigidas, hashes e BASE no conteúdo.
- Continuar dos checkpoints existentes e testar antes de escalar; lotes pequenos sob RAM ~8 GB / HD D:. Evitar dupla conversão e recursos pagos.
- Reconciliar GDB → Parquet staging → fato histórico por DIST/ano/entidade/métrica. Preservar `quantidade_registros` e `quantidade_cod_id_distinto`, extensões, potências conforme validação semântica por ano. Não assumir layout V11 ou revisão DDA 2026 para bases 2022–2024. Catalogar diferenças e versões de métricas, status `comparavel_2025`. Valores ausentes são N/D, não zero.
- Não adaptar o validador rígido `2025-12-31` para aceitar anos históricos: criar testes/validador histórico independente.

### B2. Pesquisa **sistemática** de incorporações e perímetros
- O objetivo não é só ver nomes antigos; reconstruir **duas séries**: valores originais por DIST/ano e valores comparáveis ao **perímetro societário/territorial da distribuidora sucessora de 2025**.
- Caso obrigatório EPB/EBO: Energisa Borborema incorporada pela Energisa Paraíba, autorização ANEEL REA 12.687 de 13/09/2022 e incorporação formalizada 30/04/2023, **confirmar documentação oficial e DISTs nos GDBs**; em 2022 investigar EPB+EBO somente para entidades/métricas provadamente disjuntas, em 2023 examinar se a EPB já inclui a EBO para não duplicar; não inferir somente pelo nome/grupo.
- Pesquisar **todas as demais** possíveis fusões, incorporações, mudanças de área, transferências de concessão, cisões e renomeações entre 2022 e 2025. Consultar ANEEL/atos societários oficiais e confrontar `DIST`, contratos, `BASE`, `ARAT`, `CONJ`, `CTMT`, datas de autorização vs efetivação; evidenciar o que é hipótese ou caso confirmado.
- Regras canônicas por ano, DIST origem→DIST sucessora vigente 2025, tipo do evento, área total/parcial, entidade, métrica, vigência, fonte, aditividade. Para transferências parciais não somar 100% de uma predecessora. Tratar múltiplos eventos, sem dupla contagem. Mudar grupo econômico não é automaticamente fusão de concessões.
- Gerar os cinco artefatos exigidos em `docs/HARMONIZACAO-SUCESSAO-2022-2025.md`: `eventos_sucessao_distribuidoras.csv`, `ponte_perimetro_2025.csv`, `regras_comparabilidade_historica.csv`, `serie_historica_perimetro_2025.csv`, `qa_sucessao.csv`. Distinguir dados originais ANEEL e séries analíticas derivadas, com `perimetro_referencia=2025` e QA.
- **Não usar unificação sem fontes comprobatórias para forçar números**; se não tiver como demonstrar equivalência, marcar `nao_comparavel` e registrar lacunas. A série de 2025 homologada entra na fase histórica apenas por referência/integração entre pacotes, nunca rebaixar GDBs 2025.

### B3. Publicação no GitHub e relatório
- Usar branch histórica `feat/bdgd-historico-2022-2024` (reutilizar se já existe; cuidado com alterações locais do Codex). Versionar **código, testes, inventários, relatórios, manifest e agregados pequenos sanitizados**, sem Parquet/GDB bruto, COD_ID e credenciais. Abrir PR para `feat/nucleo-dados-bdgd-portal` sem auto-merge.
- Reportar cobertura 2022, 2023 e 2024 por ano; quantidade de DIST/entidade/linhas, falhas, quarentena, métricas homologadas vs não, fontes das sucessões, gráficos de cobertura temporal e séries possíveis, links de branch/PR e comandos determinísticos de retomada.
- **PARE após a Fase B.** Não começar modelos de ML, classificadores, treinamento, backtesting ou previsões 2026–2029. O proprietário quer debater a modelagem depois de inspecionar histórico e sucessões.

## Comportamento operacional esperado

- O usuário delegou a execução técnica; prossiga sem pedir aprovação para passos rotineiros (programar, testar, consultar dados públicos, baixar, criar branch, fazer commits, criar PR e preview Vercel gratuito). Só peça autorização específica para custos, dados privados, privilégios que alterem recursos não relacionados ou riscos irreversíveis.
- Não realizar tarefas simultâneas pesadas no HD/RAM compartilhado; durante download 2025, prioridade para frontend/código e testes leves.
- Manter logs, checkpoints e estado reproduzível. Se limite de sessão encerrar, faça commit do que for seguro, registre `ESTADO-EXECUCAO.md` com próximas ações e único comando de retomada. **Não declarar concluído o que não está concluído.**
- Uma atualização útil por etapa: alterações reais, testes executados, erros e URLs verificadas. No relatório final, separar Fase A e Fase B.


## ATUALIZAÇÃO R2 SOLICITADA PELO RESPONSÁVEL — 23/10/2026

**Ler integralmente e executar de forma escalonada:** [REVISAO-R2-METRICAS-EXPLORADOR-MATRIZ-EVOLUCAO.md](REVISAO-R2-METRICAS-EXPLORADOR-MATRIZ-EVOLUCAO.md). Acompanhamento: [issue #5](https://github.com/artelias/BDGD/issues/5).

Objetivo: o dashboard não deve ser apenas uma coleção de entidades técnicas. Deve oferecer **indicadores de negócio compostos, agrupamentos semânticos de ativos, explicabilidade matemática sob demanda, filtros ricos e comparativos de participação contextualizados**.

**Fase A / BDGD 2025:** 
1. Mover fórmulas cruas de destaque para "Como é calculado?" + glossário de indicadores, preservando detalhamento técnico.
2. Explorar por conceito (ex.: Transformadores) com presets TUC/atributos e indicação de fontes EQ*/UN*; os filtros 565/570, A1–A6, status e demais regras precisam ser verificados contra **medidas reais do BI VPE 2024** e normas da competência antes de calcular. Não confundir linha BDGD, equipamento e unidade, nem somar populações repetidas.
3. `/explorar/`: inventário de todos os atributos/relacionamentos, com filtros somente se cubo/vínculo homologado. Para alta tensão investigar SSDAT↔CTAT/SUB/CONJ e recortes de linha/circuito AT, sem deduzir relações não comprovadas.
4. Participação de uma categoria **dentro do grupo** e participação desse grupo **na mesma categoria Brasil**, com denominadores, unidades, qualidade e cobertura idênticos; percentuais nacionais só com universo suficientemente completo.
5. Matriz com multi-seleção de entidades e presets por conceito, além de famílias, grupo e DIST; eventuais filtros DDA com aplicabilidade explícita e CSV do recorte.
6. Panorama orientado a negócio, com indicadores explicáveis e navegáveis; preservar poligonais ARAT oficiais, qualidade e identidade Apple-inspired.

**Fase B / 2022–2025:** depois de extrair, auditar e harmonizar a sucessão de distribuidoras (EPB/EBO etc.), ativar a nova aba **Evolução histórica** com tabela anual **já calculada** de 2022, 2023, 2024 e 2025, variações absolutas e percentuais, seleção simples de empresa/grupo/indicadores, sem exploração DDA complexa. Durante a Fase A, pode criar a rota em estado "dados históricos em preparação" sem números inventados. Não iniciar ML, previsões ou cenários.

**Ordem e segurança:** terminar o release técnico 2025 e não antecipar produção com GDBs faltantes. Implementar R2 em incrementos testados na branch/PR corretos, preferencialmente após a homologação 2025 se o ETL final exigir toda a RAM/disco. Não alterar `main`, não forçar merges, não publicar dados privados. Documentar explicitamente pendências de métricas do BI quando o PBIX/DAX não estiver disponível.
