# 02 — Evidências de testes (engenharia)

**Objeto:** branch `rc/1.0-20261101`, SHA de código `1be7a43593bb723c1a1054fbcc1403faf2a5793f`. Ele inclui a integração do PR #21 (`81414e6`) e a adaptação dos testes E2E.

- **Commit definitivo da RC:** é o filho direto de `1be7a43` e só altera documentação (`HOMOLOGACAO/ENGENHARIA/` e `docs/ENTREGA_FINAL_2026/`). Isso se confere com `git diff --stat 1be7a43 rc/1.0-20261101`. O CI do commit definitivo aparece nos checks do PR #22 e no relatório de entrega.
- **Ambiente local:** execuções de 04/11/2026, em Windows 10 e Node 22.
  - Python 3.12.2 com scikit-learn 1.9.1, para o Motor V2.
  - Python com scikit-learn 1.8.0, para o gerador público `motor_cenarios`.
- **CI:** GitHub Actions, em `ubuntu-latest`.

Cada linha traz o comando para repetir a execução.

## Python

| Bateria | Comando | Resultado |
|---|---|---|
| Motor V2, auditoria completa (sintéticos + locais com `D:` + públicos) | `python -m motor_v2.nacional.testes` | **281 de 281** OK (179 sintéticos, 93 locais, 9 públicos) |
| Emulação do Actions com `D:` bloqueado | `python -m motor_v2.tests.emular_ci` | 179 OK, 1 skip herdado (precisa da base local) |
| Gerador público de cenários | `python -m unittest discover -s motor_cenarios -p "test_*.py"` | 25 OK |
| Regeneração idêntica do produto público | `python motor_cenarios/cenarios.py output-historico/contrato-integracao motor_cenarios/entrada motor_cenarios/entrada motor_cenarios/saida web/public/data/previsoes/cenarios-motor.json --check` | **OK**: 29 métricas, 16.010 contagens, 2 na folga de 1 unidade (limite 80). Nenhum modelo foi retreinado nem substituído |

## Front-end

| Bateria | Comando (em `web/`) | Resultado |
|---|---|---|
| ESLint | `npm run lint` | 0 problemas |
| TypeScript | `npm run typecheck` | 0 erros |
| Vitest | `npm test` | **196 de 196** (22 arquivos) |
| Build de homologação | `NEXT_PUBLIC_MOTOR_V2=homologacao npm run build` | OK ("MOTOR V2: build de homologação") |
| Playwright completo, local (desktop, Android, iPhone estreito emulado) | `node scripts/servir-estatico.mjs out 3231` + `PW_BASE_URL=http://127.0.0.1:3231 npx playwright test` | **352 de 352** (41,2 min), sem testes desativados nem pulados |

### Testes E2E adaptados à retirada do painel exploratório (PR #21)

O PR #21 retirou o painel "Explorar cenários 2026–2030". Os oito specs que o usavam passaram a exigir o mesmo comportamento no painel "Cenários de expansão por métrica física". Nenhum teste foi removido ou marcado como `skip`. O detalhe por spec está em `docs/ENTREGA_FINAL_2026/06_TESTES_E_CI.md`. Em resumo:

| Spec | O que passa a exigir no painel principal |
|---|---|
| `auditoria-pr6` | todas as DIST com série, 2030 publicado, CSV igual à tela (com a completude), rótulos do gráfico dentro da caixa, falha 503 com alerta e "Tentar novamente", foco na tabela no celular |
| `motor-universal` | título do painel único; o painel antigo não existe mais |
| `natureza-fisica` | painel retirado; produto preservado, com contagens inteiras |
| `previsoes-integracao` | o painel principal vem antes da ressalva longa (posição medida); celular |
| `publicacoes-previsoes` | DIST 26, alimentadores: 2025 observado = 123; 2030 = Moderado do produto; CSV com as mesmas linhas |
| `qa-final` | iPhone: rede MT da DIST 7019, Agressivo, 9 linhas, download do CSV |
| `reconciliacao` | Coopera (DIST 5370) em consumidores: bloqueada, com a ressalva e as observações (225); sem tabela nem CSV |
| `riscos-cenarios` | nenhuma trajetória ≤ 0 publicada; DIST 39 (reatores) não oferecida; completude visível no celular |
| `cenarios-motor` (asserção da Coopera atualizada) | a Coopera é oferecida em consumidores e fica bloqueada (antes: não era oferecida) |

A lógica do painel retirado (riscos, zeros técnicos) continua coberta no Vitest. O produto `cenarios-exploratorios-2026-2030.json` continua publicado e validado no CI.

## CI Linux no SHA de código `1be7a43`

| Workflow | Run | Resultado |
|---|---|---|
| Núcleo de Dados BDGD — web 2025, push (lint, tipos, Vitest, gerador `--check`, contrato físico, validadores ETL, build de produção com portão fechado, build de homologação, Playwright completo) | [41926075003](https://github.com/artelias/BDGD/actions/runs/41926075003) | **success** |
| Núcleo de Dados BDGD — web 2025, pull request #22 | [41926084739](https://github.com/artelias/BDGD/actions/runs/41926084739) | **success** |
| Motor V2 — testes sintéticos | [41926084772](https://github.com/artelias/BDGD/actions/runs/41926084772) | **success** |
| Núcleo de Dados BDGD — checks 2025 | [41926084724](https://github.com/artelias/BDGD/actions/runs/41926084724) | **success** |
| Patrimônio MCPSE — contratos | [41926084832](https://github.com/artelias/BDGD/actions/runs/41926084832) | **success** |
| Motor Universal BDGD — contratos | [41926085523](https://github.com/artelias/BDGD/actions/runs/41926085523) | **success** |

Os workflows de push filtram por caminho. Por isso, um commit só de documentação não dispara de novo o workflow web de push, e o CI do commit definitivo vem dos workflows do pull request #22, que avaliam o diff inteiro do PR.

## Preview Vercel do SHA `1be7a43`

| Campo | Valor |
|---|---|
| Deployment | `dpl_2PoxnWdtqzufgNkGnwRPiCJEJ82p`, estado READY |
| URL | `https://nucleo-dados-bdgd-p1fhpozoi-arthurhenriqueelias-6367.vercel.app` (protegida por SSO) |
| Build | clone `rc/1.0-20261101` @ `1be7a43`; `prebuild` com "MOTOR V2: build de homologação; produto experimental copiado para public/data/motor-v2."; `next build` com 11 páginas estáticas |
| Conteúdo | **não inspecionado** pela ferramenta (SSO). A inspeção humana segue `05_CHECKLIST_INSPECAO_PREVIEW.md` |

## O que não foi testado

- o conteúdo do preview Vercel (exige login SSO);
- o Safari em aparelho físico;
- os 93 testes locais no CI, porque dependem da base em `D:`.
