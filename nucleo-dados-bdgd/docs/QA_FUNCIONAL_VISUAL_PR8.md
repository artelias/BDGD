# QA funcional e visual — PR #8

Base: `db0f27ba5cbc329a70794d65a956cd18fe1660d7`, branch `feat/chatgpt-qa-cenarios-reconciliados-codex`.
Branch de correção: `feat/qa-funcional-visual-final-pr8`.

## Correções

| Problema comprovado | Correção e regressão |
|---|---|
| Busca global não encontrava Previsões/cenários | Indexação da página e seus termos; teste de busca e abertura |
| Busca por UCAT abria o conceito com outra entidade técnica | Link preserva `tec=UCAT`; teste da entidade exibida |
| Diálogos não completavam o ciclo de teclado e retorno ao acionador | Foco inicial, Tab/Shift+Tab, Escape, retorno do foco, fundo inerte e bloqueio de rolagem |
| Folha Mais permanecia aberta ao selecionar a página atual | Fechamento explícito nos links; regressão em celular |
| Modo avançado inacessível com a lateral oculta no celular | Acionador móvel com estado acessível; abertura da visão técnica |
| Marca cortada na lateral e última opção dos segmentos esmaecida | Marca com quebra de linha e retirada da máscara permanente |
| Textos de UC v2, ausência física e modelagem contradiziam a interface atual | UC v3 explicitada; diagnóstico legado identificado; N/D separado de zero técnico e ausência física; cenários existentes separados do modelo estrutural ainda não estimado |
| Inventário mantinha referências genéricas à quarentena | Classes específicas de competência, divergência e publicação não localizada |
| CSV habilitado sem linhas/colunas na Matriz | Exportação desabilitada no estado vazio; busca e limpeza testadas |
| Contato no rodapé podia exceder telas estreitas | Quebra de texto sem perder o endereço |

## Cobertura executada

As sete páginas — Panorama, Explorar Ativos, Matriz, Comparador, Evolução Histórica, Previsões e Metodologia — são abertas no build estático, com espera pelos dados efetivos, capturas iniciais e de conteúdo, checagem de erros JavaScript/HTTP e axe WCAG A/AA, nos temas claro e escuro. A suíte inclui desktop 1440×900, Android emulado e iPhone estreito emulado 320×568, além de uma verificação da folha de navegação em paisagem.

Os fluxos cobrem mapa e seleção de distribuidora/grupo, filtros e categorias, TUC 565/570 e potência, facetas técnicas, tabelas e gráficos, comparação e radar, busca com/sem resultados, navegação pelas sete páginas, CSVs de recortes e simulações, estados históricos e dados ausentes. Os testes já existentes de riscos, OLS, proveniência e backtests foram preservados.

As capturas não são uma comparação automática de pixels: são evidência de navegação para inspeção visual. O axe verifica critérios automatizáveis; não representa certificação integral de acessibilidade. A emulação de iPhone usa Chromium, não Safari/iOS físico. Tempos de carga são registrados por teste como diagnóstico local, sem equivalência a benchmark de produção.

## Preservação e pendências externas

506 arquivos protegidos comparados por SHA-256, sem alterações: dados publicados, contratos/ETL, motor e risco de cenários, histórico-contrato e o componente inteiro PrevisoesExploratorias. Não foram modificados arquivos oficiais, GDBs ou checkpoints. Nenhuma aprovação de fonte, republicação ou homologação humana foi feita. Nenhum merge ou deploy foi executado.

Continuam dependentes de decisão/documentação externa: os 13 pares de publicações divergentes; as 11 publicações não localizadas; a validação humana das ressalvas de origem e dos zeros técnicos; reconciliação de sucessões societárias pela frente de dados; homologação estatística dos cenários. As 14 exclusões por competência permanecem aplicadas no inventário. O universo de 414 publicações não foi reclassificado por esta revisão. Os cenários 2026–2030 continuam simulações condicionais, sem validação preditiva.

## Evidências reproduzíveis

Executar em `nucleo-dados-bdgd/web`: `npm ci`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` e `npx playwright test`. O workflow também executa os gates de pacote, assets, histórico, homologação, contrato nacional, cenários e auditoria Python independente.

O job web publica o artefato `qa-desktop-mobile-<run_id>` com relatório HTML, capturas, anexos CSV/JSON e traces de falhas, retido por 14 dias. A página do PR registra o resultado final do CI e o link para essa execução. Para preservar evidências além do prazo, baixar o artefato no GitHub Actions.
