# PROMPT EXECUTIVO — Claude implementa R2; ChatGPT audita e publica depois

**Proprietário:** Arthur Henrique Elias de Lima  
**Projeto:** Núcleo de Dados da BDGD — dashboard público a partir da BDGD ANEEL  
**Decisão do responsável:** 23/10/2026  
**Contrato de entrega:** Claude termina 2025, implementa revisões aprovadas, testa, publica apenas preview e entrega PR + evidências; **não promove produção**. ChatGPT (em nova conversa/turno e mediante autorização do usuário) audita PR, release e preview e então cuida da publicação em produção.

## ATUALIZAÇÃO DE CONTEXTO — PBIX NÃO DISPONÍVEL NO PC DO CLAUDE (23/10/2026)

O proprietário **confirmou que o PBIX do BI VPE de referência NÃO está na máquina do Claude**. Essa ausência é **conhecida** e **NÃO deve bloquear** a finalização do ETL 2025, a R2, os filtros DDA/TUC comprovados, o preview ou a entrega do PR. **Não voltar a perguntar onde está o PBIX, não fingir que o leu e não afirmar equivalência ao BI sem evidência.**

**Procedimento obrigatório substitutivo:**
1. **Desenvolver as métricas BDGD 2025 independentemente do BI** a partir do Manual BDGD aplicável, MCPSE, DDA oficial, schema e valores reais de staging/GDB, relacionamento EQ↔UN validado por DIST + DATA_BASE, regras de grão, deduplicação e QA. Para TUC 565/570 e classificações A1–A6, confirmar códigos e atributos na fonte normativa e nos dados antes de construir o preset. A falta do PBIX **não autoriza atalhos metodológicos**.
2. Criar `docs/MATRIZ-PARIDADE-METRICAS-VPE-2024.md` como **matriz de referência aguardando BI**. Documentar para cada indicador: `metric_id`, conceito, entidades/joins, TUC e atributos, definição BDGD independente, unidade, regra SQL/ETL, QA 2025, fonte normativa e `paridade_BI_VPE = NAO_AVALIADA_PBIX_AUSENTE`. Não inventar nomes DAX, medidas Power Query nem filtros internos do BI.
3. Separar **(a) indicador auditado diretamente na BDGD 2025** de **(b) paridade com indicador do BI de referência**. O primeiro pode aparecer no dashboard, desde que esteja rigorosamente homologado por dados/normas e não traga o rótulo de equivalência ao BI. O segundo somente após receber arquivo PBIX ou extração fidedigna de suas medidas e regras.
4. Presets de negócio cujo significado possa ser provado independentemente (ex.: TUC real validada, agregação correta sem dupla contagem) podem ser habilitados com legenda clara. **Somente os indicadores que dependerem exclusivamente de regras desconhecidas do PBIX** ficam N/D ou "definição pendente" com razão, sem impedir os demais.
5. **Gate de produção:** a falta de PBIX não transforma todos os dados BDGD 2025 em "não homologados"; o que é mandatório é QA independente para o indicador **efetivamente publicado**. O relatório de handoff deve separar `QA_BDGD_2025` de `PARIDADE_BI_VPE`, deixando o segundo explicitamente pendente para atualização posterior.
6. Nunca usar o BI VPE de 2024 como fonte numérica da competência 2025, nem criar valores fictícios para suplência. Manter o código preparado para integrar as regras do BI quando o proprietário fornecer o arquivo em outra etapa.

**Esta instrução prevalece sobre frases anteriores que pudessem sugerir obrigatoriedade de localizar o PBIX antes de desenvolver indicadores BDGD normativos.**

## ALERTA SOBRE SUBCONTAGEM — TUC 0/00/000, TIP_UNID E QTD (23/10/2026)

O responsável teme corretamente que filtros `TUC=XXX` deixem ativos válidos fora da contagem. Um **script operacional anterior fornecido pelo proprietário** contém a regra `CHAVE(COM+UC) = SUM(QTD WHERE TUC=160 OU (TUC em {0,00,000,vazio} E TIP_UNID no conjunto específico))`. A versão `CHAVE(UC)` considera apenas a TUC 160. **Não é prova de regra do PBIX**, mas evidência suficiente para exigir auditoria de `00` antes de publicar categorias finais.

