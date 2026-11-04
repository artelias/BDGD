# 06 — Decisões pendentes e recomendação sobre a publicação em produção

## Situação

- **Produção atual:** deploy de 28/10/2026 (`74190e2`). Ela **não contém** as correções da RC 1.0:
  - contagens inteiras;
  - tema do mapa;
  - lateral;
  - completude dos cenários e regra "extremo só com Moderado";
  - portão de plausibilidade;
  - P2 de hidratação;
  - painel único de cenários (PR #21).
- **RC 1.0:** branch `rc/1.0-20261101`, PR #22 em rascunho. As baterias e o CI estão em `02_EVIDENCIAS_TESTES.md`.

## Recomendação

**Publicar a RC 1.0 em produção como produto de dados com cenários experimentais**, depois de três condições, nesta ordem:
1. inspeção do preview pelo checklist `05`, **sem falha crítica**; falhas maiores corrigidas ou aceitas por escrito;
2. CI verde no SHA a publicar (web com E2E completo e sintético);
3. decisão humana no termo `04`.

Fundamento:
- a RC corrige defeitos **visíveis e já em produção** (decimais em contagens, mapa, cenários incompletos sem explicação, cenários extremos implausíveis), sem alterar números observados;
- os cenários públicos (`motor_cenarios`) vêm rotulados como "simulação condicional, sem validação científica independente". Cada série mostra se é completa ou parcial, com o motivo, e nenhum cenário ausente é preenchido;
- o parecer científico (branch `homologacao/cientifica-20261103`) classifica as previsões de 2026–2030 como **não homologáveis com a evidência atual** nos horizontes de 2 a 5 anos. Isso é compatível com publicação **experimental rotulada**, não com publicação como previsão validada.

**O que não publicar:**
- **Motor V2** (projeções por distribuidora do motor nacional): continua atrás do portão de homologação. A produção não o mostra (o CI reprova a build de produção que o expuser). Publicá-lo exige uma decisão própria;
- modelos do piloto granular e da otimização: registros experimentais, fora do produto.

## Decisões que dependem de você

| # | Decisão | Opções | Recomendação |
|---|---|---|---|
| 1 | Aceite funcional do preview | seguir / corrigir | inspecionar pelo checklist 05 |
| 2 | Aceite de engenharia | aceito / aceito com ressalvas / reprovado (termo 04) | aceito com ressalvas, se o item 1 não tiver falha crítica |
| 3 | Totais nacionais de Conservador/Agressivo no Motor V2 (soma dos extremos individuais) | manter rotulados / mostrar só o Moderado nacional | só afeta a homologação enquanto o Motor V2 não for para a produção |
| 4 | Publicar o Motor V2 em produção | sim / não | **não nesta versão** (experimental, não homologado) |
| 5 | Caminho de publicação da RC | (a) merge da pilha #22 → #17 → … até a branch de produção da Vercel; (b) promoção do deployment de preview do SHA aprovado | definir a branch de produção. Hoje a produção veio de `feat/metodologia-modelos-por-empresa-20261028`, não da `main`, que só tem o diagrama inicial |
| 6 | PR #15 (implementação concorrente da limpeza de UX) | fechar como superado / manter | fechar como superado |
| 7 | Pontes cadastrais: renumeração de conjuntos (15–17 DIST), Celesc 2023, DIST 7019 | homologar / manter excluídas | processo próprio; hoje elas ficam excluídas sem imputação |
| 8 | Deriva como Moderado da rede BT | nova comparação independente / manter `ridge_painel` | nova comparação na próxima competência (candidato 3 de `11_CANDIDATOS_CONFIRMATORIOS.md`) |
| 9 | Homologação científica | assinaturas do parecer 10 | não assinar homologação para 2026–2030 com a evidência atual |
| 10 | Safari em iPhone físico | inspecionar no item 8 do checklist / aceitar o risco | inspecionar |
