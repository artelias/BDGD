"use client";
import type { Indice } from "@/lib/confiabilidade/tipos";
import s from "./conf.module.css";

const n = (v: number | undefined) => (v ?? 0).toLocaleString("pt-BR");

/** Fontes, fórmulas, estados e limites do módulo. Os números de cobertura vêm do índice publicado, não de texto fixo. */
export function MetodologiaConf({ indice }: { indice: Indice }) {
  const t = indice.totais, f = indice.fontes;
  const grupos = [...new Set(indice.metricas.map((m) => m.grupo))];
  return (
    <div className={s.prosa} data-testid="conf-metodologia">
      <h3>Fontes</h3>
      <ul>
        <li><b>Continuidade (DEC, FEC, componentes, limites e NumCon):</b> {f.continuidade.nome}, <a href={f.continuidade.url} target="_blank" rel="noreferrer">dados abertos da ANEEL</a>, licença {f.continuidade.licenca}. Arquivo gerado pela ANEEL em {f.continuidade.gerado_pela_aneel_em}. Estado: <code>OBSERVADO_OFICIAL</code>.</li>
        <li><b>Infraestrutura por conjunto:</b> {f.infraestrutura.nome}. Estado: <code>DERIVADO_EXPLORATORIO</code> ({f.infraestrutura.nota}).</li>
        <li><b>Geometria:</b> {f.geometria.nome}, data-base {f.geometria.data_base}. São os polígonos publicados pelas distribuidoras, simplificados para visualização. As áreas de atuação (ARAT) só aparecem no nível Brasil e nunca representam conjuntos.</li>
        <li>O arquivo de atributos físico-elétricos dos conjuntos da ANEEL só tem dados até 2014; por isso não é usado.</li>
      </ul>

      <h3>Cobertura deste pacote</h3>
      <ul>
        <li>{n(t.distribuidoras)} distribuidoras e {n(t.conjuntos)} conjuntos com DEC/FEC em pelo menos um ano de {indice.anos[0]} a {indice.anos[indice.anos.length - 1]}; {n(t.conjunto_ano)} combinações conjunto × ano.</li>
        <li>{n(t.conjunto_ano_com_infra)} combinações têm infraestrutura da BDGD do mesmo ano; nas demais a infraestrutura aparece como N/D, com o motivo.</li>
        <li>{n(t.conjuntos_com_geo)} conjuntos têm polígono oficial em 31/12/2025. Conjuntos extintos antes disso ficam sem polígono; nenhum limite é desenhado para eles.</li>
        <li>Reconstrução do DEC/FEC pelos DIC/FIC da BDGD: calculada em {n(t.rec_calculado)} combinações e reconciliada com o oficial em {n(t.rec_validado)} (diferença de até {Math.round(indice.tolerancia_reconstrucao.relativa * 100)}% ou {indice.tolerancia_reconstrucao.absoluta.toLocaleString("pt-BR")} em valor absoluto).</li>
      </ul>

      <h3>Como o DEC e o FEC são calculados e agregados</h3>
      <ul>
        <li>DEC e FEC do conjunto são médias por consumidor: <code>DEC = Σ DIC ÷ Cc</code> e <code>FEC = Σ FIC ÷ Cc</code>, em que Cc é o número de consumidores do conjunto no período (PRODIST, Módulo 8). Somar DIC ou FIC dá só o numerador.</li>
        <li>O valor anual do conjunto é a soma dos 12 valores mensais apurados. Com menos de 12 meses, o ano aparece como apuração parcial.</li>
        <li>O valor de uma distribuidora ou grupo é a média dos conjuntos ponderada pelos consumidores de cada mês, somada nos meses. Nunca a média simples dos conjuntos. Esse agregado é derivado aqui e pode diferir em centésimos do global publicado pela ANEEL.</li>
        <li>Desempenho regulatório = apurado ÷ limite anual do conjunto. Os limites são anuais; por isso o mapa mensal só mostra valor absoluto.</li>
        <li>Os componentes mostram a origem (interna ou externa, programada ou não). Parcelas expurgadas (dia crítico, situação de emergência) não compõem o indicador apurado.</li>
      </ul>

      <h3>Oficial × reconstruído</h3>
      <p>O indicador oficial é sempre a referência. O reconstruído soma os DIC/FIC mensais das unidades consumidoras da BDGD do conjunto e divide pelo NumCon oficial de cada mês; serve para auditar a coerência entre as duas bases. A fotografia da BDGD é de 31/12 e não equivale à população faturada de cada mês, então o valor reconstruído nunca substitui o oficial.</p>

      <h3>Infraestrutura: regras físicas</h3>
      <ul>
        <li>Tudo é levado ao conjunto por chaves cadastrais da BDGD (CONJ, CTMT, UNI_TR_MT, UN_SE, UN_RE). Nenhum vínculo é criado por proximidade no mapa.</li>
        <li>Contagens são inteiras. Instalações (UN) e equipamentos (EQ) são visões diferentes da mesma população e nunca são somados.</li>
        <li>Um alimentador pode atender mais de um conjunto: cada conjunto recebe só a parcela cadastrada nele. O DEC/FEC do conjunto não é atribuído a alimentadores.</li>
        <li>Contagens de consumidores de 1 a {indice.supressao_k - 1} por alimentador não são publicadas. Nenhum dado individual de consumidor sai da base.</li>
        <li>Ausência é N/D, nunca zero, e fica fora de somas, médias e ordenações.</li>
      </ul>

      <h3>Comparações e pares</h3>
      <ul>
        <li>Pares semelhantes: os 20 conjuntos de outras distribuidoras mais próximos em porte, densidade, parcela não urbana, rede MT por consumidor e consumo por consumidor, em distância padronizada pelo intervalo interquartil nacional.</li>
        <li>Clima, vegetação, idade dos ativos, automação efetiva e práticas de operação não estão nestes dados. Semelhança de contexto reduz, mas não elimina, diferenças de território.</li>
        <li>Rankings e contrastes descrevem diferenças. Nenhum deles é evidência de eficiência ou de causa.</li>
      </ul>

      <h3>Dicionário de métricas</h3>
      {grupos.map((g) => (
        <div key={g}>
          <p style={{ margin: "12px 0 4px", color: "var(--text)", fontWeight: 620 }}>{g}</p>
          <ul>{indice.metricas.filter((m) => m.grupo === g).map((m) => <li key={m.id}><b>{m.nome}</b> ({m.unidade}): {m.definicao}</li>)}</ul>
        </div>
      ))}

      <h3>Proveniência</h3>
      <p>Contrato <code>{indice.contrato}</code>, gerado em {indice.gerado_em}. Cada arquivo publicado tem SHA-256 em <code>manifesto.json</code>; os arquivos da ANEEL usados estão identificados por SHA-256 e data de modificação no índice. O módulo é independente dos motores de previsão 2026–2030 e não altera os demais produtos do portal.</p>
    </div>
  );
}
