# IASC ANEEL — integração sob chave verificada

**Fonte oficial**: https://dadosabertos.aneel.gov.br/dataset/indice-aneel-de-satisfacao-do-consumidor-iasc (dados atualizados em 26/06/2026, publicação anual por distribuidora, desde 2006). Recurso CSV oficial: https://dadosabertos.aneel.gov.br/dataset/f216da23-4b7e-4bbe-9833-06905331a827/resource/7abd3a47-1e1a-4a33-933b-48d658a6f912/download/indice-aneel-satisfacao-consumidor.csv.

Colunas verificadas na documentação da ANEEL: `NumAno`, `SigAgente`, `NumCNPJ`, `MdaIndicadorSatisfacao` e demais componentes da pesquisa.

A base BDGD 2025 publicada em `distribuidoras.csv` identifica distribuidoras pelo `dist`, mas não traz o CNPJ em coluna explícita. Portanto, **não existe join confiável direto automático**. Nome, sigla e grupo não são chave jurídica suficiente; não associar `SigAgente` por similaridade textual ou usar valores de empresas predecessoras fora da vigência.

Mecanismo implementado em `etl/iasc/prepare_iasc.py`: aceitar CSV ANEEL baixado localmente + `depara.csv` curado com exatamente `dist,ano,cnpj,status,fonte_vinculo`. Publicar somente quando o par `(DIST,ano)` tiver um CNPJ comprovado e exclusividade no próprio ano, a fonte oficial tiver uma única observação `(CNPJ,ano)` e a nota for numérica entre 0 e 100. Rejeitar duplicidade, fonte de vínculo ausente ou qualquer incerteza. A saída contém apenas agregados anuais e URLs verificáveis; nunca divulga o de-para com CNPJ na aplicação. A correspondência deve registrar mudanças de titularidade por ano.

**Atenção semântica**: `MdaIndicadorSatisfacao` é a variável de satisfação reportada no conjunto IASC. Não a chamar de escore composto geral sem prova de equivalência metodológica; a origem inclui várias dimensões (qualidade, satisfação, confiança, fidelidade, valor). Comparações longitudinais exigem testar mudanças no questionário/modelo. Nunca misturar dados IASC com a contagem de ativos BDGD.

Execução futura, após curadoria de `depara.csv`:

```bash
python nucleo-dados-bdgd/etl/iasc/prepare_iasc.py --iasc indice-aneel-satisfacao-consumidor.csv --depara depara_auditado.csv --ano 2025 --saida resultado_iasc_2025.json
python -m unittest discover -s nucleo-dados-bdgd/etl/iasc -p 'test_*.py'
```

Nenhum resultado por DIST foi exibido no Panorama nesta fase: correspondências ainda não auditadas. O pipeline é executável e está pronto para consumir a chave validada, mas não possui CNPJs inventados.
