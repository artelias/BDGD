# Harmonização de sucessão de distribuidoras — BDGD 2022–2025

**Decisão de escopo:** usar SOMENTE as competências **31/12/2022, 31/12/2023, 31/12/2024 e 31/12/2025** no estudo histórico/preditivo. **Não inventariar/baixar/processar 2020 nem 2021** nesta etapa. A necessidade de recompor empresas sucessoras **não autoriza** adicionar anos anteriores.

## Por que isto é necessário

Uma concessão de 2025 pode incluir ativos e áreas que antes estavam sob mais de uma distribuidora, por incorporações, agrupamentos de concessões, transferências parciais, cisões ou mudança de `DIST`/razão social. Uma série por `DIST` bruto pareceria crescer/subtrair ativos devido a alteração do **perímetro reportado**, não por crescimento orgânico.

A análise histórica terá **duas visões lado a lado**:
1. **PUBLICAÇÃO ORIGINAL:** valor de cada `DIST` e ano tal qual publicado, com provenance/hash, sem reatribuir números retroativamente.
2. **PERÍMETRO COMPARÁVEL DE REFERÊNCIA 2025:** agrega predecessoras e transferências válidas para reconstruir o território/perímetro da sucessora vigente em 2025, com regra explícita de cada ano/entidade/métrica, fontes e QA. Trata-se de **série analítica derivada**, não de publicação histórica original da ANEEL.

O nome de empresa e o grupo controlador **não são prova suficiente** para fusão ou aditividade. Grupo econômico é dimensão de participação; sucessão de concessão é outra relação.

## Caso de estudo confirmado: Energisa Borborema (EBO) → Energisa Paraíba (EPB)

- A ANEEL autorizou o agrupamento pelo ato **Resolução Autorizativa nº 12.687, de 13/09/2022**.
- A incorporação da EBO pela EPB foi aprovada/efetivada em **30/04/2023**, conforme ata da EBO e comunicação da Energisa de resultado do 2º trimestre de 2023 (a partir de 2T23 os números financeiros já consolidados).
- A ANEEL também descreveu que a EPB passou a abranger os contratos de concessão **019/2001-ANEEL (EPB)** e **008/2000-ANEEL (EBO)**; termo aditivo de 09/08/2023.
- **NÃO inventar códigos DIST:** localizar EBO e EPB pelo catálogo ArcGIS/BASE de cada competência e registrar os códigos reais em documento de evidência; não presumir que sigla antiga continue presente em 2023.

Fontes verificadas:
- Resultados EPB 2T23: https://api.mziq.com/mzfilemanager/v2/d/dda7929f-3116-4655-b9e4-0ca05481e464/0d2852f1-19b6-2f70-c389-cfc0d998b226?origin=1
- Ata de incorporação EBO (publicação em diário oficial estadual): https://auniao.pb.gov.br/servicos/editais-balancos-e-atas-na-integra/energisa-borborema-27-05-23-cdepc.pdf
- Processo tarifário ANEEL 2023 com referência ao agrupamento: https://www2.aneel.gov.br/cedoc/areh20233250_1.pdf

**Hipótese de auditoria a verificar nos próprios GDBs:**
- Ano-base **2022:** EPB original e EBO original podem coexistir; se confirmadas áreas/entidades **disjuntas** e métodos iguais, visão comparável EPB(2025) em 2022 = EPB(2022) + EBO(2022) **por métrica aditiva**. Sem confirmação, não publicar soma.
- Ano-base **2023:** após incorporação em abril, a EPB **pode** já refletir ambas as áreas no GDB de 31/12/2023. Examinar BASE/ARAT/CONJ e cobertura por ativos; se refletir tudo, usar EPB 2023 **uma vez**, não somar EBO arquivada/duplicada. Se parcial, registrar lacuna e necessidade de regra específica, sem reconstrução automática.
- **2024–2025:** analisar sucessora EPB conforme publicação oficial, verificando perímetro de referência, cobertura e alterações remanescentes; não supor identidade perfeita sem QA.

Este caso é uma **regra de mapeamento candidata, ainda condicionada a evidência de cada GDB**. O evento societário confirmado não prova, isoladamente, que somar quantitativos de todos os registros e atributos seja válido.

## Entregáveis adicionais Codex para 2022–2024

Gerar ao lado dos inventários e fatos históricos:

### `eventos_sucessao_distribuidoras.csv`

`evento_id,tipo_evento,data_autorizacao,data_efetivacao,fonte_oficial,confianca,observacao`.

