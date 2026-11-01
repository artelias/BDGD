# 09 — Limitações reais e decisões humanas pendentes

## Limitações dos dados e da validação (não contornáveis nesta entrega)

1. **Não há 3 origens independentes.** Há 2 (2023 e 2024) e nenhum point-in-time elegível (vintage não comprovada). Nenhum modelo é cientificamente homologado.
2. **Horizontes acima de 1 ano não são validados.** 2027–2030 são extrapolações com fórmula explícita.
3. **Cenários não são intervalos de confiança.** Conservador e Agressivo são hipóteses de crescimento extremo observado na própria série.
4. **Totais nacionais são PARCIAIS.** Três DIST aplicáveis não têm publicação de 2025 (Cerci, Ceres, Cooperalianca); o kVA e os reguladores cobrem só as DIST com dados fisicamente consistentes.
5. **Extraordinárias nunca são publicadas automaticamente.**
6. **Potência de reguladores** é publicada por DIST na convenção registrada (própria ou passante) e **não tem total nacional**. Em 33 DIST o campo mistura convenções.
7. **TUC 570 kVA:** 37 DIST ficam fora porque o kVA do equipamento diverge mais de 5% do da instalação, ou não passam o gate. É preciso decidir qual fonte prevalece (ver decisão 5).
8. **Territorialização:** só as cinco séries do nível A são territoriais. As demais entidades têm campos territoriais, mas exigem extração e modelagem territorial ainda não feitas.
9. **Covariáveis externas:** PIB e população do IBGE, DEC e FEC não entram nas séries por distribuidora. EPE e IPEA não estão integrados.
10. **Interface (P2, anterior a esta integração):** uma cópia oculta e não hidratada da página pode ficar em `<div hidden id="S:0">`, por causa do Suspense do layout raiz. É invisível, mas duplica ids no DOM (ver `06_TESTES_E_CI.md`).
11. **Ambiente:** os testes que dependem da base local em `D:` (93) rodam só nesta máquina. O Safari em aparelho físico não foi testado; o "iPhone estreito" é emulado no Chromium.

## Decisões que cabem a você

1. **Abrir os PRs em DRAFT** pelos links do relatório final, porque não há integração GitHub autorizada nesta sessão:
   - a integração, `integracao/produto-final-20261101` → `feat/motor-cenarios-publicacao-20261028` (#17);
   - o Motor V2, `feat/motor-v2-entrega-20261031` → #18.
2. **Autorizar a publicação do Motor V2 em produção**, que hoje está fechada pelo portão. Enquanto isso, só a homologação e o preview o exibem.
3. **Homologar ou não a ponte da Celesc 2023**, a política `INTERVALO_NAO_ANUAL` (hoje ressalva) e a regra de sucessão societária usada no Motor V2.
4. **Adotar `consumidores_reconciliado` como fonte pública de Consumidores** (hoje interna e canônica no Motor V2; o motor público V1 usa o contrato).
5. **TUC 570:** decidir se o kVA da instalação (UNTRAT) pode substituir o do equipamento quando divergem; isso liberaria até 37 DIST.
6. **Reguladores:** decidir se a métrica pública deve ser a potência passante calculada (V × I, homogênea por construção) em vez de POT_NOM.
7. **Ordem de merge e destino das branches de trabalho** (`feat/motor-v2-granular-territorial`, `codex/qa-frontend-homologacao-20261031`, `wt-qa-integracao-v2-20261031`).
8. **Fechar o PR #15** como superado pelo #16: é uma implementação concorrente da mesma limpeza de UX e não foi incorporado.
9. **Expansão territorial** das demais entidades (geradores, iluminação, postes etc.) numa próxima etapa.
