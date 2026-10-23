"use client";
import { motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { DataError, LoadingBlock } from "@/components/ui/Feedback";
import { Pill } from "@/components/ui/Value";
import { CONCEITOS, INDICADORES } from "@/lib/catalogo";
import type { Dataset } from "@/lib/dataset";
import { useData, useQualidade } from "@/lib/data-context";
import { fmt, fmtDate, METRIC_LABEL } from "@/lib/format";
import type { Metric } from "@/lib/types";
import p from "./pages.module.css";
import s from "./metodologia.module.css";

const SECS = [
  ["fonte", "Fonte e competência"], ["cobertura", "Cobertura"], ["regras", "Regras de contagem"], ["dicionario", "Dicionário de indicadores"], ["homologacao", "Homologação por métrica"],
  ["qualidade", "Qualidade e alertas"], ["grupos", "Grupos econômicos"], ["dda", "DDA e vínculos"], ["vpe", "BI VPE 2024"], ["privacidade", "Privacidade e licença"], ["reproducao", "Reprodutibilidade"],
] as const;

const ALERTA: Record<string, string> = {
  potencia_UG_acima_75kW: "Registros de unidades geradoras com POT_INST acima de 75 kW em BT (inclui sistemas SIGFI cujo valor não se comporta como kW). Valores preservados; potência de geração publicada como N/D.",
  uc_cod_id_ativo_duplicado: "Consumidores com mais de um registro ativado para o mesmo COD_ID (regra UC v2). Quantidade N/D; registros e distintos publicados.",
  uc_sobreposicao_entre_entidades: "COD_ID presente em mais de uma entidade UC (BT, MT, AT). Por isso o total de consumidores usa a união de códigos por distribuidora.",
  filtro_indisponivel: "Chaves de circuito/subestação que não existem na tabela de destino (> 5% de órfãos). O filtro fica indisponível; contagens independentes seguem válidas.",
  divergencia_potencia: "Potência total das unidades transformadoras diverge mais de 5% da potência dos equipamentos (via DDA). As duas visões não são somadas.",
  POT_NOM_provavel_MVA: "Unidades transformadoras com POT_NOM aparentemente em MVA (valor × 1000 coincide com o equipamento). Valor original preservado, com alerta.",
};
const HOMOL: Record<string, ["ok" | "warn" | "nd" | "default", string]> = {
  homologada: ["ok", "Homologada"], homologada_com_ressalvas: ["warn", "Com ressalvas"], nao_homologada: ["nd", "Não homologada"], informativa: ["default", "Informativa"],
};

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
  const homol = useMemo(() => ds.raw.homologacao.filter((h) => h.status !== "informativa"), [ds]);
  const nh = homol.reduce<Record<string, number>>((a, h) => { a[h.status] = (a[h.status] ?? 0) + 1; return a; }, {});

  return (
    <>
      <header className={`${p.head} rise`}>
        <div className="eyebrow">Proveniência · regras · qualidade</div>
        <h1 className="display" style={{ marginTop: 8 }}>Metodologia e qualidade</h1>
        <p className="lede">Como cada número foi obtido a partir das BDGDs oficiais de 31/12/2025, o que foi homologado, o que permanece N/D e por quê.</p>
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
            <p className="caption">Release <span className="mono">{rel.release_id}</span> · gerado em {fmtDate(rel.generated_at)} · status {rel.status === "homologado" ? "homologado" : "parcial (em validação)"} · contrato {rel.schema_version}</p>
          </section>

          <section id="cobertura" className={s.sec}>
            <h2>Cobertura</h2>
            <p>O universo considera toda distribuidora que já publicou BDGD no catálogo (2016–2025). Ausência de arquivo 2025 é um estado próprio, nunca zero.</p>
            <div className={s.scroll} tabIndex={0} role="region" aria-label="Tabela rolável">
              <table className={s.tbl}>
                <thead><tr><th>DIST</th><th>Distribuidora</th><th>Situação 2025</th><th>Observação</th></tr></thead>
                <tbody>
                  {cov.map((c) => (
                    <tr key={c.dist}>
                      <td className="num">{c.dist}</td><td>{c.sigla.replaceAll("_", " ")}</td>
                      <td>{c.status === "processada" ? <Pill tone="ok">Publicada</Pill> : c.status === "sem_publicacao_2025" ? <Pill tone="nd">Sem BDGD 2025</Pill> : c.status === "quarentena" ? <Pill tone="warn">Quarentena</Pill> : <Pill>Em processamento</Pill>}</td>
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
              <div className={s.rule}><dt>Quantidade</dt><dd>COUNT(*) dos registros da camada. Para consumidores (UCBT, UCMT, UCAT), COUNT(DISTINCT COD_ID) quando a regra UC v2 valida a entidade.</dd></div>
              <div className={s.rule}><dt>Regra UC v2</dt><dd>Um COD_ID repetido com um registro ativado (SIT_ATIV = AT) e outros desativados (DS) é histórico de estado no ano, não conflito. A contagem distinta é homologada quando não há COD_ID nulo, SIT_ATIV só assume AT/DS e há no máximo um registro ativado por COD_ID. Fora disso a quantidade fica N/D e registros e distintos continuam publicados.</dd></div>
              <div className={s.rule}><dt>Consumidores totais</dt><dd>As três entidades UC podem compartilhar códigos; o total por distribuidora usa a união de COD_ID, e só então soma-se entre distribuidoras.</dd></div>
              <div className={s.rule}><dt>Extensão (km)</dt><dd>SUM(COMP)/1000 dos segmentos SSDMT, SSDBT, SSDAT e RAMLIG — comprimento declarado na BDGD, não comprimento geométrico. Somas em decimal exato para que categorias reconciliem com o total.</dd></div>
              <div className={s.rule}><dt>Potência (kVA)</dt><dd>UNTRMT: POT_NOM em kVA; UNTRAT: POT_NOM em MVA × 1000; EQTRMT, EQTRAT, EQRE: código POT_NOM traduzido pela tabela DDA TPOTAPRT. Unidade e equipamento descrevem a mesma população e nunca são somados.</dd></div>
              <div className={s.rule}><dt>Geração (UG*)</dt><dd>Contagens publicadas. Potência instalada não homologada: há valores acima de 75 kW em BT e sistemas SIGFI cujo POT_INST não se comporta como kW. Nenhum corte artificial foi aplicado; o valor é N/D.</dd></div>
              <div className={s.rule}><dt>Entre distribuidoras</dt><dd>DISTs são partições: métricas por distribuidora são aditivas entre si. Grupos somam só vínculos verificados; distribuidoras sem grupo confirmado não entram em somas de grupo.</dd></div>
              <div className={s.rule}><dt>Filtros DDA</dt><dd>Cada filtro usa um cubo cujas dimensões são exatamente as filtradas. Sem cubo conjunto, a combinação é indisponível — nunca se multiplicam percentuais marginais.</dd></div>
            </dl>
          </section>

          <section id="dicionario" className={s.sec}>
            <h2>Dicionário de indicadores · Como é calculado?</h2>
            <p>Cada indicador do painel em linguagem direta, com o cálculo técnico e as ressalvas. Os nomes de negócio são os mesmos usados no Panorama, na Matriz e no Comparador.</p>
            {CONCEITOS.filter((c) => INDICADORES.some((i) => i.conceito === c.id)).map((c) => (
              <div key={c.id}>
                <h3>{c.nome}</h3>
                <dl>
                  {INDICADORES.filter((i) => i.conceito === c.id).map((i) => (
                    <div key={i.id} className={s.rule} id={`ind-${i.id}`}>
                      <dt>{i.nome}<div className="caption mono" style={{ fontWeight: 400, marginTop: 2 }}>{i.ent ?? "UCBT+UCMT+UCAT"} · {METRIC_LABEL[i.metric]}</div></dt>
                      <dd>{i.explicacao}<div className="mono caption" style={{ marginTop: 6 }}>{i.tecnico}</div>{i.ressalva && <div className="caption" style={{ marginTop: 4, color: "var(--warn)" }}>{i.ressalva}</div>}</dd>
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

          <section id="homologacao" className={s.sec}>
            <h2>Homologação por métrica</h2>
            <p>Critério: reconciliação exata entre o agregado e uma leitura independente do GDB (contagens e somas) em cada distribuidora, mais o estado de qualidade por DIST. {nh.homologada ?? 0} métricas homologadas, {nh.homologada_com_ressalvas ?? 0} com ressalvas e {nh.nao_homologada ?? 0} não homologadas.</p>
            <div className={s.scroll} tabIndex={0} role="region" aria-label="Tabela rolável">
              <table className={s.tbl}>
                <thead><tr><th>Entidade</th><th>Métrica</th><th>Situação</th><th className="r">DIST com valor</th><th className="r">N/D</th><th className="r">Alertas</th><th className="r">Reconciliações</th></tr></thead>
                <tbody>
                  {homol.map((h) => (
                    <tr key={`${h.entidade}-${h.metrica}`}>
                      <td><span className="mono">{h.entidade}</span></td><td>{METRIC_LABEL[h.metrica as Metric] ?? "Potência instalada (kW)"}</td>
                      <td><Pill tone={HOMOL[h.status]?.[0] ?? "default"}>{HOMOL[h.status]?.[1] ?? h.status}</Pill></td>
                      <td className="r num">{h.comValor}</td><td className="r num">{h.nd}</td><td className="r num">{h.alerta}</td><td className="r num">{h.recOk}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section id="qualidade" className={s.sec}>
            <h2>Qualidade e alertas</h2>
            <p>Anomalias da fonte são preservadas e documentadas; nenhum dado oficial é corrigido. Alertas não bloqueiam métricas independentes corretas.</p>
            {!q.data ? <LoadingBlock lines={3} /> : (
              <>
                <table className={s.tbl}>
                  <thead><tr><th>Alerta</th><th className="r">Ocorrências</th></tr></thead>
                  <tbody>
                    {Object.entries(q.data.alertasPorTipo).sort((a, b) => b[1] - a[1]).map(([t, n]) => (
                      <tr key={t}><td><div style={{ fontWeight: 560 }}>{t.replaceAll("_", " ")}</div><div className="caption">{ALERTA[t] ?? ""}</div></td><td className="r num">{n}</td></tr>
                    ))}
                  </tbody>
                </table>
                <h3>Consumidores fora da regra UC v2</h3>
                <table className={s.tbl}>
                  <thead><tr><th>DIST</th><th>Entidade</th><th className="r">Registros</th><th className="r">COD_ID distintos</th><th>Motivo</th></tr></thead>
                  <tbody>{q.data.ucRegraV2.filter((u) => !u.valida).map((u) => <tr key={`${u.dist}${u.entidade}`}><td className="num">{u.dist} · {ds.dist(u.dist)?.sigla.replaceAll("_", " ")}</td><td className="mono">{u.entidade}</td><td className="r num">{fmt(u.registros)}</td><td className="r num">{fmt(u.distintos)}</td><td className="caption">{u.motivos}</td></tr>)}</tbody>
                </table>
                <h3>Áreas de atuação (ARAT)</h3>
                <p>Geometria exclusivamente da entidade ARAT de cada GDB 2025, reprojetada para EPSG:4326, simplificada preservando topologia em projeção equivalente local. Diferença máxima de área: <b className="num">{fmt(Math.max(...q.data.arat.map((a) => Math.abs(Number(a.dif_area_pct ?? 0)))), undefined)}%</b>; geometrias de saída válidas em {q.data.arat.filter((a) => a.valida_saida === "True").length} de {q.data.arat.length}. A vista nacional aplica simplificação adicional apenas para desenho; o detalhe de cada distribuidora usa o arquivo oficial do pacote.</p>
              </>
            )}
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
            <h2>DDA e vínculos</h2>
            <p>Descrições de códigos: catálogo <span className="mono">{rel.dda_version}</span>. Rótulos de atributos: Manual BDGD Revisão 5. Vínculos entre entidades (UN*/EQ*, CTMT, SUB, CONJ) validados com o catálogo de relacionamentos do IA Builder, por <span className="mono">DIST + COD_ID</span>; alvos polimórficos avaliados pela união dos destinos. A tabela de domínio TSIST não existe no catálogo M10 e seus códigos aparecem sem descrição.</p>
          </section>

          <section id="vpe" className={s.sec}>
            <h2>Relação com o BI VPE 2024</h2>
            <p>O BI VPE usa a BDGD de 31/12/2024 e serve apenas como referência metodológica (definições, filtros, estrutura). Não é gabarito quantitativo: os números deste portal são reconciliados exclusivamente com as BDGDs de 31/12/2025.</p>
            <p>A matriz de paridade entre as métricas deste portal e as do BI VPE está <b>bloqueada</b>: o arquivo do BI não está disponível no ambiente de processamento. Nenhuma equivalência entre TUC/A1 e os filtros do BI é afirmada até essa auditoria.</p>
          </section>

          <section id="privacidade" className={s.sec}>
            <h2>Privacidade e licença</h2>
            <p>{rel.privacidade} Nenhum arquivo GDB, Parquet ou identificador individual é publicado. {rel.licenca}</p>
            <p>Agregados calculados a partir dos dados abertos da ANEEL (BDGD). Desenvolvido por Arthur Henrique Elias de Lima · <a href="mailto:Arthur.henrique.elias@gmail.com">Arthur.henrique.elias@gmail.com</a>.</p>
          </section>

          <section id="reproducao" className={s.sec}>
            <h2>Reprodutibilidade</h2>
            <p>O pipeline (Python, GDAL/pyogrio, DuckDB, shapely) está versionado no repositório, com checkpoints por distribuidora, reconciliação contra a origem e validador estrutural do pacote. Os arquivos deste site são gerados a partir do pacote público validado, sem acesso a dados brutos.</p>
          </section>
        </article>
      </div>
    </>
  );
}
