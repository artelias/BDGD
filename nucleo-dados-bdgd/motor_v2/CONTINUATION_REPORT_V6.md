# Motor V2 — estabilização após d6729d3 (29/10/2026)

Mesma branch (`feat/motor-v2-granular-territorial`), base `d6729d3`. Sem download de 2021, sem instalação de dependências, sem processamento nacional, sem merge e sem deploy. Contrato de contagens inteiras, resultados, checkpoints e commits anteriores preservados. **Nenhuma previsão 2026–2030 foi declarada validada ou homologada; nenhum backtest PIT é declarado validado.**

## Matriz de verificação

| # | Item | Status | Resultado | Bloqueio restante |
|---|---|---|---|---|
| 1 | Conversão de unidades (`metric_contract.convert`) | ✅ | kVA↔MVA e kW↔MW↔W livres; **potência aparente ↔ ativa só com `power_factor` ∈ (0,1] explícito** (S = P/fp); fator informado onde não se cruza o tipo, valor não finito, km↔kVA e contagens: erro. 32 testes do contrato | — |
| 2 | Parsers web rejeitam incoerência | ✅ | `exigirCoerencia` (natureza × unidade × métrica) em `parseCenarios` e `parseResumoMotor`; `valorPublico`/`formatarFisico` **não arredondam**: contagem fracionária ou negativa é erro; `arredondarContagem` ficou só para produtores. Tooltip mostra "valor inválido" em vez de arredondar. MVA numa métrica em kVA é recusada (sem conversão silenciosa) | — |
| 3 | Falha restante do Vitest | ✅ | Causa: `blobShaOrigem` calculado sobre bytes CRLF (checkout autocrlf, `88a3cca…`) em vez do blob git (LF, `fc50a72…`). Hash normalizado em LF no gerador, no teste e em `auditoria_pr6.py`; produtos regenerados. **Reproduzido e corrigido no checkout real da branch**, sem sincronizações temporárias | — |
| 4 | 2 testes do `motor_universal` e divergência de hash | ✅ | Não era corrupção: o contrato nacional é íntegro; o hash era sobre bytes brutos (CRLF no Windows). Hash do contrato e `code_digest` agora em LF. 81 testes OK. `experiment_id`/`code_version` regenerados e rastreados em `motor_universal/RASTREABILIDADE_RESUMO.json` (anterior e novo, motivo); `experiment_id` depende só das entradas, não das saídas; números do resumo inalterados | `--check-web` exato **local** (Windows) difere ~1,5e-13 em floats (ULP); árbitro é o CI Linux, não executado aqui |
| 5a | Vitest completo | ✅ | **161 testes, 20 arquivos** | — |
| 5b | TypeScript / ESLint | ✅ | `tsc --noEmit` e `eslint .` sem erros | — |
| 5c | Build | ✅ | `next build` (export estático, 11 páginas) OK | — |
| 5d | Playwright completo | ✅ | **148 testes** (desktop, mobile, iPhone estreito): 147 passaram na primeira rodada; 1 falhou por expectativa antiga que exigia `184.6` no CSV de **alimentadores** (contagem). Corrigida para `185` (igual ao card) e reexecutada: 9/9 no recorte afetado | — |
| 5e | Gráficos de clientes, transformadores, extensão e potência | ✅ | Nova `e2e/natureza-fisica.spec.ts` (6 testes): gráfico + **tooltip por hover**, tabela anual e CSV baixado para consumidores, trafo (quantidade), Rede MT (km) e trafo (kVA); exploratórios e motor universal (tabela + JSON exportado). **Achado e correção:** o eixo Y do gráfico saía em formato en-US (`260,000`), que um leitor pt-BR lê como 260 com três decimais; agora pt-BR (`260.000`) e com `minInterval: 1` para contagens | — |
| 6 | Auditoria dos três produtos públicos | ✅ | `python -m motor_v2.audit_public_products` (3 testes): **0 contagens fracionárias, 0 negativas, 0 incoerências** em `cenarios-motor.json` (22.224 contagens), resumo do motor universal (29.132), cenários exploratórios (13.590) e no CSV de cenários (21.094); extensão/potência mantêm decimais (7.535, 6.013, 2.535, 7.233). JSON, CSV, tooltip e tabela cobertos (Python + Playwright). Saída: `reports/auditoria_produtos_publicos.json` | Resíduo de **forma**, não de valor: 5.049 contagens do CSV (`base_2025`) e o histórico observado de `cenarios-motor.json` saem como `123.0`/`88.0` (inteiro grafado com `.0`). Normalizar exige regenerar os produtos; adiado para a regeneração no Linux, onde o `--check` é árbitro |
| 7 | Metodologia point-in-time | ✅ (documental + biblioteca) | `METODOLOGIA_POINT_IN_TIME.md`: competência ≠ publicação ≠ origem ≠ ano-alvo; `vintage.py`; `usable(..., origin_date=None)` opcional, **padrão inalterado**; datas reais não alteradas; `claim()` nunca promove carimbo/inferência, modo reconciliado ou leitura vazia | **Vintages não provadas** (o inventário local só traz a revisão atual); relógio por data de publicação é decisão de projeto; PIT segue inatingível pelo relógio legado (0 de 19 competências geradas antes do fim do ano) |
| 8 | Testes de competência anterior publicada e revisões posteriores | ✅ | `tests/test_vintage.py`: 18 testes — competência anterior disponível na origem é usada com sua 1ª versão; revisões posteriores rejeitadas (e listadas); só valem a partir do dia da publicação; competência não publicada = indisponível; alvo já publicado = vazamento; origem após o ano-alvo recusada; horizonte efetivo; imutabilidade; integração com `usable` | — |

## Suítes e regenerações

| Verificação | Resultado |
|---|---|
| `motor_v2` | **177 OK** (156 anteriores + 18 vintage + 3 auditoria) |
| `motor_universal` | 81 OK |
| `motor_cenarios` | 13 OK; `cenarios.py --check`: 29 métricas regeneradas **idênticas** ao produto publicado |
| `88_cenarios_exploratorios.mjs --check` (commit do CI `e5115f49…`) | OK, 1.792 séries, blob `fc50a72…` |
| `auditoria_pr6.py` | PASSOU |
| Hashes preservados | 12 agregados + checkpoints `585da4d176babebf`; 114 checkpoints `90169fb05589f3ba`; extração `assets-1` `4c148fdf7951e9fc` — **recalculados, iguais** |

## Bloqueios remanescentes (nenhum foi contornado)
1. **Vintages não provadas**: sem registro de publicação por versão não há backtest PIT; nada foi consultado externamente.
2. Decisão de projeto sobre o relógio de origem por data de publicação (e sobre o corte de características de treino, que ainda usa o fim do ano da característica).
3. Mínimo de 3 origens independentes continua não atendido; 2021 isoladamente não o garante (V5).
4. `--check-web` do `motor_universal` e a regeneração dos produtos no ambiente Linux do CI (inclui o `.0` de contagens): árbitro é o CI.
5. Homologação humana das 4 pontes de CONJ (V5) e autorização para aquisição de 2021 seguem pendentes.
