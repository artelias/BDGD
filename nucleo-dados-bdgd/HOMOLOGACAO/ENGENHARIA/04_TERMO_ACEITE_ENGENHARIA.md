# 04 — Termo de aceite de engenharia: Núcleo de Dados BDGD, Release Candidate 1.0

> **Este termo NÃO está assinado nem aceito.** Ele reúne a evidência técnica para a decisão humana. O aceite só existe quando as pessoas identificadas preencherem a seção 9. Nenhuma assinatura, aceite ou aprovação foi registrado em nome de alguém.

## 1. Identificação do objeto

| Campo | Valor |
|---|---|
| Produto | Núcleo de Dados BDGD (portal web e produtos de dados públicos) |
| Versão | Release Candidate 1.0 (pacote web `nucleo-dados-bdgd-web@1.0.0`) |
| Repositório | `artelias/BDGD` |
| Branch | `rc/1.0-20261101` |
| Pull request | #22, em rascunho, de `rc/1.0-20261101` para `feat/motor-cenarios-publicacao-20261028` (#17) |
| SHA de código avaliado | `1be7a43593bb723c1a1054fbcc1403faf2a5793f` |
| Commit definitivo | filho direto de `1be7a43` que acrescenta este dossiê. Só altera `HOMOLOGACAO/ENGENHARIA/` e `docs/ENTREGA_FINAL_2026/`, o que se confere com `git diff --stat 1be7a43 rc/1.0-20261101`. O CI dele está nos checks do PR #22 |
| Data da avaliação técnica | 04/11/2026 |
| Competência dos dados | 31/12/2025, com histórico de 2022 a 2025 e cenários de 2026 a 2030 |
| Ambientes avaliados | build estática local (produção e homologação); CI no GitHub Actions (Linux); preview Vercel `dpl_2PoxnWdtqzufgNkGnwRPiCJEJ82p` (build verificada, conteúdo não inspecionado) |

## 2. Escopo

**Dentro do escopo:**
- integridade e contratos do ETL BDGD;
- reconciliação das entidades físicas;
- natureza física das métricas (contagens inteiras, unidades);
- portão de plausibilidade dos cenários;
- bloqueios, ressalvas e completude dos cenários;
- segurança e portão de publicação do Motor V2;
- cobertura das séries projetadas;
- interface, filtros e exportações, no desktop e no celular;
- painel único de cenários, depois da integração do PR #21;
- coerência entre histórico e projeção na mesma coorte;
- apresentação dos agregados nacionais;
- testes e CI.

**Fora do escopo:**
- homologação científica dos modelos (Processo B, dossiê separado na branch `homologacao/cientifica-20261103`);
- decisão de publicar o Motor V2 em produção;
- desempenho preditivo como critério de aceite técnico.

**Um produto tecnicamente aceito pode ser cientificamente experimental.** Este termo não declara validade científica de nenhuma previsão.

## 3. Matriz de requisitos

Fonte: `01_MATRIZ_REQUISITOS.csv`, gerada por `gerar_matriz_requisitos.py`, com evidências e observações. São **24 requisitos**:
- **18 atendidos**;
- **4 atendidos com ressalva**;
- **0 não atendidos**;
- **2 não verificados**.

