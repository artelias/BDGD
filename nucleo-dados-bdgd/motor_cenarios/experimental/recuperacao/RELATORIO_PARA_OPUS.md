# Entrega experimental ao Opus — 2026-11-05

**Estado: implementação experimental com piloto validado; entrega nacional bloqueada,
não pronta para aceite científico.** Não houve merge, deploy, alteração da RC,
produto público, dados originais, branch científica ou PR #22.

## Referências e ambiente

- RC verificada: `rc/1.0-20261101@dba5fdfa1ae2e5f086555e8c03edb5aeebe67af9`.
- Protocolo congelado: `recuperacao-1`, commit `d478e16`, sem alterações.
- Base da branch própria: `exp/recuperacao-cenarios-20261104@6ec3b6d0e69b34750aea56520f1ba6734ef4b74f`.
- Otimização incorporada na base: `997c4d7cdaf92d8306b3a4e0702e578b25f154dc`.
- Dossiê científico: `3748c95553a48459f8fdf506a847ca03ddc4da5c`.
- Branch de entrega: `codex/recuperacao-cenarios-20261105`. O hash exato está no
  commit da entrega e na mensagem final; `git rev-parse HEAD` o reproduz.
- Worktree isolado `/workspace/BDGD-recuperacao`, em Linux, autorizado pelo usuário
  em substituição ao disco D:. A base escolhida reaproveita a pesquisa já reunida;
  nenhum merge novo foi criado. O arquivo `cenarios.py` e o JSON público são
  idênticos aos da RC, apesar de as histórias de branches serem distintas.
- Nenhuma biblioteca instalada. Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0,
  scikit-learn 1.8.0. A referência registra Windows, Python 3.14.3, NumPy 2.5.4,
  SciPy 1.18.1 e scikit-learn 1.8.0. A relação causal entre essas diferenças e
  cada divergência numérica ainda precisa ser confirmada.

## Implementação e preservação

Pacote `motor_cenarios/recuperacao/`, independente do gerador público, com modos
originais, otimizados e condicionais. Reutiliza o contrato físico do Motor V2,
o Motor original, as configurações finais X e as funções científicas congeladas.
Não refaz a busca de 1.504 ajustes. Inventário por métrica com trajetórias 2026–2030,
parâmetros, variáveis, pontos retrospectivos, elegibilidade e motivos; avaliação
por DIST com WAPE local, qualidade Q1–Q9, escolhas e proveniência.

Hashes das entradas, código de referência, relatórios científicos, código novo
e bibliotecas vinculam cada execução e cache. Verificação antes e depois do
processamento. O cache contém resultados JSON, não modelos pickle. Saídas só
em diretório experimental, sem sobrescrever execuções anteriores. O Moderado e
histórico são copiados do produto, incluindo N/D; não há proposta de substituição
nem liberação das 121 séries que exigiriam decisão de contrato.

## Comparação exata do piloto aprovado

**Escopo: consumidores/quantidade, 98 distribuidoras. Somente originais (P1 + P2/O).**

| Indicador | Antes | Depois |
|---|---:|---:|
| Séries completas | 0 | 60 |
| Séries parciais | 88 | 28 |
| Séries sem previsão | 10 | 10 |
| Extremos com modelos independentes | 88 | 148 |
| Extremos condicionais | 0 | 0 |
| Posições ausentes por erro, causa B | 0 | 0 |
| Posições ausentes por plausibilidade, causa E | 0 | 0 |

Ganho: **60 séries completas**, nenhuma perda de completude neste piloto.
Permanecem 38 séries não completas: 28 parciais e 10 sem previsão. Causas das
48 posições ainda ausentes: 26 A2 (lado oposto), 2 D (diferença insuficiente),
20 H (sem Moderado). As 60 recuperações correspondem à causa I anterior.
Não se somam conceitos físicos diferentes nem namespaces EQ/UN.

- `SERIES_RECUPERADAS.csv`: todas as 60 séries recuperadas.
- `SERIES_BLOQUEADAS.csv`: todas as 38 séries não completas, com causas.
- `piloto-final/comparacao.csv`: todas as colunas solicitadas, 98 linhas.
- `piloto-final/cobertura.csv`: ganhos/perdas por métrica e por distribuidora.
- `piloto-final/produto.json` e `cenarios.csv`: série observada, anteriores,
  trajetórias novas, modelos, categorias e motivos.
- `piloto-final/inventario.json` e `elegibilidade.csv`: algoritmos, parâmetros,
  erros/WAPE/R², pontos, motivos de rejeição e hashes.
- `piloto-final/gabarito.json`: 98 séries comparadas com 02, sem divergências;
  comparação das linhas 06 de P1/P2 sobrepostas ao escopo, sem divergências.
  As demais linhas 06 são explicitamente contadas fora do escopo (não aprovadas).

Exemplo real: consumidores da Energisa AC (DIST 26), Agressivo `knn_analogos`,
340.627 em 2030; Moderado preservado. As regras são verificadas nos cinco anos,
não apenas em 2030. Condicionais nunca são descritos como intervalos de confiança.

