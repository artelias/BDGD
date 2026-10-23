# PROMPT FINAL AO CLAUDE — R3 Explorar Ativos + iniciar Evolução Histórica + diagnosticar Previsões

**Responsável:** Arthur Henrique Elias de Lima  
**Decisão de escopo:** 23/10/2026  
**Projeto:** Núcleo de Dados da BDGD · `artelias/BDGD`  
**Código ativo:** PR [#4](https://github.com/artelias/BDGD/pull/4), branch `feat/dashboard-bdgd-2025`. **Este arquivo fica apenas na branch de especificações `feat/nucleo-dados-bdgd-portal`, sem alterar aplicação nem Vercel por si só.**

## 0. Leitura e precedência

Leia este contrato integralmente, junto do [prompt R2](PROMPT-CLAUDE-EXECUCAO-R2-ATE-PREVIEW.md), da [revisão R2](REVISAO-R2-METRICAS-EXPLORADOR-MATRIZ-EVOLUCAO.md), das decisões R3 mais recentes na [issue #5](https://github.com/artelias/BDGD/issues/5) e do [handoff R2](HANDOFF-R2-PRE-PRODUCAO.md) no branch do PR. **Estas instruções mais recentes substituem qualquer fluxo de Explorar que obrigue começar por uma entidade BDGD e qualquer diretriz antiga que proibisse iniciar a coleta do histórico 2022–2024.**

Implementar as mudanças **na branch do PR** (reconciliar atualizações de documentação sem conflito), versionar com commits, testar e entregar **PREVIEW**, nunca produção. Preservar design Apple-inspired, mapa, motion/zoom, funcionamento do Comparador, outros requisitos aprovados de Panorama e Matriz. O usuário indicou que o restante está encaminhado; **não recriar o dashboard e não reabrir decisões já fechadas**.

## 1. Corrigir completamente o fluxo da página Explorar Ativos

### 1.1 Conceito clicável primeiro; nunca forçar escolha de UN/EQ

**Erro atual:** no `web/src/components/pages/Explorar.tsx`, o menu "Transformadores" é apenas agrupador visual; clicar nele não seleciona um conceito: só há seleção de folhas `UNTRMT`, `EQTRMT`, `UNTRAT`, `EQTRAT`. Isso é semanticamente errado para a UX pretendida.

**Nova interação obrigatória:**
1. Clicar no **título/cartão do conceito** seleciona-o imediatamente e mostra visão agregada do conceito no escopo atual (Brasil/grupo/DIST), sem necessitar escolher uma tabela.
2. Mostrar **recortes patrimoniais descobertos por TUC nos equipamentos elegíveis**, em cartões/botões compreensíveis com quantidade e, quando tecnicamente homologada, potência. O conceito `Transformadores` mostra **TUC 565 distribuição; TUC 570 força; TUC 575 medida se presente em entidade aplicável**, além de **demais TUCs realmente encontradas**, com descrição MCPSE/DDA quando existe. Não limitar recortes aos 565/570 codificados no catálogo atual, nem assumir que 575 pertence especificamente à tabela EQTRMT.
3. Selecionar um recorte de TUC abre **características filtráveis** (A1; A2–A6 somente quando existirem fontes/cubos; tensão, fases, tipo, potência em faixas, localização, ligação, situação etc se verificáveis). Gráfico e tabela mostram distribuição por categorias **com rótulos DDA legíveis**; escolha entre `Quantidade` e `Potência` quando ambas válidas. Exportação reproduz seleção, métrica, TUC, unidade, fonte e escopo. TUC '000' pode aparecer com rótulo neutro; o responsável **adiou** a auditoria excepcional de `00` e não quer que isso bloqueie o fluxo.
4. **Entidades como detalhe técnico opcional:** `EQTRMT`, `EQTRAT`, `EQTRM` identificam **equipamentos**; `UNTRMT`, `UNTRAT` representam **instalações**. Descobrir cardinalidade e soma sem duplicidade, vinculando chaves autorizadas por DIST e competência. **Nunca** somar instalação + equipamento ou denominar instalação como transformador físico. A vista principal de quantidade deve ter **uma população canônica documentada** (preferir equipamentos com TUC válida onde aplicável). Contagens de instalações podem aparecer em aba/detalhe `Onde estão instalados`.
5. **Se houver categoria sem TUC aplicável**, oferecer recortes semânticos pela entidade/atributo apropriado, sem forçar classificação patrimonial fictícia. Indicadores totais e de participação obedecem ao mesmo grão e população.

**UX de exemplo:** `Explorar ativos → Transformadores → Força (TUC 570) → Brasil → Quantidade/Potência → Tipo de bem ou Tensão`. Ao mudar para `Grupo Econômico X`, atualizar todo o gráfico e os totais, inclusive as duas participações.

### 1.2 Catálogo de conceitos: nomenclatura definitiva e desdobramentos

| Menu público (conceito clicável) | Recortes iniciais / comportamento |
|---|---|
| **Transformadores** | Distribuição (TUC 565), força (TUC 570), medida (TUC 575 **se encontrada**) e outros TUCs válidos; quantidade de equipamentos e potência nominal se homologada; instalação como detalhe separado |
| **Redes** | BT/MT/AT; tipo/material/fases/localização/tensão onde existir; comprimento em km como medida principal; ramais onde apropriado |
| **Consumidores** | BT/MT/AT e `GRU_TEN` quando aplicável; situação de ativação `SIT_ATIV`, classe, fases, urbano/rural e demais atributos DDA importantes; conceito total só com união válida e sem duplicidade de COD_ID |
| **Geradores** | **Renomear de "Geração conectada" para "Geradores"**; recortes BT/MT/AT, tipo de sistema, fonte, situação e outros campos existentes; quantidade homologada; **não** exibir potência UG* como homologada se a semântica ainda estiver pendente |
| **Chaves** | Conceito próprio, TUC 160 e tipos A1 validados; características de fases, tensão, localização quando validáveis |
| **Disjuntores** | Conceito próprio, TUC 210 quando aplicável e características funcionais |
| **Religadores** | Conceito próprio, TUC 345; fases mono/bi/tri, urbano/rural, tensão **somente se atributo/vínculo real provar** |
| **Outros dispositivos de seccionamento** | Seccionalizadores/fusíveis e demais tipos, se a fonte permitir classificá-los por TUC+A1; evitar confundir com chaves e somas sobrepostas |
| **Reguladores** | **Renomear "Regulação de tensão" para "Reguladores"**; TUC 340, filtro MT/AT e atributos sem separar colunas de instalações/equipamentos |
| **Bancos de capacitores** | **Renomear "Compensação de reativos" para "Bancos de capacitores"** para TUC 125; se houver outros compensadores/reatores, expor como outros conceitos ou tipos reais — não rotular qualquer equipamento EQCR indiscriminadamente como banco de capacitor |
| **Medidores** | Equipamentos de medição, tipo/tecnologia do medidor e atributos DDA verificáveis |
| **Transformadores de medida** | Conceito próprio quando dados suportarem EQTRM/TUC 575; não duplicar transformadores de medida em dois indicadores somados |
| **Estruturas e iluminação** | Conceito clicável; **PONNOT** para Postes (TUC 255, A1 01 se confirmado) versus Torres (A1 02 se confirmado), outros pontos válidos; `PIP` iluminação pública separado internamente; não chamar todos PONNOT de postes |
| **Subestações** | `SUB` conta subestações; filtros de atributos mais relevantes (tipo/tensão/localização) e drill-down **"Ativos associados"**: transformadores, circuitos/alimentadores, seccionadores, reguladores, barramentos, bays e demais vínculos **efetivamente comprovados**, com totais por SUB |
| **Circuitos/Alimentadores** | CTMT / CTAT com filtros de nível/tensão, subestação e características relevantes, e drill-down **"Ativos associados ao circuito"** (redes, transformadores, chaves, religadores, consumidores se relação existente); evitar inventar CTBT |
| **Conjuntos** | `CONJ`; visão por conjunto com ativos associados, subestações/circuitos e consumidores onde a chave relacional e perímetro forem demonstrados |
| **Perdas e balanço energético** | **Manter funcionamento e estrutura atuais**, como solicitado; página de menor prioridade nesta mudança |
| **Barramentos e bays** | Acessíveis e suficientes no detalhamento de subestação, sem excesso de abas independentes; se forem disponibilizados como conceito isolado no modo avançado, não forçar exposição no menu principal |

Os conceitos são **descobertos e curados com base no MCPSE, Manual BDGD, campos e DDA efetivamente presentes**. Não inventar TUC ou categoria apenas pelo exemplo. Os termos técnicos e códigos BDGD continuam acessíveis em `Modo avançado` e documentação, mas não no menu principal.

### 1.3 Grupo, Brasil, distribuidora e participação dupla

Preservar o seletor de escopo **Brasil / Grupo / Distribuidora**. Ao selecionar Grupo, permitir `Todas as distribuidoras do grupo` e seleção de **uma ou várias** DIST pertencentes ao grupo, com filtro em cascata e sem misturar outras empresas.

Para cada categoria TUC/atributo, mostrar simultaneamente:
- **Valor do recorte** (quantidade e/ou potência, cada um com unidade e população comparáveis).
- **Participação dentro do grupo/escopo:** `recorte selecionado / total da mesma população (e métrica) dentro do grupo/escopo`. Em Brasil, mostrar `participação no Brasil` e evitar cartão nacional redundante 100%.
- **Participação da seleção no Brasil:** `recorte do grupo (ou DIST) / total da mesma categoria no Brasil`; não comparar TUC filtrada com total brasileiro sem esse filtro. Para seleção de várias DIST, indicar `distribuidoras selecionadas`, não Grupo inteiro.
- Quando não for possível provar partição disjunta, cobertura ou população, sinalizar N/D de forma **discreta e honesta**, sem cálculos arbitrários. Guardar auditoria completa na Metodologia e CSV.

**Exemplo fictício:** Grupo X tem 2.000 transformadores de força TUC 570 dentro de 10.000 transformadores desse universo; no Brasil há 20.000 TUC 570. Participação interna = 20%, participação no Brasil nessa TUC = 10%. Estes valores são didáticos, não dados oficiais.

### 1.4 Atributos + gráfico + tabela de categorias

Na área central: **nome do conceito**, filtros contextuais, cartões de TUC/recorte descobertos, **Quantidade/Potência** quando válida, gráfico interativo por atributo, **tabela sob o gráfico** com categoria, quantidade, potência/unidade e percentuais quando comparáveis, e ações de download. Priorizar cerca de 2–6 atributos essenciais por conceito; outros ficam em `Mais características`. Não transformar a tela em inventário enorme de QA.

Em `SUB`, `CTMT/CTAT` e `CONJ`, permitir selecionar o objeto específico pela chave/descrição pública permitida e listar contagens de ativos vinculados **por relação real**, com vínculos deduplicados (um EQ tem uma instalação, um circuito pode cruzar várias redes; fazer QA de relações N:1/1:N para não multiplicar contagens). Se não houver campo para fazer um vínculo seguro, exibir `recurso indisponível` naquela categoria, não estimar. Agregar por DIST+identificador canônico de SUB/CTMT/CONJ, sem exportar IDs pessoais sensíveis.

**Critério de prioridade:** conceito clicável e transformadores completos primeiro; em seguida redes, consumidores, geradores; dispositivos elétricos, medidores, estruturas; depois drill-down de subestações/circuitos/conjuntos com relacionamentos reais. Reutilizar componentes/cubos do Explorar e preservar filtros em URL.

## 2. INICIAR a Evolução Histórica — deixar de ser apenas "Histórico em preparação"

O usuário quer iniciar a execução do histórico e construir a melhor experiência comparativa de **2022, 2023, 2024 e 2025**. Não há pedido para baixar 2020 ou 2021.

### 2.1 Inventário e execução de dados históricos

No handoff R2, o histórico foi reportado em `2022: 74/99`, `2023: 62/89`, `2024: 76/97`, **0 anos homologados**, com runner pausado `STOP_REQUESTED` para priorizar 2025. Esses números são um **snapshot histórico, não verificação atual**: conferir imediatamente os arquivos, inventário ANEEL, checkpoints, RAM/CPU/disco e jobs existentes antes de retomar.

- Propor/retomar com segurança jobs 2022–2024 **somente depois de checar autorização, integridade dos arquivos e risco de concorrência no mesmo PC**; não invalidar nem reprocessar os 99/99 de 2025. Executar por checkpoints e lotes pequenos com logs e controle de retomada; se Claude não tem acesso a máquina/credenciais, deixar comandos executáveis e pendências verificáveis.
- Obter a publicação anual elegível por DIST em cada competência. Distinguir ausência de GDB naquele ano, falha de ETL, N/D na métrica e zero válido.
- Aplicar o **mesmo catálogo semântico de conceitos/TUC e métricas** possível em cada ano, com versão de regra. Checar que códigos/dicionário/tipagem podem mudar ao longo dos anos; não assumir compatibilidade. Regra do ativo é idêntica onde homologada ou bloqueia comparação naquele par de anos.
- **Sucessões e mudanças de perímetro:** usar [HARMONIZACAO-SUCESSAO-2022-2025.md](HARMONIZACAO-SUCESSAO-2022-2025.md), especialmente caso EPB/EBO. Manter séries observadas `publicação original por DIST/ano` e **série derivada `perímetro comparável à referência 2025`**, rotuladas claramente. Não somar sucessoras e predecessoras duplicadas, nem fingir crescimento por alteração de concessão.
- Grupo econômico: distinguir `grupo controlador em cada ano` versus `grupo de referência 2025` com regra explícita e evidência. NÃO aplicar automaticamente vínculos empresariais de 2025 a 2022 como se fossem oficiais de 2022.
- Pacote histórico *separado* do 2025, rastreável, leve e sem COD_ID individual; registrar denominador/cobertura comparável por competência. O CI deve impedir séries publicadas não homologadas.

### 2.2 Solicitar ao Claude a MELHOR UX — não reproduzir 99 linhas por 4 anos sem planejamento

Desenhar e implementar arquitetura visual premium e legível, preservando identidade atual. O usuário **delega ao Claude a escolha da composição visual mais adequada**, mas exige:

1. Escopo em **três modos sempre presentes**: **Brasil / Grupo econômico / Distribuidora**.
2. **Múltiplas distribuidoras** ao selecionar modo Distribuidora; selecionar primeiro um Grupo para restringir e escolher DIST desse grupo (uma, algumas ou todas) como atalho; também permitir pesquisar e comparar DIST de grupos distintos quando no modo livre.
3. Conceitos/indicadores **iguais aos da Matriz e Explorar**, principalmente consumidores, redes BT/MT/AT em km, transformadores, chaves/religadores, medidores, geradores, subestações, circuitos etc.; separar quantidade, km e potência em séries com unidades corretas.
4. **Gráfico temporal** 2022–2025 com uma linha por empresa/grupo/seleção, cartões com diferença absoluta, percentual acumulado, variação ano a ano e CAGR **somente quando matematicamente definido**; permitir visões Brasil, empresas lado a lado e grupos, além de uma tabela histórica exportável. Não misturar indicadores de unidades diferentes num único eixo. Até cerca de 5–8 linhas visíveis antes de incentivar filtro; preservar acessibilidade e desempenho com 99 DIST.
5. Propor, testar e justificar ao menos duas composições: (A) linha temporal + tabela; (B) matriz/heatmap de anos × DIST/grupos com detalhes em clique, inclusive crescimento percentual. Selecionar a melhor para default e incluir outra como alternância se houver real valor.
6. **Homogeneidade:** selecionar `composição oficial por ano` vs `perímetro comparável 2025` quando ambos existirem e forem confiáveis. Exibir explicação curta em português simples de incorporações e quebras de série. Não completar intervalos com zero, interpolação, números simulados ou previsão disfarçada de histórico.
7. Histórico que não tenha sido homologado deve aparecer como preparação/indisponível; mostrar evolução **real apenas para anos, DIST e métricas efetivamente homologados**. Se nenhum recorte atingir essa condição, construir UX com estrutura funcional, skeleton/empty states honestos e prova de cálculo em testes sintéticos, mas nenhum gráfico público com dados falsos.

### 2.3 Entregáveis da evolução

- Inventário por ano (alvo, processado, pendente, sem publicação, QA/homologado), estado atual real e comandos para retomada.
- Arquivos de comparação histórica e pontes de perímetro a partir das fontes, método por métrica/ano/empresa, evidência de sucessão, pacote validado.
- Página `/evolucao/` redesenhada com seletor de escopos, seleção múltipla, indicadores, gráficos/tabela e mensagens honestas quando faltar homologação.
- Testes unitários/E2E para anos ausentes, predecessor/sucessora, grupos e multi-DIST, crescimento com base zero, subpopulações e consistência com a Matriz 2025.
- Preview Vercel apenas após build/CI, sem alterar produção.

## 3. Previsões — avaliar a viabilidade e preparar a especificação, sem prometer modelo válido já

O usuário **passou a autorizar uma avaliação de viabilidade das previsões**, não treinamentos automáticos. A regra anterior "não desenvolver ML na R2" **continua valendo para a implementação de modelos** até o histórico comparável ser homologado e o usuário aprovar a proposta metodológica.

Produzir `docs/ESTUDO-VIABILIDADE-PREVISOES-BDGD.md` com:
- Métricas candidatas: consumidores, km de redes BT/MT/AT, equipamentos TUC e demais indicadores com série completa; segmentações Brasil/grupo/DIST apenas onde há **identidade histórica e comparabilidade**.
- **Limitação central:** 2022–2025 são **somente 4 observações anuais** por série. Isso é insuficiente para aprender tendências complexas de forma robusta, separar choques estruturais e validar modelos exigentes. Para 2026 em diante, propor baseline simples (persistência, crescimento conservador com limites documentados e cenário, regressão simples apenas se teste/diagnóstico permitir) versus modelos ML mais complexos **não recomendados de início**. Com apenas 4 pontos, backtesting tem baixíssima potência; intervalos de incerteza precisam ser conservadores e demonstrar caráter exploratório.
- Como tratar concessões, mudança regulatória/DDA, mudanças de TUC, crescimento aparente por reclassificação, valores censurados e medidas sobrepostas. Sem gerar previsões para entidades N/D ou séries com ruptura não reconciliada.
- Para cada modelo futuro: horizonte, variáveis externas necessárias (mercado, expansão de rede, novas ligações, investimentos/cadastros, fatores macro e territoriais), nível de agregação, cenário base/alto/baixo, métricas de erro MAE/MAPE/sMAPE onde apropriado, treino e validação temporal, riscos e governança.
- **Que informações faltam?** Produzir tabela `dado necessário | onde obter | existe? | homologado? | risco | ação`, incluindo histórico completo, pontes societárias, filtros de ativos, índices macro externos, e decisão de horizonte (ex.: 2026–2030) a confirmar com proprietário.
- Pode preparar contratos e *protótipos de interface sem valores futuros públicos* para a página Previsões, se isso não impactar o release e houver testes; **não publicar prognósticos como fatos, não treinar ML automaticamente e não prometer acurácia**.
- Explicar com clareza a diferença entre **evolução observada** (história) e **cenário/projeção** (previsão futura), tanto na interface quanto na documentação.

## 4. Qualidade de UI e compromisso com o usuário

- Ajustar apenas o necessário para deixar as novas páginas integradas à aplicação existente. No Explorar, **categoria clicável como objeto principal** em desktop/mobile e acessível por teclado; entrar diretamente em Transformadores/Redes/Consumidores etc, sem subitem técnico obrigatório. Geradores, Reguladores e Bancos de Capacitores com nomes pedidos.
- A tabela abaixo do gráfico deve identificar **categoria, métrica e unidade** com clareza; exibir quantidade e potência separadas (nunca misturar em eixo ou somar).
- Evitar as descrições extensas, avisos repetidos sobre "N distribuidoras sem valor homologado" e jargões em páginas de negócio. Preservar precisão: quando houver cobertura parcial, **não chamar número de total nacional**, e deixar documentação de qualidade em Metodologia.
- Experiência `Brasil / Grupo / Distribuidora` coerente com Matriz e Comparador; **um catálogo semântico reutilizável** e fontes DDA/MCPSE referenciadas. Regras de filtros cruzados só com cubos exatos, **não estimar cruzamentos**.
- Não alterar nomenclatura, seleção e conceito do Comparador aprovado (Tabela / Gráficos / Radar na mesma área, e benchmark por grupos, por DIST e Brasil total), que constam da issue #5. Se isso ainda não estiver implementado, integrar à entrega R3 sem regressão.

## 5. Execução, testes e handoff para ChatGPT

1. Criar/ajustar catálogo semântico e testes de TUC/entidades; corrigir navegação de categorias clicáveis e filtros; garantir que todas as somas tenham população e unidades definidas; UI real no navegador desktop/mobile.
2. Implementar e auditar drill-down de SUB/CTMT/CTAT/CONJ com **contagens de vínculos distintos**, e validação de fonte. Se os relacionamentos só permitirem parte do escopo, entregar essa parte com status transparente, sem inventar os demais.
3. Verificar situação real de ETL histórico na máquina; iniciar/retomar com checkpoints seguros 2022–2024 quando viável, homologar recortes conforme dados disponíveis; construir página Evolução com gráficos/tabela reais para células já homologadas.
4. Produzir estudo de viabilidade de Previsões; **sem treino de modelo e sem produção**.
5. Testar `lint`, `typecheck`, unit, package validation, Playwright mobile/desktop, acessibilidade, limites/valores nulos, ranking e comparabilidade histórica; preservar 2025 pronto.
6. Gerar **preview** no projeto Vercel correto e atualizar PR #4, issue #5 e `HANDOFF-R3-PRE-PRODUCAO.md` com SHA exato, URL/ID do deploy READY, status histórico verdadeiro, prints, evidências de contagem EQ→UN/TUC, resumo das métricas, QA por etapa, bloqueios e o que ficará para uma R4.
7. **Proibido** merge automático em `main`, force-push, alteração do projeto `geoia-data-hub`, mudança no domínio/branch/proteção de produção ou promoção de deploy. A publicação pública ocorrerá **somente depois** de revisão independente pelo ChatGPT e autorização explícita do proprietário.

## Critérios mínimos para aceitar a entrega

- [ ] Clicar em Transformadores abre conceito imediatamente, descobre TUC 565/570 e demais TUC presentes, inclusive 575 se real, sem forçar UNTRMT/EQTRMT na navegação.
- [ ] Quantidade e potência por TUC, gráfico, tabela abaixo com unidade, recortes de atributos e participações internas/nacionais consistentes.
- [ ] Redes/Consumidores/Geradores/Chaves/Disjuntores/Religadores/Reguladores/Bancos/Medidores/Estruturas/Subestações/Circuitos/Conjuntos acessíveis por conceitos e com desdobramentos úteis, sem somas UN+EQ.
- [ ] Ativos vinculados por SUB, alimentador e CONJ contados por chave validada, sem multiplicação por joins e sem exposição indevida de identificadores.
- [ ] Evolução oferece 3 modos Brasil, Grupo, Distribuidora (multi-DIST), gráficos/tabela, somente 2022–2025 homologados, consolidação por perímetro demonstrada.
- [ ] Previsões têm diagnóstico realista de dados e viabilidade, sem publicação de números previstos sem aprovação.
- [ ] R2 preservada (mapa, comparador, matriz, visual, QA, privacidade) e preview/PR prontos para nova auditoria ChatGPT.
