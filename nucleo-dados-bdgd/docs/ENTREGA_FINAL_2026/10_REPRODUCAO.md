# 10 — Reprodução

Todos os caminhos são relativos a `nucleo-dados-bdgd/`.

## Sem a base local (qualquer máquina, Linux inclusive)

```bash
# Motor V2: suítes sintéticas (mesmo comando do workflow motor-v2-sintetico.yml)
python -m motor_v2.tests.suites
# Motor público de cenários (scikit-learn 1.8.0 de motor_universal/requirements-ml.txt)
python -m unittest discover -s motor_cenarios -p 'test_*.py'
python motor_cenarios/cenarios.py output-historico/contrato-integracao motor_cenarios/entrada motor_cenarios/entrada motor_cenarios/saida web/public/data/previsoes/cenarios-motor.json --check
python -m unittest discover -s motor_v2/tests -p test_metric_contract.py
python -m unittest discover -s motor_v2/tests -p test_public_audit.py
# Web
cd web
npm ci
npm run lint && npm run typecheck && npm test
npm run build                                            # produção: portão fechado (sem Motor V2)
NEXT_PUBLIC_MOTOR_V2=homologacao npm run build           # homologação: Motor V2 visível
npx playwright test                                      # E2E sobre out/ (servido em 3211)
# Matriz completa a partir do produto versionado
python ../docs/ENTREGA_FINAL_2026/gerar_matriz.py
```

## Com a base local (`D:\NUCLEO_BDGD_2025`)

```bash
PY=D:/NUCLEO_BDGD_2025/motor_v2/.venv/Scripts/python.exe     # Python 3.12.2, scikit-learn 1.9.1
$PY -m motor_v2.nacional.testes                                # 256 testes (163 sintéticos, 93 locais)
$PY -m motor_v2.tests.emular_ci                                # sintéticos com D:\ bloqueado
$PY -m motor_v2.nacional.reguladores                           # convenção de potência dos reguladores (~1 min)
$PY -m motor_v2.nacional.potencia_b                            # TUC 570 e reguladores no nível B (~4 min)
$PY -m motor_v2.nacional.cobertura --verificar-na              # matriz definitiva; confere NA nos Parquets
$PY -m motor_v2.nacional.exportar_web --saida web/data-motor-v2
$PY -m motor_v2.nacional.consolidar --repo-copy motor_v2/reports/nacional
```

O gerador público (`motor_cenarios/cenarios.py`) deve rodar com scikit-learn 1.8.0 (`D:/NUCLEO_BDGD_2025/.venv-motor`). Com a 1.9.1, o HistGradientBoosting diverge do produto publicado.

No Windows, o `serve` que o Playwright sobe pode cair com `EMFILE: too many open files` no meio da bateria. Isso aconteceu nesta entrega, depois de 129 testes. Use o servidor mínimo do repositório e aponte o Playwright para ele:

```bash
node scripts/servir-estatico.mjs out 3231
PW_BASE_URL=http://127.0.0.1:3231 npx playwright test
```

No Windows com `core.autocrlf=true`, os dados de `web/public`, `output-historico` e `output-publicavel` precisam estar com LF (bytes do blob) para que os validadores de checksum passem. Para isso, faça de novo o checkout desses arquivos com `git -c core.autocrlf=false checkout`.

## O que não é reproduzido

A extração nacional das publicações (cerca de 2,8 h), os aproximadamente 20 mil candidatos de ML e o treinamento nacional rodaram uma vez e **não foram repetidos** nesta entrega. Desta vez rodaram só:
- a classificação dos reguladores;
- as séries de potência no nível B;
- a matriz de cobertura;
- o exportador;
- a regeneração do produto público com o `--check`.
