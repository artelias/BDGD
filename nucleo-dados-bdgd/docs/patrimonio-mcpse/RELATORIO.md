# Dicionário patrimonial MCPSE × BDGD — entrega documental parcial

**Base PR #11 (`c808880`), sem merge/deploy.** A conclusão normativa universal está bloqueada por dois insumos: PDF integral da Revisão 3 e registros dos Parquets EQ/UN existentes no disco D: da máquina de processamento. Não se apresenta a Revisão 2 como Revisão 3, nem inventário de arquivos como leitura de registros. Nenhum target homologado foi alterado.

## Fontes efetivamente lidas

- MCPSE `20220204_MCPSE_texto_definitivo_resol_674_2015.pdf`, 219 páginas, **Revisão 2 identificada na capa e nos cabeçalhos**. Tabela I pp.173–188, auxiliares pp.189–210. SHA-256 e URL oficial em `data/dicionario.json`. Cópia fornecida no acervo do projeto; não se usa o nome do arquivo para presumir edição.
- Endereço oficial da Revisão 3 localizado: https://www2.aneel.gov.br/cedoc/aren20221020_2_6.pdf. A indexação identifica REN 1.020/2022 e revisão de conceito do glossário; download integral retornou HTTP 403. O portal ANEEL também aponta para uma cópia com nome `20220204_MCPSE_texto_definitivo_resol_674_2015.pdf`, que não prova ser a revisão vigente. Nenhuma equivalência normativa 2022–2025 foi presumida com base apenas no nome/link ou no motivo resumido de revisão.
- `BDGD_DDA_CATALOG_M10.json`, versão 1.1, autoridade declarada `INTERNAL_DDA_MIRROR`, 43 tabelas/1.369 valores. Serve para confrontar codificações, não certifica vigência de cada ano. É preservada essa autoridade, sem renomeá-la como fonte normativa oficial.
- `BDGD_HANDOFF_CHATGPT.zip`, cópia de transferência de 25/10/2026: inventários e esquemas dos Parquets, mas **nenhum Parquet com registros**, conforme README e inspeção do ZIP. Lista 16.899 arquivos, 104 DIST e 43 entidades em 2022–2025; isso inclui publicações distintas e não é um universo de observações independentes nem seleção formal de republicações.
- Cubos conjuntos publicados de 2025: 27 códigos de TUC observados nos conceitos com TUC/A1. Há 2.187 grupos DIST×conceito×TUC×A1. São grupos de cubos existentes, não equipamentos individuais nem modelos treinados. Não há A2–A6 nesses cubos conjuntos; seus filtros não são aplicados ficticiamente às quantidades.

A ferramenta XLSM de apoio e o seed JSON do acervo foram localizados e inspecionados como auxiliares; macros não foram executadas e nenhum preenchimento da planilha foi adotado como autoridade normativa.

## Conteúdo disponível

- 105 TUCs documentais com nomes e evidências da Tabela I, tipos de bens/códigos A1, páginas e atributos na ordem documental original.
- 16 TUCs com posição de slots conferida no documento lido: 125, 130, 135, 160, 210, 325, 330, 340, 345, 540, 545, 560, 565, 570, 575 e 580. **As demais 89 não têm slots atribuídos automaticamente.** Descrições de bens em células mescladas podem corresponder a um grupo e são marcadas; nenhuma descrição individual é inventada para célula vazia.
- Tabelas II, IIIA, IIIB, IV–XV, incluindo materiais/isolamento locais da Tabela I e divisão de bitola A4/A6. Valores originais, descrições, unidades, natureza pontual/faixa/composta e páginas são preservados.
- Dicionário long TUC×A1×atributo, inventário por entidade/DIST/ano/publicação, confrontação de namespaces de potência e ambiguidades, em Parquet principal e CSV.gz (`data/auditoria`).
- Consulta web sob demanda em Explorar e Previsões: TUC, tipo de bem, A1–A6, código, DIST do agregado, descrição/página, N/D, estado e exportação JSON. Mostra a revisão efetivamente lida e a vigência pendente.

## Achados técnicos

| TUC | Potência no documento lido | Observação |
|---|---|---|
| 125/130 | A4 → IIIA | Potência reativa, não aparente |
| 340 | A3 → IIIB | A4 é corrente nominal (V) |
| 540/545/560/565/570/580 | A4 → IIIB | Faixa patrimonial, não nominal exata |
| 575 | Não há slot de potência nominal | A4 → XII para A1 01/20; XIV para 02/11/12/13 |