| ID | Área | Requisito | Resultado |
|---|---|---|---|
| ENG-01 | Integridade BDGD/ETL | Competência única 31/12/2025, sem preencher DIST sem GDB 2025 com outro ano | atendido |
| ENG-02 | Integridade BDGD/ETL | Contratos de dados versionados e verificados | atendido |
| ENG-03 | Reconciliação de entidades físicas | Agregados reconciliados com os arquivos de origem | atendido |
| ENG-04 | Reconciliação de entidades físicas | Hierarquia UCBT/Consumidores coerente também nas projeções | atendido |
| ENG-05 | Contagens inteiras e unidades | Contagem física sempre inteira em JSON, CSV, cards, gráficos, tooltips, tabelas e comparadores | atendido |
| ENG-06 | Portão de plausibilidade | Extremos implausíveis não divulgados como válidos; correção só com evidência; sem teto arbitrário | atendido com ressalva |
| ENG-07 | Bloqueios e ressalvas | Cenário ou série sem valor publicável aparece com estado e motivo, nunca como zero | atendido |
| ENG-08 | Segurança e publicação | Motor V2 nunca na build de produção | atendido |
| ENG-09 | Segurança e publicação | Produtos públicos sem identificador individual, credencial ou segredo | atendido |
| ENG-10 | Segurança e publicação | Nenhuma publicação, merge ou deploy sem autorização humana | atendido |
| ENG-11 | Cobertura das séries projetadas | Séries parciais não contam como completas | atendido com ressalva |
| ENG-12 | Interface, filtros e exportações | Filtros, tabela, gráfico e CSV sincronizados; sem rolagem horizontal em 7 larguras | atendido |
| ENG-13 | Interface, filtros e exportações | Tema claro/escuro estável no mapa e nos gráficos | atendido |
| ENG-14 | Interface, filtros e exportações | Navegação principal sem informação técnica | atendido |
| ENG-15 | Interface, filtros e exportações | Hidratação sem cópia oculta nem ids duplicados | atendido |
| ENG-16 | Testes | Python, TypeScript, ESLint, Vitest e Playwright aprovados sem enfraquecer asserções | atendido |
| ENG-17 | CI e versionamento | CI Linux aprovado; branch e SHA rastreáveis; PR em rascunho | atendido |
| ENG-18 | Coerência histórico × projeção | Totais comparam histórico e projeção sobre o mesmo conjunto de séries | atendido |
| ENG-19 | Agregados nacionais | Agregado nacional dos extremos não apresentado como cenário nacional | atendido com ressalva |
| ENG-20 | Agregados nacionais | Cenário Agressivo nacional de geradores avaliado | atendido com ressalva |
| ENG-21 | Publicação | Preview de homologação verificado em conteúdo | não verificado |
| ENG-22 | Ciência (fora do escopo) | Homologação científica dos modelos | não verificado |
| ENG-23 | Interface, filtros e exportações | Painel único de cenários sem perder as ressalvas do painel retirado (PR #21) | atendido |
| ENG-24 | Segurança e publicação | Nenhum modelo experimental publicado ou substituído automaticamente | atendido |

## 4. Resultados dos testes no SHA de código `1be7a43`

Os comandos e as contagens estão em `02_EVIDENCIAS_TESTES.md`.

| Bateria | Resultado |
|---|---|
| Motor V2, auditoria completa (`motor_v2.nacional.testes`) | 281 de 281 |
| Emulação do CI sem `D:` (`emular_ci`) | 179 OK, 1 skip herdado |
| Gerador público (`motor_cenarios`) | 25 OK |
| Regeneração idêntica (`cenarios.py --check`) | OK: 29 métricas, 16.010 contagens, folga 2 de 80 |
| ESLint | 0 problemas |
| TypeScript | 0 erros |
| Vitest | 196 de 196 (22 arquivos) |
| Playwright completo, local (desktop, Android, iPhone emulado) | 352 de 352, sem testes desativados ou pulados |
| Build de homologação | OK |

Os oito specs E2E que dependiam do painel retirado pelo PR #21 foram adaptados para exigir o mesmo comportamento no painel principal. Nenhum foi desativado.

## 5. Evidências de CI no SHA de código `1be7a43`

| Workflow | Run | Resultado |
|---|---|---|
| Núcleo de Dados BDGD — web 2025 (push), com E2E completo | [41926075003](https://github.com/artelias/BDGD/actions/runs/41926075003) | success |
| Núcleo de Dados BDGD — web 2025 (PR #22) | [41926084739](https://github.com/artelias/BDGD/actions/runs/41926084739) | success |
| Motor V2 — testes sintéticos | [41926084772](https://github.com/artelias/BDGD/actions/runs/41926084772) | success |
| Núcleo de Dados BDGD — checks 2025 | [41926084724](https://github.com/artelias/BDGD/actions/runs/41926084724) | success |
| Patrimônio MCPSE — contratos | [41926084832](https://github.com/artelias/BDGD/actions/runs/41926084832) | success |
| Motor Universal BDGD — contratos | [41926085523](https://github.com/artelias/BDGD/actions/runs/41926085523) | success |

O commit definitivo também precisa ter CI verde nos checks do PR #22. Sem isso, o requisito ENG-17 deixa de valer (critério 1 da seção 8).

## 6. Ressalvas que acompanham um eventual aceite

1. **Preview não inspecionado em conteúdo** (NC-ENG-06, ENG-21). O preview do SHA final exige login SSO, que a ferramenta não alcança. A build foi verificada no log da Vercel. O revisor humano inspeciona o preview pelo checklist `05_CHECKLIST_INSPECAO_PREVIEW.md` (10 áreas, itens com severidade). Uma falha crítica impede o aceite.
2. **Totais nacionais dos extremos no Motor V2** (NC-ENG-07, ENG-19 e ENG-20). A tela de homologação mostra o Moderado como total nacional. Conservador e Agressivo aparecem como "soma dos extremos individuais", com alerta em 23 de 28 totais. Em geradores, o Agressivo implícito é de 53,3%/ano, contra 27,7–43,5%/ano observados. Isso só afeta a homologação, porque o Motor V2 não vai para a produção.
3. **Produto público com previsões parciais** (NC-ENG-08, ENG-11). São 755 séries completas, 1.206 parciais e 241 sem previsão, todas explicitadas na tela e no CSV. A maioria das parciais vem da regra de seleção por métrica, não de defeito de exibição.
4. **Parâmetros do portão de plausibilidade** (ENG-06). `TOL_MODELO` = 25% e `BASE_MINIMA` = 10 são parâmetros documentados, não derivados dos dados.
5. **Limites do ambiente de teste.** O Safari em aparelho físico não foi testado (NC-ENG-10); ele entra no item 8 do checklist 05. Os 93 testes do Motor V2 que leem a base local não rodam no CI (NC-ENG-11).
6. **Natureza científica dos cenários.** Os cenários de 2026 a 2030 são simulações experimentais rotuladas, sem validação científica independente. O parecer científico consolidado classifica os horizontes de 2 a 5 anos como **NÃO HOMOLOGÁVEIS COM A EVIDÊNCIA ATUAL**. O aceite de engenharia não muda essa classificação.

## 7. Pendências e decisões humanas

Nenhuma não conformidade crítica está aberta (`03_NAO_CONFORMIDADES.md`). As pendências são decisões humanas, descritas com as recomendações em `06_DECISOES_E_RECOMENDACAO_PUBLICACAO.md`:

1. Inspeção do preview pelo checklist 05 (ressalva 1).
2. Decisão deste termo (seção 9).
3. Totais nacionais dos extremos no Motor V2 (ressalva 2).
4. Publicação do Motor V2 em produção (recomendação: não nesta versão).
5. Caminho de publicação da RC e definição da branch de produção. Hoje a produção vem de `feat/metodologia-modelos-por-empresa-20261028`, não da `main`.
6. Destino do PR #15 (recomendação: fechar como superado).
7. Pontes cadastrais (renumeração de conjuntos, Celesc 2023, DIST 7019), que hoje ficam excluídas sem imputação.
8. Nova comparação independente da deriva como Moderado da rede BT, na próxima competência. Nada é substituído automaticamente.
9. Assinaturas do parecer científico, com a recomendação de não homologar 2026–2030 com a evidência atual.
10. Safari em iPhone físico (ressalva 5).

Nenhum merge, deploy de produção ou promoção de preview foi feito.

## 8. Critérios de reprovação (qualquer um impede o aceite)

1. Qualquer bateria obrigatória falhando no SHA a publicar: Python, ESLint, TypeScript, Vitest, Playwright completo, CI Linux web e sintético.
2. Contagem física fracionária ou negativa em qualquer produto público ou tela.
3. Cenário extremo publicado sem o Moderado, ou série parcial apresentada como completa.
4. Valor bloqueado pelo portão de plausibilidade exibido como previsão.
5. Motor V2 presente numa build de produção.
6. Identificador individual, credencial ou segredo nos produtos públicos.
7. Não conformidade crítica aberta, incluindo falha crítica no checklist 05.
8. Mudança nos números publicados sem regeneração verificada (`cenarios.py --check`) ou sem registro.
9. Teste desativado, pulado ou afrouxado para obter CI verde.
10. Preview do SHA final com comportamento diferente do verificado localmente, observado na inspeção pelo checklist 05.

## 9. Decisão humana

Os campos abaixo são de preenchimento exclusivo das pessoas que decidem. Eles estão vazios porque nenhuma decisão foi tomada. O resultado da inspeção do preview é registrado na tabela "Registro da inspeção" do checklist 05 e citado aqui pelo número das falhas.

| Papel | Nome | Função/organização | Decisão (aceito / aceito com ressalvas / reprovado) | Ressalvas aceitas (números da seção 6) | Resultado do checklist 05 (falhas críticas e maiores) | Data | Assinatura |
|---|---|---|---|---|---|---|---|
| Responsável técnico pelo produto | | | | | | | |
| Revisor de engenharia independente | | | | | | | |
| Responsável pela publicação | | | | | | | |
