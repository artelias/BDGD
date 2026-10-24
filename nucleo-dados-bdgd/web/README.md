# Núcleo de Dados da BDGD — aplicação web

Portal público, sem login, dos agregados BDGD com **DATA_BASE = 31/12/2025**. Desenvolvido por **Arthur Henrique Elias de Lima** ([Arthur.henrique.elias@gmail.com](mailto:Arthur.henrique.elias@gmail.com)). Fonte dos dados: ANEEL — BDGD (Dados Abertos).

## Arquitetura (custo zero, sem servidor)

- **Next.js 16 (App Router) + TypeScript + React 19**, exportação estática (`output: "export"`).
- **Dados:** JSON/GeoJSON versionados em `public/data/2025-12-31/`, gerados por `etl/bdgd2025/85_assets_web.py` **a partir do pacote público validado** (contrato 1.1.0). Nenhum GDB, Parquet ou `COD_ID` chega ao navegador.
- **Camada de consulta** (`src/lib/dataset.ts`, `src/lib/facets.ts`) implementa no cliente a semântica do contrato: fato-base sem filtro; filtro DDA apenas com cubo de dimensões idênticas; `combinacao_nao_suportada` sem cubo; rollup só com `permite_rollup = sim`; N/D nunca vira zero; grupos somam somente vínculos verificados; consumidores pela união de COD_ID por DIST.
- **Mapa:** MapLibre GL 6 (carregado sob demanda, worker servido como estático) com a ARAT oficial; base de contexto Natural Earth (domínio público), sem serviço de tiles.
- **Gráficos:** Apache ECharts 6 modular (barras, grade, tooltip, aria; renderer SVG), sob demanda.
- **Movimento:** `motion` apenas para molas com física (indicadores, folhas, troca A/B); o resto é CSS com tokens.

Por que sem banco agora: o volume publicado é pequeno (≈ 380 KB de índice, ≈ 360 KB de geometria nacional, facetas por entidade sob demanda, maior arquivo ≈ 730 KB) e somente leitura. CDN estática dá latência baixa, nenhuma credencial exposta e custo zero. PostgreSQL/PostGIS (`database/schema.sql`) continua sendo o caminho quando houver séries históricas ou consultas ad hoc maiores.

## Rotas

| Rota | Conteúdo |
|---|---|
| `/` | Panorama: mapa ARAT por grupo verificado, painel contextual, KPIs com cobertura, grupos, ranking, inventário das 42 entidades, cobertura 2025 |
| `/matriz/` | Matriz DIST × entidade (métrica principal, quantidade, registros, COD_ID distintos), famílias, ordenação, transposição, CSV |
| `/comparar/` | Empresa × empresa, grupo × grupo, empresa × grupo; Δ e Δ% (N/D se B = 0), cobertura por lado, CSV, link |
| `/explorar/` | Entidade + escopo + facetas DDA em cascata (cubos conjuntos), descrições do DDA M10 e rótulos do Manual Rev. 5 |
| `/metodologia/` | Fonte, cobertura das 114 distribuidoras, regras, homologação por métrica, alertas, grupos com fontes, licença |
| `/previsoes/` | Roteiro “em planejamento” (sem resultados) |
| `/design/` | Vitrine do sistema de componentes (fora da navegação) |

Estado compartilhável na URL (`?dist=`, `?grupo=`, `?a=`/`?b=`, `?ent=`, `?a1=`/`?c1=`/`?a2=`, `?metrica=`), sem identificadores individuais.

## Comandos

```bash
npm ci
npm run dev          # http://localhost:3210
npm run lint && npm run typecheck && npm test
npm run build        # gera out/ (estático)
npx playwright test  # E2E contra out/ servido em :3211 (desktop + celular)
node scripts/shots.mjs http://localhost:3210 docs/screenshots   # capturas claro/escuro, desktop/celular
```

Deploy: qualquer CDN estática. Na Vercel, projeto estático (framework "Other") com *Root Directory* `nucleo-dados-bdgd/web`, build `npm run build` e saída `out` (ver `vercel.json`).
