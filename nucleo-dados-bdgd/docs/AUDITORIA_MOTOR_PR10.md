# Auditoria do Motor Universal — PR #10

Auditoria de código e artefatos realizada em 26/10/2026. Branch própria `feat/auditoria-cobertura-features-pr10`, derivada exatamente do HEAD do PR #10, `413e444227f98a5b14e83398c31c0b978e9777ad`. Cadeia preservada: esta entrega → #10 → #9 → #8 → #6 → #4. Nenhum merge, deploy de produção, reextração de GDB, alteração de checkpoint ou homologação humana.

## Evidência de partida

Os três workflows do PR #10 foram consultados e estavam concluídos com sucesso: motor `40386951279`, web `40386951308`, checks `40386951167`. O ZIP do artefato `12680912149` foi baixado e lido; seu manifesto identifica experimento `507c53fd65dc31cfbf44e68575ff8c9ad8897c8d39ef6c050e7d0b0579aea144`, com 2.850 diagnósticos: 1.545 simulações condicionais e 1.305 bloqueios. Não se presumiu que a descrição do PR provava os números. A nova execução leu os mesmos produtos nacionais e conferiu o hash da fonte; não refez a extração histórica.

## 25 ativos, 29 combinações e 2.850 séries

O catálogo contém 25 ativos nomeados e 29 combinações ativo/métrica. O contrato atual contém quatro competências por cada uma de 25 combinações × 114 DIST = 11.400 linhas, formando **2.850 séries com linhas**. Uma série é DIST + ativo + métrica, com território, regra e perímetro rastreados. Não são 2.850 empresas, nem 11.400 observações independentes.

As quatro combinações adicionais são `potencia_kva` de `trafo_dist`, `trafo_forca`, `trafo_medida` e `reguladores`. Cada uma tem 114 combinações esperadas e zero linhas no contrato atual: **456 ausências de cobertura de métrica**. Não são 456 séries que foram treinadas ou descartadas silenciosamente. O núcleo anterior listava motivo de ausência por objetivo, mas não publicava o denominador completo por DIST. Agora a matriz inclui essas combinações sem fabricar alvos.

**3.306 esperadas = 2.850 com linhas + 456 sem histórico**. Nas 2.850 com linhas, **1.545 executáveis + 1.305 bloqueadas**. Trata-se do universo das DIST presentes no painel; não certifica completude do universo nacional, população ativa ou disjunção territorial.

| Métrica | Esperadas | Com linhas | Executáveis | Bloqueadas | Sem histórico |
|---|---:|---:|---:|---:|---:|
| extensao_km | 456 | 456 | 276 | 180 | 0 |
| potencia_kva | 456 | 0 | 0 | 0 | 456 |
| quantidade | 2394 | 2394 | 1269 | 1125 | 0 |

As colunas obrigatórias da matriz estão presentes: DIST, OBJETIVO_ID, METRICA, ANOS_DISPONIVEIS, ANOS_VALIDOS, STATUS e MOTIVO_BLOQUEIO. Inclui ainda anos registrados, segmento final, ano de fronteira, causas contribuintes, justificativas do motor, resolução e evidências anuais com estado/homologação/publicação/motivo da origem.

`ANOS_DISPONIVEIS` significa anos com valor não nulo, inclusive zero técnico; não comprova divulgação point-in-time. `ANOS_VALIDOS` aplica qualidade local, cobertura, disponibilidade no corte e comparabilidade; elegibilidade exige ainda o segmento final contíguo. Ter quatro linhas registradas não significa quatro observações válidas.

Arquivos completos, derivados e versionados:

- [Matriz Parquet principal — 3.306 linhas](auditoria-motor-pr10/cobertura.parquet).
- [Matriz CSV completa comprimida](auditoria-motor-pr10/cobertura.csv.gz). O CSV descomprimido também é produzido pelo CLI e publicado no artefato do CI.
- [Resumo e classificação JSON](auditoria-motor-pr10/cobertura-resumo.json).
- [Totais por métrica](auditoria-motor-pr10/cobertura-por-metrica.csv) e [por ativo/métrica — 29 linhas](auditoria-motor-pr10/cobertura-por-objetivo.csv).
- [Integridade dos produtos de origem](auditoria-motor-pr10/integridade.json).

## Auditoria dos 1.305 bloqueios

