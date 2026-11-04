# Integração temporária e reprodução

| Origem | Head inspecionado | Conteúdo relevante |
|---|---|---|
| [PR 17](https://github.com/artelias/BDGD/pull/17) | `f0ad962` | Contratos públicos e motor de cenários V1 |
| [PR 18](https://github.com/artelias/BDGD/pull/18) | `74190e2` | Metodologia por distribuidora |
| [PR 19](https://github.com/artelias/BDGD/pull/19) | `09cd749` | Natureza física, contagens inteiras e auditoria de produtos |
| [PR 20](https://github.com/artelias/BDGD/pull/20) | `10be0e0` | Tema, persistência e tolerância a storage bloqueado |

Os três últimos PRs partem do PR 17. A branch `codex/qa-frontend-homologacao-20261031` reúne os commits dos quatro até `5543735`, sem conflitos nessa composição. Os testes de regressão e as correções da interface vieram em `f92dad9` e `de225f5`. O checkout de QA está em `D:\NUCLEO_BDGD_2025\wt-qa-frontend`.

## Composição com a branch do Motor V2

A composição direta de QA com `badfd2498ea59ff4a842fb1359abcb2ddf47da5d` revelou conflitos em oito arquivos de `nucleo-dados-bdgd`.

- `motor_cenarios/cenarios.py` e `motor_cenarios/test_publico.py`
- `motor_cenarios/saida/CENARIOS_CONSERVADOR_MODERADO_AGRESSIVO.csv`, `MANIFESTO.json`, `MATRIZ_MODELO_POR_METRICA.csv` e `TABELA_FINAL_METRICA_DISTRIBUIDORA.csv`
- `motor_v2/tests/test_metric_contract.py`
- `web/public/data/previsoes/cenarios-motor.json`

Para testar uma resolução concreta, a árvore temporária mantém `web` e `motor_cenarios` integralmente iguais aos do QA `de225f5`, e `motor_v2` integralmente igual à branch publicada `badfd24`. Isso preserva a relação entre gerador, manifesto e produto público e inclui os testes adicionais de contrato físico do V2. `git diff --exit-code` confirmou as três identidades. O checkout separado está em `D:\NUCLEO_BDGD_2025\wt-qa-integracao-v2-20261031`, detached HEAD `254446b`, árvore `32f5844b7f916cb4d53ba7cad5dd2156b5ef4b01`. É uma proposta de resolução local. A escolha do gerador público para uma integração oficial cabe aos responsáveis pelos dois PRs.

## Reprodução dos testes web

Na pasta `nucleo-dados-bdgd/web`, usar o Node e as dependências do lockfile. Nesta máquina foi reaproveitada uma cópia local das dependências já disponíveis. A exportação estática deve ser servida em loopback. A variável `PW_BASE_URL` informa o servidor ao Playwright.

```powershell
node node_modules/typescript/bin/tsc --noEmit
node node_modules/eslint/bin/eslint.js .
node node_modules/vitest/vitest.mjs run --maxWorkers=1
node scripts/copy-maplibre-worker.mjs
node node_modules/next/dist/bin/next build
node scripts/flatten-segment-prefetch.mjs out
# Em outro terminal, servir a pasta out com o serve instalado no ambiente.
$env:PW_BASE_URL = 'http://127.0.0.1:3231'
$env:QA_RESULTADOS = 'D:\NUCLEO_BDGD_2025\qa-evidence-20261031\nova-execucao.jsonl'
node node_modules/@playwright/test/cli.js test '--reporter=list,./scripts/qa-reporter.ts'
python ../docs/qa-frontend-20261031/gerar_matriz.py $env:QA_RESULTADOS
```

Usar um nome de JSONL diferente para cada execução. O reporter acrescenta cada resultado concluído ao arquivo. Screenshots e traces de falhas permanecem no diretório de resultados. O projeto `iphone-estreito` emula viewport, toque e agente de usuário no Chromium. Uma validação de Safari físico exigiria aparelho e navegador correspondentes.
