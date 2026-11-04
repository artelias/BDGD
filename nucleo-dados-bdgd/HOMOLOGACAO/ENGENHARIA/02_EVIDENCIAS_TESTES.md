# 02 — Evidências de testes (engenharia)

**Objeto:** `rc/1.0-20261101`, SHA `e4bc55cadee8b0bb025f46475852262d26cfd423 (código testado; o commit seguinte só preenche este dossiê)`. As execuções locais foram feitas em 03/11/2026, em Windows 10, Node 22 e Python 3.12.2 (Motor V2, scikit-learn 1.9.1) / 3.14 (gerador público, scikit-learn 1.8.0). O CI roda em GitHub Actions (ubuntu-latest). Cada linha traz o comando para repetir a execução.

## Python

| Bateria | Comando | Resultado |
|---|---|---|
| Motor V2, auditoria completa (sintéticos + locais com `D:` + públicos) | `python -m motor_v2.nacional.testes` | **281 de 281** OK (179 sintéticos, 93 locais, 9 públicos) |
| Emulação do Actions com `D:` bloqueado | `python -m motor_v2.tests.emular_ci` | 179 OK, 1 skip herdado (precisa da base local) |
| Produto web do Motor V2 | `python -m unittest motor_v2.tests.test_produto_web_v2` | 6 OK |
| Gerador público de cenários | `python -m unittest discover -s motor_cenarios -p "test_*.py"` | 25 OK |
| Regeneração idêntica do produto público | `python motor_cenarios/cenarios.py output-historico/contrato-integracao motor_cenarios/entrada motor_cenarios/entrada motor_cenarios/saida web/public/data/previsoes/cenarios-motor.json --check` | **OK**: 29 métricas, 16.010 contagens, 2 na folga de 1 unidade (limite 80) |

## Front-end

| Bateria | Comando (em `web/`) | Resultado |
|---|---|---|
| ESLint | `npm run lint` | 0 problemas |
| TypeScript | `npm run typecheck` | 0 erros |
| Vitest | `npm test` | **196 de 196** (22 arquivos) |
| Build de homologação | `NEXT_PUBLIC_MOTOR_V2=homologacao npm run build` | OK ("MOTOR V2: build de homologação") |
| Playwright completo, local (desktop, Android, iPhone estreito emulado) | `node scripts/servir-estatico.mjs out 3231` + `PW_BASE_URL=http://127.0.0.1:3231 npx playwright test` | **347 de 351**. As 4 falhas (`natureza-fisica.spec.ts`) eram o teste lendo a coluna do CSV pela posição antiga; corrigido para localizar pelo cabeçalho, sem afrouxar a exigência de inteiros |
| Playwright, specs afetados na build final | `npx playwright test e2e/natureza-fisica.spec.ts e2e/release-correcoes.spec.ts e2e/motor-v2.spec.ts e2e/cenarios-motor.spec.ts e2e/mapa-tema.spec.ts` | **33 de 33** |
| Playwright, specs de cenários depois do ajuste final de texto (viés físico relativo) | `npx playwright test e2e/cenarios-motor.spec.ts e2e/natureza-fisica.spec.ts e2e/release-correcoes.spec.ts` | **21 de 21** |

## CI Linux no SHA final

| Workflow | Run | Resultado |
|---|---|---|
| Núcleo de Dados BDGD — web 2025 (lint, tipos, Vitest, gerador `--check`, contrato físico, validadores ETL, build de produção com portão fechado, build de homologação, Playwright completo) | [41747836815](https://github.com/artelias/BDGD/actions/runs/41747836815) | **success** |
| Motor V2 — testes sintéticos | [41747837003](https://github.com/artelias/BDGD/actions/runs/41747837003) | **success** |

## Evidência visual

As capturas da build final ficam no relatório da sessão, e o revisor pode reproduzi-las com o Playwright:
- Previsões com previsão parcial explícita;
- agregado nacional de geradores com alerta;
- mapa coerente depois de 9 alternâncias de tema.

## O que não foi testado

- conteúdo do preview Vercel (SSO);
- Safari em aparelho físico;
- os 93 testes locais no CI (dependem da base em `D:`).