A causa principal é exclusiva e explica a fronteira que inviabiliza o segmento final. Causas contribuintes podem coexistir em diferentes anos: sua soma não é o total de bloqueios. Histórico insuficiente é o mecanismo final em todos os 1.305 casos; a coluna principal detalha a origem da insuficiência.

| Causa | Principal, exclusiva | Séries com causa contribuinte |
|---|---:|---:|
| Histórico insuficiente | 0 | 1305 |
| Ausência de observações | 134 | 152 |
| Homologação/decisão pendente | 329 | 511 |
| Ruptura cadastral | 40 | 55 |
| Incompatibilidade temporal | 0 | 0 |
| Sobreposição/não somável | 0 | 25 |
| Unidade incompatível | 0 | 0 |
| Falta de comparabilidade | 0 | 0 |
| Zero técnico sem evidência independente | 277 | 298 |
| Não aplicável | 454 | 462 |
| Cobertura incompleta/desconhecida | 71 | 1068 |
| Outros | 0 | 0 |

Exemplos rastreáveis na matriz: DIST 32/alimentadores interrompe o segmento por republicações divergentes em 2023 pendentes de decisão; DIST 31/alimentadores tem ruptura em 2025; DIST 380/alimentadores tem cobertura não comprovada em 2024, além da pendência anterior. Esses registros são evidência de bloqueio, não autorização para aprovar fontes.

Não há liberação automática possível com os dados atuais mantendo os critérios. Os 454 casos classificados como não aplicáveis permanecem N/D e não precisam ser transformados em séries numéricas. Os demais 851 dependem de decisão formal de fonte (329), evidência independente de zero (277), observações/fontes adicionais (134), comprovação de cobertura (71) ou ponte de população/ruptura (40). Potência exige painel comparável novo para as 456 combinações ausentes, separadas dos 1.305 bloqueios existentes. Problemas de unidade e incompatibilidade temporal são recusados/bloqueados nos testes de integração, mas não foram encontrados como causa principal nesse contrato real.

## Duplicidade e sobreposição

As chaves long e wide são únicas no experimento real. Não se encontrou duplicidade de linhas. O catálogo revela uma interseção potencial: **seccionalizadores são o recorte EQSE/TUC 160/A1 10 dentro de chaves EQSE/TUC 160**. São objetivos legítimos para consulta separada; somá-los duplicaria estoque. Transformadores 565/570/575 usam entidades comuns com filtros TUC disjuntos. O catálogo não prova disjunção de todas as populações reais: a agregação nacional continua bloqueada sem contrato de universo/disjunção.

Há também 25 séries bloqueadas que contêm flag de não somável em algum ano. Isso não é equivalente a 25 duplicidades; a matriz preserva a restrição original e suas causas adicionais.

## Defeitos comprovados e correções

1. **Alvo divulgado após a origem entrava no backtest marcado apenas como retrospectivo.** Agora divulgação conhecida posterior à origem bloqueia o fold de todos os candidatos, incluindo persistência/OLS. Disponibilidade desconhecida continua explicitamente retrospectiva; não se inventam datas históricas.
2. **Não havia junção wide por objetivo para valores específicos de ativo.** Bundle v2 mantém targets long e wide compartilhado, acrescentando wide opcional por ANO + DIST + OBJETIVO_ID. Dois joins m:1, sem multiplicação; v1 continua legível. Flags de comparabilidade, evidência, ruptura e versão por observação são preservadas.
3. **Cenários de uma série curta podiam ser ignorados pelo maior ano global de outra DIST.** Agora linhas wide futuras são associadas por série, com placeholders de alvo exclusivamente NULL.
4. **Checagem Arrow verificava nomes, mas não tipos exatos nem colisões reservadas.** Tipos incorretos, nomes reservados/duplicados, chaves duplicadas e features órfãs são recusados. Divergência em features compartilhadas não é resolvida por média ou primeira linha.
5. **Ausência integral de feature de treino era tratada diferente de NULL autorizado.** Ausência genuína pode usar imputação de treino somente se declarada. Divulgação tardia nunca é imputável. Covariável futura ausente/NULL bloqueia a projeção enriquecida; coluna inteiramente ausente não recebe valor arbitrário.
6. **Razões/interações ausentes podiam chegar à imputação sem autorização própria.** Agora a autorização é exigida nos dois componentes no treino; não se gera zero de denominador inválido. Uma referência futura em relação à própria divulgação também exige identificação explícita de cenário.
7. **Números de catálogo não mostravam o denominador de cobertura na interface.** O dashboard passa a distinguir esperadas, com linhas, bloqueadas e sem histórico; a tabela e a exportação incluem cobertura por métrica. O parser recusa contagens incompatíveis com as séries.

