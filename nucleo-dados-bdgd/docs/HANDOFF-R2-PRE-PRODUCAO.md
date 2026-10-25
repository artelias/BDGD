# Handoff R2 — pré-produção (Claude → auditoria ChatGPT)

**Data:** 23/10/2026 · **Responsável pelo produto:** Arthur Henrique Elias de Lima · **Escopo:** revisão R2 até preview. **Nada foi publicado em produção.** A `main` não foi alterada, não houve merge automático nem force push.

## 1. PR, branch e commits

| Item | Valor |
|---|---|
| PR | https://github.com/artelias/BDGD/pull/4 (rascunho) · base `feat/nucleo-dados-bdgd-portal` |
| Branch | `feat/dashboard-bdgd-2025` |
| Issue | https://github.com/artelias/BDGD/issues/5 |
| Commits R2 | `508ae3f` ETL R2 + pacote homologado versionado + gate de CI · `8c533d2` web R2 · `316bbb7` merge das especificações R2 do portal · `7ac023c` vínculos EQ→UN, rótulo neutro TUC, matriz de paridade, capturas (CI verde, preview READY e verificado) · commit seguinte: títulos de página + este handoff |
| Commits anteriores (fase A) | `b618df9`, `7fd73db`, `2fcb9dc`, `53bff26`, `1a50855` |

## 2. Preview Vercel

| Item | Valor |
|---|---|
| Projeto | `nucleo-dados-bdgd` (`prj_yO3RCoffttr3LSnLP5quAyU26uej`), time Hobby `team_3IqA7EuZ6Mr93rksDBf0f5Yv` |
| Deploy do commit `7ac023c` | `dpl_FsXfyBcFwYtPsTngFNZ6PDQSVGFy` · `target: preview` (null) · READY · verificado com Playwright no preview protegido: 7 rotas + navegação cliente, nenhuma resposta 4xx/5xx, nenhum erro de console, release `bdgd-2025-12-31-v1-99d-2f6fa3879a` servido |
| URL fixa da branch | https://nucleo-dados-bdgd-git-feat-dash-7286b5-arthurhenriqueelias-6367.vercel.app |
| Proteção | `ssoProtection: all_except_custom_domains` (inalterada). Teste autenticado: ferramenta `get_access_to_vercel_url`/link de compartilhamento do painel Vercel |
| Configuração | `framework: null`, `installCommand: npm ci`, `buildCommand: npm run build`, `outputDirectory: out`, Node 22.x, root `nucleo-dados-bdgd/web`, `productionBranch: main` — **nenhuma** alteração de domínio, alias, branch de produção ou proteção nesta fase |
| Outros projetos | `geoia-data-hub` não foi tocado |
| Observação | previews da branch `feat/nucleo-dados-bdgd-portal` (só documentação, sem a aplicação web) aparecem como ERROR no mesmo projeto; não afetam esta branch |

## 3. Dados 2025

| Item | Valor |
|---|---|
| Release | `bdgd-2025-12-31-v1-99d-2f6fa3879a` · contrato 1.1.0 · `status: homologado` · `quality.status: aprovado` (critérios técnicos automatizados) |
| Data-base | somente `2025-12-31`; nenhuma substituição por 2024/2026 |
| GDB elegíveis / processados | 99 / 99 · quarentena 0 · falhas de reconciliação 0 |
| Sem publicação 2025 (ausentes, nunca zero) | DIST 70, 71, 72, 73, 75, 84, 386, 397, 2904, 5217, 5274, 5279, 6611, 6612, 6896 |
| Critérios de homologação (`manifest.homologacao.criterios`) | todas elegíveis processadas; reconciliação sem falhas; facetas exatas DECIMAL; ARAT válida em todas; grupos com fonte ou "não confirmado"; facetas R2 (município/TUC) em todas; sem colunas individuais — **todos verdadeiros** |
| Métricas | 86 homologadas, 10 com ressalvas, 3 não homologadas (potência UG* — N/D), 39 informativas (`metricas_homologacao.csv`) |
| N/D relevantes | quantidade de consumidores N/D em 22 de 297 tabelas UC (regra UC v2: mais de um registro ativado por código); potência de geração N/D em todas (POT_INST sem semântica comprovada); potência UNTRAT N/D em 2 DIST |
| Pacote | `nucleo-dados-bdgd/output-publicavel/2025-12-31` (36 MB, só agregados) · validador estrutural OK |
| Separação de QA | `QA_BDGD_2025`: acima. `PARIDADE_BI_VPE`: **NAO_AVALIADA_PBIX_AUSENTE** — ver `MATRIZ-PARIDADE-METRICAS-VPE-2024.md` |

