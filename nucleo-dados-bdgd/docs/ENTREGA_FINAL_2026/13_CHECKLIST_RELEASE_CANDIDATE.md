# 13 — Checklist do release candidate 1.0

Branch `rc/1.0-20261101`, partindo de `81263e0`. Código testado: `ae3ef26`; os commits seguintes só alteram documentação e o log de resultados, e têm o CI registrado no relatório final.

| # | Critério | Estado | Evidência |
|---|---|---|---|
| 1 | Todas as previsões extremas auditadas | **Atendido** | 2.707 de 2.707 séries (`12_MATRIZ_PLAUSIBILIDADE.csv`); 420 alertas; classes e causas em `11_*` |
| 2 | Nenhum cenário bloqueado exposto como previsão válida | **Atendido** | o contrato rejeita cenário bloqueado com valor (`validarDist`); testes de produto, de CSV e de grupo; torres, seccionalizadores e transformadores de medida sem extremos sem evidência |
| 3 | Totais refletem as séries elegíveis | **Atendido** | os três cenários somam o mesmo conjunto de séries; Moderado de todas à parte; todos `PARCIAL`; cobertura 2.484 séries com 15 valores |
| 4 | Reconciliação física e hashes | **Atendido** | auditoria local 275 de 275; Consumidores ≥ UCBT em toda célula; bloqueio coerente entre os dois; `VERIFICACOES_INTEGRIDADE` ok |
| 5 | IDs duplicados (React) | **Corrigido** | `Suspense` raiz removido; `e2e/hidratacao.spec.ts` 15 de 15; ver `06_*` |
| 6 | Correções finais do Codex conciliadas | **Atendido** | branch dele em `de225f5`; o trabalho não publicado no worktree dele (Matriz, dois specs, três documentos) está integrado; nada novo desde 31/10 |
| 7 | Nenhum P0 ou P1 aberto | **Atendido** | nenhum conhecido; o único defeito aberto da interface era o P2, corrigido |
| 8 | CI completo no commit final | **Atendido no commit de código**; ver o relatório para o commit final de documentação | [web `ae3ef26`](https://github.com/artelias/BDGD/actions/runs/41445552427) success; [sintético `ae3ef26`](https://github.com/artelias/BDGD/actions/runs/41445552399) success |
| 9 | Preview de homologação validada | **Parcial** | o preview (`dpl_DCb7qChp4qUtA7iQaZ3vRmVBvF53`) está READY e implanta o commit testado `ae3ef26`; o log de build registra "MOTOR V2: build de homologação". O conteúdo **não foi inspecionado**: o preview é protegido por SSO e a ferramenta do Vercel não alcança o deployment |
| 10 | Pacote de documentação coerente | **Atendido** | documentos 01 a 13 atualizados; contagens antigas marcadas como superadas |
| 11 | PRs em Draft ou preparados | **Preparados** | não há integração GitHub autorizada nesta sessão; corpos e links no relatório final |
| 12 | Nenhuma publicação experimental sem autorização | **Atendido** | produção na Vercel continua no deploy de 28/10 (`74190e2`); builds de produção do CI reprovam se expuserem o Motor V2 |

## Testes

| Bateria | Resultado |
|---|---|
| Motor V2, auditoria local | 275 de 275 |
| Emulação do CI sem `D:` | 179 OK, 1 skip herdado |
| ESLint, TypeScript | 0, 0 |
| Vitest | 182 de 182 |
| Playwright completo, local | **339 de 339** |
| Playwright completo, CI Linux | success |
| Gerador público (`cenarios.py --check`), contrato físico, auditoria pública | OK no CI |

## Defeitos conhecidos que não impedem o release

- Geradores: o total nacional Agressivo é um composto de extremos individuais (ver `11_*` e `09_*`).
- Limiares do portão são percentis empíricos de 4 anos; `TOL_MODELO` e `BASE_MINIMA` são parâmetros do portão.
- Safari em aparelho físico não foi testado.

## Estado

**RELEASE_CANDIDATE_1_0_APROVADO**, com duas ressalvas explícitas: o conteúdo do preview não foi inspecionado e o total nacional Agressivo de geradores está sinalizado para decisão humana. Zero modelos cientificamente homologados; isto não é homologação científica.

## Correções finais de release (03/11/2026)

| Defeito | Estado | Evidência |
|---|---|---|
| Cenários incompletos sem explicação coerente | **Corrigido** | completude única nos dois produtos; 8 extremos sem Moderado removidos do produto público; `14_*` |
| Contagens com decimais | **Corrigido** | JSON do Motor V2 em inteiros; eixo e formatadores; testes Python, Vitest e E2E |
| Informação técnica na lateral | **Corrigido** | `e2e/release-correcoes.spec.ts` |
| Mapa com tema misturado | **Corrigido** | `e2e/mapa-tema.spec.ts` |
| Agregado nacional dos extremos apresentado como cenário (NC-ENG-01) | **Corrigido** | `agregado_extremos`; o documento 11 tinha uma afirmação sem lastro, agora corrigida |

O aceite formal de engenharia está em `HOMOLOGACAO/ENGENHARIA/` e **não está assinado**. A homologação científica é um processo separado.