**Ler e executar** [ALERTA-METRICAS-TUC-00-QTD-CHAVES.md](ALERTA-METRICAS-TUC-00-QTD-CHAVES.md). Pontos críticos:
- Não incluir todos os registros `TUC 00` numa categoria: checar `TIP_UNID`, entidade, vínculo e semântica QTD.
- Não confundir `SUM(QTD)` no consolidado intermediário com `COUNT(*)`/distinct no GDB.
- Não transportar filtro `PROPRIEDADE=PD` do script para a visão nacional sem declarar e validar recorte.
- Investigar os campos reais da BDGD 2025 e construir reconciliador `classificado` vs `zero/não informado` com alertas e possíveis contagens residuais por métrica; auditar postes, medidores, transformadores, chaves **individualmente**.
- Não bloquear execução por ausência de PBIX. Não utilizar projeções nem ML do script antigo; seu uso é somente evidência descritiva histórica.
- Publicar indicadores de negócio compostos **apenas** onde relação da origem, filtros e distinção física estão comprovados; com campo necessário ausente, exibir N/D e evidência, não número fabricado.

Esta regra é **prioritária para o comparador e o benchmarking**, porque um ranking de grupos ou distribuidoras que ignore ativos legitimamente contados no universo seria enganoso.

## 0. Fontes, escopo, coordenação de trabalho e limites

**Ler integralmente antes de alterar código:**
- [Revisão R2 com regras semânticas e radar/benchmarking](REVISAO-R2-METRICAS-EXPLORADOR-MATRIZ-EVOLUCAO.md)
- [Direção de arte UI/UX Apple-inspired e uso seletivo 21st.dev](DIRECAO-ARTE-UIUX.md)
- [Contrato de dados 2025](CONTRATO-DADOS-2025.md)
- [Fatos e facetas](MODELO-FATOS-FACETAS-2025.md)
- [Harmonização e sucessões 2022–2025](HARMONIZACAO-SUCESSAO-2022-2025.md)
- [Estado da execução](ESTADO-EXECUCAO.md) e documentação nova do branch ativo.
- Issue https://github.com/artelias/BDGD/issues/5 e PR https://github.com/artelias/BDGD/pull/4.

**Repositório** `artelias/BDGD`. A branch do portal `feat/nucleo-dados-bdgd-portal` contém estas especificações; o código atual de Claude está na branch `feat/dashboard-bdgd-2025`, com PR #4 em rascunho. Trabalhar **a partir do estado mais recente do PR ativo**, incorporar estas especificações por leitura/merge seguro conforme situação real, nunca sobrescrever modificações alheias, nunca dar force-push ou merge automático em `main`.

O dashboard é produto técnico com dados reais oficiais de `DATA_BASE=2025-12-31`. Manter **foco nas funcionalidades aprovadas e limpeza visual**, sem substituir visual já aprovado, sem efeitos gratuitos, sem reconstrução completa ou novo projeto. O usuário gosta especialmente do **zoom animado das distribuidoras**, gráfico atual de diferenças do Comparador, motion design, cores, acabamento Apple-inspired e visualização ARAT. Preservar isso.

**Condição material de execução:** Claude e Codex trabalham no mesmo Windows/HDD com RAM escassa. Priorizar ETL 2025, checkpoints e facetas; não executar jobs pesados concorrentes desnecessários. Estado de `94/99 DIST` é somente **relato anterior**, não assumir ainda atual: inspecionar checkpoints reais na máquina. Nenhum dado privado, GDB, Parquet integral, COD_ID pessoal, CPF, credencial ou token deve ir ao GitHub/Vercel públicos.

