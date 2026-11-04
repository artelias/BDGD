# 04 — Metodologia: modelos, cenários, variáveis e reconciliação

A referência completa é `motor_v2/nacional/METODOLOGIA.md`, com os detalhes de fórmulas, triagem e elegibilidade. Este documento resume o que o produto mostra e como interpretar.

## Modelo e cenário são coisas diferentes

- **Moderado** é a trajetória do modelo escolhido para a série.
- **Conservador** e **Agressivo** deslocam o crescimento log1p anual do Moderado para o **menor** e o **maior** crescimento observado nas transições comparáveis da própria série (2022–2025), depois da triagem de saltos atípicos. Isso só acontece quando esses crescimentos são mais extremos que o do Moderado.
- Se não forem mais extremos, os três coincidem. A **degeneração** é registrada (`cenarios_meta.degenerados`) e mostrada na interface. Nunca se criam diferenças artificiais.
- Os valores têm piso zero, e o piso é registrado. Vale sempre `Conservador ≤ Moderado ≤ Agressivo`.
- **Os cenários não são intervalos de confiança.** A incerteza histórica entra só pela amplitude das transições observadas.

## Seleção do modelo moderado

Candidatos:
- baselines: persistência, deriva e CAGR;
- ML: OLS, Ridge, Elastic Net, Poisson (só contagens), Random Forest e HistGradientBoosting, em dois escopos de pool:
  - mesmo **grupo econômico**;
  - **10 DIST comparáveis**, as mais próximas por log do estoque e log dos consumidores.

Avaliação: origem móvel em **2023 e 2024**, horizonte de 1 ano, mesmos pontos para todos os candidatos. Subconjunto de features e hiperparâmetros escolhidos numa origem interna, sem olhar o teste.

Regra de escolha: um ML só vence se for **pelo menos 5% melhor** que o melhor baseline no escore robusto **e** não for pior em nenhuma origem. Caso contrário vale o baseline por política (`PROJETADA_BASELINE`). Não se presume que ML supere baseline: 1.602 séries ficaram em baseline e 995 em modelo escolhido, ML ou tendência.

Equações:
- persistência: `y(T+h) = y(T)`;
- deriva: `y(T+h) = y(T) + h·inclinação`;
- CAGR: `y(T+h) = y(T)·g^h`;
- ML: `y(T+h) = expm1(log1p y(T) + h·d)`, com `d` o passo de um ano previsto pelo modelo.

O passo é mantido constante porque **não há covariáveis futuras**, e essa hipótese matemática é documentada.

## Coeficientes e explicabilidade

- **Lineares** (OLS, Ridge, Elastic Net, Poisson no log da média): `d = b0 + Σ bᵢ·xᵢ`. A execução nacional não persistiu os coeficientes. Eles foram **recuperados por reajuste determinístico** no mesmo pool e na mesma seleção, e são publicados só quando o reajuste reproduz exatamente a trajetória armazenada: **214 de 214**.
- **Random Forest e HistGradientBoosting** não têm equação linear nem coeficientes. A interface descreve o mecanismo e as features, e marca N/D.
- **Baselines** mostram a fórmula; não há coeficiente estimado.

## Variáveis explicativas

**Usadas nas séries por distribuidora:**
- log do estoque em t−1;
- log dos consumidores em t−1;
- log dos km de rede MT em t−1;
- crescimento anterior (t−2 → t−1).

**Registradas, mas não usadas nesta execução:**
- PIB e população municipais do IBGE;
- DEC e FEC;
- clientes por transformador, kVA por consumidor;
- densidade e área urbana/rural.

Essas entram no motor de cenários público do PR #17 e no nível territorial; no nível B não entram.

**Recusadas ou ausentes:**
- EPE e IPEA não estão integrados;
- `recent_connection_share` (DAT_CON) continua desligada até uma auditoria por DIST separar ligação nova de alteração cadastral.

## Reconciliação física

- `Consumidores = UCBT + complemento`, com complemento ≥ 0. A fonte canônica interna é `consumidores_reconciliado`. Resultado: 1.545 células, 0 violações e 385 de 385 fechamentos históricos. A previsão independente de Consumidores fica só como comparação.
- Erro ponta a ponta do caminho reconciliado: WAPE de 2,59%, contra 2,78% do B independente (p = 0,67, estatisticamente indistinguíveis).
- Em cada série: 15 combinações únicas, contagens inteiras e não negativas, unidades separadas e sem conversão kVA ↔ kW ↔ kVAr.
- Grandezas não aditivas (potência própria × passante de reguladores) nunca viram total nacional.

## Validação: o que existe e o que não existe

- Só **2 origens** independentes (a regra de homologação exige 3) e **nenhum point-in-time** elegível (vintage não comprovada). **Zero modelos cientificamente homologados.**
- **Horizontes acima de 1 ano não são validados.** 2027–2030 são extrapolações com fórmula explícita.
- Os textos públicos dizem "comparação retrospectiva", não validação. O status do motor público passou a `simulacao_comparada_retrospectivamente`.

## Perímetros e pontes

- **Celesc 2023:** a ponte experimental continua pendente de homologação humana.
- **EPB/EBO 2023:** a transição não é comparável (sucessão), e a EBO não é tratada como empresa ativa.
- **EMR/ENF 2022:** o perímetro já está contido na EMR, e a ENF não é somada.
- **`INTERVALO_NAO_ANUAL`** é uma ressalva, não uma exclusão: a data-base de 31/12 está correta e só a data inicial dos fluxos difere.
