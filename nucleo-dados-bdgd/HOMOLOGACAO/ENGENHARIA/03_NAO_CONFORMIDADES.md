# 03 — Não conformidades (engenharia)

Severidade:
- **Crítica:** bloqueia o aceite.
- **Maior:** precisa estar corrigida ou ter aceite humano explícito.
- **Menor:** registrada, não bloqueia.

Estado:
- ABERTA;
- CORRIGIDA (com evidência);
- ACEITA_COM_RESSALVA (depende de decisão humana registrada no termo).

## Corrigidas nesta rodada (antes do aceite)

| Id | Severidade | Descrição | Causa | Correção e evidência | Estado |
|---|---|---|---|---|---|
| NC-ENG-01 | Maior | O agregado nacional dos cenários extremos aparecia como cenário nacional. O documento 11 afirmava um alerta nacional de geradores que não existia nos artefatos nem na tela | Soma dos extremos individuais sem rótulo nem comparação com a trajetória nacional | `exportar_web.agregado_extremos` compara o crescimento implícito com o nacional observado na mesma coorte. A tela mostra o Moderado como total e os extremos como "soma dos extremos individuais (não é cenário nacional)", com alerta (23 de 28 totais fora da faixa observada). Documento 11 corrigido. Testes: `test_produto_web_v2.AgregadoNacionalDosExtremos`, `e2e/release-correcoes.spec.ts` (geradores) | CORRIGIDA |
| NC-ENG-02 | Maior | Produto público com 8 extremos publicados sem o Moderado (6 séries); a tela mostrava o estado da métrica para séries parciais | Regra de publicação por cenário, independente, no gerador | Regra "extremo só com Moderado" e motivos por série; `aplicar_regra_moderado.py`; `cenarios.py --check` OK; completude única na tela. Ver `docs/ENTREGA_FINAL_2026/14` | CORRIGIDA |
| NC-ENG-03 | Maior | Contagens com decimais: JSON do Motor V2 (`36241.0`), eixo da Evolução, `fmt()` genérico e notação compacta "12,5 mil" | Serialização float no exportador; eixo sem `minInterval`; formatadores genéricos | Inteiros JSON no exportador (fração = erro); `fmtEixo`/`minInterval`; contagem nunca compacta. Testes: Python, Vitest e E2E | CORRIGIDA |
| NC-ENG-04 | Maior | Mapa com cores misturadas após alternar o tema | `data-theme` gravado num efeito do pai, depois dos efeitos dos filhos | `useLayoutEffect` no ThemeProvider. `e2e/mapa-tema.spec.ts`: 10 alternâncias, pixels do canvas, desktop e mobile | CORRIGIDA |
| NC-ENG-05 | Menor | Informação técnica na navegação principal | Bloco de metadados na lateral | Removida; mantida em Metodologia e qualidade. `e2e/release-correcoes.spec.ts` | CORRIGIDA |
| NC-ENG-09 | Menor | PR da RC não aberto | Sem integração GitHub autorizada na sessão | PR #22 aberto em rascunho pelo responsável (base #17) | CORRIGIDA |
| NC-ENG-12 | Maior | Commit `26ec937` (evidências de CI e contagens do termo) relatado como publicado, mas ausente no remoto | O push falhou sem mensagem de erro e não foi conferido com `git ls-remote` | Publicado nesta rodada e conferido no remoto; a partir daqui todo push é verificado com `ls-remote` | CORRIGIDA |
| NC-ENG-13 | Maior | Ao retirar o painel exploratório (PR #21), a ressalva da Coopera (UCBT 2025 vazia, subtotal 225 AT) e as observações cadastrais deixariam de aparecer em Previsões | Só o painel retirado mostrava a Coopera selecionável e bloqueada e o componente de observações | No painel principal, a Coopera fica selecionável e bloqueada em consumidores, e as observações da DIST/ativo aparecem (`1be7a43`). Testes: `reconciliacao.spec.ts`, `cenarios-motor.spec.ts` | CORRIGIDA |
| NC-ENG-14 | Menor | A primeira adaptação do teste de "rótulos cortados" para o painel principal usava `getBBox().x` | No ECharts o texto é posicionado por `transform`, e o x local é negativo por construção | Verificação pela geometria na tela (cada rótulo dentro da caixa do gráfico) | CORRIGIDA |

## Abertas ou dependentes de decisão humana

| Id | Severidade | Descrição | Por que não foi corrigida aqui | Ação necessária | Estado |
|---|---|---|---|---|---|
| NC-ENG-06 | Maior | Preview de homologação não inspecionado em conteúdo | O preview exige login SSO da Vercel, e a ferramenta disponível não alcança o conteúdo | Inspeção humana pelo checklist `05_CHECKLIST_INSPECAO_PREVIEW.md` (10 áreas, itens com severidade) | ABERTA |
| NC-ENG-07 | Maior | Totais nacionais de Conservador/Agressivo: publicar ou não | Decisão de produto (a tela já rotula e alerta) | Decidir se a versão de produção mostra a soma dos extremos ou só o Moderado nacional | ACEITA_COM_RESSALVA |
| NC-ENG-08 | Menor | Produto público com 1.206 séries parciais (1 ou 2 cenários) | É uma regra de seleção do motor, não um defeito de exibição; ampliar exige o trabalho de otimização, sem relaxar a tolerância | Revisão do relatório de otimização (branch experimental) antes de qualquer mudança no produto | ACEITA_COM_RESSALVA |
| NC-ENG-10 | Menor | Safari em aparelho físico não testado | Sem dispositivo; o projeto iPhone estreito emula o viewport no Chromium | Teste manual em iOS antes da produção | ABERTA |
| NC-ENG-11 | Menor | 93 testes do Motor V2 dependem dos dados locais em `D:` | Volume e licença dos dados brutos; não vão para o CI | Registrado; a auditoria local completa é parte da evidência | ACEITA_COM_RESSALVA |

**Nenhuma não conformidade crítica aberta.** As maiores abertas (NC-ENG-06 e NC-ENG-07) dependem de ação humana e estão no termo como condições do aceite.