**Autoria e contato corrigidos em TODO o webapp**, sem variações:
- **Desenvolvido por Arthur Henrique Elias de Lima**
- **Contato:** `Arthur.henrique.elias@gmail.com` com link `mailto:Arthur.henrique.elias@gmail.com` (autorização de exibição expressa do proprietário).
- Preservar link da fonte **ANEEL — BDGD (Dados Abertos)**. Remover a repetitiva frase **"Projeto independente, não oficial da ANEEL"** do rodapé público conforme preferência do usuário, mas **não sugerir certificação, patrocínio ou endosso da ANEEL**: responsabilidade, origem, metodologia e atribuição precisam continuar claros nas páginas técnicas/documentação. Não usar logotipos/identidade governamentais de forma enganosa.

## A. Parte de ChatGPT (ORQUESTRAÇÃO, ESPECIFICAÇÃO E RELEASE GATE)

**Já definida/realizada:** consolidar requisitos, critérios matemáticos, evidência no GitHub, planilha lógica de aceite, precedência entre documentos e ordem de entrega. Esta especificação representa a parcela de ChatGPT. Claude **não precisa esperar novos prompts** para implementar tudo deste documento.

**Após entrega do Claude e novo comando do usuário (ou envio do PR/relatório):** ChatGPT fará a revisão independente de PR/branch, contrato, métricas, CI, cobertura 2025, teste visual/preview e segurança Vercel. Só **depois** de autorização explícita do usuário para colocar em produção, promoverá o release homologado na Vercel em uma ação distinta (sem mexer em `geoia-data-hub`), com plano de rollback. Não afirmar que uma produção foi lançada sem executar e confirmar.

**Critério negativo:** se o Claude terminar sem homologação 2025, PR aberto e preview testado, ChatGPT aponta bloqueadores e NÃO publica apenas por pressão de calendário. O usuário decidirá corrigir ou autorizar outro escopo deliberadamente.

## B. Parte de Claude — IMPLEMENTAÇÃO, TESTES E HANDOFF COMPLETO

### B0. Verificar estado/finish ETL 2025 antes de afirmar release homologado

- Auditar inventário `99` publicações válidas `31/12/2025` (e ausências 2025 entre DIST históricos), checkpoints e hash de origem. Concluir dist restantes, sem recomputar já concluídos sem necessidade. Testar CPU/RAM disponível e evitar derrubar processamento.
- Concluir facetas exatas com cobertura para todas DIST aplicáveis, cubos conjuntos curados, valores decimais e comparabilidade. Regenerar pacote único e assets web. Executar reconciliações, indicadores de consumidores UC v2, potenciais conversões de potência MVA↔kVA, validação de qualidade e integridade.
- **Release homologado só após gates reais:** todas DIST elegíveis processadas, nenhuma quarentena/bloqueio incompatível, reconciliador passou, facetas/ARAT/grupos verificados e pendências de regra anotadas. Se alguma métrica permanecer N/D, explicitar por que, sem descartar o release completo onde as demais métricas sejam homologáveis. Não inferir homologação universal de métricas pelo sucesso de contagens brutas.
- O validador de publicação no CI **não pode pular silenciosamente** o pacote final por ausência de `manifest.json`: configurar teste compatível com artefatos efetivamente publicados (download/verificação/fixture de contrato ou materialização de output público em CI), e tornar o gate de release obrigatório.

### B1. Limpeza visual global sem perder personalidade

- Ajustar espaçamento, alinhamento, fluidez, títulos claros e nomenclatura empresarial, **mantendo componentes, animações, mapa, gráficos e estética Apple-inspired já aprovados**. Microinterações sutis com `prefers-reduced-motion`, foco e leitores de tela. Verificar smartphones iPhone/Android e monitores; light/dark, número e unidade nunca se encostam em outro card.
- Evitar jargão BDGD/TUC/COD_ID em cartões de alto nível; usar terminologia de negócio com nome técnico opcional e glossário. Priorizar informações legíveis e precisas, sem encher tela de fórmulas, badges, "AI look", skeletons intermináveis ou efeitos de partículas.
- Em revisão visual e screencasts, **não chamar de concluída** a funcionalidade sem testar a interação do usuário, incluindo links, filtros, reatividade, chart hover e exportação.

### B2. PANORAMA BRASIL — modificações aprovadas

