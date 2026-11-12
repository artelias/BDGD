# Testes e desempenho

## Testes do módulo

| Camada | Arquivo | Testes | O que cobre |
|---|---|---:|---|
| Python | `confiabilidade/tests/test_confiabilidade.py` | 22 | fórmulas PRODIST, métricas, zero × N/D, supressão, reconstrução, validação do produto, auditoria do produto real, contrato do `fatores.json`, idempotência (EPB 2025 → INALTERADO), geometria, estatística sintética e vereditos |
| Vitest | `web/tests/confiabilidade.test.ts` | 20 | soma mensal, acumulado, ponderação por NumCon, situação × limite, quantis e cores por tema, modo regulatório, comparação (N/D preservado, % sem relativa), frases sem causalidade, pares, ranking, perfil, URL A/B, produto real (EPB 74.625 transformadores, chaves únicas, geometria por distribuidora) |
| Playwright | `web/e2e/confiabilidade.spec.ts` | 9 desktop + 1 `@mobile` | Brasil → EPB; DEC/FEC, ano, mês, % do limite; ficha (componentes internas × externas); comparador + CSV; benchmarking; fatores e metodologia; mapa (hover, clique, zoom, volta ao Brasil) com Energisa AC; tema claro/escuro; celular sem rolagem horizontal; sem erro de console |
| Auditoria | `python -m confiabilidade.auditoria` | A1–A6 | manifesto, chaves, contrato, totais × portal, reconciliação, geometria |

Comandos em OPERACAO.md. Nenhum teste existente foi desativado ou alterado.

## Execução no Windows: servidor estático

`npm run e2e` sem `PW_BASE_URL` sobe `npx serve@14.2.4 out -l 3211`. Em 12/11/2026 esse servidor caiu no meio da suíte com
`EMFILE: too many open files` (Windows), e os 233 testes seguintes falharam com `ECONNREFUSED` (128 passaram antes da
queda). Não eram falhas da aplicação. A suíte foi repetida com o servidor do próprio projeto, feito para isso
(`node scripts/servir-estatico.mjs out 3232` + `PW_BASE_URL=http://127.0.0.1:3232 npx playwright test`). Resultado na
seção de evidências do RELATORIO_FINAL.md.

## Desempenho

### Tamanho do produto (`web/public/data/confiabilidade`, 204 arquivos, 50,8 MB no disco)

| Arquivo | Bruto | gzip |
|---|---:|---:|
| `indice.json` | 132 kB | 16 kB |
| `nacional/2025.json` (um por ano) | 1.028 kB | 479 kB |
| `fatores.json` | 480 kB | 183 kB |
| `distribuidoras/6600.json` (EPB) + `geo/6600.json` | 724 + 202 kB | 142 + 58 kB |
| `distribuidoras/26.json` (EAC) + `geo/26.json` | 175 + 157 kB | 34 + 45 kB |
| `distribuidoras/4950.json` + `geo/4950.json` (maior) | 3.110 + 1.473 kB | 596 + 433 kB |
| mediana das 99 distribuidoras (dados / geo) | 15 / 11 kB | 4 / 4 kB |

O carregamento é **por distribuidora**: nada de outra empresa é baixado ao selecionar uma. O nacional só é baixado no
comparador, no benchmarking e na escala "Conjuntos do Brasil" (desde `8626c60`, não mais ao abrir a página nem no recorte
mensal). `fetch` com `force-cache` e cache de módulo: trocar de aba ou voltar a uma distribuidora não baixa de novo.

### Tempo até a tela pronta (`node scripts/medir-confiabilidade.mjs`, build estático, cache frio)

Servidor local **sem compressão** (pior caso: a hospedagem serve JSON e JS com gzip, 3–5× menos bytes). "Celular" =
390 × 844, rede 4G emulada (9 Mbit/s, 60 ms) e CPU 4× mais lenta. Pronto = mapa com todos os polígonos coloridos,
ficha visível, tabela de pares preenchida etc.

| Tela | Desktop | Celular 4G + CPU 4× | Dados do módulo (bruto) |
|---|---:|---:|---:|
| Brasil | 1,2 s | 3,4 s | 132 kB |
| EPB 6600 (75 conjuntos) | 2,3 s | 10,0 s | 2.086 kB |
| Energisa AC 26 (15 conjuntos) | 2,2 s | 9,1 s | 1.493 kB |
| Maior distribuidora (4950) | 2,5 s | 13,3 s | 5.744 kB |
| Ficha EPB (Mataraca) | 1,4 s | 8,9 s | 2.086 kB |
| Benchmarking EPB | 0,9 s | 6,6 s | 2.181 kB |
| Fatores | 0,7 s | 4,8 s | 612 kB |

Leitura: no desktop tudo fica pronto em até 2,5 s. No celular o tempo é dominado pelos bytes sem compressão. Com gzip, os
dados da EPB caem de 2.086 para ~695 kB, e o nacional (479 kB com gzip) passa a ser o maior item na escala padrão.

### Recomendação (não aplicada: exige republicar o produto)

Publicar no `indice.json` as quebras nacionais por ano e indicador (5 números × 2 × 4 anos) e usar o nacional só no
comparador e no benchmarking. A escala "Conjuntos do Brasil" deixaria de baixar ~1 MB (479 kB com gzip) por distribuidora
aberta. Fica para a próxima publicação controlada, junto com uma regeneração justificada do produto; não foi feita agora
porque a regra da retomada proíbe reprocessar dados para resolver problema só de frontend.
