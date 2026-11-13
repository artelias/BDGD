# Auditoria final de homologação técnica: módulo de Confiabilidade DEC/FEC

Data: 12/11/2026 · Repositório `artelias/BDGD` · Branch `feat/inteligencia-confiabilidade-dec-fec-20261111`
Commit de referência auditado: **`4ba0710`** (preservado) · Correções desta auditoria: commits seguintes da mesma branch
(SHA final = ponta da branch, conferida com `git ls-remote`; um documento não pode citar o próprio commit). Sem merge e sem deploy. Nenhuma assinatura humana preenchida.

## 1. Recomendação

**APROVADO COM RESSALVAS** (aceite técnico, não regulatório), condicionado a:
1. CI do GitHub verde **no SHA final** da branch (seção 5). Até lá, os testes desta auditoria são locais e **não** valem como CI.
2. Homologação humana do conteúdo regulatório (critério 16 de LIMITACOES_E_ACEITE.md), sem a qual o aceite não é final.

O `4ba0710` sozinho seria **reprovado**: publicava o FEC de 2025 da Elektro (soma de 11 meses) como anual, sem aviso, e o
comparava ao limite anual, aos rankings e às quebras nacionais. O defeito foi corrigido e coberto por testes (seção 3).

## 2. Matriz de homologação

| # | Critério | Evidência verificável | Situação |
|---|---|---|---|
| 1 | DEC/FEC, mensais, NumCon, limites e componentes do produto iguais à fonte ANEEL | `auditoria/homologacao/a1_aneel.py` contra o parquet e o CSV brutos: 0 divergências em 12.502 conjunto-anos (antes e depois das correções; componentes conferidas no DEC; no FEC da Elektro 2025 elas passam a cobrir os mesmos 11 meses do indicador) | atendido |
| 2 | Componentes: apurado = internas | DEC = DECIP + DECIND em 150.163/150.163 conjunto-meses; FEC = FECIP + FECIND em 150.033/150.033. Somar externas falha em 4%; somar expurgos falha em 53–58% | atendido |
| 3 | Expurgos e externas fora do indicador | `publicar.EXPURGOS` = INC, INE, INO, IPC, XNC, XPC (domínio ANEEL: dia crítico, emergência, racionamento/ONS); ficha marca "não compõe" | atendido; **revisão de especialista pendente** |
| 4 | Limites anuais, só contra valor anual completo | limites = CSV bruto em 100%; 17 conjunto-anos sem limite (alerta `sem_limite`); valor parcial não é comparado (corrigido) | atendido após correção |
| 5 | Apuração parcial sinalizada e fora das comparações | **defeito no `4ba0710`** (seção 3). Corrigido: alerta para DEC ou FEC, `nacional` com `meses_*`, `completo_dec/fec`, frontend com `valorComparavel` | atendido após correção |
| 6 | Reconstrução DIC/FIC no mesmo período do oficial | **defeito no `4ba0710`**: somava 12 meses de FIC contra 11 de FEC oficial (Elektro 2025 FEC 35% reconciliado). Corrigido: mesmos meses dos dois lados (100%) | atendido após correção |
| 7 | 83 combinações < 80% investigadas sem invalidar o oficial | 49 de empresas com 1 conjunto; 4 com DIC zerado na BDGD; grandes com deslocamento uniforme (definição/cadastro do DIC declarado). Oficial íntegro (critério 1). `a2_rec_saida.txt` | atendido; critério de 5% segue **experimental** |
| 8 | R² comparado entre modelos equivalentes | mesmas 5 partições por distribuidora nos 4 modelos, sem sobreposição, R² reproduzido exatamente (`R2_PAREADO.json`). A frase "0,43 → 0,53" comparava Ridge com floresta: corrigida; ganho real +0,02 a +0,06, IC inclui zero salvo floresta/DEC | atendido após correção de texto |
| 9 | Vereditos com regra única | H7 dava NAO_SUSTENTADA com ρ = −0,10 e IC largo, contra a regra do H1–H6. Corrigido para INCONCLUSIVA (`veredito_variacao`, testado). H1–H6 conferidos contra os IC publicados | atendido após correção |
| 10 | Linguagem não causal | textos de Fatores, comparador e docs; teste Vitest/e2e de frases | atendido |
| 11 | Pareamento | 20 vizinhos de **outras** distribuidoras, mesmo ano, 5 critérios de contexto em unidades de IQR, alvo exige 3 critérios; parciais agora fora. Ressalva: rede MT/consumidor é "contexto" no pareamento e "infraestrutura" no estudo | atendido com ressalva |
| 12 | Geometria 2025 em anos anteriores sinalizada | antes: só "conjuntos extintos não têm polígono". Agora o mapa de 2022–2024 avisa que desenha os limites de 2025 e que a densidade usa a área de 2025 | atendido após correção |
| 13 | Desempenho no celular | seção 4 | atendido com ressalva |
| 14 | Quebras nacionais no `indice.json` sem mudar valores | Python reproduz exatamente as quebras do frontend (`linhasNacionais` + `quebrasQuantis`) nos 4 anos × DEC/FEC; 267 bytes. **Viável, não aplicado** (não é defeito; muda o carregamento do mapa) | viável, pendente de decisão |
| 15 | Testes locais | seção 5 | ver seção 5 |
| 16 | CI no SHA exato | **nenhuma execução do GitHub Actions** em `4ba0710`: a branch não está nos gatilhos de push e não há `workflow_dispatch`. Só o preview da Vercel (build Linux) passou | **pendente (bloqueia o aceite final)** |
| 17 | RC, produção, Motor de Expansão, bases BDGD e dados originais intocados | `git diff 4ba0710..HEAD --stat` só em `confiabilidade/`, `web/` do módulo e `docs/CONFIABILIDADE`; brutos ANEEL só lidos | atendido |
| 18 | Revisão de especialista de regulação | homologação humana com CHECKLIST_REGULATORIO.md | **pendente** |