### TUC e vínculo EQ→UN
Facetas `TUC` e `A1+TUC` lidas dos campos reais de EQTRMT, EQTRAT, EQSE, EQRE, EQCR, EQME, EQTRM, BAR e PONNOT; descrições do MCPSE (Res. 674/2015). Vínculos validados por chave existente no destino. Evidência nacional (99 DIST): EQTRMT TUC 565 = 6.103.972 equipamentos → 6.010.967 instalações UNTRMT distintas; EQSE TUC 160 = 5.268.771 → 2.543.002 instalações. Tabela completa em `MATRIZ-PARIDADE-METRICAS-VPE-2024.md` e `indicadores_vinculos_tuc.csv`. Códigos sem correspondência no MCPSE (ex. `000`) aparecem com rótulo neutro; a auditoria adicional desses códigos foi retirada do escopo pelo proprietário. Achado registrado para revisão futura: em alguns grupos o código `000` concentra parte relevante da potência de EQTRMT (ex.: Energisa, 64,5%).

### Facetas e cobertura
283 cubos (434 linhas de catálogo; 386 com rollup permitido, 48 não — categorias de UC sobrepostas). 18 cubos por município (código IBGE do campo `MUN` em UC*, UG*, UN*, PIP, PONNOT; redes SSD* não têm o campo e não recebem recorte municipal) e 18 por TUC. QA de município (`qa_municipios.csv`): 16 códigos fora da tabela IBGE (457 registros) e 563 registros sem código, de 203,9 milhões. Os cubos municipais de UC são agregados por município; recomenda-se ao auditor confirmar a política de publicação para municípios com poucos consumidores.

### Grupos e distribuidoras
11 grupos com controlador em 31/12/2025 comprovado por fonte; demais distribuidoras "grupo não confirmado", fora de somas de grupo. Mudanças posteriores (transferências J&F concluídas em abril/2026) não alteram 2025.

## 4. Testes (local, commit `7ac023c`)

| Etapa | Resultado |
|---|---|
| ESLint / TypeScript | sem erros |
| Vitest | 31/31 (inclui aceite do radar: A=1500, MAX_g=2000 → 75%; MAX_d=1200 → 125%) |
| Smoke do contrato + validador do pacote | OK |
| Build estático Next 16.4.2 | OK (9 rotas) |
| Playwright E2E + axe (desktop e celular) | 29/29 — inclui: clicar de novo desmarca, clique fora das áreas volta ao Brasil, "Ver Brasil", ranking 12↔99 com feedback, KPIs sem transbordo, "Como é calculado?", N/D explicado, rodapé/contato, Matriz extensão + UF + CSV, comparador espelhado + radar >100%, Explorar TUC 565 + participação + vínculos, Evolução sem números, acessibilidade em 6 rotas claro/escuro |
| CI GitHub | workflow `nucleo-bdgd-web.yml`; agora **exige** o pacote versionado e a coerência `release_id` pacote = assets web |

## 5. Capturas
`nucleo-dados-bdgd/docs/screenshots/r2/` — Panorama, detalhe de distribuidora, Matriz, Comparador (valores A × B + radar), Explorar (TUC 565, grupo Energisa), Evolução e Metodologia, em desktop e celular, claro e escuro.

## 6. Checklist por tela

