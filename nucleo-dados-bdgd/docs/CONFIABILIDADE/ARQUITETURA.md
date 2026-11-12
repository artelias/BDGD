# Arquitetura

```
 ANEEL dados abertos (ODbL)                 BDGD 2022–2025 (Parquets do Núcleo, somente leitura)
 indicadores-continuidade-coletivos          379 cargas DIST × ano já convertidas
          │                                              │
  confiabilidade/aneel.py                       confiabilidade/infra.py      confiabilidade/geo.py
  baixar → preparar                             DIST × ANO × CONJ            camada CONJ 2025
          │                                              │                            │
          ▼                                              ▼                            ▼
 <trabalho>/derivado/                     <trabalho>/derivado/infra/          <trabalho>/derivado/geo/
 continuidade.parquet, limites.parquet    DIST=<d>/ANO=<a>.json               <d>.json
 PROVENIENCIA_ANEEL.json                  (assinatura idempotente)
          └──────────────────────────────┬───────────────────────────────────────┘
                                         ▼
                           confiabilidade/publicar.py  (monta em pasta temporária, valida, troca atômica)
                                         ▼
                 web/public/data/confiabilidade/   (produto público, 204 arquivos, ~50 MB)
                 indice.json · distribuidoras/<d>.json · geo/<d>.json · nacional/<ano>.json
                 fatores.json (estatistica.py) · manifesto.json (SHA-256 + bytes)
                                         ▼
                  confiabilidade/auditoria.py (A1–A6)      web/src → /confiabilidade (Next.js estático)
```

`<trabalho>` = `D:/NUCLEO_BDGD_2025/confiabilidade` (variável `CONF_TRABALHO`). Nada do módulo grava nas bases BDGD
originais, nos Parquets nacionais nem no pacote `web/public/data/2025-12-31` do portal.

## Python (`confiabilidade/`)

| Arquivo | Papel |
|---|---|
| `contrato.py` | estados de dado, fórmulas PRODIST, tolerância da reconstrução, regras zero × N/D (só biblioteca padrão) |
| `aneel.py` | download incremental (CKAN `last_modified`) e normalização; falha se houver valores conflitantes para a mesma chave |
| `infra.py` | infraestrutura por conjunto a partir dos Parquets da BDGD; idempotente por assinatura (código + Parquets lidos) |
| `geo.py` | polígonos oficiais dos conjuntos (BDGD 2025), simplificados para o mapa; área geodésica na geometria original |
| `metricas.py` | dicionário único das métricas (tipo, unidade, sentido) e das razões derivadas |
| `publicar.py` | produto público compacto; completa zeros observados (camada lida sem linhas) e mantém N/D (camada ausente) |
| `auditoria.py` | auditoria do produto publicado (manifesto, chaves, contrato, totais, reconciliação, geometria) |
| `estatistica.py` | estudo observacional de fatores associados → `fatores.json` |
| `tests/` | 22 testes `unittest` (fórmulas, métricas, zero × N/D, reconstrução, produto real, contrato de fatores, idempotência) |

## Produto público (`web/public/data/confiabilidade/`)

| Arquivo | Conteúdo | Carregado quando |
|---|---|---|
| `indice.json` | distribuidoras, anos, agregados anuais, tolerâncias, cobertura | abertura da página |
| `distribuidoras/<d>.json` | conjuntos da distribuidora: blocos anuais oficiais (12 meses, limites, componentes), infraestrutura por ano, alimentadores, reconstrução | ao selecionar a distribuidora |
| `geo/<d>.json` | polígonos simplificados dos conjuntos | ao selecionar a distribuidora |
| `nacional/<ano>.json` | uma linha por conjunto do Brasil (indicadores + métricas) | comparador, benchmarking e escala "Conjuntos do Brasil" |
| `fatores.json` | estudo de fatores associados (DEC e FEC) | aba Fatores |
| `manifesto.json` | SHA-256 e tamanho de cada arquivo | auditoria |

## Frontend (`web/src`)

* `app/confiabilidade/page.tsx` → `components/confiabilidade/Confiabilidade.tsx` (abas: Mapa e conjuntos, Comparar A × B,
  Benchmarking, Fatores associados, Metodologia). Estado inteiro na URL (`lib/confiabilidade/estado.ts`): `dist`, `conj`,
  `ind`, `ano`, `mes`, `cor`, `sit`, `ref`, `grupo`, `aba`, `a`, `b`.
* `MapaConfiabilidade.tsx`: MapLibre com camadas `arat-*` (áreas das distribuidoras, nível Brasil) e `conj-*`
  (conjuntos); cores por `feature-state`; `cooperativeGestures` (a rolagem da página não fica presa no mapa);
  `onPronto` dispara o enquadramento só depois do `load`.
* `lib/confiabilidade/calculo.ts`: regras de exibição testadas (variação, situação, comparação, pares, perfil, ranking,
  frases sem linguagem causal); `escala.ts`: quantis e paletas por tema; `graficos.ts`: opções ECharts.
* `lib/confiabilidade/dados.ts`: `fetch` com cache de módulo e `force-cache`; falha fechada (sem dado real, nenhum número).