Eventos `incorporacao`, `agrupamento_concessao`, `cisao`, `transferencia_parcial`, `mudanca_dist` devem ser distinguíveis. Datas de autorização não são necessariamente datas de efetivação.

### `ponte_perimetro_2025.csv`

`ano_base,dist_origem,dist_destino_2025,evento_id,escopo_territorial,criterio_inclusao,cobertura,status_qualidade,fonte_evidencia`.

Relação por ano com eventuais múltiplos predecessores por destino, inclusive casos parciais. Para transferência parcial é necessário delimitar área/ativos com vínculo espacial ou circuito; **não agregar 100% do DIST de origem em caso de transferência apenas parcial**.

### `regras_comparabilidade_historica.csv`

`dist_destino_2025,ano_base,entidade,metrica,unidade,versao_metrica,metodo_consolidacao,origens_incluidas,prova_disjuncao,status_qualidade,motivo_bloqueio`.

A regra varia conforme entidade e métrica: `SUM` apenas para aditivos e disjuntos; contagem distinta exige estratégia de união de chaves com origem/competência, enquanto valores ambíguos ficam `N/D`, nunca 0. Não somar potência UN* e EQ* do mesmo objeto nem unidades kVA/MVA não convertidas.

### `serie_historica_perimetro_2025.csv`

`dist_destino_2025,ano_base,entidade,metrica,unidade,valor,perimetro_referencia,modelo,origens_incluidas,status_qualidade,fonte_serie`.

`perimetro_referencia=2025`, `modelo=consolidado_comparavel`. O arquivo é **derivado**, distinto de `historico_ativos_agregados_2022_2024.csv` (origem histórica).

### `qa_sucessao.csv`

`evento_id,ano_base,dist_destino_2025,entidade,metrica,origens_esperadas,origens_encontradas,diferenca,prova_sem_duplicidade,validacao_arat,status`.

## Procedimento de análise

1. Inventariar para cada ano 2022/23/24 (e fazer join de 2025 apenas quando sua carga estiver homologada): `DIST`, nome, contratos de concessão e eventuais aliases; rastrear extinções/incorporações.
2. Consultar atos oficiais ANEEL e fontes societárias, documentar autorização versus efetivação e se houve mudança territorial ou apenas razão social.
3. Conferir `BASE`, `ARAT`, `CONJ`, vínculos territoriais e métricas de cada ano; evitar atribuir automaticamente consolidação às empresas do mesmo grupo.
4. Calcular série **original** por empresa/ano sem mutação do bruto.
5. Para `perimetro_2025`, consolidar predecessores **somente após** documentar participação no perímetro atual, compatibilidade métrica e ausência de sobreposição/duplicação; nenhuma mesma parte pode entrar duas vezes no agregado de um ano.
6. Marcar separadamente `mudanca_perimetro` (efeito reorganização), `crescimento_organico` e `nao_identificavel`. Não prometer decomposição se só houver totais e não houver suporte para classificar ativos.
7. Repetir para outros grupos/distribuidoras; não limitar à EPB/EBO.
8. **Treino preditivo futuro:** usar apenas séries comparáveis, com quebra estrutural marcada ou excluída. Não tratar a incorporação como crescimento orgânico. A curadoria dos dados históricos não inicia automaticamente treinamento.

## Controles de QA

- Garantir exatamente os quatro exercícios elegíveis, **2022–2025**; a execução Codex obtém 2022–2024 e não modifica/rebaixa 2025.
- Evitar colisões de `COD_ID` entre DISTs: no staging, chave técnica `(DATA_BASE,DIST_ORIGEM,ENTIDADE,COD_ID)`. Isso não resolve conflitos da mesma chave ou chaves de ativos renomeados na sucessora; investigar separadamente.
- Contagens `DISTINCT` por categoria e somas entre predecessores requerem prova de partições disjuntas/identidade canônica. Sem prova, **N/D**.
- Não somar ARAT como área sem tratar sobreposição; geometria deve ser a união topológica validada.
- Distinção obrigatória entre dado público oficial original e métrica derivada reconstruída para comparabilidade.
- Dados de 2020 e 2021 não serão coletados, nem usados em ML, nem incorporados ao produto nessa fase.

**Status:** escopo técnico e caso histórico confirmados em fonte externa, implementação e comparação dos GDBs ainda **pendentes**. Produzir relatório de evidência antes de classificar qualquer consolidação como `aprovado`.
