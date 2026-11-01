# 01 — Relatório executivo final do Núcleo de Dados BDGD (2026-11-01)

## O produto

O Núcleo de Dados BDGD é um dashboard estático, sem servidor nem banco, que analisa os ativos físicos da distribuição de energia elétrica brasileira a partir da BDGD/ANEEL. Ele tem sete páginas:

| Página | Conteúdo |
|---|---|
| Panorama | Ativos físicos nacionais, mapa e ranking |
| Explorar | Por categoria, entidade, TUC e atributos |
| Matriz | Comparação nacional DIST × ativo |
| Comparador | Empresas e grupos econômicos |
| Evolução | Série histórica 2022–2025 com estado de homologação de cada célula |
| Previsões | Motor público V1 de cenários por métrica e, na homologação, o Motor V2 por distribuidora |
| Metodologia | Fontes, regras, qualidade, modelos e a ficha do Motor V2 por empresa e métrica |

A versão integrada está na branch `integracao/produto-final-20261101`. Ela reúne:
- a homologação funcional do Codex;
- os PRs #17 a #20;
- o Motor V2;
- os patches A, B e C do contrato físico.

Cada contrato tem uma única implementação (ver `05_INTEGRACAO_PRS_E_BRANCHES.md`).

## O Motor V2 nesta entrega

| Indicador | 6327239 (31/10) | Agora |
|---|---|---|
| Universo tratado | 114 DIST × 25 conceitos no nível B (2.850) | **114 DIST × 30 objetivos/métricas = 3.420 combinações** |
| Combinações com estado e motivo | 2.850 (438 só "bloqueada") | **3.420 (100%)**, com 10 estados documentados e `BLOQUEIO_TECNICO` = 0 |
| Combinações com 15 valores (5 anos × 3 cenários) | 2.412 (B) + 512 (A) | **2.707** (97,1% das aplicáveis) |
| Pares do catálogo com previsão | 26 de 29 | **28 de 29** (TUC 575 kVA é não aplicável por semântica) |
| Métricas de potência por DIST | nenhuma | TUC 565 kVA (99 DIST), TUC 570 kVA (60), reguladores kVA (59, sem total) |
| Coeficientes de modelos lineares | não publicados | **214 de 214** recuperados e verificados |
| Modelos cientificamente homologados | 0 | **0** (2 origens < 3 exigidas, sem point-in-time) |

As 438 combinações sem série foram auditadas uma a uma:
- 275 são sucessão societária;
- 162 são ativo não aplicável, conferido nos Parquets locais (0 registros);
- 1 é dado não homologado (Coprel, circuitos AT);
- **0 eram defeito de código.**

A Energisa Borborema, incorporada em 2023, deixou de ser tratada como empresa ativa.

**Interface.** A página Previsões mostra, por empresa ou grupo:
- ativo, métrica, unidade e cenário;
- histórico × projeção;
- estado e motivo;
- modelo e justificativa;
- erros (MAE, RMSE, WAPE, viés) e ganho sobre o baseline;
- cobertura nacional e total `PARCIAL`/`COMPLETO`;
- exportação CSV do recorte.

A Metodologia ganhou uma ficha por empresa e métrica, com competências, publicações, algoritmo, equação, coeficientes (ou N/D justificado), baselines, cenários extremos e status de homologação. Tudo é pré-calculado: nada é treinado no navegador.

**Publicação.** O Motor V2 fica atrás de um **portão de homologação**. Ele aparece em builds de homologação e em previews da Vercel, que são protegidos por SSO e respondem 302 sem autenticação. A produção continua fechada até a autorização final. O CI reprova uma build de produção que exponha o Motor V2.

## Correções obrigatórias atendidas

- **"Três cenários validados retrospectivamente"** virou "comparados retrospectivamente", e o status público passou a `simulacao_comparada_retrospectivamente`.
- **Recolhimento da barra lateral:** a largura real muda de 244 para 68 px e o conteúdo acompanha. Há regressão do Codex (altura baixa, teclado, armazenamento bloqueado) e uma nova regressão nas sete páginas em 1440, 1024, 901, 900, 768, 390 e 320 px.
- **Defeitos P0 e P1 do Codex** (INV-01, INV-02, LAT-01) estão integrados com as regressões dele.
- **Patch B:** o erro físico pós-arredondamento foi publicado **sem alterar nenhum número já publicado**, e o `--check` oficial aprova.

## Testes

O resumo está em `06_TESTES_E_CI.md`. Python, estatística, contratos, front-end e CI rodaram na árvore integrada.

## Limitações e decisões

As seis ressalvas obrigatórias continuam valendo:
- não há 3 origens independentes;
- não há point-in-time elegível;
- horizontes acima de 1 ano não são validados;
- cenários não são intervalos de confiança;
- totais parciais são `PARCIAL`;
- extraordinárias nunca são publicadas automaticamente.

As decisões que cabem a você estão em `09_LIMITACOES_E_DECISOES.md`. **Conclusão técnica do produto não é homologação científica das previsões.**
