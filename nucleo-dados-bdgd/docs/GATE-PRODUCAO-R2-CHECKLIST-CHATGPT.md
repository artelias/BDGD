# Gate de produção — revisão independente por ChatGPT

**Projeto:** Núcleo de Dados da BDGD (artelias/BDGD). **Responsável pelo produto:** Arthur Henrique Elias de Lima. **Data do contrato:** 23/10/2026.

**Separação de funções:** Claude implementa e entrega preview + PR; ChatGPT audita quando o proprietário voltar e, apenas com comando explícito de publicação em produção, executa promoção/deploy controlado e confirma o resultado. Este documento **não autoriza publicação automática**.

## Informações a receber do Claude

| Campo | Obrigatório |
|---|---|
| URL do PR atualizado, branch, base e SHA exato do commit | Sim |
| Projeto Vercel, URL e ID do deployment READY de preview | Sim |
| URL protegida/forma de teste autenticado do preview | Se protegido |
| Manifesto de release 2025, versão de contrato, data-base, origem e geração | Sim |
| Total de GDB elegíveis, processados, ausentes sem publicação e quarentena | Sim |
| Relatório ETL com reconciliação por DIST e estado de facetas | Sim |
| Auditoria BI VPE 2024 por regra; indicadores faltantes e N/D | Sim ou bloqueador |
| Dicionário de métricas TUC, fonte, unidades, joins EQ/UN e QA | Sim para indicadores exibidos |
| Cobertura de recortes DDA e algoritmos de participações/benchmark | Sim |
| Resultados de lint, tsc, unit, smoke/validador, CI e Playwright | Sim |
| Capturas reais desktop/mobile, light/dark, páginas e estados | Sim |
| Plano de rollback, proteção e alias Vercel atual, nenhum projeto alheio afetado | Sim |

## Checklist de auditoria técnica e visual do ChatGPT

- [ ] Analisar diff completo do PR, arquivos de configuração CI/Next/Vercel e reportar vulnerabilidades, dependências ou mudanças fora do escopo.
- [ ] Confirmar que os números **não** são inventados; dados 2025, ausência 2025 e histórico 2022–2024 não se misturam.
- [ ] Verificar manifesto, QA por DIST, facetas exatas e cobertura completa (caso parcial, declarar restrição e não chamar homologado).
- [ ] Diferenciar linha/registros, COD_ID distintos, população física por TUC e unidade/equipamento; aplicar regras auditadas por métrica, não por suposição.
- [ ] Participação interna do grupo e participação na mesma categoria nacional com denominadores, rollup e cobertura compatíveis; testes com categorias sobrepostas e universo parcial.
- [ ] Benchmark radar grupo: máximo entre grupos verificados; benchmark individual: máximo entre DIST elegíveis; Brasil total: total nacional. Os líderes por indicador precisam de nome, valor, fonte, cobertura; porcentagens podem ultrapassar 100% com aviso, sem truncamento.
- [ ] Checar em browser que mapa seleciona, faz zoom, desmarca ao clicar na mesma DIST e em vazio, botão `Ver Brasil` fica visível com painel aberto; nenhuma corrida assíncrona.
- [ ] Rank `Todas`/12 muda efetivamente a lista e rolagem; KPIs não estouram em 360–390 px, 768–1024 e desktop.
- [ ] Nome e email corretos; terminologia limpa, links ANEEL e ausência de afirmação enganosa de chancela. Barra Metodologia não foi redesenhada sem aprovação.
- [ ] Matriz/Comparador/Explorar com filtros reais e sem combinatória DDA simulada; município/linha AT somente com vínculo comprovado.
- [ ] Matriz de evolução: dados anuais observados e homologados comparáveis ao perímetro 2025, ou placeholder honesto; não exibir previsão ML.
- [ ] CI verde para exato SHA candidato, validação do mesmo pacote servido, Playwright, accessibility axe, screenshots mobile/light/dark, segurança do bundle (sem COD_ID/credenciais).
- [ ] Vercel preview do exato SHA confirmado sem erros runtime; produção e projeto `geoia-data-hub` inalterados.

## Condições precedentes de promoção

- [ ] **Solicitação expressa do usuário em um turno futuro** autorizando esta versão concreta para produção; este documento não substitui autorização.
- [ ] Identificar de forma inequívoca **deployment ID e SHA** aprovados para promover. Não publicar o último commit por conveniência se houver novos changes não auditados.
- [ ] Conferir projeto **`nucleo-dados-bdgd`** e escopo da equipe, branch de produção, aliases/domínios, custos e proteção de login. Evitar qualquer ação no `geoia-data-hub`.
- [ ] Garantir que não haverá deploy acidental da `main`, que a branch/PR não será mergeada sem autorização, e que a promoção não expõe dados privados.
- [ ] Guardar ID/URL de deployment anterior apto ao rollback e plano de revert; manter preview funcional.
- [ ] Após promoção: acessar **URL pública** sem autenticação desnecessária, confirmar rotas/assets/CORS, MapLibre worker/ARAT, mapas, filtros e no-console-errors, responsividade e cabeçalhos de segurança.
- [ ] Documentar URL pública final, SHA e resultado real de homologação; se erro, retornar para versão anterior e informar.

**Se qualquer condição crítica falhar, não promover.** Enviar um relatório conciso de pendências ao proprietário para correção pelo Claude. ChatGPT não executa essas verificações em segundo plano nem publica automaticamente quando o Claude concluir.
