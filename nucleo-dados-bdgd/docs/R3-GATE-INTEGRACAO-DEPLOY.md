# Gate de integração e publicação — PR #4 + PR #6

**Estado:** checklist de aprovação, não autorização de deploy. Nenhum merge ou publicação é automático.

## 1. Fronteiras de responsabilidade
- **PR #4 (Claude):** Explorar Ativos, Matriz, Comparador, Evolução, catálogo, ETL histórico, auditoria e reconciliação de dados.
- **PR #6 (ChatGPT):** Panorama, interface/contrato de Previsões, metodologia matemática, laboratório de Motion Design e documentação de arquitetura.
- **Atenção:** PR #6 foi criado sobre a branch do PR #4. Comparar a base de cada PR antes de integrar, evitando commits duplicados. Se o PR #4 avançar, rebase/merge controlado após inspeção do diff, sem sobrescrever alterações locais do Claude.

## 2. Critérios bloqueantes — dashboard observacional
- [ ] PR #4 está estável, sem processamento histórico pendente que contamine a base pública.
- [ ] Todas as métricas publicadas têm origem, competência, unidade, regra de contagem, cobertura e estado de homologação.
- [ ] Ausência, quarentena e ruptura temporal nunca são convertidas em zero.
- [ ] Reconciliação por DIST/entidade/métrica com a BDGD original, incluindo regras de COD_ID e DDA.
- [ ] Sem dupla contagem de UN*/EQ*, UC entre entidades, ou perímetros societários.
- [ ] Os módulos Panorama, Explorar, Matriz, Comparador, Evolução e Metodologia apresentam estados de erro e N/D coerentes.
- [ ] Navegação, filtros combinados, responsividade, teclado, contraste, leitores de tela e movimento reduzido revisados.
- [ ] Sem publicação de GDB bruto, Parquet privado, identificadores individuais ou credenciais.
- [ ] Dependências e licenças conferidas, links externos revisados.
- [ ] `npm ci`, `npm run typecheck`, `npm run lint`, `npm test`, `npm run validate:data` e `npm run build` aprovados no checkout integrado.
- [ ] Smoke test do build estático com filtros, mapas, exportações, erros de rede e navegação.
- [ ] Aprovação explícita do responsável antes de merge, promoção ou deploy.

## 3. Critérios bloqueantes — previsões quantitativas
- [ ] Histórico multianual homologado e perímetros de EPB/EBO e EMR/EMG/ENF reconciliados.
- [ ] Cobertura e granularidade adequadas à família de ativos e ao horizonte; observações suficientes para backtesting.
- [ ] Topologia, restrições elétricas e premissas econômicas rastreáveis.
- [ ] Baseline, cortes temporais, métricas fora da amostra, viés e sensibilidade documentados.
- [ ] Evidências de validação vinculadas à versão de dados, código, modelo e protocolo.
- [ ] Cenário condicional rotulado como simulação; não publicado como previsão homologada.
- [ ] CAPEX com preços-base, deflator, unidades, substituições e custos explicitados.
- [ ] Revisão estatística e elétrica independente; aprovação de publicação.
- [ ] Testes do contrato de previsão e testes de integração com dados reais aprovados.

**Nota:** o contrato de publicação implementa uma barreira preliminar (evidências, mínimo de observações, comparação com baseline e cobertura integral). Não substitui auditoria estatística nem comprova a veracidade de metadados enviados. A regra de cinco observações e duas origens de teste é apenas um piso técnico inicial; deve ser endurecida por modelo e horizonte.

## 4. Motion Design System
- [ ] Laboratório `/design` revisado visualmente em desktop e mobile.
- [ ] Respeito a `prefers-reduced-motion` e possibilidade de desligar movimento.
- [ ] Animação não modifica valor numérico, filtro ativo ou estado de homologação.
- [ ] Transições sem layout shift relevante ou degradação perceptível em aparelhos modestos.
- [ ] Componentes e tempos de transição aprovados antes de propagação às páginas de dados.

## 5. Sequência de liberação
1. Homologar dados e PR #4.
2. Integrar PR #6 em branch de integração com inspeção de conflitos.
3. Executar pipeline de testes, build, acessibilidade e smoke tests.
4. Disponibilizar preview restrito e coletar aprovação.
5. Publicar dashboard observacional com previsões não validadas ocultas/identificadas como pesquisa.
6. Liberar projeções somente após os critérios da seção 3.

## 6. Pendências verificáveis desta frente
- Código enviado ao GitHub não equivale a build executado.
- Testes Vitest adicionados, mas **não executados nesta sessão**.
- Sem acesso aos GDBs locais do Claude para reconciliação independente.
- Sem merge, sem preview publicado e sem deploy.
