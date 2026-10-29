# Validação de release — Motor de Expansão Elétrica + cadeia PR #14 → #16 → #17

Data: 28/10/2026. Branch `feat/motor-cenarios-publicacao-20261028`, PR artelias/BDGD#17 (rascunho, base `fix/limpeza-paineis-seletores-20261028` = PR #16, que tem base no PR #14). Commit validado: `4ff0cc3a92e38b9e7317c2395e5cf5626193c1cc`.

## Situação: **APTO para produção; publicação em produção NÃO efetivada**

Todos os critérios técnicos de aceite foram atendidos no commit acima. A criação do deployment de produção foi negada pelo controle de permissões do agente (Claude Code) e não foi contornada.

## Resultados

| Verificação | Onde | Resultado |
|---|---|---|
| Lint (ESLint) | local + CI | OK |
| Tipos (tsc) | local + CI | OK |
| Testes unitários (Vitest) | local + CI | 146/146 |
| Auditoria de dependências de produção | CI | OK |
| Resumo do motor universal (`--check-web`) | CI | OK |
| Motor de cenários: testes (6) e regeneração `--check` | local + CI | OK |
| Smoke do contrato 2025, publicação 2025-12-31, assets web | local + CI | OK |
| Série histórica 2022–2025 | local + CI | OK |
| Homologação web (13 pares com seleção comprovada) | local + CI | OK |
| Contrato nacional (11.400 linhas, 13 republicações conferidas) | local + CI | OK (antes: 319 erros) |
| Cenários exploratórios 88 (`--check`) | local + CI | OK (1.792 séries) |
| Auditoria independente `auditoria_pr6.py` | local + CI | PASSOU |
| Build estático Next.js | local + CI | OK (10 rotas) |
| E2E Playwright (desktop, Android, iPhone 320 px) + axe | CI | OK; local: 131/138 na 1ª execução (7 expectativas desatualizadas, corrigidas) e 61/61 nos specs afetados |
| Motor Universal (Parquet, anti-leakage, cobertura, KNN bloqueado) | CI | OK |
| Patrimônio MCPSE | CI | OK (local Windows: 3 erros de bloqueio de arquivo/dependência, não relacionados) |
| Checks 2025 | CI | OK |
| Preview Vercel do commit | Vercel `dpl_HfeMvpyenu3dgM6CJFTduE99oF4j` | READY |

## Bloqueios encontrados e resolvidos

1. **Manifesto do contrato nacional com hashes inválidos** (prefixo de zeros) e gate com 319 erros: contrato regenerado por `87_contrato_nacional.py`; valores e estados idênticos; validador passou a conferir as 13 republicações contra a decisão registrada.
2. **GitHub Actions `action_required`**: o workflow web tinha um passo temporário com `contents: write` que fazia push no branch do PR #14 com o `GITHUB_TOKEN`. Removido; permissões agora `contents: read` e `persist-credentials: false`. Novos pushes do usuário acionam o CI normalmente (4/4 verdes).
3. Artefatos derivados desatualizados após a seleção das republicações (cobertura do motor, KNN real, estágio 88, testes E2E e auditoria): regenerados ou atualizados, sem alterar dados brutos nem checkpoints.

## Ação necessária para publicar (pelo responsável)

Uma das opções, pelos mecanismos oficiais:

- **Vercel (painel):** projeto `nucleo-dados-bdgd` → Deployments → criar deployment de produção a partir do commit `4ff0cc3` do branch `feat/motor-cenarios-publicacao-20261028` (ou "Redeploy" do preview `dpl_HfeMvpyenu3dgM6CJFTduE99oF4j` escolhendo *Production*).
- **Vercel CLI:** a partir de um checkout desse commit, `vercel deploy --prod` no projeto `nucleo-dados-bdgd` (escopo da equipe `arthurhenriqueelias-6367`).
- **Claude Code:** autorizar a ferramenta `create_deployment` da integração Vercel (regra de permissão) e pedir a publicação; o agente cria o deployment de produção desse mesmo commit.

**Acesso público:** o projeto tem *Vercel Authentication* ativa para todos os deployments exceto domínios personalizados (`ssoProtection: all_except_custom_domains`). Mesmo após a publicação, o endereço `*.vercel.app` de produção exigirá login na Vercel (HTTP 401/403 para visitantes). Para acesso público, o responsável deve adicionar um domínio personalizado ou ajustar a proteção em Settings → Deployment Protection. Essa configuração de segurança não foi alterada.

## Pendências

- Decidir o merge da pilha de PRs (#4 → … → #17); nenhum merge foi feito.
- `homologacao.json` versionado não é reproduzido byte a byte pelo `86_homologacao_web.py` versionado (estados e valores idênticos; diferem textos de motivo). Recomenda-se versionar a versão do 86 que gerou o asset.
- Potência de reguladores e de transformadores de medida: bloqueada (sem POT_NOM numérico auditável).
- Variáveis externas de mercado ANEEL (SAMP), DEC/FEC e EPE: não integradas; estimativas populacionais 2024–2025 e PIB 2022–2023 não usadas por disponibilidade/ano-base (ver `VARIAVEIS_INTERNAS_EXTERNAS.csv`).
- Homologação humana dos 13 pares, ponte EPB←EBO e demais decisões da Fase 4 continuam pendentes; a seleção da versão mais recente é critério técnico-editorial com ressalva.