## 3. Defeitos comprovados e corrigidos

| Defeito | Prova | Correção | Regressão |
|---|---|---|---|
| FEC jun/2025 da Elektro ausente na ANEEL → FEC anual de 11 meses sem alerta, comparado ao limite, nas quebras, rankings, pares; `acima_fec` = 2 | `SELECT … WHERE ndec<>nfec` no parquet bruto: só ELEKTRO 2025 mês 6 (130 × 0) | `publicar.py`: alerta DEC **ou** FEC; `acima_*` só com 12 meses; `completo_dec/fec`; `meses_*` no nacional. Frontend: `anualCompleto`, `valorComparavel`, `completoDist` (ficha, mapa, lista, comparador, benchmarking) | Python `test_apuracao_parcial_sinalizada_e_fora_do_limite`; Vitest "apuração parcial" (3) e "Elektro 2025"; e2e "apuração parcial: FEC 2025 da Elektro" |
| Reconstrução comparava 12 meses de FIC com 11 de FEC | Elektro 2025 FEC: mediana reconstruído/oficial 1,063 | `reconstrucao()` usa os meses com oficial, dos dois lados; grava `meses_dec/fec` | Python `test_mes_sem_oficial_fica_fora_dos_dois_lados` |
| Componentes somadas em 12 meses e FEC em 11: parcelas internas da Elektro 2025 somavam 104% na ficha; gráfico anual e "contra o ano anterior" tratavam o FEC parcial como comparável | captura da ficha (conjunto 13449): 0,14 + 2,14 = 2,28 ≠ 2,19 | `continuidade_ano()` soma componentes só nos meses com indicador; ficha sem limite para ano parcial e com o motivo certo | Python `test_componentes_internas_somam_o_indicador_no_mesmo_periodo` (todos os conjunto-anos) |
| H7 "não sustentada" contra a regra declarada | ρ = −0,076 (DEC) e −0,104 (FEC) com IC contendo zero | `veredito_variacao` com a regra do H1–H6 | Python `test_veredito_h7_usa_a_mesma_regra` |
| Relatório/limitações: ganho "0,43 → 0,53" entre modelos diferentes; nota da tela atribuía R² baixo a "diferenças entre distribuidoras" | `R2_PAREADO.json` | textos corrigidos (docs e `Fatores.tsx`) | — (texto) |
| Mapa de anos anteriores sem aviso de geometria/área de 2025 | `publicar.py` usa `area_km2` do polígono de 2025 para todos os anos | aviso no mapa quando ano < 2025 | e2e "ano anterior a 2025 avisa…" |
| Contagem da identidade citava 150.033 para DEC | DEC tem 150.163 conjunto-meses | Metodologia e docs | — |

Republicação controlada (`publicar` 27 s + `estatistica` ~6 min; nenhuma das 379 cargas BDGD reexecutada). Comparação
campo a campo com `4ba0710` (`a4_diff.py`): **nenhum** DEC, FEC, limite, valor mensal, NumCon ou métrica de
infraestrutura mudou; mudaram só `alertas` (130), `acima_dec` (1) e `acima_fec` (1), `completo_*`, `meses_*`, a componente
FEC interna não programada dos 130 conjuntos da Elektro 2025 (junho retirado; ex.: 2,14 → 2,05) e a reconstrução de 135
conjunto-anos (validados 11.237 → 11.325). No `fatores.json` só mudou o H7.

## 4. Desempenho no celular

Medido de novo com o servidor comprimindo em gzip, como a hospedagem (`auditoria/homologacao/servir-gzip.mjs` +
`scripts/medir-confiabilidade.mjs`; resultado em `medicao_celular_gzip.json`). Celular = 390 × 844, 4G emulado (9 Mbit/s,
60 ms), CPU 4× mais lenta, cache frio.

