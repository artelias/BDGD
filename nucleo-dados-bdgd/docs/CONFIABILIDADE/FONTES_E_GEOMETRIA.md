# Fontes e geometria

## ANEEL — Indicadores coletivos de continuidade (estado `OBSERVADO_OFICIAL`)

* Dataset `indicadores-coletivos-de-continuidade-dec-e-fec`, arquivo `indicadores-continuidade-coletivos-2020-2029.parquet`,
  licença ODbL. Arquivo gerado pela ANEEL em 2026-11-05.
* Entram, por conjunto e mês de 2022 a 2025: `DEC`, `FEC`, `NumCon` e as componentes de origem
  (`DECIP`, `DECIND`, `DECXP`, `DECXN` e expurgos `DECINC`, `DECINE`, `DECINO`, `DECIPC`, `DECXNC`, `DECXPC`, idem FEC);
  e os limites anuais (`limites.parquet`).
* As linhas do arquivo oficial vêm duplicadas: duplicatas exatas são removidas; valores conflitantes para a mesma chave
  (conjunto, indicador, ano, mês) **interrompem** a preparação (nada é gravado). Limites conflitantes também.
* Identidade verificada (12/11/2026, `continuidade.parquet`): **DEC = DECIP + DECIND** e **FEC = FECIP + FECIND** em
  150.033 de 150.033 conjunto-meses com DEC e FEC. As componentes externas (`XP`, `XN`) e os expurgos são informados
  pela ANEEL mas não compõem o indicador apurado. A proveniência gravada antes desta data registrava a soma com as
  externas (válida em 95,8% dos casos, quando a externa é zero); `aneel.py` foi corrigido para gravar a identidade certa
  na próxima preparação.
* Lacuna da fonte (auditoria de 12/11/2026): a ANEEL não publicou o **FEC de junho de 2025 da Elektro** (130 conjuntos; o
  DEC do mês existe). Por isso há 150.163 conjunto-meses com DEC e 150.033 com FEC. O FEC anual desses conjuntos soma 11
  meses, recebe o alerta `apuracao_parcial` e fica fora das comparações (limite, quebras, posições, rankings, reconstrução).
* O arquivo de atributos físico-elétricos dos conjuntos da ANEEL só vai até 2014: não é usado.

## BDGD (estado `DERIVADO_EXPLORATORIO`)

* Parquets do Núcleo de Dados da BDGD, competências 2022–2025 (379 cargas DIST × ano), lidos em modo somente leitura por
  `infra.py`. A chave de ligação é cadastral: `CONJ`, `CTMT`, `UNI_TR_MT`, `UN_SE`, `UN_RE`. Nenhum vínculo por
  proximidade geográfica.
* Regras físicas: as mesmas do portal (consumidores = unidades distintas ativas por entidade; rede = `SUM(COMP)/1000`;
  transformadores = equipamentos `EQTRMT` TUC 565 levados pela instalação; instalações e equipamentos nunca somados).
* Contagens de consumidores de 1 a 4 por alimentador são suprimidas (`uc_suprimido`); o frontend mantém N/D e não as
  transforma em zero.
* Totais 2025 conferidos com o pacote público do portal (auditoria A4): transformadores, km MT e km BT **iguais** para
  EPB (6600), ESE (6587) e Energisa AC (26). Consumidores somados por conjunto diferem de +22 (EPB), +10 (ESE) e −4 (EAC)
  da união do portal: a soma por conjunto conta BT + MT + AT por entidade, e registros sem conjunto válido ficam fora.

## Geometria (`geo.py`)

* Origem: camada `CONJ` da BDGD 2025 (EPSG:4674), polígonos publicados pelas distribuidoras, data-base 2025-12-31,
  estado `POLIGONO_OFICIAL_SIMPLIFICADO`.
* Simplificação por polígono com preservação de topologia (~110 m); podem surgir frestas mínimas entre vizinhos: serve para
  visualização, não para medição. A área (km²) é geodésica e calculada na geometria **original**.
* Cobertura (auditoria A6): 3.147 conjuntos com apuração em 2025, 3.147 com polígono; nenhum polígono de conjunto sem
  apuração. Conjuntos extintos antes de 31/12/2025 aparecem só na lista (sem polígono, com aviso).
* No nível Brasil o mapa usa as áreas de atuação (ARAT) do pacote do portal; elas nunca representam conjuntos.
