# Módulo futuro — Inteligência Preditiva BDGD (escopo pós-dashboard)

**Status:** planejado, **não iniciado**. Esta fase não bloqueia o dashboard oficial de 31/12/2025 e não muda o contrato público 2025 (totais e DDA). Nenhum GDB histórico será publicado no navegador.

## 1. Objetivo de negócio

Permitir que usuários do **Núcleo de Dados da BDGD** visualizem e comparem:
- **Distribuidora × distribuidora**, **grupo × grupo** e **distribuidora × grupo** por métrica/entidade; panorama nacional.
- Série histórica real e, em separado, **previsão de quatro exercícios subsequentes** ao último ano-base homologado. Primeira versão, partindo de 2025: **2026, 2027, 2028 e 2029**.
- Classificações inteligíveis de trajetória (expansão, estabilidade, retração; aceleração e desaceleração apenas quando a série sustentar), ranking de crescimento, riscos de incerteza e cenários.
- Desdobramento por família BDGD, entidade e métricas válidas (contagens, km, kVA); atributos DDA só se houver séries históricas comparáveis e cobertura suficiente para aquela faceta.

**Proibição:** não mostrar projeção como valor real da ANEEL. Realizados e previstos terão séries/legendas/estilos diferentes, e cada previsão terá origem, data de treinamento, hipótese e incerteza.

## 2. Dependência estatística inegociável

A única BDGD de 31/12/2025 **não fornece séries temporais para treinar crescimento histórico**. Nem dezenas de empresas em um único ano substituem anos passados ao estimar evolução temporal específica. É necessário gerar dataset **histórico segregado do dashboard oficial**, prioritariamente **2022–2025**, abrangendo quatro competências anuais pós-revisão regulatória de 2021; **2023–2025** é alternativa mínima apenas quando 2022 não for comparável, com a mesma métrica/unidade, grupos versionados, data-base e cobertura por `DIST`.

- Extrair prioritariamente os GDBs de **2022, 2023 e 2024** em projeto ETL **separado**, reutilizando 2025 homologado, somente após concluir M0–M5 e aprovar esforço de armazenamento/processamento. Não coletar bases anteriores a 2022 para o primeiro modelo; ampliar janela somente com nova decisão explícita.
- O histórico do BI VPE 2024 pode ajudar a entender *fórmulas*, mas **não** é automaticamente uma linha de treino equivalente; históricos de GDBs devem ser recalculados com definições reconciliadas. Não forçar resultados VPE 2024 a igualar dados 2025.
- Tratar substituições de concessionárias, fusões, cisões e mudanças de DIST e controlador econômico com tabela de vigência temporal e mapeamento auditado. Sem harmonização, a série pode ser interrompida.
- Alterações de layout, nomenclatura, DDA, critério de contagem única, geometrias e potência geram quebras estruturais; criar `metric_version` e sinalizar séries não comparáveis.
- Se apenas 2025 estiver disponível para uma entidade/DIST, mostrar **"histórico insuficiente para previsão por aprendizado de máquina"**; com **2023–2025 (três anos)** usar prioritariamente descrição e cenários cautelosos, sem anunciar previsão ML validada; com **2022–2025 (quatro anos)** admitir baseline exploratória e modelos de painel/hierárquicos, somente se a métrica for comparável e o teste fora da amostra sustentar a apresentação. Onde faltarem observações ou robustez, previsão indisponível ou cenário assumido (explicitamente não preditivo).


## 2.1. Recorte histórico fechado aprovado para planejamento (22/10/2026)

O responsável pelo projeto considera as BDGDs **anteriores a 2022** menos comparáveis após mudanças relevantes no Manual e no PRODIST. O primeiro estudo de tendência ficará **limitado aos quatro anos-base: 2022, 2023, 2024 e 2025**. O fallback técnico é **2023–2025**, exclusivamente para análise descritiva/simulações transparentes quando 2022 apresentar divergência de modelo não harmonizável. Não recorrer automaticamente a 2019, 2020 ou 2021 apenas para aumentar a amostra.

**Justificativa regulatória:** o Manual de Instruções BDGD Revisão 1 entrou em vigor em **02/01/2022** por Despacho ANEEL nº 3.935/2021. Isso delimita o ponto de partida, mas **não prova equivalência entre todas as versões de 2022 a 2025**. Examinar por entidade e campo as transformações e DDA ocorridas durante 2022–2025, unidade e regras de cálculo.