| Tela | Celular, sem gzip (relatório anterior) | Celular, com gzip | Dados do módulo com gzip |
|---|---:|---:|---:|
| Brasil | 3,4 s | 2,6 s | 16 kB |
| EPB 6600 | 10,0 s | 7,1 s | 686 kB |
| Energisa AC 26 | 9,1 s | 6,6 s | 568 kB |
| Maior distribuidora (4950) | 13,3 s | 7,9 s | 1.474 kB |
| Ficha EPB | 8,9 s | 6,3 s | 686 kB |
| Benchmarking EPB | 6,6 s | 4,8 s | 965 kB |
| Fatores | 4,8 s | 3,8 s | 197 kB |

O nacional do ano (476 kB com gzip) é 69–84% dos dados de uma distribuidora na escala padrão "Conjuntos do Brasil"
(EPB: 476 de 686 kB; Energisa AC: 476 de 568 kB). Ele só é usado ali para as quebras da escala. **Verificação de
viabilidade (item 14)**: as quebras calculadas em Python a partir de `nacional/{ano}.json` (só valores com 12 meses) são
idênticas às do frontend (`linhasNacionais` + `quebrasQuantis`, executados no Node 24) nos 4 anos × DEC/FEC, ocupam 267 bytes
e não mudam valores nem metodologia (`auditoria/homologacao/quebras.mjs`). Publicá-las no `indice.json` tiraria ~476 kB
dessas telas; o tempo ganho não foi medido. Não aplicado: não é defeito e muda o carregamento do mapa, então fica para
decisão (republicação controlada já está provada barata: `publicar` 27 s).

## 5. Testes e CI

Execuções locais no Windows sobre a árvore final (build `NEXT_PUBLIC_MOTOR_V2=homologacao`, como a CI). **Não são CI.**

| Verificação | Resultado |
|---|---|
| `npm run typecheck`, `npm run lint` | saída 0 |
| Vitest (suíte inteira) | 23 arquivos, **220/220** (216 + 4 de regressão) |
| Python `unittest` (`-X utf8`) | **26/26** (22 + 4 de regressão) |
| Playwright do módulo (build de homologação) | **12/12** (10 + 2 de regressão) |
| Auditoria do produto A1–A6 | `falhas: []` |
| Build de homologação | saída 0 |

* Suíte e2e inteira não foi repetida: só arquivos do módulo mudaram, e nenhum outro módulo importa `lib/` ou
  `components/confiabilidade` (verificado com `grep`). Último resultado completo: 361/361 em `4ba0710`.
* Sem `-X utf8`, o teste da auditoria quebra no console cp1252 do Windows (`UnicodeEncodeError` ao imprimir "−"); é do
  ambiente, não do código.

**Cobertura da CI.** O workflow `nucleo-bdgd-web.yml` roda lint, tipos, Vitest (`tests/**`, inclui `confiabilidade.test.ts`), os
dois builds e a suíte Playwright inteira (inclui `confiabilidade.spec.ts`, desktop e `@mobile`). Nenhum workflow rodava
`confiabilidade/tests`; o workflow novo e isolado `confiabilidade.yml` roda os testes Python (os que exigem a BDGD local
se declaram pulados) e regenera a auditoria A1–A6 a partir dos arquivos versionados, exigindo `falhas: []` e igualdade
com a evidência versionada. Resultados da CI: no PR.

**CI no SHA exato.** `GET /repos/artelias/BDGD/actions/runs?head_sha=4ba07100…` → `total_count: 0`. Os gatilhos de push de
`nucleo-bdgd-web.yml`, `nucleo-dados-bdgd.yml` e `patrimonio.yml` não incluem `feat/inteligencia-*` e nenhum workflow tem
`workflow_dispatch`; o único check no SHA é o preview da Vercel (build Linux, sucesso), que não substitui a CI. Alterar
os workflows para forçar a execução mudaria a CI compartilhada, por isso não foi feito. **Solicitação:** abrir um PR em
rascunho `feat/inteligencia-confiabilidade-dec-fec-20261111` → `rc/1.0-20261101`; isso dispara `nucleo-bdgd-web`,
`nucleo-dados-bdgd` e `patrimonio`. Os workflows de PR testam o commit de merge, mas como a ponta da RC (`dba5fdf`) é
ancestral da branch, a árvore testada é a mesma do SHA final enquanto a RC não andar. Conferir no PR que o `head_sha` dos
checks é o da ponta da branch.

## 6. Ressalvas que não bloqueiam

* Critério de reconciliação de 5% é experimental; grandes empresas com deslocamento uniforme de 4–13% ficam abaixo.
* Ganho preditivo da infraestrutura pequeno e incerto; o estudo é observacional, sem correção para 8 comparações.
* Densidade de 2022–2024 com área de 2025; pareamento e estudo usam definições de contexto diferentes.
* A proveniência ANEEL gravada (anterior a 12/11/2026) ainda registra a identidade antiga até a próxima `aneel preparar`.
