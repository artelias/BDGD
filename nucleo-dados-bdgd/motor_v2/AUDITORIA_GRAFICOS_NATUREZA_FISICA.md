# Auditoria do dashboard — contagens fracionárias (29/10/2026)

Escopo: o dashboard **existente neste checkout** (`web/`, que inclui o PR #17 e anteriores). O Motor V2 **não** está publicado nem é consumido por nenhuma página: nenhuma tela lê saídas de `motor_v2/`. Nada foi publicado em produção nesta etapa; as correções ficam na branch.

## 1. O que o usuário viu (confirmado)

| Produto público | Contagens projetadas | Fracionárias **antes** | **Depois** |
|---|---:|---:|---:|
| `cenarios-motor.json` (página Previsões, explorador de cenários) | 16.045 | **11.394 (71%)** | 0 |
| `motor-universal-resumo.json.gz` (Previsões, motor universal) | 21.490 | **10.986 (51%)** | 0 |
| `cenarios-exploratorios-2026-2030.json` (Previsões, cenários exploratórios) | 7.550 | **4.638 (61%)** | 0 |

Locais de exibição que mostravam ou exportavam a fração (arquivo, comportamento anterior):

1. `CenariosMotor.tsx`: **tooltip do gráfico** com `maximumFractionDigits: 1` (ex.: "92.010,8 transformadores"); a tabela já arredondava na tela (0 casas), mas o **CSV exportado** e o JSON de origem continham `92010.762`.
2. `MotorUniversal.tsx`: `number()` com até 2 casas para qualquer métrica ("Simulação condicional para 2030: 649,5 transformadores"), tabela anual idem; a exportação JSON levava os decimais do modelo.
3. `PrevisoesExploratorias.tsx`: a tela formatava `itens` com 0 casas, mas o **CSV** exportava o valor bruto da tendência linear (ex.: `98271.158`) e o JSON de origem era fracionário.
4. `motor_cenarios/saida/*.csv` e `TABELA_FINAL_*`: trajetórias com 3 casas para contagens (`127.577` alimentadores).

Páginas **não** afetadas: Panorama, Matriz, Explorar, Comparar, Evolução (mostram estoques observados, inteiros por construção; as razões e percentuais já são decimais por natureza).

## 2. Correção

Contrato único de natureza física (`motor_v2/metric_contract.py`, espelhado em `web/src/lib/natureza-fisica.ts` e em `88_cenarios_exploratorios.mjs`): contagem = inteiro não negativo com arredondamento **meio para cima** declarado; extensão, potência, energia e razões mantêm decimais; unidade não classificada é erro.

- **Na origem:** `motor_cenarios/cenarios.py` e `88_cenarios_exploratorios.mjs` publicam inteiros para contagens; o resumo do motor universal foi convertido (`motor_universal/__main__.py::fisico` e o arquivo versionado). O valor bruto fica **só** em `INTERNAL_RAW_PREDICTIONS.csv`, fora do repositório (`--internal-dir`), e a métrica de erro física (`mae_fisico`, `wape_fisico`, `vies_fisico`) é publicada **ao lado** do erro contínuo (modelos com previsão negativa recebem `fisico_motivo`, sem erro físico forçado). A seleção de cenários continua usando o erro contínuo.
- **Na borda (web):** `parseCenarios` e `parseResumoMotor` **recusam** o produto se houver contagem fracionária (não arredondam em silêncio); tooltip, tabelas e CSV usam `formatarFisico`/`valorPublico`; o CSV de cenários e o de exploratórios só gravam inteiros para contagens.
- **Barreiras de teste:** `natureza-fisica.test.ts` varre os três produtos reais; `motor_cenarios/test_publico.py` verifica JSON e CSV; `auditoria_pr6.py` (conferência independente) recalcula a tendência e exige o inteiro pelo mesmo contrato.

## 3. Pendências desta auditoria
- `--check-web` do motor universal e o workflow de CI dependem do manifesto do contrato nacional corrigido (PR #17); neste checkout o hash do manifesto diverge (2 testes de `motor_universal` falham **antes e depois** desta mudança). O resumo foi convertido no lugar, mantendo os números brutos; após rebasear em um contrato íntegro é preciso regenerar `experiment_id`/`code_version`.
- Verificação visual (Playwright/screenshots) não foi executada nesta etapa; verificados tipos, lint e testes unitários (`vitest`).
- Totais de grupo no explorador de cenários somam inteiros por DIST (portanto são inteiros); a ordem Conservador ≤ Moderado ≤ Agressivo vale pelo total agregado do metric, não necessariamente por DIST (aviso já exibido na tela).