## Limite nacional: portão de reprodução reprovado

A contagem original nacional foi reconferida: **755 completas, 1.206 parciais,
241 sem previsão**, total 2.202. **Não há contagem nacional posterior válida.**
`COBERTURA_NACIONAL_PENDENTE.json` mantém os resultados posteriores como null.

O processamento nacional parou em `bancos_capacitores/quantidade`:

- Modelo: `random_forest_painel`.
- WAPE publicado: **0.0600573022094799**.
- WAPE reconstruído: **0.06005597829053297**.
- Diferença absoluta: aproximadamente **1.32391894693e-6**.
- Limite congelado: **< 1e-9**.

`nacional-final/bloqueio.json` e o log preservam a evidência. Não se relaxou o
limite nem se continuou a produção nacional após esse portão. As contagens
1.343, 711, 1.039 ou 1.239 do estudo anterior não são apresentadas como resultado
desta implementação.

## Piloto com otimizados e B-HIST: diagnóstico, sem aceite

O piloto adicional reutilizou o cache e bloqueou `knn_analogos_otim` de consumidores:
S observado 0.03620207211997554 contra 0.036207 registrado; F observado
0.023107202334389846 contra 0.023106 registrado. Ambos ultrapassam a tolerância
da reprodução. Não foi tornado elegível para aumentar cobertura.

O artefato diagnóstico tem 84 completas, 4 parciais e 10 sem previsão, mas
**não é resultado aprovado**: 113 campos divergem dos gabaritos, incluindo
36 modelos, 36 valores 2030, 36 estados de auditoria, 3 classes e 2 campos Q7.
O CLI retorna 1 e `aceite_gabarito=false`. Esses dados ficam em
`piloto-final-condicionais/`, separados do piloto aprovado. Nenhum limite foi
alterado para reproduzir artificialmente o relatório anterior.

## Testes e reprodução

| Verificação | Resultado efetivo |
|---|---|
| 34 testes novos da recuperação | passaram |
| 25 testes existentes do gerador | passaram |
| `unittest discover -s motor_cenarios` | 59 executados, 0 falhas/erros, nenhum ignorado |
| Gerador público `cenarios.py --check` | passou; 29 métricas, 16.010 contagens, 2 na folga já existente |
| Repetição do piloto, com cache | 9 artefatos determinísticos idênticos byte a byte |
| Suíte sintética existente Motor V2 | 59 casos no runner, 12 erros de importação por DuckDB ausente; 47 passaram, nenhum ignorado |
| `npm test` | não executou testes: Vitest do projeto ausente |
| `npm run e2e` | não executou testes: runner Playwright Test do projeto ausente |
| Nacional estrito | falhou no portão documentado |
| Piloto X/B-HIST | falhou no gabarito documentado |

Os logs estão em `evidencias/`. O gate público admite tolerância entre plataformas
mais ampla; seu sucesso não substitui o protocolo científico. Nenhum teste foi
desativado. Não se afirma regressão ampliada completa nem CI verde. Não houve
nova interface nem teste de interface do produto experimental nesta etapa.

## Consumo e determinismo

Piloto final: **4,345 s**, pico acumulado de RSS **146,965 MiB**; etapa da métrica
2,827 s. A reexecução usa cache validado; tempos/RSS ficam em `execucao.json`,
fora da comparação determinística. `DETERMINISMO.json` registra os hashes iguais
e as medições da repetição. Uma thread BLAS/OpenMP por execução; estimadores com
`n_jobs=1`; limite de endereçamento de 8 GiB. Nenhum Parquet nacional carregado,
extração nova, busca de hiperparâmetros ou grande artefato em C:.

## Parecer e desbloqueio necessários

**Modelos novos efetivamente utilizados: nenhum.** N1/N2/N5 permanecem congelados;
N6 reprovado e modelos granulares sem contrato DIST não entram. As alternativas
para medidores/rede AT/torres não substituem o Moderado. kVA continua marcado
EXPERIMENTAL_KVA na API e só pode entrar quando superar os mesmos gates.

Para concluir a execução nacional sob o protocolo atual, é necessário um ambiente
que reproduza os resultados de referência, com dependências já disponíveis, ou
caches completos de trajetórias e backtest com hashes verificáveis. Se isso não
for possível, cabe ao Opus avaliar uma versão de protocolo para portabilidade,
com sensibilidade separada e justificação; o Codex não autorizou essa alteração.
A regressão ampliada requer DuckDB e os runners do projeto já provisionados.

O Opus deve revisar as divergências e emitir parecer independente antes de qualquer
integração. Não foi possível encaminhar uma mensagem direta a um destinatário
Opus nesta sessão; este dossiê e a branch publicada são a entrega para essa revisão.
Toda comparação com 2025 é retrospectiva/exploratória, com alvo já consultado.
**Nenhum horizonte 2026–2030 é declarado homologado.**
