# Patches propostos sobre o PR #19 (não aplicados)

São patches **sobre** `fix/natureza-fisica-contagens-inteiras-20261029` (cabeça `09cd749`), para que o contrato físico público tenha **uma única implementação, a do #19**, e os diagnósticos do Motor V2 entrem só como complementos.

**Nada foi aplicado a nenhuma branch.** A aplicação depende de decisão humana; o patch 0002 também depende do Codex (UI).

| Patch | Arquivos | Efeito público | Verificação feita |
|---|---|---|---|
| `0001` A: diagnóstico interno `--internal-dir` | `motor_cenarios/cenarios.py`, `motor_cenarios/test_diagnostico_interno.py` (novo) | **nenhum** | ver nota A |
| `0002` B: erro físico ao lado do contínuo | `motor_cenarios/cenarios.py`, `motor_cenarios/test_publico.py` | **aditivo**: campos `mae_fisico`, `wape_fisico`, `vies_fisico` e `fisico_motivo` em `modelos` de cada métrica de contagem | ver nota B |
| `0003` C: CI da web | `.github/workflows/nucleo-bdgd-web.yml` | nenhum | ver nota C |

**Nota A.**
- Os 7 arquivos públicos regenerados são idênticos com e sem a opção.
- O `--check` aprova com scikit-learn 1.8.0: 29 métricas, e 2 de 16.045 contagens na folga de 1 unidade.
- Gravar sob `web/`, `motor_cenarios/saida`, `output-publicavel` ou `output-historico` é recusado (teste).
- O diagnóstico grava 22.320 linhas; nas 16.045 contagens, o valor físico é sempre o half-up do bruto.

**Nota B.**
- Retirados os campos novos, o JSON regenerado é idêntico; os CSVs também.
- Os campos aparecem em 168 modelos de contagem com erro físico e em 16 com `PREVISAO_NEGATIVA_NAO_PUBLICAVEL`; nunca em métricas contínuas.
- O teste novo passa com o produto regenerado e reprova com o produto atual, por desenho.
- **Exige:** regenerar `motor_cenarios/saida/*` e `web/public/data/previsoes/cenarios-motor.json` com scikit-learn 1.8.0, aprovar `--check` e tipar os campos em `web/src/lib/cenarios-motor.ts` (Codex).

**Nota C.**
- Na árvore Motor V2 + #19, com `D:\` bloqueado, o passo atual roda 248 testes com **5 erros**.
- Com o patch, rodam 25 + 3 testes, todos OK.
- **Recomendado antes de incorporar o Motor V2.**

Aplicar, numa branch nova a partir do #19, nunca na própria branch sem autorização:

```bash
git switch -c integracao/pr19-motor-v2 origin/fix/natureza-fisica-contagens-inteiras-20261029
git am --3way nucleo-dados-bdgd/motor_v2/integracao/pr19/0001-*.patch nucleo-dados-bdgd/motor_v2/integracao/pr19/0003-*.patch
```

`0002` só depois da decisão sobre o produto público. Gere os produtos derivados com o gerador (`cenarios.py`), **nunca** mesclando à mão.

**Atenção a versões.** Com scikit-learn 1.9.1, o HistGradientBoosting (`hgb_painel`) diverge do produto publicado em 158 pontos, com ou sem os patches. Use a versão fixada em `motor_universal/requirements-ml.txt` (1.8.0).