Ajustes adicionais: alvos conhecidos tardios também são recusados na API direta de modelos quando há corte informado; projeções recursivas intermediárias negativas/não finitas são rejeitadas imediatamente; horizontes inválidos são recusados. Folds registram anos de treino, corte e identidade da série. Agregados por objetivo registram hash da cobertura e aviso de comparação pareada necessária.

## Controles estatísticos preservados

Treino expansivo por série, sem divisão aleatória ou pooling de linhas; lags só usam passado. Média/escala/categorias aprendidas no treino; categorias futuras não alteram o encoder. Última origem reservada para auditoria, sem selecionar pelo seu erro; critérios conservadores mantêm persistência nas quatro observações reais. Erros por horizonte separados; WAPE NULL com denominador zero; grupos de unidades diferentes não se somam. Coberturas de modelos devem ser pareadas antes de comparação agregada.

Zero técnico permanece 0 com estado e fora do treino; zero verificado exige evidência independente. N/D não vira zero. Stock negativo/não finito é rejeitado, sem truncamento. Diferença líquida pode ser negativa; não atravessa lacuna/ruptura/não comparabilidade. Necessidade de expansão permanece NULL. Nenhum intervalo probabilístico foi inventado e nenhuma previsão foi cientificamente homologada.

## Contrato final e chegada do painel enriquecido

[Contrato completo de features](../motor_universal/CONTRATO_FEATURES.md): Parquet long/wide, escopo por ativo, metadados por variável, corte/disponibilidade, NULL, versionamento e municípios multi-DIST. Pré-validação municipal verifica vínculos, soma de pesos, população do peso e evidência de rateio, sem ativar agregação municipal nem presumir que um peso serve para todas as variáveis.

**Prontidão:** pronto tecnicamente para receber e validar um bundle real em DIST × ano, compartilhado e/ou específico por ativo. Não está demonstrada prontidão científica para modelos enriquecidos: depende dos dados reais, disponibilidade histórica, comparabilidade e amostra efetiva. Os quatro anos atuais permitem no máximo duas origens anuais de um passo por série; ML foi exercitado apenas em fixtures sintéticas identificadas nos testes.

Claude ainda deve entregar Parquets/dicionário, fontes e versões por variável, atributos e relações EQ/UN verificados, covariáveis internas/externas comparáveis, disponibilidade histórica e cenários futuros explícitos. Matriz municipal e modelo de população/pesos continuam necessários para futura granularidade municipal. Modelos pooled/hierárquicos e demais extensões não implementadas no PR #10 continuam fora desta entrega; não se reconstruiu o motor.

## Validação desta entrega

- Python: 61 testes aprovados localmente, com dependências ML opcionais instaladas; 28 novos testes de integração/auditoria.
- TypeScript: 128 testes aprovados localmente; quatro regressões novas de cobertura/exportação.
- Lint e tipos aprovados localmente.
- Build estático aprovado localmente. E2E: resultados finais, links e evidências registrados no PR da entrega após execução do CI. Não considerar execução local bloqueada como aprovação.
- Tentativa local de Playwright: o servidor `serve` abortou em `uv_interface_addresses` por restrição do ambiente; com servidor Python, o Chromium chegou a iniciar, mas abortou em `socket() failed: Operation not permitted`. Nenhuma dessas tentativas locais é contabilizada como E2E aprovado. O runner GitHub Actions executa Chrome desktop, Android e iPhone estreito emulado; não equivale a Safari/iOS físico.

O artefato do CI publica Parquets de entrada/resultados, matriz completa, manifestos e registro de execução. Experimento desta auditoria: `6786a18a45f920003350f4d0c9efbe18835c4ad4a13762a99bbba92630d18427`. Os bytes de `targets.parquet` foram comparados com o artefato original do PR #10: idênticos. 500 arquivos oficiais/ETL/históricos/assets preexistentes foram comparados por SHA-256, sem alterações; ver evidência de integridade.