**Interpretação amostral:** 99 empresas com quatro exercícios podem formar um painel com centenas de séries entidade/empresa, permitindo **pooling** de informações transversais e variáveis anuais padronizadas; ainda há **somente quatro observações de tempo por série**. Resultados de 2026–2029 deverão indicar forte incerteza e cobertura/erros de backtest conhecidos apenas nos horizontes que forem observáveis.

**Gate para ML:** mínimo de três competências comparáveis para descrever tendência; quatro competências preferenciais para avaliação exploratória de modelos simples e modelos pooled/hierárquicos. Para rotular uma previsão `modelo_validado_horizonte_4`, exigir quantidade de anos adicionais que permitam backtest temporal desse horizonte; caso contrário marcar `horizonte_4_nao_validado`, disponibilizar somente como **cenário/projeção exploratória** com premissas e limites explícitos, ou não disponibilizar caso nem isso seja justificável.

**Não utilizar os milhões de registros brutos como observações temporalmente independentes.** Os ativos da mesma distribuidora pertencem a estruturas de rede correlacionadas; ao dividir treino/teste, usar blocos temporais e/ou unidades hierárquicas e impedir vazamento de dados do mesmo ativo entre anos.

Referências de marco regulatório: [ANEEL — BDGD dados abertos](https://dadosabertos.aneel.gov.br/dataset/base-de-dados-geografica-da-distribuidora-bdgd), [REN 937/2021 — revisão PRODIST Módulo 10](https://www2.aneel.gov.br/cedoc/ren2021937.pdf), [Despacho 3935/2021 — vigência da Revisão 1 em 02/01/2022](https://abrapch.org.br/2021/12/diario-oficial-uniao-13-12-2021/).

## 3. Granularidade e catálogo de alvos

Cada série elegível é identificada por `DIST × entidade × metrica × versao_metrica`. Unidade deve ser explícita e fixa; métricas de grandezas distintas não são intercambiáveis.

- **Contagens:** `quantidade_registros` e `quantidade_cod_id_distinto` separadas; aditividade verificada, especialmente UCBT/UCMT/UCAT.
- **Extensões:** `extensao_km`, com mudança de rede/classificação documentada.
- **Potências:** `potencia_kva` somente quando unidade, DDA e qualidade forem homologadas; não inventar normalização de UG*/SIGFI ou UNTRMT/EQTRMT.
- **Facetas DDA:** não multiplicar percentuais marginais, não somar distintos por categorias sobrepostas; previsões segmentadas serão fase posterior e somente em dimensões comparáveis e disjuntas ou com cálculo canônico.
- **Grupo econômico:** por padrão publicar soma de distribuidoras do grupo com estrutura de associação **congelada e identificada na competência-base 2025** para o horizonte futuro; mudanças societárias previstas são cenários explícitos, nunca previsão implícita do grupo.

## 4. Modelagem e classificação

### Baselines obrigatórios
Antes de alegar que ML melhora previsões, testar referências simples:
1. Último valor conhecido (naive).
2. Tendência linear com restrições documentadas e janela ajustada.
3. Crescimento composto histórico robusto quando sustentado por anos disponíveis, com piso não negativo para medidas não negativas.
4. ETS/alisamento exponencial quando apropriado.

### Modelos candidatos
- Regressão temporal regularizada por empresa/ativo; efeitos hierárquicos e `pooling` entre empresas e ativos quando for justificável e não mascarar diferenças.
- Gradient boosting (CatBoost/LightGBM/scikit-learn) com variáveis defasadas **somente** se volume de séries, histórico e covariáveis sustentarem treinamento e validação fora da amostra.
- Modelos hierárquicos que preservem coerência empresa → grupo → Brasil; reconciliação matemática dos totais e intervalos. Avaliar modelar empresas e agregar vs. modelos por grupo.
- Redes neurais/LSTM/transformers **não são padrão** para séries anuais curtas (**três ou quatro observações por distribuidora-entidade**); só experimentar com evidência de melhoria fora da amostra e histórico bastante maior. A quantidade de **milhões de linhas por GDB não equivale a milhões de pontos anuais**; elas podem enriquecer os preditores consolidados, mas não validam, por si, projeções de quatro anos.
- Variáveis externas (economia, carga, número de consumidores, mudanças regulatórias) só com fonte oficial, disponibilidade na data de previsão, cobertura e prevenção de *data leakage*.

### Classificação de tendências
- Classificação **descritiva e verificável**, não rótulos arbitrários: expansão, estabilidade, retração conforme inclinação, intervalo e tolerância por métrica definidos previamente com especialistas.
- Aceleração/desaceleração, outliers e descontinuidade apenas se houver janelas temporais adequadas; não atribuir "risco" regulatório, financeiro ou operacional sem rótulos-alvo oficiais e métricas validadas.
- Separar **classificação da trajetória histórica** de **categoria da previsão**; probabilidade/confiança só quando calibrada; explicar critérios no tooltip/metodologia.

## 5. Validação temporal, qualidade e decisão de publicar

- Ordenar por data-base, treinar exclusivamente com anos anteriores ao período testado (**rolling-origin / walk-forward**), e comparar desempenho por horizonte quando houver observações suficientes. Com somente **2022–2025 (quatro pontos anuais por série)**, o backtest em horizonte 1 já é limitado e **não permite validar empiricamente um horizonte de 3–4 anos** com treino histórico adequado. Não apresentar as projeções 2028/2029 como "modelo validado para esse horizonte" sem evidência adicional; indicar a limitação e usar cenários/sensibilidade com incerteza não calibrada quando apropriado.
- Seleção de modelos **por alvo/grupo de séries**, com backtesting que não permita informação futura em variáveis, DDA, grupo econômico ou normalização.
- Medir MAE, WAPE, sMAPE/MASE quando válidos, viés, cobertura de intervalos (por exemplo, 80% e 95%) e estabilidade por empresa/família. Evitar MAPE para séries zero/próximas de zero.
- Comparar com baseline; aprovar ML somente quando houver ganho material e estável fora da amostra, com cobertura e qualidade. **Sem histórico suficiente ou ganho comprovado → baseline transparente ou "previsão indisponível".**
- Exigir magnitude não negativa para grandezas físicas, coerência de unidades e reconciliação de hierarquia. Registrar exceções, séries com faltas, quebras estruturais e mudança de controlador.
- A acurácia dos quatro anos futuros é **incerta** até os anos se realizarem; nunca declarar precisão garantida. Mostrar intervalos crescentes e hipóteses.
- Documentar custos de treinamento, versão de código, hash do conjunto de treinamento, versões de dados, configuração e métricas por `model_run_id`.

## 6. Pipeline offline e publicação leve

Executar localmente no mesmo ambiente/maquinário ETL autorizado (CPU, RAM limitada, disco D:, checkpoints), em pipeline **independente do ETL 2025**, sem depender de GPU:

```text
GDBs históricos por DIST/ano (privados, processamento Python/DuckDB)
    ↓ validação de BASE, DDA, métrica e chave / harmonização temporal
historico_ativos_agregados.parquet (PRIVADO)
    ↓ treino em CPU + comparação com baseline + backtesting temporal
modelo_versionado e relatorio_qa (PRIVADOS)
    ↓ inferência batch para 2026, 2027, 2028, 2029
previsoes_2026_2029.csv + classificacoes.csv + modelo_manifest.json
    ↓ sanitização, auditoria de métricas/licenciamento, publicação aprovada
PostgreSQL (tabelas separadas de previsões) OU JSON/CSV estáticos versionados em CDN
    ↓ APIs read-only (ou assets estáticos) — o frontend NÃO treina modelos
Dashboard "Inteligência Preditiva" — web/Vercel
```

**O site não precisa do modelo treinado** (pickle/joblib, scripts, GDB ou Parquets privados). Ele recebe **as previsões já calculadas e sumarizadas**, intervalos, classificação, metadados e métricas de QA. O modelo pode permanecer versionado fora da infraestrutura pública e ser reexecutado quando houver nova competência homologada.

Se a saída pública agregada couber em arquivos compactos, usar JSON/CSV/Parquet públicos *apenas com agregados aprovados*, preferindo JSON estático no navegador; se crescer e exigir filtros pesados, usar PostgreSQL com endpoints próprios. Não provisionar custo agora.

## 7. Contrato futuro de saída (ainda não implementado)

`modelo_manifest.json`:
- `schema_version`, `model_run_id`, `training_cutoff`, `training_years`, `training_hash`, `model_type`, `fallback_policy`, `metrics_qa`, `published_at`, `prediction_years=[2026,2027,2028,2029]`, `status_qualidade`.

`previsoes_2026_2029.csv`, uma linha por `model_run_id, entidade, metrica, nivel, id_nivel, ano`:
- `ano`, `tipo=previsto`, `valor_previsto`, `limite_inferior_80`, `limite_superior_80`, `limite_inferior_95`, `limite_superior_95`, `unidade`, `metodo`, `status_confianca`, `status_qualidade`, `cenário` (central/conservador/expansivo **somente** se definição formal).
- `nivel`: `dist`, `grupo` ou `brasil`; `id_nivel`: chave correspondente (DIST, grupo econômico verificado ou `BR`).
- Usar limites vazios/N/D se intervalos não calibrados; nunca fabricar intervalos ou probabilidades. Não duplicar somas por grupo; o nível nacional deve reconciliar com o universo de empresas incluídas, com cobertura explícita.

`classificacoes.csv`: `model_run_id,nivel,id_nivel,entidade,metrica,janela_historica,classificacao_trajetoria,classificacao_previsao,criterio,confianca,status_qualidade`.

`historico_publico.csv`: agregados anuais reais **homologados** (dist/grupo/entidade/métrica/ano/valor/unidade/cobertura) somente quando autorizados para publicação; nunca disponibilizar diretamente Parquets/GDBs privados.

`qa_modelos.csv`: `model_run_id,metrica,familia,horizonte,baseline,mae,wape,vies,cobertura_intervalos,amostras_backtest,status_aceite`.

## 8. Interface futura (página / módulo independente)

- **Aba "Inteligência Preditiva"** no portal, após "Panorama", "Ativos" e "Comparador"; marcar claramente como **planejado** até haver dados reais e modelos validados.
- Alternância de série **Histórico oficial** vs **Previsão do modelo** (sólido vs. tracejado), seletor por empresa, grupo e ativo, comparações A/B e perspectiva nacional, com série de 2025 destacada como último realizado.
- Cartões com taxa anual esperada, valor esperado em 2029, variação 2025→2029, classe de trajetória e faixa de incerteza.
- Gráficos de linha e bandas de incerteza; ranking por taxa prevista por entidade/unidade; tabela com 2025, 2026–2029 e export CSV de **previsões identificadas**.
- Ferramenta de cenários **separada** de modelo preditivo; sliders para hipóteses explícitas (taxa de crescimento, choque ou investimento) não serão apresentados como inferência estatística.
- Facetas DDA históricas/futuras só quando o contrato de dimensões por série e a cobertura temporal forem homologados, sem dupla contagem.
- Avisos de baixa confiabilidade, grupos sem fonte e empresas sem histórico; não mascarar lacunas, zero não substitui N/D.

## 9. Roadmap adicional — após dashboard 2025

- **M6 — Inventário 2022–2025 comparável:** verificar a disponibilidade das competências **2022, 2023 e 2024** para as empresas que tenham 2025; confirmar mudança de modelo de 2021/2022, cobertura, DDA/layout e grupos temporais; obter aprovação para processar. Caso 2022 não seja harmonizável, usar **2023–2025** para análise descritiva e cenários, registrando que previsão ML de quatro anos permanece de baixa sustentação.
- **M7 — ETL histórico separado:** gerar séries anuais auditadas por empresa, entidade e métrica; contratos/QA e análises exploratórias.
- **M8 — Baselines e modelos:** backtesting temporal, ML quando justificável, classificação de tendências, reconciliação hierárquica e intervalos.
- **M9 — Publicação preditiva:** pacote público sumarizado + API/tabelas (ou JSON estático) + aba preditiva, comparação futura e documentação.
- **M10 — Operação:** re-treino anual ao incorporar nova BDGD, monitoramento da precisão, drift, mudanças societárias e novas versões de métrica.

**Condição de início:** homologação e publicação do dashboard 2025; planejamento técnico pode ser revisado antes. **Não executar coleta histórica ou treinamento automaticamente nesta fase**, a menos que o responsável autorize separadamente.

## 10. Segurança, custo e licenciamento

- Mesmo pipeline offline sem GPU, sem expor dados brutos, chaves individuais, identificadores de UC ou modelos privados no browser.
- Verificar licenças ANEEL e tratamento temporal/histórico; qualquer redistribuição ou agregação pública passa por QA e aprovação.
- Nenhum serviço pago ou deploy é necessário para a etapa de desenho. Futuramente comparar publicação estática vs. banco.
- Forecast não é dado regulatório nem previsão oficial da ANEEL; divulgar metodologia, fonte e limitações.

**Autoria da aplicação:** Arthur Henrique Lima — Núcleo de Dados da BDGD.