A Tabela IIIB lida tem **77 entradas, todas sem potência pontual inequívoca**. Isso não diz que nenhum transformador tem potência conhecida: diz que esse código patrimonial, isoladamente, não fornece seu valor exato. Não usar limite superior, ponto médio ou primeira alternativa como potência nominal. Existem ainda códigos ambíguos na cópia: II/91 e VIII_A4/80–81; o resolvedor preserva alternativas e recusa escolher uma.

MCPSE IIIB e DDA TPOTAPRT são **namespaces diferentes**. Por exemplo, MCPSE IIIB 29 significa faixa até 75 kVA; DDA TPOTAPRT 29 significa 207 kVA. Um número igual não comprova correspondência. Não se reaproveita a tabela DDA para traduzir A4. `POT_NOM` de EQTRMT/EQTRAT/EQRE pode ser auditado separadamente pelo domínio TPOTAPRT, sem habilitação para os modelos até comparação por ano. `POT_NOM` de UNTRMT/UNTRAT não recebe conversão histórica automática de unidades.

## Pipeline de leitura dos Parquets existentes

```sh
python -m pip install -r patrimonio/requirements.txt
python -m patrimonio --manifest /caminho/manifesto-selecionado.json --output /caminho/novo-enriquecimento
```

Manifesto `parquets-patrimonio-1`: `dataset_version` obrigatório; `files` contém `path`, `DIST`, `ANO`, `ENTIDADE`, `PUBLICACAO`, `sha256` e `status_fonte`. Usar uma lista versionada da seleção formal; o programa não varre/aprova republicações automaticamente. `SELECIONADA_FORMALMENTE` é declaração do fornecedor, não decisão tomada pelo programa. Outros estados são preservados e não habilitam atributos.

Lê lotes de 4.096 registros e somente as colunas necessárias; hashes são calculados por blocos. Unicidade controlada em SQLite temporário em disco (não um set global na RAM): `(DIST, ANO, ENTIDADE, PUBLICACAO, COD_ID)`. Duplicidade gera erro, sem deduplicação silenciosa. EQ e UN são visões separadas; não há JOIN ou soma entre elas, nem inferência de identidade global por COD_ID. A contagem entre publicações não é somada nacionalmente.

Escreve Parquets novos com códigos originais em `ATRIBUTOS_JSON`, traduções/estado/página, candidatas de potência separadas do campo nativo, `POTENCIA_HOMOLOGADA_KVA = NULL` e `ELEGIVEL_MODELO = false`. Verifica os hashes de entrada antes/depois. Não escreve nos arquivos originais, GDBs, checkpoints ou targets.

Uma tradução documental distingue VAZIO, NAO_APLICAVEL_DECLARADO, NAO_APLICAVEL_DOCUMENTAL, CODIGO_NAO_TRADUZIDO, A1/TUC_NAO_TRADUZIDO, SLOT_NAO_VERIFICADO, CODIGO_AMBIGUO e RESTRICAO_CONTEXTUAL_PENDENTE. Código 0 do DDA não se converte em potência zero. Slots não aplicáveis em R2 continuam sujeitos à confirmação normativa; não significam ausência física do ativo.

`features.to_feature` recusa traduções pendentes. Não há feature real nova ou alteração dos alvos no motor. Para completar o painel, será necessário conferir a Revisão 3/vigências, os slots restantes e os registros reais, além de fontes/datas de disponibilidade, unidades e comparabilidade. Relações EQ/UN e recuperação via instalação exigem cardinalidade validada em contrato separado, não associação implícita.

## Reproduzir a extração e o inventário sem GDB

```sh
python -m patrimonio.build --pdf /caminho/manual.pdf --dda /caminho/BDGD_DDA_CATALOG_M10.json --output /tmp/catalogo-documental
python -m patrimonio --handoff /caminho/BDGD_HANDOFF_CHATGPT.zip --output /tmp/inventario-documental
python -m patrimonio.web_product
python -m unittest discover -s patrimonio/tests -v
```

Os 500 arquivos históricos preexistentes permanecem byte a byte preservados. O produto novo é derivado e separado. Fixtures sintéticas só aparecem nos testes; nunca são publicadas como dados reais. O CI verifica 23 testes novos Python, os 62 do motor existente, a reprodutibilidade do produto web, unitários TypeScript, lint/tipos/build e Playwright desktop/mobile. Resultados e evidências finais são registrados no PR; execução local de Chromium é impedida pela restrição de sockets deste ambiente.

**Estado de conclusão:** implementação documental/pipeline/consulta entregue; dicionário universal normativamente validado e auditoria de valores dos registros ainda não concluídos. A conclusão exige os dois insumos inacessíveis e conferência dos 89 mapeamentos de slots restantes. Não confundir CI aprovado com validação normativa ou homologação humana.
