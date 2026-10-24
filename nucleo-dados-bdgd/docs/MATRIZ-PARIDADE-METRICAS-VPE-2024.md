# Matriz de paridade — métricas do portal × BI VPE 2024

**Estado:** matriz de referência **aguardando o BI**. O arquivo PBIX do BI VPE 2024 não está disponível no ambiente de processamento (ausência confirmada pelo proprietário em 23/10/2026). Conforme `PROMPT-CLAUDE-EXECUCAO-R2-ATE-PREVIEW.md`, isso **não bloqueia** a R2: cada indicador abaixo foi construído e auditado diretamente na BDGD 2025 (`QA_BDGD_2025`), e a paridade com o BI fica explicitamente pendente (`PARIDADE_BI_VPE = NAO_AVALIADA_PBIX_AUSENTE`). Nenhum nome de medida DAX, etapa Power Query ou filtro interno do BI é citado ou presumido.

Fontes normativas: Manual BDGD (Rev. 5, campos e tipos), MCPSE (Res. ANEEL 674/2015, Tabela I — TUC e A1), DDA M10 (domínios), IBGE (códigos de município). Dados: GDBs ANEEL com `DATA_BASE = 2025-12-31`, 99/99 distribuidoras elegíveis. Pacote: `output-publicavel/2025-12-31` (release `bdgd-2025-12-31-v1-99d-2f6fa3879a`).

## Indicadores exibidos

| metric_id | Conceito | Entidade / junção | TUC e atributos | Definição BDGD independente | Unidade | Regra ETL | QA_BDGD_2025 | PARIDADE_BI_VPE |
|---|---|---|---|---|---|---|---|---|
| uc | Consumidores | UCBT ∪ UCMT ∪ UCAT por DIST | — | Códigos de consumidor distintos (regra UC v2) unidos entre as três camadas | itens | `COUNT(DISTINCT COD_ID)` por DIST na união; soma entre DIST | Homologada com ressalvas: N/D nas DIST com UC inválida pela regra v2 (22 de 297 tabelas UC) | NAO_AVALIADA_PBIX_AUSENTE |
| ssdmt / ssdbt / ssdat | Redes | SSDMT, SSDBT, SSDAT | — | Comprimento declarado dos segmentos | km | `SUM(COMP)/1000` em DECIMAL(38,6) | SSDMT e SSDBT homologadas; SSDAT com ressalvas (COMP nulo ou zero em parte dos segmentos); reconciliação exata com leitura independente do GDB | NAO_AVALIADA_PBIX_AUSENTE |
| ramlig | Redes | RAMLIG | — | Comprimento declarado dos ramais | km | `SUM(COMP)/1000` | Homologada com ressalvas (COMP nulo ou zero em parte dos ramais) | NAO_AVALIADA_PBIX_AUSENTE |
| untrmt | Transformadores | UNTRMT | — | Instalações transformadoras MT/BT | itens | `COUNT(*)` | Homologada | NAO_AVALIADA_PBIX_AUSENTE |
| eqtrmt | Transformadores | EQTRMT (→ UNTRMT via `UNI_TR_MT`) | TUC 565/570, A1 | Potência nominal dos equipamentos | kVA | `SUM(TPOTAPRT[POT_NOM])` (DDA) | Homologada com ressalvas (alertas de divergência UN×EQ preservados) | NAO_AVALIADA_PBIX_AUSENTE |
| untrat / eqtrat | Transformadores AT | UNTRAT, EQTRAT (→ UNTRAT via `UNI_TR_AT`) | TUC 570, A1 | Instalações e potência AT | itens / kVA | `COUNT(*)`; `POT_NOM × 1000` (UNTRAT, MVA) e DDA (EQTRAT) | Quantidade homologada; potência com ressalvas (UNTRAT N/D em 2 DIST) | NAO_AVALIADA_PBIX_AUSENTE |
| eqse | Seccionamento | EQSE (→ UNSEAT/UNSEMT/UNSEBT via `UN_SE`) | TUC 160, 210, 345 | Equipamentos de seccionamento | itens | `COUNT(*)` | Homologada | NAO_AVALIADA_PBIX_AUSENTE |
| eqre | Regulação | EQRE (→ UNREAT/UNREMT via `UN_RE`) | TUC 340 | Reguladores de tensão | itens | `COUNT(*)` | Homologada | NAO_AVALIADA_PBIX_AUSENTE |
| eqcr | Compensação | EQCR (→ UNCR* via `UN_CR`) | TUC 125 | Capacitores e compensadores | itens | `COUNT(*)` | Homologada | NAO_AVALIADA_PBIX_AUSENTE |
| eqme, ponnot, pip, sub, ctmt, ctat, ugbt, ugmt | Diversos | camada única | TUC (EQME, PONNOT) | Contagem de registros da camada | itens | `COUNT(*)` | Homologada | NAO_AVALIADA_PBIX_AUSENTE |
| potência UG* | Geração | UGBT/UGMT/UGAT | — | POT_INST sem unidade/semântica comprovada | — | não publicada | **Não homologada (N/D)**: valores > 75 kW em BT e sistemas SIGFI | NAO_AVALIADA_PBIX_AUSENTE |

## Evidência TUC e vínculo equipamento → instalação (nacional, 99 DIST)

Lido dos campos `TUC` e do campo vinculado de cada EQ*; contagem de instalações distintas por chave de vínculo existente no destino (`indicadores_vinculos_tuc.csv`).

| Entidade | TUC (MCPSE) | Equipamentos | Com vínculo válido | Instalações distintas | DIST |
|---|---|---:|---:|---:|---:|
| EQTRMT | 565 Transformador de distribuição | 6.103.972 | 6.096.956 | 6.010.967 | 99 |
| EQTRMT | 570 Transformador de força | 2.414 | 2.405 | 2.401 | 45 |
| EQTRAT | 570 Transformador de força | 7.245 | 7.245 | 7.210 | 62 |
| EQSE | 160 Chave | 5.268.771 | 5.268.368 | 2.543.002 | 99 |
| EQSE | 345 Religador | 207.693 | 207.681 | 185.666 | 99 |
| EQSE | 210 Disjuntor | 30.918 | 30.864 | 30.589 | 63 |
| EQRE | 340 Regulador de tensão | 49.535 | 49.509 | 17.732 | 91 |
| EQCR | 125 Banco de capacitores paralelo | 42.844 | 42.544 | 29.162 | 98 |

Leitura: um equipamento não é uma instalação (ex.: chaves são montadas em conjuntos; 5,27 mi de equipamentos ocupam 2,54 mi de instalações). O portal publica as duas grandezas separadas e nunca as soma.

Códigos de TUC sem correspondência na Tabela I do MCPSE (por exemplo `000`) aparecem como “Código … (sem correspondência no MCPSE)”, sem significado atribuído. A auditoria adicional desses códigos foi **retirada do escopo atual** pelo proprietário.

## Pendências

- Paridade com o BI VPE 2024: aguardar PBIX ou extração fidedigna das medidas; preencher a coluna `PARIDADE_BI_VPE` por indicador.
- Atributos A2–A6 do TUC: o MCPSE local descreve apenas nomes de atributos (sem domínio codificado); não há cubo publicado.
