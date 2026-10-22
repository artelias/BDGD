# Modelo de duas camadas de fatos — total vs. DDA (BDGD 31/12/2025)

**Decisão em 22/10/2026, após segunda execução do Claude:** aceita a observação de que a matriz deve ser reconciliada contra **fatos-base**, sem duplicar categorias de domínio. A separação por DDA é necessária para os filtros interativos. Esta especificação esclarece `CONTRATO-DADOS-2025.md` e deve ser incorporada ao ETL. Não é necessário refazer os GDBs: as facetas podem ser geradas a partir do staging local por entidade.

## Grãos distintos: nunca misturar na mesma soma

### A — Fato-base `ativos_agregados.csv`
- **Exatamente uma linha por `DIST × entidade × DATA_BASE=2025-12-31`**.
- `dimensoes_json = {}` sem dimensão adicional; `quantidade`, `quantidade_registros`, `quantidade_cod_id_distinto`, `extensao_km`, `potencia_kva`, `status_qualidade`, `motivo_qualidade`. Ausência de uma métrica = CSV vazio, não 0.
- É a única fonte de `matriz_empresas_2025.csv` e dos KPIs nacionais **sem filtros técnicos DDA**, com exceção de cálculos compostos entre entidades que exigem regras próprias.
- `quantidade_cod_id_distinto` precisa ser obtida por `COUNT(DISTINCT)` no nível da entidade, não pela soma de distintos em categorias. `quantidade` para consumidores conflitantes pode ficar NULL até regra canônica homologada.
- Para uma empresa sem entidade BDGD identificada, publicar status de cobertura `nao_disponivel` em inventário separado. Não gerar zero artificial.

### B — Facetas `ativos_facetas.csv`
- Uma linha por **`DIST × entidade × facet_id × combinação dos códigos DDA × métrica`**; exatamente uma métrica por linha.
- `facet_id` associa as linhas a uma definição específica do catálogo de facetas.
- Campos: `dist,entidade,data_base,facet_id,dimensoes_json,metrica,valor,unidade,status_qualidade,motivo_qualidade`.
- Exemplo esquemático (NÃO é código DDA real): para uma entidade de rede com filtro conjunto `{localizacao,fas_con}`, armazenar uma única cubagem com as duas dimensões, e não somar separadamente histogramas de `localizacao` e `fas_con`.
- O atributo DDA só é permitido quando há mapeamento validado para entidade/campo/versão e o preenchimento correto. `desconhecido` deve ser categoria explícita só quando corresponde a dado sem código válido, **nunca** inventar correspondência descritiva.

### C — `facetas_catalogo.csv` (contrato de rollup)
Uma linha por `facet_id × entidade × metrica` com campos:
`facet_id,entidade,dimensoes_json,metrica,unidade,cobertura,particao_disjunta,permite_rollup,status_qualidade`.
- `dimensoes_json` = **array JSON de nomes de atributos oficiais** suportados em conjunto (ex.: `["ARE_LOC","FAS_CON"]`, sujeito à validação do esquema real).
- `cobertura`: `completa`, `parcial` ou `desconhecida`.
- `particao_disjunta`: `sim` ou `nao` — se uma única chave de ativo puder entrar em duas categorias do mesmo facet_id, marcar `nao`.
- `permite_rollup`: `sim` **somente** quando cobertura completa, partição disjunta e QA aprovado para **a métrica específica**. Caso contrário `nao`. **Não é seguro herdar essa permissão para `COUNT(DISTINCT)` de outro cubo.**
- `status_qualidade`: `aprovado`, `alerta`, `bloqueado`, `em_validacao`, `nao_aplicavel`.
- Uma faceta pode ser considerada homologada para um `DIST` e não para outro. Na primeira versão, usar configuração conservadora por faceta; qualquer caso de qualidade dependente da distribuidora deve ser controlado em `ativos_facetas.csv` e na API. A publicação `status_qualidade=aprovado` no catálogo **não implica aprovação universal**: verificar também as linhas de cada DIST.

## Exemplo matemático com dados fictícios

