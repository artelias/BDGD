# Métricas, comparador e benchmarking

## Dicionário de métricas

A definição única está em `confiabilidade/metricas.py` (id, rótulo, unidade, tipo, regra de cálculo) e é publicada no
`indice.json`; a aba **Metodologia** renderiza o dicionário a partir dela, então o texto da tela e o cálculo não divergem.
Grupos: Consumidores · Território · Rede · Alimentadores · Transformação · Seccionamento e proteção.

Tipos: `contagem` (inteiro), `continua` (km, kVA, MWh, km²), `razao` (por unidade), `pct` (0–1). O campo `sentido` só
documenta a leitura física; não é juízo de desempenho. Razões por 100 km de rede MT usam `log1p` nos modelos.

Ressalvas mostradas junto às métricas: potência nominal (kVA) é declarada e não homologada (há distribuidoras em outra
escala); instalações (UN) e equipamentos (EQ) nunca são somados; `consumidores_divergentes` sinaliza conjunto cuja contagem
da BDGD difere muito do NumCon (métricas por consumidor pouco confiáveis).

## Comparador A × B (aba "Comparar A × B")

* URL: `?aba=comparar&a=<DIST>-<CONJ>&b=<DIST>-<CONJ>` (pode cruzar distribuidoras). Botão "trocar" inverte os lados.
* Qualidade: DEC, FEC, limites, % do limite, variação contra o ano anterior. Infraestrutura: as métricas do dicionário,
  com diferença absoluta e relativa. Para métricas em % a diferença relativa não é calculada (seria % de %).
* Frases automáticas comparam valores e posições e nunca usam "porque", "causa" ou "devido" (testado no Vitest e no e2e).
* Barras: cada métrica na própria escala (o maior dos dois lados = barra cheia); diferença relativa = (A − B) ÷ |B|.
* Exporta CSV `confiabilidade_comparacao_<A>_x_<B>_<ano>.csv`.

## Benchmarking (aba "Benchmarking")

* **Pares semelhantes**: os 20 conjuntos de **outras** distribuidoras mais próximos em porte (log), densidade (log),
  parcela não urbana, rede MT por consumidor (log) e consumo por consumidor, distância padronizada pelo intervalo
  interquartil nacional do ano (0 = idêntico). Os critérios são fixos (`CRITERIOS_PADRAO`) e listados na tela; critério N/D
  no conjunto-alvo sai do cálculo e o motivo é exibido. A tela mostra a mediana e os quartis dos pares e a posição (P) do alvo.
* **Perfil por quartil**: mediana de cada métrica nos conjuntos com indicador ≤ Q1 (melhores), entre Q1 e Q3 e ≥ Q3
  (piores) no Brasil; contraste = (mediana dos piores − mediana dos melhores) ÷ IQR da métrica: tamanho da diferença, não causa.
* **Ranking** (15 itens): melhores, piores, maiores melhorias, maiores pioras, acima do limite.
* Semelhança de contexto reduz, mas não elimina, diferenças de território (clima, vegetação, idade de ativos não estão nos
  dados). Rankings descrevem diferenças; não são evidência de eficiência.
