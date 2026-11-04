# 05 — Checklist de inspeção funcional no preview autenticado

**Para o responsável pela inspeção.** Abra o preview Vercel do SHA definitivo da RC (a URL está no relatório de entrega e no PR #22), autenticado. Marque cada item como OK, falha ou não verificado. Os resultados alimentam o termo de aceite (`04`).

**Severidade:**
- **Crítica:** número errado, valor bloqueado mostrado como previsão, contagem fracionária, dado de outra distribuidora, página quebrada. **Impede o aceite.**
- **Maior:** a informação existe mas engana ou falta (motivo ausente, ressalva sumida, exportação divergente da tela), ou há falha de navegação no celular. **Exige correção ou aceite explícito com ressalva.**
- **Menor:** estética, texto ou alinhamento, sem efeito no conteúdo. Registrar e não bloquear.

Ambiente sugerido: desktop (Chrome, 1440 px) e **iPhone (Safari)**. O item 8 só vale em aparelho físico, que os testes automatizados não cobrem.

## 1. Panorama e mapa

| # | Ação | Esperado | Sev. |
|---|---|---|---|
| 1.1 | Abrir `/` | mapa das ARAT carregado; KPI de consumidores visível; nenhum erro na tela | Crítica |
| 1.2 | Alternar o tema claro/escuro **10 vezes** no botão do cabeçalho | o mar e o continente acompanham sempre o tema da página; as áreas mudam de cor; não aparece um segundo mapa; os botões + e − continuam | Maior |
| 1.3 | Clicar numa distribuidora no mapa (por exemplo Amazonas, DIST 7019) e em "Ver Brasil" | enquadra a ARAT e volta ao Brasil; o painel lateral mostra a mesma distribuidora | Maior |
| 1.4 | Conferir os números da lista (por exemplo rede de média tensão) | contagens inteiras, km com separador pt-BR; **nenhuma contagem como "12,5 mil"** | Crítica |
| 1.5 | Lateral inferior esquerda | só a autoria e o contato; **sem** "Data-base", "GDBs processados" ou "publicações não localizadas" | Menor |

## 2. Explorar ativos

| # | Ação | Esperado | Sev. |
|---|---|---|---|
| 2.1 | Abrir `/explorar/`, escolher um ativo e uma distribuidora | cards, tabela e gráfico coerentes entre si; unidade correta (itens, km, kVA) | Crítica |
| 2.2 | Abrir um `<details>` de entidade técnica (por exemplo UCAT da DIST 26) | o "zero no agregado processado" aparece com "verificação independente pendente", nunca como valor real | Maior |
| 2.3 | Exportar CSV | valores iguais aos da tela; contagens sem casas decimais | Crítica |

## 3. Matriz

| # | Ação | Esperado | Sev. |
|---|---|---|---|
| 3.1 | Abrir `/matriz/`, ordenar uma coluna, filtrar e depois "Limpar" | a ordenação e o filtro respondem; o CSV desativa sem tabela e reativa ao limpar | Maior |
| 3.2 | Conferir células N/D | N/D continua N/D (nunca zero) | Crítica |

## 4. Comparador

| # | Ação | Esperado | Sev. |
|---|---|---|---|
| 4.1 | `/comparar/` com duas distribuidoras | diferença absoluta e percentual coerentes; contagens inteiras; sem rolagem horizontal | Maior |
| 4.2 | Alternar o tema | as barras e os rótulos legíveis nos dois temas | Menor |

## 5. Evolução histórica

| # | Ação | Esperado | Sev. |
|---|---|---|---|
| 5.1 | `/evolucao/?escopo=dists&dists=95&ativo=subestacoes` | eixo Y só com inteiros (1, 2); **nenhuma marca "1,2" ou "1,5"** | Crítica |
| 5.2 | `/evolucao/?ativo=consumidores` | Brasil 2022–2023 como N/D (painel balanceado), sem total nacional inventado | Crítica |
| 5.3 | `/evolucao/?escopo=dists&dists=5370&ativo=consumidores` | Coopera 2025 com N/D e a ressalva da UCBT vazia (subtotal 225 AT) | Maior |

## 6. Cenários de expansão por métrica física (`/previsoes/`)

| # | Ação | Esperado | Sev. |
|---|---|---|---|
| 6.1 | Abrir `/previsoes/` | só o painel **"Cenários de expansão por métrica física"** como experiência de cenários; **o painel "Explorar cenários 2026–2030" não existe mais** | Maior |
| 6.2 | Ativo "Rede de média tensão", DIST 7019 | faixa "Três cenários publicados"; três colunas na tabela; gráfico com três trajetórias | Crítica |
| 6.3 | Ativo "Transformadores de distribuição", métrica "Quantidade", DIST 7019 | faixa **"Previsão parcial · 1 de 3 cenários publicados (Moderado)"**; Conservador e Agressivo desativados com "Não publicado neste recorte" e o motivo; tabela só com a coluna Moderado; nenhuma célula "Indisponível" | Crítica |
| 6.4 | Ativo "Chaves", DIST 6072 | "Cenários incompletos: previsão não publicada", sem números de projeção (um extremo nunca aparece sem o Moderado) | Crítica |
| 6.5 | Ativo "Consumidores", Distribuidora "Coopera · DIST 5370" | bloqueado, com a ressalva da Coopera e "Observações e ressalvas dos dados" (225); sem tabela nem CSV | Maior |
| 6.6 | Selecionar um grupo econômico (por exemplo Energisa) | total só com todas as trajetórias; se faltar alguma, o cenário aparece como não publicado com o número de distribuidoras faltantes | Maior |
| 6.7 | Exportar CSV (item 6.3) | colunas `conservador_nao_publicado`, `moderado_<modelo>`, `agressivo_nao_publicado`, `completude_cenarios = PARCIAL`; contagens inteiras | Crítica |
| 6.8 | Texto do painel | "sem validação científica independente"; nenhuma afirmação de previsão homologada | Maior |
| 6.9 | (Homologação) seção do Motor V2: geradores, quantidade | total nacional com o **Moderado**; extremos como "Soma dos extremos individuais (não é cenário nacional)", com o alerta de crescimento acima do observado | Maior |

## 7. Metodologia e qualidade

| # | Ação | Esperado | Sev. |
|---|---|---|---|
| 7.1 | `/metodologia/` | a linha "N GDBs processados · M publicações 2025 não localizadas" na seção Fonte; a tabela de cobertura por distribuidora | Menor |
| 7.2 | Seção do motor de cenários | modelos executados, variáveis e o Moderado por métrica coerentes com Previsões | Maior |

## 8. Navegação no iPhone (aparelho físico)

| # | Ação | Esperado | Sev. |
|---|---|---|---|
| 8.1 | Barra inferior e folha "Mais" | abrem, fecham e não cobrem o conteúdo; o foco fica dentro da folha; paisagem cabe | Maior |
| 8.2 | Tema na folha "Mais", alternado 10 vezes no Panorama | o mapa continua coerente (como no item 1.2) | Maior |
| 8.3 | As sete páginas | sem rolagem horizontal; selects utilizáveis; tabelas roláveis dentro da própria caixa | Maior |
| 8.4 | Download de CSV em Previsões | o arquivo é baixado ou abre (o Safari pode abrir em nova aba; não é defeito) | Menor |

## 9. Exportações e valores físicos

| # | Ação | Esperado | Sev. |
|---|---|---|---|
| 9.1 | Em três telas (Explorar, Evolução, Previsões), comparar o CSV com a tela | os mesmos números; contagens inteiras; km e kVA com decimais quando aplicável | Crítica |
| 9.2 | Procurar decimais em contagens nos cards e tooltips | nenhum "12,5" em transformadores, consumidores, postes, chaves e similares | Crítica |

## 10. Justificativa dos cenários indisponíveis

| # | Ação | Esperado | Sev. |
|---|---|---|---|
| 10.1 | Em três métricas parciais (transformadores qtd, geradores, reatores), passar o mouse nos cards desativados e ler a faixa | o motivo é específico: regra de seleção ("nenhum modelo plausível, dentro da tolerância de erro, com trajetória abaixo/acima do moderado"), trajetória implausível na distribuidora, histórico insuficiente, ou sem Moderado | Maior |
| 10.2 | Uma métrica bloqueada (Reguladores, Potência) | motivo do bloqueio, sem números | Crítica |

## Registro da inspeção

| Campo | Valor |
|---|---|
| SHA inspecionado | |
| URL do preview | |
| Data e hora | |
| Inspetor | |
| Dispositivos (desktop / iPhone e versão do iOS) | |
| Falhas críticas (itens) | |
| Falhas maiores (itens) | |
| Falhas menores (itens) | |
| Decisão (seguir para o aceite / corrigir) | |