1. **Mapa e zoom:** clique simples em área/distribuidora seleciona e `fitBounds`; clique **na mesma distribuidora outra vez** desmarca e **retorna automaticamente ao enquadramento Brasil**; clique em outra seleciona e faz transição fluida entre polígonos; clique em vazio do mapa desmarca e recentraliza no Brasil; implementar botão flutuante **"Ver Brasil" / recentralizar** permanentemente visível, inclusive **quando o painel de detalhe estiver aberto**. Ao recentralizar, cancelar busca/seleções geográficas que impedem visão nacional quando usuário pedir reset, ou expor claramente que somente a câmera mudou — preferir limpar seleção e enquadrar nacional. Preservar zoom/pan manuais, painéis e respeito `prefers-reduced-motion`; não reativar zoom em corrida de promises GeoJSON após limpar.
2. **Cabeçalho:** preservar `Panorama Brasil` e competência `31/12/2025`; a contagem de distribuidoras deve derivar da **cobertura do pacote verdadeiro** (não hardcode 92 ou 94). Retirar badge decorativo `Release parcial` do cabeçalho **sem ocultar estado real incompleto**: aviso discreto e clique para Metodologia/Qualidade quando não homologado; release de produção nunca ser implicitamente chamado completo sem gate.
3. **KPIs:** resolver transbordamento `857 mil km`/unidades para coluna vizinha por grid adaptativo, dimensionamento tipográfico responsivo, `min-width:0`, quebra/unidade responsiva e verificação de `font-size`, sem sacrificar legibilidade. Expor **mais KPIs realmente homologados** num bloco `Ver mais indicadores`/compositor com presets e seleção; dados existentes incluem rede AT, subestações, circuitos, geração MT, iluminação; novos KPI patrimoniais só se metodologicamente aprovados.
4. **Info amigável:** trocar matemática crua `SUM(COMP)/1000`, `COUNT(*)`, `COD_ID distintos` no tooltip principal por português direto, por exemplo **"Soma dos comprimentos declarados dos segmentos de rede de baixa tensão, convertidos para quilômetros"**. Explicação curta/longa, fórmula em painel `Como é calculado? > Ver cálculo técnico`, fonte e ressalvas acessíveis.
5. **Ranking `Todas (N)` ⇄ `Mostrar 12`:** corrigir experiência percebida de clique sem efeito. O código hoje alterna `shown = all ? rows : rows.slice(0,12)`, logo diagnosticar **rolagem/altura/visibilidade/capacidade de localizar lista expandida**, dar feedback de total exibido e testar no browser que N itens realmente aparecem, com scroll correto sem quebrar layout.
6. **Inventário:** explicar `1 N/D` como **1 distribuidora sem valor homologado/disponível para essa métrica**, com causa ao clicar e sem confundir com falta de um único ativo. Humanizar nomes de entidades e manter códigos técnicos acessíveis ao especialista; links para `Explorar ativos`.
7. **Remover seção `Cobertura da competência 2025` do Panorama** (não deletar metadados ou QA). Mover/assegurar a informação detalhada em `Metodologia e qualidade`, cujo layout **não foi aprovado para redesenho** nesta rodada.
8. Corrigir autoria em menu, rodapé, `metadata`, readmes, `og`, licença/créditos e qualquer texto de autoria; adicionar e-mail clicável; só alterar créditos de design sem apagar atribuição de fontes externas.

### B3. MATRIZ NACIONAL — filtros dinâmicos sem reduzir a qualidade técnica

