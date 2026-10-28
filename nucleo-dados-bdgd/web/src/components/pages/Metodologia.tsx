"use client";
import { ObservacoesDados } from "@/components/ui/ObservacoesDados";
import { motion } from "motion/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { DataError, LoadingBlock } from "@/components/ui/Feedback";
import { Pill } from "@/components/ui/Value";
import { CONCEITOS, INDICADORES } from "@/lib/catalogo";
import type { Dataset } from "@/lib/dataset";
import { useData, useQualidade } from "@/lib/data-context";
import { fmt, fmtDate, METRIC_LABEL } from "@/lib/format";
import p from "./pages.module.css";
import s from "./metodologia.module.css";

const SECS = [
  ["fonte", "Fonte e competência"], ["cobertura", "Cobertura"], ["regras", "Regras de contagem"], ["dicionario", "Dicionário de indicadores"],
  ["grupos", "Grupos econômicos"], ["dda", "Classificação e vínculos"], ["privacidade", "Privacidade e licença"], ["modelo-matematico", "Modelagem matemática"],
] as const;

export function Metodologia() {
  const data = useData();
  if (data.status === "loading") return <LoadingBlock lines={8} />;
  if (data.status === "error") return <DataError error={data.error} />;
  return <MetodologiaReady ds={data.ds} />;
}

