# QA independente dos cenários 2026–2030 (handoff para Codex)

**Emissão:** 25/10/2026. **Base de origem:** PR #6, `cfad5559`, que consome o contrato nacional de PR #4 (`8e2eab8`). **Branch isolada:** `feat/chatgpt-qa-cenarios-riscos-2026-2030`.

## Motivação

O motor linear de estoque BDGD faz `max(0, valor_2025 + inclinacao * horizonte)`. Esse truncamento evita estoque negativo, mas pode produzir **zero artificial em 2030**, mesmo quando a publicação oficial de 2025 tem equipamento positivo. É incorreto confundir um zero de cenário matemático com `zero_verificado` na BDGD.

Os quatro anos 2022–2025 também podem conter `zero_verificado` oriundo de validação técnica, ainda sem checagem independente por entidade original do GDB. O CSV antigo marcava cada um desses zeros como `observado`, perdendo a ressalva.

Este PR **não altera nenhuma célula de origem, curva, parâmetro, ZIP, GDB ou classificação regulatória**. Adiciona avisos à interface e preserva o estado técnico na exportação.

## Auditoria reproduzida independentemente

Universo: 1.555 séries fisicamente comparáveis do pacote `web/public/data/previsoes/cenarios-exploratorios-2026-2030.json`, com quatro observações 2022–2025 e cinco pontos condicionais 2026–2030. Os critérios abaixo são **regras de sinalização heurísticas**, não reclassificação como previsão inválida ou dado ausente.

| Critério de risco | Séries afetadas |
|---|---:|
| Ao menos um zero técnico de origem | 205 |
| Todos os quatro anos são zeros técnicos | 190 |
| Zero em 2025 após algum ano anterior com estoque positivo | 4 |
| Tendência linear seria negativa e foi truncada em zero entre 2026–2030 | 8 |
| Cenário linear de 2030 equivale a pelo menos 2× o estoque de 2025 | 69 |
| Cenário linear de 2030 equivale a no máximo 30% de 2025 | 17 |

As seis categorias **podem se sobrepor**: não somar suas contagens. Nas 205 séries com pelo menos um zero técnico, existem **792 pontos ano–DIST–ativo** marcados como `zero_verificado`. No contrato nacional completo (11.400 células), são 1.013 zeros técnicos. Portanto não se pode atribuir 1.013 à amostra de 1.555 séries.

### Evidências concretas

- DIST 87, **bancos_capacitores**: 2022=51, 2023=51, 2024=48, 2025=20. A tendência linear extrapolada cruza zero e seria negativa a partir de 2028; o motor trunca em zero. **Exibir o alerta `TENDENCIA_TRUNCADA_NO_ZERO`, não declarar ausência do equipamento**.
- DIST 39, **reatores**: 2022–2025 iguais a zero, e os quatro registros estão classificados como `zero_verificado`. Não constitui prova independente de ausência estrutural do ativo; exportação marca `zero_verificado_pendente`.
- Os 13 pares divergentes, o de/para EPB/EBO e a situação de Coprel 2023 não são alterados.

## Contratos implementados

- `web/src/lib/risco-cenarios.ts`: avaliador puro, que não escreve nem recalcula o estoque.
- `web/src/components/pages/PrevisoesExploratorias.tsx`: alertas por DIST×conceito×método e CSV enriquecido.
- `web/tests/risco-cenarios.test.ts`: cenários unitários e contagem exata nos dados reais (gate de regressão).
- `web/e2e/riscos-cenarios.spec.ts`: renderização e CSV nos exemplos DIST 87 e DIST 39, mais verificação da experiência mobile.
- `web/src/components/pages/previsoes-exploratorias.module.css`: indicação neutra, legível e responsiva.

### Saída CSV

Preserva o prefixo existente `ano,valor,classe,metodo,dist,conceitoId,unidade`, acrescentando `estado_origem,homologacao_origem,publicacao_id,avisos_estatisticos`. O ano observado com zero técnico tem `classe=zero_verificado_pendente` (não `observado`). As projeções têm `classe=simulacao_condicional` e `homologacao_origem=sem_homologacao_preditiva`.

Não se gera total Brasil, intervalos de confiança, CAPEX ou previsões homologadas.

## Coordenação com Codex

Este PR está sobre a branch do **PR #6**, não sobre a branch do Claude/PR #4. Para evitar conflito, recomenda-se ao Codex inspecionar, mas não editar simultaneamente `risco-cenarios.ts`, `risco-cenarios.test.ts`, `riscos-cenarios.spec.ts` e a área de alertas/CSV em `PrevisoesExploratorias.tsx` até integrar este patch. Codex pode continuar a auditoria das outras páginas, estabilidade, performance e estatística da linha histórica.

**Não fazer merge nem promover preview para produção sem revisão humana.**