1. Reorganizar seletor visível: **Métrica principal/Quantidade/Extensão/Potência**, apenas onde a entidade suportar. Não oferecer `Registros` e `COD_ID distintos` como escolhas empresariais concorrentes; essas semânticas permanecem em dicionário/Metodologia como procedimentos de QA e de contagem. Não trocar `COUNT(DISTINCT)` validado por `COUNT(*)` só porque usuário quer "Quantidade": quantidade de negócio deve ter definição auditada.
2. Selecionar **famílias, conceitos de negócio (Transformadores, Redes, Consumidores, Seccionamento etc.), entidades individualmente**, com multi-seleção, pesquisar/selecionar tudo/predefinidos/favoritos; preservar matriz navegável e exportar o recorte exato, com unidade/cobertura/regra.
3. Adicionar filtros **empresa/grupo/DIST, UF, município quando geocodificação/vínculo válido, tipos/área/tensão/TUC/A1-A6/atributos DDA** aplicáveis a cada métrica e entidade. **Não fingir filtro universal**: campos de entidade não presentes ou combinações de cubos inexistentes são marcados indisponíveis. Município requer geografia/joins demonstrados com QA, evitar dupla contagem por intersecção e delimitação transfronteiriça.
4. Filtros em cascata coerentes, estado em URL e chips removíveis; agrupamento por família funcional/número de ativos. Primeiro lote de filtros usáveis com cubos existentes, depois ETL para dimensões prioritárias com base em dados reais; não gerar produto cartesiano de todas as facetas.
5. Matriz e compara devem compartilhar definições de filtro/métrica e status; não criar resultados distintos para o mesmo recorte.

### B4. COMPARADOR — preservar gráfico atual e acrescentar duas visualizações

**Decisão posterior prevalece sobre antigas propostas que rejeitavam radar. O radar está APROVADO.**

- **(1) Gráfico principal = gráfico de diferenças ATUAL, manter design e transições.** Adicionar modo `Quantidade` e `Diferença (%)` onde interpretável (em quantidade/valor, preservar unidade real por indicador; não misturar absolutos heterogêneos em uma ordenação agregada). Ordenação por **Por família funcional** (conceitos de negócio, não só códigos BDGD) e **Maiores diferenças**. Diferença sinalizada: A−B; permitir interpretação clara de sentido positivo/negativo sem sugerir "melhor qualidade".
- **(2) Barras espelhadas**: A à esquerda, B à direita, identificadas coerentemente com cartões, cores, legendas e hover. Conceitos homologados, escala comum por indicador e unidades claras.
- **(3) Radar / Teia de aranha de benchmark** com seleção A (grupo ou distribuidora) e seleção B / referência: `outro grupo`, `outra distribuidora`, `Brasil — total nacional`, `Benchmark Brasil — grupos`, `Benchmark Brasil — distribuidoras`.
  - Benchmark grupos, para indicador m: `B_g,m = MAX_g(valor_grupo(g,m))` entre grupos verificados. O líder pode variar por eixo.
  - Benchmark individuais: `B_d,m = MAX_DIST(valor_dist(DIST,m))` entre distribuidoras elegíveis. O líder pode variar por eixo.
  - Brasil total = soma apropriada das DIST elegíveis `T_m`, distinta dos dois máximos.
  - Normalização por eixo: `percentual = valor_A,m / referencia_m × 100` com **mesmo denominador para A e B**. Não desenhar valores brutos km/kVA/quantidades no mesmo raio. Grupo vs líder de uma DISTRIBUIDORA pode legitimamente superar 100%; **não truncar**: autoescalar radar, rótulo de diferença de escala e tooltip completo.
  - Identificar líder real de cada eixo com nome, valor, métrica, unidade, data-base, cobertura e universo; empates; N/D ou insuficiência removem eixo com aviso, nunca viram zero. 4–8 indicadores pré-homologados, controles de seleção, legenda A/B e tabela acessível/mobile/export.
  - Priorizar nomes **"Quem lidera em volume de ativos"** ou equivalente, não `melhor desempenho` só por ter mais ativos.
- Preservar tabela técnica com detalhe por entidade e filtros DDA/TUC quando computados e reconciliados. Não duplicar gráficos inutilmente. Gráfico radar pode ser componente com carregamento diferido para performance.

### B5. EXPLORAR ATIVOS — substitui a navegação exclusivamente por "Entidades e DDA"