function MetodologiaReady({ ds }: { ds: Dataset }) {
  const q = useQualidade();
  const rel = ds.raw.release;
  const [active, setActive] = useState<string>("fonte");
  useEffect(() => {
    const io = new IntersectionObserver((es) => { const v = es.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0]; if (v) setActive(v.target.id); }, { rootMargin: "-80px 0px -60% 0px" });
    SECS.forEach(([id]) => { const el = document.getElementById(id); if (el) io.observe(el); });
    return () => io.disconnect();
  }, []);
  const cov = ds.raw.cobertura;

  return (
    <>
      <header className={`${p.head} rise`}>
        <div className="eyebrow">Proveniência · indicadores · modelos</div>
        <h1 className="display" style={{ marginTop: 8 }}>Metodologia dos ativos físicos</h1>
        <p className="lede">Definições das métricas físicas, classificação patrimonial, vínculos elétricos e metodologia de previsão; dados observados e projeções são apresentados separadamente.</p>
      </header>
      <div className={s.layout}>
        <nav className={s.toc} aria-label="Seções">
          {SECS.map(([id, t]) => (
            <a key={id} href={`#${id}`} aria-current={active === id}>
              {active === id && <motion.span layoutId="toc-bar" className={s.tocBar} transition={{ type: "spring", stiffness: 480, damping: 40 }} />}
              {t}
            </a>
          ))}
        </nav>
        <article className={s.article}>
          <section id="fonte" className={s.sec}>
            <h2>Fonte e competência</h2>
            <p>Os dados vêm da Base de Dados Geográfica da Distribuidora (BDGD), publicada pela ANEEL como File Geodatabase por distribuidora no <a href="https://dadosabertos-aneel.opendata.arcgis.com/search?tags=distribuicao" target="_blank" rel="noreferrer">catálogo de dados abertos</a>. A competência é única: <b>DATA_BASE = 31/12/2025</b>. Nenhuma distribuidora sem arquivo 2025 é preenchida com 2024 ou 2026.</p>
            <ul>
              <li>Inventário por API (paginação completa de todos os itens GDB do órgão), filtro pela data-base no título e na etiqueta do item.</li>
              <li>Validação no conteúdo: entidade <span className="mono">BASE</span> com <span className="mono">DAT_FNL = 31/12/2025</span>, <span className="mono">DIST</span> idêntico em todas as camadas e coluna <span className="mono">DATA_BASE</span> de cada registro igual a 2025-12-31.</li>
              <li>Integridade: download retomável, SHA-256 de cada arquivo e teste do ZIP; o hash aparece no painel de cada distribuidora.</li>
            </ul>
            <div className={s.stats}>
              <div className={s.stat}><div className={s.statNum}>{rel.cobertura.com_gdb_2025}</div><div className="caption">GDBs 2025 publicados</div></div>
              <div className={s.stat}><div className={s.statNum}>{rel.cobertura.processadas}</div><div className="caption">processados neste release</div></div>
              <div className={s.stat}><div className={s.statNum}>{ds.entidades.length}</div><div className="caption">entidades com agregados</div></div>
              <div className={s.stat}><div className={s.statNum}>{q.data ? fmt(q.data.reconciliacao.ok ?? 0) : "…"}</div><div className="caption">reconciliações exatas com a origem</div></div>
            </div>
            <p className="caption">Release <span className="mono">{rel.release_id}</span> · gerado em {fmtDate(rel.generated_at)} · estado {rel.status === "homologado" ? "auditado tecnicamente" : "parcial (em validação)"} · contrato {rel.schema_version}</p>
          </section>

          <section id="cobertura" className={s.sec}>
            <span id="qualidade" className="sr-only" aria-hidden="true" />
            <h2>Cobertura</h2>
            <p>O universo considera toda distribuidora que já publicou BDGD no catálogo (2016–2025). Ausência de arquivo 2025 é um estado próprio, nunca zero.</p>
            <div className={s.scroll} tabIndex={0} role="region" aria-label="Tabela rolável">
              <table className={s.tbl}>
                <thead><tr><th>DIST</th><th>Distribuidora</th><th>Situação 2025</th><th>Observação</th></tr></thead>
                <tbody>
                  {cov.map((c) => (
                    <tr key={c.dist}>
                      <td className="num">{c.dist}</td><td>{c.sigla.replaceAll("_", " ")}</td>
                      <td>{c.status === "processada" ? <Pill tone="ok">Publicada</Pill> : c.status === "sem_publicacao_2025" ? <Pill tone="nd">Publicação não localizada</Pill> : c.status === "quarentena" ? <Pill tone="warn">Bloqueio técnico — ver motivo</Pill> : <Pill>Estado técnico: {c.status}</Pill>}</td>
                      <td className="caption">{c.motivo}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section id="regras" className={s.sec}>
            <h2>Regras de contagem e unidades</h2>
            <dl>
              <div className={s.rule}><dt>Quantidade</dt><dd>A medida depende do conceito e do recorte escolhido. A visão técnica por entidade pode mostrar registros ou códigos distintos; esses valores não são intercambiáveis com o total de consumidores do catálogo.</dd></div>
              <div className={s.rule}><dt>Regra UC v3</dt><dd>O catálogo vigente conta cada unidade consumidora por código anonimizado e ponto de conexão, dentro da distribuidora. Panorama, Explorar e histórico usam essa definição; a união legada de COD_ID da regra UC v2 não deve ser interpretada como o mesmo indicador.</dd></div>
              <div className={s.rule}><dt>Consumidores totais</dt><dd>O total segue a regra UC v3 e o estado de publicação do contrato. Ausências e anomalias permanecem N/D. Uma contagem zero no agregado é um zero técnico; não comprova, isoladamente, ausência física de consumidores. Não aplicável e não homologado são estados distintos.</dd></div>
              <div className={s.rule}><dt>Extensão (km)</dt><dd>SUM(COMP)/1000 dos segmentos SSDMT, SSDBT, SSDAT e RAMLIG — comprimento declarado na BDGD, não comprimento geométrico. Somas em decimal exato para que categorias reconciliem com o total.</dd></div>
              <div className={s.rule}><dt>Potência (kVA)</dt><dd>UNTRMT: POT_NOM em kVA; UNTRAT: POT_NOM em MVA × 1000; EQTRMT, EQTRAT, EQRE: código POT_NOM traduzido pela tabela DDA TPOTAPRT. Unidade e equipamento descrevem a mesma população e nunca são somados.</dd></div>
              <div className={s.rule}><dt>Geração (UG*)</dt><dd>Contagens publicadas. Potência instalada não homologada: há valores acima de 75 kW em BT e sistemas SIGFI cujo POT_INST não se comporta como kW. Nenhum corte artificial foi aplicado; o valor é N/D.</dd></div>
              <div className={s.rule}><dt>Entre distribuidoras</dt><dd>DISTs são partições: métricas por distribuidora são aditivas entre si. Grupos somam só vínculos verificados; distribuidoras sem grupo confirmado não entram em somas de grupo.</dd></div>
              <div className={s.rule}><dt>Filtros DDA</dt><dd>Cada filtro usa um cubo cujas dimensões são exatamente as filtradas. Sem cubo conjunto, a combinação é indisponível — nunca se multiplicam percentuais marginais.</dd></div>
            </dl>
            <h3>Regras por categoria e subcategoria patrimonial</h3>
            <p>A quantidade física decorre da população de equipamentos elegíveis, identificada pelo par entidade e TUC/A1, sob DIST e competência constantes; chaves COD_ID são preservadas para prova de unicidade, não para agrupamento estatístico.</p>
            <dl>
              <div className={s.rule}><dt>Transformadores de distribuição</dt><dd>Equipamentos EQTRMT/EQTRAT com TUC 565; A1 identifica tipo do bem; A2 tensão primária; A3 secundária; A4 faixa de potência; A5 fases e A6 proteção. UNTRMT/UNTRAT informam contexto e não são somadas ao estoque EQ.</dd></div>
              <div className={s.rule}><dt>Transformadores de força</dt><dd>Equipamentos EQTRMT/EQTRAT com TUC 570; A2 e A3 descrevem tensões, A4 faixa patrimonial, A5 fases e A6 comutação. Instalações UN* não são contadas novamente.</dd></div>
              <div className={s.rule}><dt>Transformadores de medida</dt><dd>Equipamentos EQTRM com TUC 575; A3 representa relação de transformação e A4 corrente/tensão condicionada ao tipo de bem A1. Não representa potência nominal exata.</dd></div>
              <div className={s.rule}><dt>Chaves / disjuntores / religadores</dt><dd>Contagens distintas por TUC 160, 210 e 345 dentro de EQSE. Atributos A2–A6 descrevem tensão, corrente, fases, isolamento, controle e interrupção conforme a TUC. UNSE* são vínculos.</dd></div>
              <div className={s.rule}><dt>Reguladores</dt><dd>Equipamentos EQRE, TUC 340: A2 tensão, A3 faixa patrimonial de potência, A4 corrente, A5 fases. Não confundir quantidade com kVA.</dd></div>
              <div className={s.rule}><dt>Postes e torres</dt><dd>Na TUC 255, A1=01 indica poste e A1=02 torre; A2 é tipo construtivo, A3 material, A4 altura (Tabela IX) e A5 esforço (Tabela X). Confrontar com PONNOT.TIP_PN.</dd></div>
              <div className={s.rule}><dt>Redes e ramais</dt><dd>Extensão de SSDBT, SSDMT, SSDAT e RAMLIG calculada por soma do comprimento declarado COMP, em metros, dividida por 1.000; separar BT, MT, AT e ramais.</dd></div>
              <div className={s.rule}><dt>Alimentadores e circuitos</dt><dd>Número de circuitos MT em CTMT e AT em CTAT; quantidades de outros ativos atreladas somente quando os vínculos e a cardinalidade são verificáveis.</dd></div>
              <div className={s.rule}><dt>Consumidores e geradores</dt><dd>Contar unidades no grão próprio, por DIST e competência, diferenciando UCBT/UCMT/UCAT e UGBT/UGMT/UGAT. Ausências e duplicidades não viram zeros presumidos.</dd></div>
              <div className={s.rule}><dt>Capacitores, medidores e subestações</dt><dd>Contagem de EQCR por TUC, de EQME por equipamento e de SUB por subestação; subcategorias exigem a classificação patrimonial correta e não agregam equipamentos e instalações conjuntamente.</dd></div>
            </dl>
          </section>

          <section id="dicionario" className={s.sec}>
            <h2>Dicionário de indicadores · Como é calculado?</h2>
            <p>O dicionário descreve a população física de referência, a entidade de origem, a unidade de medida e os critérios de classificação. Em equipamentos com TUC, os subgrupos patrimoniais são distinguidos por TUC e A1, sem somar a instalação correspondente.</p>
            {CONCEITOS.filter((c) => INDICADORES.some((i) => i.conceito === c.id)).map((c) => (
              <div key={c.id}>
                <h3>{c.nome}</h3>
                <dl>
                  {INDICADORES.filter((i) => i.conceito === c.id).map((i) => (
                    <div key={i.id} className={s.rule} id={`ind-${i.id}`}>
                      <dt>{i.nome}<div className="caption mono" style={{ fontWeight: 400, marginTop: 2 }}>{i.ent ?? "UCBT+UCMT+UCAT"} · {METRIC_LABEL[i.metric]}</div></dt>
                      <dd>{i.explicacao}<div className="caption" style={{ marginTop: 6 }}>População: {i.ent ?? "UCBT, UCMT e UCAT"}. Medida: {METRIC_LABEL[i.metric]}. {i.metric === "quantidade" ? "Contagem de unidades elegíveis da população indicada, por TUC e tipo de bem A1 quando presentes e aplicáveis. Chaves: TUC 160; disjuntores: 210; religadores: 345; reguladores: 340; transformadores de distribuição: 565; força: 570; medida: 575; estruturas: 255. As instalações UN* não são adicionadas à contagem EQ*." : i.metric === "extensao_km" ? "Soma dos comprimentos declarados, dividida por mil para obter quilômetros." : "Soma de potências nominais apenas após validar domínio, unidade, vínculo e competência; valor N/D enquanto essas condições não forem comprovadas."}</div>{i.ressalva && <div className="caption" style={{ marginTop: 4, color: "var(--warn)" }}>{i.ressalva}</div>}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ))}
            <h3>Recortes patrimoniais (TUC) e municípios</h3>
            <dl>
              <div className={s.rule}><dt>TUC e A1</dt><dd>Tipo de Unidade de Cadastro e Tipo de Bem conforme o MCPSE (Res. ANEEL 674/2015), lidos diretamente dos campos <span className="mono">TUC</span> e <span className="mono">A1</span> dos equipamentos (EQ*), barramentos e estruturas. O mesmo código A1 tem significado diferente em cada TUC, por isso só é descrito com o TUC fixado. Equipamentos podem apontar para a mesma instalação (UN*): o pacote publica, por TUC, quantos equipamentos têm vínculo válido e quantas instalações distintas eles ocupam.</dd></div>
              <div className={s.rule}><dt>Município</dt><dd>Código IBGE do campo <span className="mono">MUN</span>, presente em consumidores, geração, instalações (UN*), iluminação pública e estruturas. Redes (SSD*) não têm o campo: recorte municipal de rede exigiria junção espacial e não é publicado. Códigos fora da tabela IBGE ficam sem nome e são contados na qualidade.</dd></div>
              <div className={s.rule}><dt>Participação</dt><dd>Duas proporções no mesmo cubo e na mesma medida: a categoria dentro do recorte e o recorte dentro do Brasil. Ficam N/D se o cubo não cobre todas as distribuidoras que têm o ativo, se as categorias se sobrepõem ou se algum valor não está homologado.</dd></div>
              <div className={s.rule}><dt>Radar · Benchmark</dt><dd>Em cada eixo, A e a referência são divididos pelo valor da referência (lado B, total Brasil, maior grupo ou maior distribuidora): a referência fica em 100% e A pode passar de 100%. Eixos sem valor de algum lado saem do gráfico. Volume maior não significa desempenho melhor.</dd></div>
            </dl>
          </section>

          <section id="grupos" className={s.sec}>
            <h2>Grupos econômicos</h2>
            <p>Controlador vigente em 31/12/2025, comprovado por publicação oficial da holding ou ato do regulador. Mudanças concluídas depois da data-base não alteram 2025 (por exemplo, as transferências da Amazonas Energia e da Roraima Energia ao grupo J&F, concluídas em abril de 2026). Sem fonte verificável, a distribuidora fica “não confirmado” e não entra em somas de grupo.</p>
            <table className={s.tbl}>
              <thead><tr><th>Grupo</th><th>Controlador</th><th className="r">DIST</th><th>Fonte</th></tr></thead>
              <tbody>{ds.grupos.map((g) => <tr key={g.id}><td style={{ fontWeight: 600 }}>{g.nome}</td><td className="caption">{g.controlador}</td><td className="r num">{ds.groupDists(g.id).length}</td><td className="caption">{g.fontes.map((f, i) => <div key={f}><a className={s.srcLink} href={f} target="_blank" rel="noreferrer">fonte {i + 1}</a></div>)}</td></tr>)}</tbody>
            </table>
            <p className="caption">{ds.dists.filter((d) => d.grupo_status !== "verificado").length} distribuidoras processadas sem grupo confirmado (municipais, independentes e cooperativas). Consulta às fontes em {ds.grupos[0]?.consultado_em}.</p>
          </section>

          <section id="dda" className={s.sec}>
            <h2>Classificação patrimonial e conectividade elétrica</h2>
            <p>A interpretação de um atributo A2–A6 é condicional ao par TUC × A1: códigos numéricos não têm significado isolado. O MCPSE estabelece as características patrimoniais por tipo de bem; o DDA estabelece domínios de atributos operacionais e de equipamentos, cuja equivalência temporal precisa ser comprovada.</p>
            <p>Em transformadores TUC 565 e 570, A2 é tensão primária, A3 secundária e A4 representa <b>faixa patrimonial</b>, não potência nominal pontual. UNTRMT.POT_NOM expressa kVA, UNTRAT.POT_NOM expressa MVA (conversão × 1.000) e EQTRMT/EQTRAT.POT_NOM é um código de domínio DDA. Não se somam as potências de instalações e equipamentos da mesma população.</p>
            <p>Os relacionamentos entre equipamentos e instalações (EQ–UN) e entre instalações, circuitos CTMT/CTAT, subestações SUB e conjuntos CONJ são vinculados por chaves de cadastro com avaliação de cardinalidade e órfãos. Conexões elétricas não são inferidas somente pela proximidade cartográfica. A tradução depende da competência, da referência documental e da cobertura de dados.</p>
            <p className="caption">Referências documentais: MCPSE, Manual BDGD, catálogo DDA {rel.dda_version} e inventários geográficos publicados.</p>
          </section>

          <section id="privacidade" className={s.sec}>
            <h2>Privacidade e licença</h2>
            <p>{rel.privacidade} Nenhum arquivo GDB, Parquet ou identificador individual é publicado. {rel.licenca}</p>
            <p>Agregados calculados a partir dos dados abertos da ANEEL (BDGD). Desenvolvido por Arthur Henrique Elias de Lima · <a href="mailto:Arthur.henrique.elias@gmail.com">Arthur.henrique.elias@gmail.com</a>.</p>
          </section>

          <section id="modelo-matematico" className={s.sec}>
            <h2>Modelagem matemática e estatística</h2>
            <p>Especificação científica do Motor de Expansão Elétrica. As expressões de inventário abaixo descrevem os cálculos físicos; as equações estruturais de demanda e investimento são <b>hipóteses de modelagem, ainda não estimadas ou validadas</b>. A página <Link href="/previsoes/">Previsões</Link> já permite comparar persistência e tendência linear em simulações condicionais do estoque, com backtest limitado. Isso não estima elasticidades econômicas, intervalos probabilísticos de previsão ou CAPEX.</p>
            <h3>1. Definições e observações</h3>
            <p>Seja <span className="mono">i</span> uma distribuidora com perímetro territorial comparável, <span className="mono">t</span> o ano e <span className="mono">k</span> o conceito de ativo. <span className="mono">A(i,t,k)</span> é o estoque físico, <span className="mono">U(i,t)</span> o número de unidades consumidoras, <span className="mono">D(i,t)</span> a demanda máxima coincidente, <span className="mono">S(i,t)</span> a capacidade instalada e <span className="mono">L(i,t)</span> a extensão de rede.</p>
            <dl className={s.rule}><dt>Inventário de equipamentos</dt><dd><code>A(i,t,k) = Σ 1[TUC(e) = k]</code><p className="caption">Soma sobre equipamentos elegíveis, dentro de DIST e ano. A instalação UN* correspondente não é novamente somada como outro equipamento.</p></dd></dl>
            <dl className={s.rule}><dt>Extensão da rede</dt><dd><code>L(i,t,v) = (1 / 1000) × Σ COMP(s)</code><p className="caption">Soma dos comprimentos declarados, em metros, dos segmentos elegíveis da classe de tensão v; resultado em km. Não confundir comprimento declarado com geometria cartográfica.</p></dd></dl>
            <dl className={s.rule}><dt>Variação de estoque</dt><dd><code>A(i,t+1,k) = A(i,t,k) + Eexp + Esub − Rsub − B</code><p className="caption">Eexp: entradas por expansão; Esub: entradas por substituição; Rsub: retiradas por substituição; B: outras baixas. Diferenças entre inventários anuais não identificam isoladamente CAPEX ou obras executadas.</p></dd></dl>
            <h3>2. Modelo estrutural de demanda</h3>
            <p>Uma hipótese econométrica candidata para a demanda, sujeita à disponibilidade e à qualidade das séries, é:</p>
            <dl className={s.rule}><dt>Demanda condicionada</dt><dd><code>ln D(i,t) = α(i) + β₁ ln U(i,t−1) + β₂ ln PIBreal(i,t−1) + β₃ X(i,t−1) + γ(t) + ε(i,t)</code><p className="caption">X representa covariáveis elétricas e econômicas previamente selecionadas (por exemplo, indústria, geração distribuída e perfil de carga). α é o efeito da distribuidora; γ é um efeito temporal quando identificável. PIB e outras variáveis devem respeitar a geografia da concessão, a defasagem de publicação e o corte temporal da previsão. Não se presume causalidade apenas pela regressão.</p></dd></dl>
            <h3>3. Capacidade e conectividade</h3>
            <dl className={s.rule}><dt>Capacidade aparente requerida</dt><dd><code>Sreq(i,t) = Dpico(i,t) / [FP(i,t) × ρalvo(i,t)]</code><p className="caption">Aplicável quando Dpico está em potência ativa, FP é fator de potência válido e ρalvo é o carregamento-alvo. Não converte automaticamente kVA em número de transformadores: são necessárias reserva efetiva, localização, granularidade dos equipamentos, restrições de rede e redundância.</p></dd></dl>
            <dl className={s.rule}><dt>Expansão física</dt><dd><code>Nnovo(i,t,k) = fₖ(Dpico, Sdisponível, topologia, dispersão, qualidade, custos)</code><p className="caption">A função fₖ depende da família de ativos e só será especificada empiricamente após auditoria dos vínculos SUB → CTMT → transformadores → segmentos → UC. Proximidade geográfica não prova conectividade elétrica.</p></dd></dl>
            <h3>4. Economia da distribuição e investimento</h3>
            <dl className={s.rule}><dt>Investimento condicional</dt><dd><code>CAPEX(i,t) = Σₖ qnovo(i,t,k) × creal(i,t,k) + Creforço + Csubstituição</code><p className="caption">qnovo é o volume executável, não apenas a necessidade técnica; creal é o custo unitário real no ano-base de preços. Juros, custo de capital, câmbio, restrições orçamentárias e ciclo regulatório podem afetar cronograma e custos. Valores nominais exigem deflator documentado.</p></dd></dl>
            <h3>5. Modelos candidatos e variáveis efetivamente disponíveis</h3>
            <dl>
              <div className={s.rule}><dt>Persistência</dt><dd><code>ŷ(i,t+h) = y(i,t)</code>. Conserva o último estoque observado. Não requer variáveis externas.</dd></div>
              <div className={s.rule}><dt>Tendência linear</dt><dd><code>ŷ(i,t+h) = α̂(i) + β̂(i) × (t+h)</code>. Ajusta a trajetória temporal por mínimos quadrados. Não requer variáveis externas.</dd></div>
              <div className={s.rule}><dt>Crescimento histórico</dt><dd>Estima evolução proporcional a partir de observações positivas e comparáveis. A projeção é condicional à continuidade da dinâmica histórica.</dd></div>
              <div className={s.rule}><dt>Ridge, Lasso e Elastic Net</dt><dd>Modelos de regressão regularizada para covariáveis correlacionadas; dependem de amostra suficiente e avaliação temporal sem vazamento.</dd></div>
              <div className={s.rule}><dt>Poisson, Random Forest e HistGradientBoosting</dt><dd>Alternativas para contagens e relações não lineares, sujeitas a disponibilidade de treino e validação fora da amostra. Cadastro no motor não significa desempenho real comprovado.</dd></div>
              <div className={s.rule}><dt>KNN de distribuidoras análogas</dt><dd>Compara distribuidoras usando variáveis comparáveis e disponíveis no instante do corte, com vizinhanças k=1, 3 e 5. Nenhum resultado real com exógenas verificadas foi liberado no contrato auditado.</dd></div>
            </dl>
            <p><b>Variáveis internas candidatas:</b> estoque histórico, TUC/A1–A6, extensão BT/MT/AT, consumidores, CTMT/CTAT, subestações, distribuição urbano/rural e conectividade comprovada. <b>Variáveis externas candidatas:</b> mercado e indicadores de continuidade da ANEEL, PIB/população/domicílios do IBGE e cenários setoriais da EPE. Nenhuma deve ser descrita como efetivamente utilizada sem fonte, data de divulgação, competência, perímetro, versão do dataset e validação temporal.</p>
            <h3>6. Identificação, validação e incerteza</h3>
            <p>Serão comparados modelos ingênuos, tendências simples, regressões regularizadas e modelos híbridos físico-estatísticos apenas quando os dados forem suficientes. A inclusão de variáveis macroeconômicas depende de melhoria verificável fora da amostra, estabilidade e coerência de engenharia.</p>
            <dl className={s.rule}><dt>Erro absoluto médio</dt><dd><code>MAE = (1/n) × Σ |y(t) − ŷ(t)|</code></dd></dl>
            <dl className={s.rule}><dt>Viés médio</dt><dd><code>BIAS = (1/n) × Σ [ŷ(t) − y(t)]</code></dd></dl>
            <dl className={s.rule}><dt>Erro percentual absoluto ponderado</dt><dd><code>WAPE = Σ |y(t) − ŷ(t)| / Σ |y(t)|</code><p className="caption">Somente quando o denominador é positivo e a agregação é comparável.</p></dd></dl>
            <p>O protocolo prevê validação com origem temporal móvel, comparação contra baselines, análise de resíduos e sensibilidade. O backtest exploratório disponível usa apenas uma origem temporal. Com somente quatro competências anuais (2022–2025), e históricos ainda não homologados, <b>não é possível afirmar desempenho robusto para horizontes longos nem calibrar intervalos probabilísticos confiáveis</b>. Os cenários disponíveis são simulações condicionais, sem homologação preditiva.</p>
            <h3>7. Incorporações e perímetros históricos</h3>
            <p>As séries de EPB devem considerar a sucessão EPB/EBO (2023), e as de EMR a sucessão EMG/ENF (2022). A reconstrução em perímetro comparável exige prova de não sobreposição dos GDBs e reconciliação por métrica. No ano de transição, não se somam automaticamente arquivos que já possam incluir a incorporada. Ausências e rupturas são N/D, jamais zero presumido.</p>
            <p className="caption">Estado desta documentação: inventário e regras de contagem BDGD 2025 são cálculos observados; demanda, capacidade futura, funções de expansão, CAPEX e modelos de erro são especificações de pesquisa até homologação e execução verificáveis.</p>
          </section>
        </article>
      </div>
      <ObservacoesDados />
    </>
  );
}
