# 04 — Termo de aceite de engenharia: Núcleo de Dados BDGD, release candidate 1.0

> **Este termo NÃO está assinado nem aceito.** Ele foi preparado com a evidência técnica para revisão. O aceite só existe quando os campos da seção 7 forem preenchidos por pessoas identificadas. Este documento não registra assinatura, aceite ou aprovação inexistente.

## 1. Identificação do objeto

| Campo | Valor |
|---|---|
| Repositório | `artelias/BDGD` |
| Branch | `rc/1.0-20261101` |
| SHA avaliado | `e4bc55cadee8b0bb025f46475852262d26cfd423 (código testado; o commit seguinte só preenche este dossiê)` (parte de `a7df5e250ee2d6e521d3c52ab92c624ab5a91712`, com as correções finais de release) |
| Data da avaliação técnica | 03/11/2026 |
| Competência dos dados | 31/12/2025 (histórico 2022–2025; cenários 2026–2030) |
| Ambiente avaliado | build estática local (produção e homologação), CI GitHub Actions (Linux) e preview Vercel (build; conteúdo não inspecionado) |

## 2. Escopo

**Dentro do escopo:**
- integridade e contratos do ETL BDGD;
- reconciliação das entidades físicas;
- natureza física das métricas (contagens inteiras, unidades);
- portão de plausibilidade dos cenários;
- bloqueios, ressalvas e completude dos cenários;
- segurança e portão de publicação do Motor V2;
- cobertura das séries projetadas;
- interface, filtros e exportações (desktop e celular);
- coerência histórico × projeção na mesma coorte;
- apresentação dos agregados nacionais;
- testes e CI.

**Fora do escopo:**
- homologação científica dos modelos (Processo B, dossiê separado);
- decisão de publicar o Motor V2 em produção;
- desempenho preditivo como critério de aceite técnico.

**Um motor tecnicamente aceito pode ser cientificamente experimental.** Este termo não declara validade científica de nenhuma previsão.

## 3. Requisitos e resultado

Ver `01_MATRIZ_REQUISITOS.csv`. São 22 requisitos:
- **15 atendidos**;
- **5 atendidos com ressalva**;
- **0 não atendidos**;
- **2 não verificados**.

O preview em conteúdo e a ciência estão fora do aceite de engenharia.

## 4. Testes executados

Ver `02_EVIDENCIAS_TESTES.md`, com comandos, contagens e identificadores dos runs. Resumo: Motor V2 281/281; emulação do CI 179 OK; gerador público 25 OK e `--check` OK; ESLint 0; TypeScript 0; Vitest 196/196; Playwright local 347/351 (4 falhas de um teste corrigido) e specs afetados 33/33 e 21/21 na build final; CI Linux web (E2E completo) e sintético success no SHA avaliado.

## 5. Ressalvas que acompanham um eventual aceite

1. **Preview não inspecionado em conteúdo** (NC-ENG-06). Um revisor humano precisa conferir no preview do SHA final: Previsões (completude e alertas), Panorama (mapa, 10 alternâncias de tema) e a lateral.
2. **Totais nacionais dos extremos** (NC-ENG-07). A tela mostra o Moderado como total nacional. Conservador e Agressivo nacionais aparecem como soma de extremos individuais, com alerta em 23 de 28 totais, incluindo geradores (Agressivo implícito de 53%/ano contra 28–44%/ano observados). A decisão de mantê-los na produção é humana.
3. **Produto público com previsões parciais** (NC-ENG-08). 1.206 séries parciais, explicitadas na tela e no CSV. A otimização dos modelos está em branch experimental e não altera esta RC.
4. **Limites do ambiente:**
   - Safari físico não testado;
   - 93 testes dependem de dados locais;
   - o PR da RC não foi aberto (sem integração autorizada).
5. **Parâmetros do portão de plausibilidade** não derivados dos dados (`TOL_MODELO`, `BASE_MINIMA`), documentados.

## 6. Critérios de reprovação (qualquer um impede o aceite)

- Qualquer bateria obrigatória (Python, ESLint, TypeScript, Vitest, Playwright completo, CI Linux web e sintético) falhando no SHA avaliado.
- Contagem física fracionária ou negativa em qualquer produto público ou tela.
- Cenário extremo publicado sem o Moderado, ou série parcial apresentada como completa.
- Valor bloqueado pelo portão de plausibilidade exibido como previsão.
- Motor V2 presente numa build de produção.
- Identificador individual, credencial ou segredo nos produtos públicos.
- Não conformidade crítica aberta.
- Mudança nos números publicados sem regeneração verificada (`cenarios.py --check`) ou sem registro.
- Preview do SHA final com comportamento diferente do verificado localmente, observado pelo revisor da ressalva 1.

## 7. Identificação e decisão humana (a preencher)

| Papel | Nome | Função/organização | Decisão (aceito / aceito com ressalvas / reprovado) | Ressalvas aceitas (números da seção 5) | Data | Assinatura |
|---|---|---|---|---|---|---|
| Responsável técnico pelo produto | | | | | | |
| Revisor de engenharia independente | | | | | | |
| Responsável pela publicação | | | | | | |

Registro da verificação do preview (ressalva 1): revisor ______, data ______, SHA conferido ______, resultado ______.