| Tela | Estado | Observação |
|---|---|---|
| Panorama | OK | toggle/clique fora/"Ver Brasil"; KPIs com container queries; até 8 indicadores e conjuntos prontos (salvos no navegador); explicações em dois níveis; ranking com rolagem e "Mostrando N de M"; N/D com distribuidoras e motivo; bloco de cobertura só na Metodologia; aviso discreto só se o release não estiver homologado |
| Matriz nacional | OK / PARCIAL | medidas principal/quantidade/extensão/potência só onde aplicáveis; ativos multi-seleção com conceitos e favoritos; grupo, distribuidoras, UF (área aproximada; valores da distribuidora inteira); chips; URL; CSV longo com versão/regra/cobertura/status. **Município**: indisponível na Matriz (exigiria cubos município × todos os tipos); disponível em Explorar para tipos com `MUN` |
| Evolução histórica | PARCIAL (honesto) | "Histórico em preparação"; só contagens de execução: 2022 74/99 processadas, 2023 62/89, 2024 76/97; 0 homologadas; runner pausado (`STOP_REQUESTED`) para priorizar 2025 |
| Comparador | OK | gráfico de diferença preservado + Valores A × B espelhados; ordenação por família funcional/maiores diferenças; Radar · Benchmark (lado B, Brasil, maior grupo, maior distribuidora), mesmo denominador, >100% sem truncar, líder por eixo, tabela acessível e CSV |
| Explorar ativos | OK / PARCIAL | conceito → recorte TUC → medida → atributos; modo avançado com códigos; escopo Brasil/grupo/distribuidora do grupo; participação dupla no mesmo cubo com N/D por cobertura/sobreposição; vínculos EQ→UN; inventário de atributos (filtrável/requer cubo/requer junção/não publicável). A2–A6 do TUC sem cubo |
| Metodologia e qualidade | OK | sem redesenho; seção `#dicionario`; cobertura mantida; texto de paridade VPE atualizado |
| Previsões | OK | roteiro, sem modelos |
| Rodapé/autoria | OK | "Desenvolvido por Arthur Henrique Elias de Lima", mailto, "ANEEL — BDGD (Dados Abertos)"; frase "Projeto independente…" removida do rodapé |

## 7. Erros e limitações conhecidos
- Paridade com o BI VPE 2024 não avaliada (PBIX ausente) — não bloqueia a R2.
- Município fora da Matriz; redes sem recorte municipal (campo inexistente).
- Pacote web: maior arquivo de faceta `UCBT.json` ≈ 4 MB (carregado sob demanda).
- Previews da branch de documentação falham no mesmo projeto (sem app web).

## 8. Segurança e dados públicos
Somente agregados por DIST/entidade/categoria; nenhum GDB, ZIP, Parquet, COD_ID, CPF, endereço ou credencial no repositório ou no Vercel. Next 16.4.2 com avisos de segurança corrigidos; `npm audit --omit=dev --audit-level=high` no CI. Nenhum recurso pago criado.

## 9. Reprodução
```bash
# ETL (Python 3.12, venv em D:\NUCLEO_BDGD_2025\.venv)
python scripts/run_lote.py ...            # extração/checkpoints por DIST (já concluída)
python scripts/75_facetas_exatas.py       # cubos exatos DECIMAL
python scripts/76_facetas_r2.py           # município, TUC, A1+TUC, vínculos EQ->UN
python scripts/80_monta_pacote.py         # pacote output-publicavel/2025-12-31
node nucleo-dados-bdgd/etl/validate-publication.mjs output-publicavel/2025-12-31
python scripts/85_assets_web.py output-publicavel/2025-12-31 nucleo-dados-bdgd/web/public/data referencias/natural_earth
# Web
cd nucleo-dados-bdgd/web && npm ci && npm run lint && npm run typecheck && npm test && npm run build && npx playwright test
```
Cópias versionadas dos scripts: `nucleo-dados-bdgd/etl/bdgd2025/`.

## 10. Rollback
Produção não foi alterada. Para descartar a R2: não promover o preview; o PR #4 continua em rascunho. Para voltar a um preview anterior, usar o deployment de `1a50855` no painel do projeto (somente preview). Nenhuma mudança de alias/domínio a desfazer.

## 11. Para o ChatGPT
Seguir `GATE-PRODUCAO-R2-CHECKLIST-CHATGPT.md`. Promoção a produção somente com autorização expressa do proprietário.
