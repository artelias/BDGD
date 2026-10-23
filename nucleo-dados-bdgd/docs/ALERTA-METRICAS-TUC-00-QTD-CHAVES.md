# ALERTA PRIORITÁRIO — TUC 0/00/000/vazio, TIP_UNID e semântica QTD (23/10/2026)

**Objetivo:** impedir subcontagem de ativos no Núcleo de Dados da BDGD, especialmente chaves, sem bloquear o Claude e sem extrapolar regras de um script antigo para qualquer entidade.

**Origem de evidência:** script Python `pipeline_previsao_bdgd_v2.py` anteriormente fornecido pelo proprietário no arquivo "Texto colado(21).txt", que lê uma tabela consolidada `ORDINÁRIA.txt` e calcula 25 métricas. **Não é uma extração do PBIX**; a presença da regra no PBIX ou sua vigência para todas as distribuidoras ainda **não foi verificada**. Não importar seus modelos preditivos nem treinar ML. Usar **somente** a lógica descritiva como hipótese operacional para auditar contra os dados originais, Manual BDGD/MCPSE e BI quando disponível.

## Evidência específica — chaves (não generalizar a todos os ativos)

O script antigo contém as seguintes definições semânticas:

```python
TIP_UNID_CHAVE = {
  15,16,17,18,19,20,21,22,23,24,25,26,27,28,
  33,34,47,48,50,35,36,45,46,57
}
m_chave_uc  = (TUC == "160")
m_chave_com = TUC.isin({"0","00","000",""}) & TIP_UNID.isin(TIP_UNID_CHAVE)

CHAVE_UC     = SUM(QTD WHERE m_chave_uc)
CHAVE_COM_UC = SUM(QTD WHERE m_chave_uc OR m_chave_com)
```

Assim, **`CHAVE(COM+UC)` pode ser maior que `CHAVE(UC)`**, apesar de as categorias COM não terem `TUC=160`. Filtrar apenas a TUC 160 **subconta** a definição COM+UC. Não confundir `TUC = "00"` com `A1="00"`, e não concluir que **todos** os valores TUC zero/vazios pertencem a chaves: a inclusão é **condicionada** a `TIP_UNID` pertinente e outras regras a validar.

### Critério crítico do universo e da unidade

- O script começa com **`PROPRIEDADE="PD"`** e, excepcionalmente, ajusta `PROPRIEDADE="PD"` em `UCBT/UCMT/UCAT` antes do filtro para não excluir consumidores. Essa é uma **regra específica da fonte intermediária** e não deve ser copiada sem auditar o universo/publicação da BDGD nacional. A seção "ativos totais" do portal **não** pode ser limitada inadvertidamente a propriedade PD sem explicitar esse recorte.
- A função usada é `SUM(QTD)`, **não `COUNT(*)`** e não automaticamente `COUNT(DISTINCT COD_ID)`. Se `ORDINÁRIA.txt` representa agregados por `DIST/EMPRESA/ANO/TUC/A1/TIP_UNID`, o número de linhas do consolidado não representa quantidade física. Confirmar a origem e semântica de `QTD` e reconstruí-la do GDB/Parquet quando apropriado. Nunca fazer `SUM(QTD)` sem coluna QTD confiável, nem reutilizar campo inexistente inventado.
- O script calcula `255 - POSTE = SUM(QTD WHERE TUC="255" AND A1="01")`; `255 - TORRE` usa `A1="02"`; `295 - MEDIDOR` usa TUC 295; `565`, `570`, `575` são recortes próprios de transformadores. **Nele não há regra observada que inclua TUC zero/vazio para esses indicadores**. Auditar exceções por conceito, jamais por `TUC=00` indiscriminado.
- `190 - CONDUTOR` e `KM REDE` no script somam `SOMA_REDE_KM` de `SSDBT/SSDMT/SSDAT`, outra classe/unidade não substituível por contagem de linhas.

## Instruções executáveis de auditoria para Claude

1. **Continuar ETL 2025 e revisão R2 sem bloquear PBIX.** O proprietário confirmou ausência de PBIX no PC do Claude. Há regras operacionais já documentadas: usá-las para montar *casos de teste e hipóteses*, não como prova universal de norma.
2. Produzir `docs/AUDITORIA-TUC-00-TIP_UNID-QTD-2025.md` com inventário por `DIST, ENTIDADE, TUC, A1, TIP_UNID, PROPRIEDADE, DATA_BASE`, quando presentes e legalmente exportáveis em agregado: `linhas`, `cod_id_distintos`, `qtd_aplicavel`, `campo_ausente`, `classificados`, `0/00/000/vazio`, `sem_classificacao`. Auditar tipagem/trim/zeros à esquerda e diferença entre ausência de campo e campo zero.
3. **Especialmente para chaves**, comparar `CHAVE(UC)` e `CHAVE(COM+UC)` pela regra operacional do script; verificar se `TIP_UNID` existe em GDB 2025 ou só em uma tabela intermediária, se é derivável de combinação de campos, e se sua lista de códigos tem correspondência normativa e vigência 2025. Se não for reproduzível no GDB com evidência, não publicar `COM+UC` como homologada; documentar cobertura e causa, sem esconder a contagem TUC 160 que seja legitimamente validada.
4. Para postes, medidores, transformadores e demais métricas, verificar **individualmente** se existem classes legítimas fora da TUC explícita. Exibir `Total de registros da entidade`, `Quantidade patrimonial classificada`, `Sem classificação / não categorizável` conforme aplicável, com regra, universo e unidade próprios. Não somar populações EQ+UN sem joins/deduplicação.
5. Para cada indicador publicar diferença e reconciliador `total_validado = parcelas_disjuntas + sem_classificacao + demais_categorias_elegiveis` **somente se universo/partições realmente disjuntos**. Não forçar fechamento contábil se há sobreposições e não inventar categoria residual.
6. Testar controle negativo: um registro/agrupado `TUC="00"`, `TIP_UNID` **fora** da lista não entra como chave; um `TUC="00"` com `TIP_UNID` **dentro** e `QTD=5` deve contribuir com **5** para COM+UC, não 1 (se esse esquema intermediário for legitimamente utilizado); `TUC="160"`, `QTD=3` contribui 3 para ambos. Testar `0`, `00`, `000`, vazio, `null`, zero à esquerda e string/número com significado explícito.
7. Incluir na matriz de paridade BI VPE o status `referencia_operacional_script_anterior`, enquanto `paridade_PBIX=NAO_AVALIADA_PBIX_AUSENTE`; nenhuma medida DAX alegada como extraída do PBIX. Handoff deve incluir métricas confirmadas, divergências, inconclusões e implicações de cobertura.
8. **Não repassar nem versionar o arquivo bruto do usuário no repositório público.** Documentar apenas regras sintéticas e referências aos metadados com origem explicada.

### Interpretação para UX

- Mostrar `Chaves — TUC 160` como recorte classificado se validado.
- Mostrar `Chaves — UC + outras classes elegíveis` **somente quando a regra COM/TIP_UNID for implementável e homologada**; tooltip explicará diferença para a TUC pura.
- `TUC não informada / 00` não significa zero equipamento e não entra automaticamente em qualquer família.
- Aviso de cobertura e `N/D` onde necessário. Comparador e benchmarking só usam indicadores equivalentes entre todos grupos/DIST comparados.

**Limite:** esta revisão é de regras de dados e qualidade, sem ML/previsão e sem publicação de produção pelo Claude.
