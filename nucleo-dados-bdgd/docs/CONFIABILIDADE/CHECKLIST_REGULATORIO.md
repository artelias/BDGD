# Checklist de homologação regulatória (especialista)

Para o especialista em regulação da distribuição (PRODIST, Módulo 8). Cada item traz o que o módulo faz e onde conferir.
**Os campos de decisão e a assinatura ficam em branco: só o especialista os preenche.** A leitura estatística do módulo é
observacional; nenhum item pede validação de causalidade.

Legenda da decisão: **C** conforme · **CR** conforme com ressalva · **NC** não conforme (descrever).

| # | Ponto | O que o módulo faz | Onde conferir | Decisão | Observação |
|---|---|---|---|---|---|
| 1 | Identidade DEC/FEC | DEC apurado = DECIP + DECIND; FEC = FECIP + FECIND (verificado em 100% dos conjunto-meses 2022–2025 do arquivo ANEEL, a menos do arredondamento de 0,01 por mês; na soma anual, até 0,06; as parcelas da ficha usam a soma das internas) | FONTES_E_GEOMETRIA.md; ficha → "Origem das interrupções" | | |
| 2 | Componentes externas | XP e XN exibidas como "fora do DEC/FEC", sem parcela do indicador | ficha de qualquer conjunto | | |
| 3 | Expurgos | INC, INE, INO, IPC, XNC, XPC somados em "Expurgado", exibidos como "não compõe" | `publicar.EXPURGOS`; domínio `dominio-indicadores.csv` | | |
| 4 | Período anual | Valor anual do conjunto = soma dos 12 valores mensais publicados | Metodologia; FORMULAS_E_RECONCILIACAO.md | | |
| 5 | Agregado da distribuidora | Média dos conjuntos ponderada pelo NumCon de cada mês, somada nos meses; rotulado "derivado", pode diferir em centésimos do global ANEEL | Metodologia; selo "derivado dos conjuntos" | | |
| 6 | Limites regulatórios | Limite anual do conjunto (arquivo de limites ANEEL); desempenho = apurado ÷ limite; sem comparação no recorte mensal; 17 conjunto-anos sem limite publicados com aviso | ficha, KPI "% do limite"; mapa "% do limite" | | |
| 7 | Apuração parcial | Menos de 12 meses de DEC **ou** FEC: valor exibido com aviso, fora de limite, quebras, posições, rankings, pares e comparador | alerta `apuracao_parcial` na ficha | | |
| 8 | Caso Elektro 2025 | ANEEL sem FEC de jun/2025 nos 130 conjuntos: FEC anual = 11 meses, parcial; componentes e reconstrução restritas aos 11 meses; DEC 2025 completo e comparável | `?dist=385&ind=fec&conj=13449`; HOMOLOGACAO_TECNICA.md, seção 3 | | |
| 9 | Reconstrução por DIC/FIC | Σ DIC (FIC) da BDGD ÷ NumCon oficial, só nos meses com oficial; critério **experimental** de 5%; é auditoria de coerência da BDGD, nunca substitui o oficial | ficha → "Reconstrução a partir da BDGD"; FORMULAS_E_RECONCILIACAO.md | | |
| 10 | Leitura das 83 combinações < 80% | Tratadas como divergência da BDGD declarada (DIC zerado, empresas de 1 conjunto, deslocamento uniforme por empresa-ano), não como erro do oficial | `auditoria/RECONCILIACAO_POR_DIST_ANO_INDICADOR.csv`; `auditoria/homologacao/a2_rec_saida.txt` | | |
| 11 | Oficial × derivado | Selos: "oficial ANEEL" (DEC, FEC, limites, componentes) × "derivado" (agregado da distribuidora, infraestrutura BDGD, reconstrução, estatística) | ficha, comparador, Fatores | | |
| 12 | Linguagem | Frases descrevem diferenças e associações; nunca "porque", "causa", "devido"; rankings não são juízo de eficiência | comparador, benchmarking, Fatores | | |

## Pontos em que a opinião do especialista é pedida explicitamente

1. Se XNC e XPC (externas em dia crítico) devem aparecer como "expurgo" ou como "externa".
2. Se o tratamento da apuração parcial (exibir com aviso e excluir das comparações) é adequado, ou se o ano deveria ser
   omitido.
3. Se o critério experimental de 5% da reconstrução deve ser mantido, ajustado ou retirado da interface.

## Registro (preenchimento exclusivo do especialista)

| Campo | |
|---|---|
| Nome | |
| Função / registro profissional | |
| Commit avaliado | |
| Decisão geral (aprovado / aprovado com ressalvas / reprovado) | |
| Ressalvas | |
| Data | |
| Assinatura | |
