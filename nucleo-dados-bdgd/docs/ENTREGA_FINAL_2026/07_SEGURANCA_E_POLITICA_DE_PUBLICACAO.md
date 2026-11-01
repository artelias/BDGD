# 07 — Segurança dos dados e política de publicação

## Portão de publicação do Motor V2

O produto do Motor V2 (`web/data-motor-v2/`) é **experimental e não homologado**. Ele só entra no site estático numa build de homologação:
- o script `web/scripts/motor-v2-gate.mjs`, que roda em `predev` e `prebuild`, apaga `public/data/motor-v2/` e só copia o produto quando `NEXT_PUBLIC_MOTOR_V2=homologacao` ou `VERCEL_ENV=preview`;
- `next.config.mjs` grava a mesma decisão na interface: fora da homologação, Previsões e Metodologia mostram só o aviso do portão;
- `.gitignore` ignora `public/data/motor-v2/`, que nunca é versionado em `public/`.

Esse comportamento é testado de três formas:
- `tests/motor-v2.test.ts` roda o script em diretório temporário com quatro ambientes: produção local, produção Vercel, homologação e preview;
- o workflow da web faz uma build de produção e **falha** se `out/data/motor-v2` existir ou se o estado `PROJETADA_EXPERIMENTAL` aparecer em HTML ou JSON;
- o E2E roda numa build de homologação separada, **nunca publicada** pelo workflow.

A publicação em produção depende da autorização final. Ela exige mudar o portão de forma explícita, o que não foi feito.

## Verificações executadas nesta entrega

| Controle | Resultado |
|---|---|
| Identificadores individuais (`COD_ID`, `PAC_*`, CPF, CNPJ) nos dados públicos e no produto do Motor V2 | `COD_ID` aparece só como verbete do dicionário de campos, classificado `nao_publicavel`, **sem valores**. Nenhum padrão de CPF. O teste do produto do Motor V2 reprova `COD_ID`, `PAC_1`, `CPF`, `password`, `token`, `secret` e chaves privadas |
| Credenciais versionadas (AWS, GitHub, OpenAI, Slack, chave privada, `VERCEL_TOKEN`, senha literal) | nenhuma ocorrência no repositório (`git grep`); nenhum `.env` versionado |
| Dados brutos sensíveis | nenhum Parquet ou base bruta no repositório; o produto web são agregados por DIST × métrica × ano |
| Publicação extraordinária indevida | só a publicação ordinária selecionada no contrato entra; extraordinárias nunca entram automaticamente |
| Previsão experimental apresentada como homologada | toda série projetada traz `homologado: false` e o motivo; a interface mostra "experimental, não homologado" (E2E). O texto "validados retrospectivamente" foi substituído por "comparados retrospectivamente" |
| Total parcial anunciado como completo | `rotulo_total` vale `PARCIAL` sempre que falta DIST aplicável ou âncora 2025 (teste do produto e E2E). Potência de reguladores não tem total. Somas de grupo dizem quais DIST ficaram fora |
| N/D convertido em zero | histórico ausente fica `null` (teste do produto); somas de grupo não completam com zero (teste unitário); o CSV deixa N/D vazio |
| Contagem fracionária ou negativa | `validarDist` rejeita, o teste do produto confere todas as séries, e `audit_public_products` do #19 confere os produtos públicos |

## O que continua fora do escopo do portão

- O motor público V1 (`/data/previsoes/cenarios-motor.json`, PR #17/#19) já estava publicado e continua igual. A única mudança foram os campos de erro físico do patch B, sem alterar nenhum número publicado.
- O deploy de produção e a liberação pública do Motor V2 dependem de decisão humana (ver `09_LIMITACOES_E_DECISOES.md`).
