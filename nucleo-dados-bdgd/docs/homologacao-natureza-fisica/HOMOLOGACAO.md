# Homologação — contagens inteiras nos produtos públicos (29/10/2026)

Correção independente do Motor V2 experimental. Base: topo do PR #17 (`f0ad962`). Nenhum cálculo estatístico, seleção de modelo, data de fonte, checkpoint ou treinamento foi alterado; nenhuma extração, aquisição de 2021 ou processamento nacional foi feito.

## O que muda
- **Contrato** (`motor_v2/metric_contract.py`, só biblioteca padrão): natureza física por unidade; contagem é inteiro ≥ 0, arredondada meio-para-cima **apenas no produtor**; kVA/kW (aparente/ativa) só convertem com fator de potência explícito.
- **Produtores**: `motor_cenarios/cenarios.py` publica contagens como inteiros (trajetórias, histórico observado e `base_2025`), declara `natureza` por métrica e aborta se uma contagem sair com casa decimal; `relatorio.py` não imprime `650.0`/`649.5` para contagens; `motor_universal` declara `natureza_fisica` e arredonda `futuro` das contagens.
- **Web**: parsers recusam natureza × unidade × métrica incoerentes e contagem fracionária/negativa (erro, nunca arredondamento silencioso); tooltip, tabela, CSV e eixo Y (pt-BR, ticks inteiros) seguem a natureza; `N/D` permanece `N/D`.
- **Hash LF**: SHA-256 do contrato nacional e do código do motor universal sobre texto normalizado em LF (checkout Windows × Linux).
- **CI**: passo novo roda `motor_v2/tests` (contrato + auditoria) e `motor_v2.audit_public_products`.

## Origem dos dados regenerados
Derivados do produto **gerado no Linux** do PR #17, sem recomputar estatística: valor publicado (3 casas) → meio-para-cima nas contagens; histórico inteiro; `natureza` adicionada. 13 valores publicados estavam exatamente em `x,500` (empate não recuperável do bruto, resolvido meio-para-cima). Km e kVA ficam byte a byte como no PR #17. O `--check` do CI regenera tudo no Linux e compara (contagens projetadas: ver "Folga de 1 unidade" abaixo; histórico observado: exato)

## Folga de 1 unidade nas contagens projetadas (`cenarios.py --check`)
- **Por que existe.** O arredondamento meio-para-cima de um bruto com ruído de plataforma (RF/HGB, Windows × Linux) pode virar uma unidade, e o produto derivado do Linux tem 13 empates `x,500` cujo bruto não é recuperável. Em séries pequenas (< 200, 40% dos pontos) 1 unidade excede a regra relativa de 0,5%.
- **Quanto é usada, na prática.** Regeneração Windows × produto derivado do Linux: 98,2% dos pontos idênticos; 0,47% (76 de 16.045) só passam pela folga; 0,9% divergem além das duas regras (máx. 13%, ruído RF/HGB entre plataformas, motivo pelo qual o árbitro é o CI Linux). No Linux a folga só deveria ser necessária nos 13 empates.
- **Risco de mascarar diferença real.** Um deslocamento de +1 em séries pequenas passaria pela regra isolada. Mitigação implementada: a folga é **limitada em quantidade** (`FOLGA_MAXIMA` = 0,5% das contagens projetadas, mínimo 20); acima disso o `--check` reprova com "deslocamento sistemático". Escolhas de modelo, estados e histórico observado seguem exatos; diferença de 2 ou mais unidades fora da regra relativa reprova. O número usado é impresso como `::notice::` no log do CI. Testes: `motor_cenarios/test_tolerancia.py` (9 casos: aceita, conta, rejeita 2 unidades, rejeita deslocamento sistemático, aceita ruído esparso, histórico exato, contínuos inalterados).
- **Risco residual.** Uma regressão que desloque menos de 0,5% das contagens em exatamente 1 unidade passa. Aceito: seria indistinguível do ruído que a folga existe para absorver, e não altera o modelo escolhido nem a ordem de grandeza publicada.. `motor-universal-resumo.json.gz` = resumo Linux do PR #17 transformado pela mesma regra (igualdade verificada campo a campo).

## Verificações locais (Windows)
| Verificação | Resultado |
|---|---|
| Vitest | 161/161 |
| `tsc --noEmit`, ESLint | sem erros |
| `next build` | OK (export estático, 11 páginas) |
| Playwright completo (desktop, mobile, iPhone estreito) | **148/148** |
| `motor_v2/tests` (contrato 25 + auditoria 3) | 28 OK |
| `motor_cenarios` (inclui `test_publico.py`) | 13 OK |
| `motor_universal` | 81 OK |
| `88_cenarios_exploratorios.mjs --check` (commit do CI `e5115f49…`) | OK, 1.792 séries |
| `auditoria_pr6.py`, `smoke.mjs` | PASSOU / OK |
| `motor_v2.audit_public_products` | 0 contagens fracionárias, 0 negativas, 0 incoerências, 0 contagens grafadas com casa decimal |
| `cenarios.py --check` local | **diverge** (158 diferenças); o PR #17 **sem alterações** diverge igualmente no Windows (297): ruído RF/HGB entre plataformas. Árbitro: CI Linux |
| `motor_universal --check-web` local | diverge em 12 floats contínuos (≤ 4,3e-14 relativo); 0 diferenças em projeções inteiras. Árbitro: CI Linux |

Cobertura E2E nova (`e2e/natureza-fisica.spec.ts`): gráfico, tooltip por hover, tabela e CSV baixado para consumidores, transformadores (quantidade e kVA) e Rede MT (km); exploratórios e motor universal (tabela + JSON exportado).

## Relação com o Motor V2
O Motor V2 (`feat/motor-v2-granular-territorial`, `f2bb937`) segue intacto. Ele contém um superconjunto desta correção (inclui erro físico de backtest e predições brutas internas, não levados aqui). Ao integrar, `cenarios.py`, `test_publico.py`, `test_metric_contract.py` e os dados de `motor_cenarios/saida` terão conflito trivial: vale a versão do Motor V2 para código e a deste PR para os dados regenerados a partir do Linux.
