# Otimização experimental dos modelos de cenários

**Experimental. Não altera o produto publicado nem a RC 1.0, e não é homologação científica.**

O protocolo foi registrado antes da execução: `PROTOCOLO_OTIMIZACAO.md`. Antes do commit do protocolo houve uma única execução de depuração em `trafo_dist/quantidade` (`OTIM_SO`), feita para testar o código. Ela não alterou nenhum parâmetro do protocolo e foi refeita na execução completa.

```bash
D:/NUCLEO_BDGD_2025/.venv-motor/Scripts/python.exe motor_cenarios/otimizacao/otimizar.py \
  output-historico/contrato-integracao motor_cenarios/entrada motor_cenarios/entrada \
  web/public/data/previsoes/cenarios-motor.json motor_cenarios/otimizacao/saida
```

Usa a mesma versão do gerador (scikit-learn 1.8.0, numpy) e não precisa de nenhuma dependência nova. A execução completa leva cerca de 25 minutos (27 métricas). O cache (`saida/cache.json`) evita refazer ajustes já feitos.

## Saídas (`saida/`)

| Arquivo | Conteúdo |
|---|---|
| `MATRIZ_MODELOS_OTIMIZADOS.csv` | Por DIST × ativo × métrica × cenário: algoritmo, variáveis, hiperparâmetros, mecanismo, R² e erros fora da amostra (etapas S e F), horizonte validado, comparação com o modelo anterior, valor 2030, plausibilidade, homologação e motivo |
| `MODELOS_AVALIADOS.csv` | Por métrica e modelo (original, otimizado, baseline): WAPE, MAE, RMSE, viés, R² (estoque, variação, crescimento) e erro físico nas etapas S, F e H2; estabilidade; melhor baseline; veredito da otimização |
| `VARIAVEIS_SELECAO.csv` | Por métrica e variável: filtro (disponibilidade, constância, redundância), importância por permutação na etapa S por algoritmo e se foi selecionada |
| `BUSCA_TENTATIVAS.csv` | Cada ajuste executado (custo e número de tentativas) |
| `PONTOS_AVALIACAO.csv` | Erros ponto a ponto das etapas F e H2, base do bootstrap no dossiê científico |
| `RESUMO_OTIMIZACAO.json` | Respostas às 10 perguntas de entrega, protocolo e tempo |