- Nome primário de tela **`Explorar ativos`**; modo avançado `Entidades BDGD e DDA` preserva consulta por código.
- Fluxo `conceito de negócio → preset curado → métrica → atributos e filtros`; Transformadores como piloto: transformador de distribuição/força/nível de tensão, TUC 565/570, EQTRMT/EQTRAT e UNTRMT/UNTRAT com vínculos corretos. **Não inventar "TUC 00" nem somar unidade + equipamento sem deduplicar**. Procurar medidas reais do BI VPE 2024 (se acessível) e mapear regras de inclusão/exclusão, TUC, A1..A6, potencia, contagens. 2024 é referência metodológica, não meta numérica de 2025.
- Escopo `Brasil / Grupo / Distribuidora`; quando escolher grupo, mostrar **seletor dependente das empresas do próprio grupo** (uma, múltiplas ou grupo todo), em painel suspenso amigável. Não permitir seleção de empresas alheias sem evidência; todos os atributos com proveniência.
- Inventariar **todos** os atributos físicos aplicáveis por entidade, separando `campo existente`, `atributo DDA mapeado`, `faceta calculada`, `junção necessário` e `não publicável`. Aumentar filtragem de TUC, características, níveis, área, propriedade, tipo etc com dados homologados; SSDAT e CTAT/subestação/linha AT só com vinculação e cardinalidade realmente validadas.
- Para cada categoria, exibir **(a) percentual da categoria dentro do grupo/empresa** e **(b) percentual do grupo/empresa na mesma categoria do Brasil**, sempre com mesmo cubo, definição/métrica e denominador explícito; cubo nacional incompleto (ex.: 2/86 DIST) **NÃO** pode virar participação Brasil oficial. Categorias sobrepostas ou N/D impedem percentual falso. Exibir total absoluto/unidade e coberturas de cada visão.
- Preservar os gráficos, interação por categoria, transições e CSV; melhorar insights sem criar narrativa inventada.

### B6. EVOLUÇÃO HISTÓRICA — etapa separada, não previsão

- Nova rota `/evolucao/` no menu, idealmente após Matriz e antes de Comparador. **Tabela pré-calculada**, sem exigir filtros avançados DDA; selecionar empresa/grupo e indicadores homologados, mostrar 2022/2023/2024/2025, variação absoluta e percentual com condição de comparabilidade.
- **Não buscar 2020/2021.** Respeitar estudos de sucessões e perímetro 2025 (ex. EPB/EBO), comparando published vs. ajustado à referência 2025, sem duplicar e sem fingir que incorporação é crescimento.
- Enquanto o ETL histórico 2022–2024 e QA não terminarem, lançar SOMENTE esqueleto honesto `Histórico em preparação` **sem números simulados no release**. Só ativar séries reais depois de auditoria e sucesso de pacote, eventualmente como release seguinte.
- **Sem ML, sem previsões 2026–2029 e sem chamada de treino.**

### B7. METODOLOGIA E QUALIDADE — mudança mínima por enquanto

O usuário disse que essa tela será debatida em separado. **Não redesenhar nem reescrever todo seu conteúdo agora.** Apenas manter dados, QA, proveniência, legenda N/D e adicionar a seção estritamente necessária `Dicionário de indicadores / Como é calculado?` referenciada pelas demais telas, preservando acesso à fórmula completa, DAX/SQL quando genuinamente auditados. Informações de cobertura retiradas do Panorama permanecem acessíveis aqui. Normas e fontes ANEEL devem estar corretas, com data de vigência.

### B8. Qualidade de engenharia, publicação PREVIEW e handoff

