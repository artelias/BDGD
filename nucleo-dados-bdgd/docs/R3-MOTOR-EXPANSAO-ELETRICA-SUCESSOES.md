# Sucessões Energisa — séries comparáveis para previsão
Data de verificação: 2026-10-23. **Regras de ponte propostas; dados GDB ainda não auditados.**

## Eventos documentados
- **EMG + ENF -> EMR**: incorporação da Energisa Nova Friburgo pela Energisa Minas Gerais em **30/11/2022**; alteração da denominação da incorporadora para Energisa Minas Rio. Fontes: https://www.abrasca.org.br/noticias/sia-cia-1627-energisa-reorganizacao-societaria-de-controladas e https://www.energisa.com.br/sites/energisa/files/2025-02/energisa-relatorio-anual-2022.pdf_0.pdf
- **EPB + EBO -> EPB**: incorporação da Energisa Borborema pela Energisa Paraíba em **30/04/2023**. Fonte societária primária: https://auniao.pb.gov.br/servicos/editais-balancos-e-atas-na-integra/energisa-borborema-27-05-23-cdepc.pdf . Regulação: REA ANEEL 12.687/2022 e quinto termo aditivo em 09/08/2023, https://www2.aneel.gov.br/cedoc/areh20233250_1.pdf
- Relações com investidores Energisa declara **2022 EMG+ENF** para comparação e **EPB+EBO consolidados a partir do 2T23** em indicadores empresariais, o que não prova como os arquivos BDGD anuais foram gerados: https://api.mziq.com/mzfilemanager/v2/d/60f49a2d-bd8c-4fd9-95ab-bdf833097a83/dc350561-9644-95fc-2c31-21acf9bf09f9?origin=1

## Contrato de transformação — nunca alterar os dados brutos
Criar duas visões: `original_publicado` e `perimetro_comparavel_2025`.
**EPB**: 2022 candidata = EPB_2022 + EBO_2022 **somente se** ambos os GDBs representam áreas disjuntas e mesma métrica. 2023 = verificar se EPB_2023 já absorve EBO e se existe EBO_2023 separado; proibir soma duplicada. 2024–2025 = EPB conforme publicado e auditado.
**EMR**: 2022 = verificar se arquivo EMR/EMG de 31/12/2022 já incorpora ENF; somar EMG+ENF **somente se** disjuntos. 2023–2025 = EMR conforme publicado e auditado.
**Chave de ponte**: `evento_id, predecessor_dist, sucessor_dist, data_efetiva, competencia, conceito, metrica, regra_agregacao, evidencia_disjuncao, estado_validacao`.
Usar **DIST real obtido do catálogo ANEEL**, não inferir por nome ou supor COD_ID único. Não fixar DIST de EBO/ENF/EMG sem consultar GDB e cadastro regulatório.
Somar contagens, km e potências **somente se aditivas** e sem duplicidade. Para taxas, razões, médias, DEC/FEC, percentuais e indicadores normalizados: reconstruir numeradores e denominadores com regras específicas; não somar diretamente.
Preservar origem, hash, ano, cobertura, GDBs componentes, totais antes/depois e estado `pendente|validado|bloqueado`. Se não comprovada a comparabilidade, **bloquear previsão e exibir N/D**, sem preencher lacunas ou forçar crescimento.
Testes: não dupla contagem, mesma métrica e unidade, reconciliação das predecessoras, ausência de salto cadastral confundido com crescimento físico, série 2022–2025 em perímetro constante, conferência 2023 e 2022 no ano de transição.