Suponha 10 UCBT distintas na empresa e 12 registros brutos.
- Se `ARE_LOC` é categorização exclusiva e completa: Urbana=7, Rural=3; `7+3=10`. `particao_disjunta=sim`, `cobertura=completa`, rollup permitido.
- Se o mesmo COD_ID tem área Urbana e Rural em registros conflitantes, as contagens distintas por área podem ser Urbana=8 e Rural=4. **8+4=12 não significa 12 UCs**. Rollup vetado; KPI total continua 10 e o filtro por área deve ser tratado como ambíguo ou apresentar os recortes auditados com ressalva, nunca inferir denominadores.
- Para filtro simultâneo `ARE_LOC=Urbana` e `FAS_CON=Trifásico`, usar **fato conjunto** `{ARE_LOC,FAS_CON}`. Não multiplicar percentuais nem realizar interseção aproximada dos totais marginais.
- Um facet_id não deve misturar métricas de linhas com graus de cobertura diferentes; resultados não homologados ficam N/D, não zero.

## Semântica exigida do backend

1. **Sem filtro DDA**: ler fato-base, não somar linhas de `ativos_facetas`.
2. **Com filtro**: buscar cubo com TODAS as dimensões filtradas e uma métrica explicitamente suportada; derivar subconjuntos e somar categorias não filtradas **somente com `permite_rollup=sim`**; se cobertura/QA não permitir, retornar `valor: null` + `status: "indisponivel_por_qualidade"`, não valor extrapolado.
3. **Múltiplos filtros DDA**: buscar faceta conjunta que contenha todas as dimensões e tenha comprovada aditividade para a métrica. Se faltar qualquer dimensão, retornar `combinacao_nao_suportada`, nunca multiplicar as marginais.
4. **Grupo econômico/país**: somar métricas por distribuidora só quando a métrica é aditiva entre DISTs (DISTs são partições por definição), sem duplicar controlador; para `COUNT(DISTINCT)` entre entidades, verificar interseção de chaves; se sobreposta, calcular união canônica no ETL.
5. **Comparador empresa × grupo**: aplicar mesma competência, métrica, DDA e cobertura separadamente a cada lado; indicar sempre o `número de DISTs` elegíveis em cada recorte.
6. **Reconciliar facetas com total-base**: somente quando `cobertura=completa`, `particao_disjunta=sim`, `permite_rollup=sim`, e nenhuma linha da combinação esteja bloqueada; a soma deve ser igual ao total da mesma métrica e DIST dentro da tolerância homologada. Os demais cubos não devem entrar nessa comparação como se fossem partições completas.
7. **Ausências**: se total-base existe e a faceta não, não preencher artificialmente a faceta. Exibir ativo no inventário, mas filtro não disponível.

## Contrato do manifesto

```json
{
  "schema_version": "1.1.0",
  "files": {
    "fatos": "ativos_agregados.csv",
    "matriz": "matriz_empresas_2025.csv",
    "facetas": "ativos_facetas.csv",
    "facetas_catalogo": "facetas_catalogo.csv"
  }
}
```

**Compatibilidade:** o validador aceita `schema_version=1.0.0` para pacotes-piloto **sem arquivos de facetas**, preservando o trabalho já feito. Para facetas em produção usar `1.1.0` e incluir ambos os arquivos, e só homologá-los após as verificações de partição acima. Um pacote 1.0.0 não atende filtros DDA técnicos do portal real.

## Situações identificadas no piloto

- Energisa AC (DIST 26): COD_ID duplicados/conflitantes em UCBT — números de registros e distintos separados; faceta de distintas marcada como não aditiva quando houver múltiplas categorias por COD_ID.
- CEA Equatorial (DIST 31): CTMT órfãos — facetas por circuito não disponíveis, sem invalidar métricas independentes.
- CPFL Santa Cruz (DIST 69): diferenças UNTRMT vs EQTRMT — preservar unidades e bloquear comparação automática das potências conflitantes.
- UG*/SIGFI e potência DDA com valores extremos — não somar nem corrigir automaticamente; potência N/D até regra dimensional confirmada.

## Estado
- Documento técnico e validador são **especificações de integração**, não dados oficiais e não prova de conformidade dos GDBs.
- Não foi recebida cópia do `D:\NUCLEO_BDGD_2025` nem os 135 logs de testes do piloto; números dependem do relatório do Claude encaminhado pelo usuário.
- BI VPE 2024 é **referência metodológica**, não gabarito quantitativo. BDGD 2025 é referência única de reconciliação.