- Atualizar nomes, textos, títulos, i18n pt-BR, readmes (protótipo legado fictício vs web real), links e testes; remover **somente** os elementos redundantes e jargões empresariais discutidos. Do not break `next export` (arquivos `__next`, prefetch, CSS MapLibre worker, geometrias ARAT).
- Testar alterações unitárias e Playwright E2E: duplo clique na mesma distribuidora, clique em vazio, botão permanentemente acessível, ranking 12↔N, overflow KPIs, texto N/D correto, tel/rodapé, matriz filtros, comparador A/B + benchmarks independentes, radar >100%, cobertura e variações zero/ND, mobile drawer e acessibilidade AA, `prefers-reduced-motion`.
- Inspecionar screenshots reais de todas as páginas em **desktop/mobile**, ambos temas, e corrigir visual até ficar minimalista e coerente; verificar rotas/worker MapLibre/sem console errors no preview.
- **Vercel:** usar apenas o projeto existente `nucleo-dados-bdgd` e **deploy `preview`**, sem promover para produção, sem mudar domínios/aliases, `main`, `productionBranch` ou remover proteção do ambiente de produção. Preview pode continuar protegido por login. Não mudar/destruir `geoia-data-hub`. Se o controle Git iniciar `production` involuntariamente, interromper/relatar e corrigir automação de origem para manter só preview; não anunciar produção.
- Manter commits rastreáveis e PR em rascunho para review, com issue #5 e evidências dos testes. **Não mergear nem fechar PR sem autorização.** Se uma correção depender de extração adicional/ausência de PBIX, registrar `Bloqueio` e entregar o restante sem fabricar.
- Quando terminar, enviar um relatório `HANDOFF-R2-PRE-PRODUCAO.md` (commitado) com: PR e branch, SHAs, preview URL, data-base/processadas/ausentes, quais métricas homologadas ou N/D, evidências da TUC/relação EQ-UN, atributos adicionais, facetas e cobertura, padronização de grupo/DIST, resultado de cada teste, screenshots desktop/mobile, erros conhecidos, Vercel config/project/estado da proteção, dados públicos e segurança, comando de reprodução, status/harmonização histórica, instruções de rollback e checklist por tela marcado `OK / PARCIAL / BLOQUEADO`.
- Usuário enviará **o PR/relatório de handoff** ao ChatGPT para auditoria. **Não solicitar ao usuário liberação de produção nesta fase.** Só ChatGPT, após nova autorização expressa, fará promoção de preview homologado para produção.

## C. Hierarquia de decisões

1. Esta especificação contém as **últimas decisões explícitas** do proprietário para Panorama, Matriz, Comparador e Explorar.
2. A seção **benchmark por grupo E por distribuidora** e radar aprovado em [R2](REVISAO-R2-METRICAS-EXPLORADOR-MATRIZ-EVOLUCAO.md) substitui qualquer texto antigo que dizia ser radar opcional/futuro.
3. A indicação "não redesenhar Metodologia e Qualidade nesta rodada" prevalece; somente conteúdo explicativo mínimo necessário.
4. O histórico 2022–2025 é realidade observada, não previsão, e não deve atrasar o release 2025 se dependente de dados ainda não disponíveis.
5. As proteções de produção, segurança, integridade e não inventar valores são superiores a qualquer requisito de estética.

## D. Check de sucesso para o Claude

**Só anunciar "concluído e pronto para ChatGPT auditar" quando:**
- [ ] Texto do autor/contato exato em toda a aplicação.
- [ ] Panorama com retorno Brasil do mapa e botão sempre visível; rótulos claros, KPI sem colisão, ranking funcional, cobertura deslocada e N/D explicado.
- [ ] Matriz com seleção de entidades/indicadores e filtros disponíveis validados, sem contagens de registros confundidas com quantidade comercial.
- [ ] Comparador preserva gráfico original, adiciona barras espelhadas e radar de benchmark **grupos e DIST** com Brasil total separado, e lideranças verificáveis por indicador.
- [ ] Explorar Ativos orientado por conceitos, filtros habilitados só quando possíveis, grupo→distribuidora, dupla participação com denominadores e cobertura.
- [ ] Evolução histórica pronta tecnicamente e com dados reais **apenas** se a homologação de 2022–2024 permitir; senão seção honesta sem números fictícios.
- [ ] Metodologia não redesenhada e avisos de qualidade/ausência não ocultados indevidamente.
- [ ] Tests/CI/QA/Playwright + screenshot evidence verdes e reproduzíveis.
- [ ] Preview Vercel **READY**, protected se aplicável; **produção inalterada**.
- [ ] PR/issue e relatório de handoff completos para revisão ChatGPT.

**Terminologia final:** Navegação `Panorama`, `Matriz nacional`, `Evolução histórica`, `Comparador`, `Explorar ativos`, `Metodologia e qualidade`, `Previsões` (somente planejamento, sem treino). Título do produto `Núcleo de Dados da BDGD`.

**Fim do contrato.**
