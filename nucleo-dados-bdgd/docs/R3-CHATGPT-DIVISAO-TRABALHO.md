# Coordenação R3: branch ChatGPT × Claude

Base comum observada em 23/10/2026: PR #4 em rascunho, HEAD `d54f7d311d77f924e4df3ff2e61d9f13cbb5478b`. Nenhuma evidência de R3 enviada à branch do Claude no instante da inspeção. Trabalho local não enviado por Claude é desconhecido.

Branch independente: `feat/chatgpt-r3-panorama-iasc-previsoes` (sem merge, produção ou alteração de Vercel).

| Responsável | Superfícies de propriedade |
|---|---|
| ChatGPT | `web/src/components/pages/Panorama.tsx`, `web/src/lib/panorama-r3.ts`, `web/tests/panorama-r3.test.ts`, `etl/iasc/**`, `docs/R3-CHATGPT-*.md` |
| Claude | `web/src/components/pages/Explorar.tsx`, `Matriz.tsx`, `Comparar.tsx`, `web/src/lib/catalogo.ts`, `dataset.ts`, `facets.ts`, `participacao.ts`, `etl/bdgd2025/**`, históricos e `Evolucao` |
| Compartilhados: revisar antes de tocar | `web/src/app/globals.css`, `web/src/lib/types.ts`, `web/src/lib/kpis.ts`, `web/src/app/panorama.module.css`, `web/public/data/**` |

ChatGPT **não altera `catalogo.ts` nem ETL de 2025**: a classificação patrimonial TUC usa agregados EQ* existentes e verifica correspondência total por `DIST+entidade`. Se Claude mudar `vinculosTuc` ou o catálogo, resolver integração por revisão de diff e regressão de testes antes do merge. A separação é por arquivos, não por simples existência de branches; mudanças sobrepostas continuam exigindo coordenação.

**Bloqueios:** sem produção/merge de branch principal; sem projeções treinadas; sem IASC vinculado por nome; sem alegar total nacional a partir de agregação parcial. Testes de regressão devem cobrir níveis Brasil, grupo e DIST e null versus zero.

**Handoff para Claude**: evitar os arquivos sob responsabilidade ChatGPT e comunicar qualquer mudança na estrutura `vinculosTuc`, esquema de `IndexData` ou semântica `UC*`. Após entrega independente, integrar através de PR dedicado, resolvendo conflitos sem sobrescrever trabalhos concomitantes.
