"use client";
import { useEffect, useRef, useState } from "react";
import { consultarCodigo, parsePatrimonio, slotPatrimonial, type PatrimonioData } from "@/lib/patrimonio";
import s from "./motor-universal.module.css";

export function Patrimonio() {
  const [data, setData] = useState<PatrimonioData | null>(null), [error, setError] = useState("");
  const [tuc, setTuc] = useState("565"), [a1, setA1] = useState("01"), [slot, setSlot] = useState("A4"), [code, setCode] = useState("29"), [dist, setDist] = useState("");
  const controller = useRef<AbortController | null>(null), loading = useRef(false);
  useEffect(() => () => controller.current?.abort(), []);
  async function load() {
    if (data || loading.current) return;
    loading.current = true; setError(""); controller.current = new AbortController();
    try {
      const response = await fetch("/data/patrimonio/dicionario.json.gz", { signal: controller.current.signal });
      if (!response.ok) throw Error("Não foi possível carregar o dicionário patrimonial.");
      const buffer = await response.arrayBuffer(), b = new Uint8Array(buffer);
      const text = b[0] === 31 && b[1] === 139 ? await new Response(new Blob([buffer]).stream().pipeThrough(new DecompressionStream("gzip"))).text() : new TextDecoder().decode(buffer);
      setData(parsePatrimonio(JSON.parse(text)));
    } catch (e) { if (!(e instanceof DOMException && e.name === "AbortError")) setError(e instanceof Error ? e.message : "Falha na leitura."); }
    finally { loading.current = false; }
  }
  const t = data?.tucs[tuc], bem = t?.bens[a1] ? a1 : Object.keys(t?.bens ?? {})[0] ?? "";
  const spec = slotPatrimonial(t, bem, slot), result = data ? consultarCodigo(data, tuc, bem, slot, code) : undefined;
  const groups = data?.agregados_tipo_bem.filter((r) => r.TUC === tuc && (!bem || r.A1 === bem) && (!dist || r.DIST === dist)) ?? [];
  const quantidade = groups.length ? groups.reduce((sum, r) => sum + r.quantidade, 0) : null;
  return <section className={s.section} data-testid="patrimonio" aria-label="Dicionário patrimonial MCPSE e BDGD">
    <h2>Dicionário patrimonial · TUC e A1–A6</h2>
    <p>Caracterização documental dos bens. Códigos patrimoniais e códigos DDA pertencem a tabelas diferentes; não são intercambiáveis.</p>
    <details onToggle={(e) => { if (e.currentTarget.open) void load(); }}>
      <summary>Consultar atributos patrimoniais</summary>
      {!data ? error ? <div role="alert">{error} <button onClick={() => void load()}>Tentar novamente</button></div> : <p role="status">Carregando dicionário…</p> : <>
        <p role="status"><b>Vigência normativa pendente.</b> Documento integral lido: Revisão {data.source.revisao_lida}. A Revisão 3 e sua aplicação por ano ainda precisam de conferência integral. Nenhum valor desta consulta altera targets ou habilita variáveis nos modelos.</p>
        <p>{Object.keys(data.tucs).length} TUCs documentais · {data.observados_cubos_2025.length} códigos de TUC observados nos cubos de 2025 · {data.auditoria.arquivos_parquet_listados.toLocaleString("pt-BR")} Parquets listados no pacote, sem acesso aos registros neste ambiente.</p>
        <div className={s.filters}>
          <label>TUC patrimonial<select value={tuc} onChange={(e) => { setTuc(e.target.value); setA1(""); }}>
            {[...new Set([...data.observados_cubos_2025, ...Object.keys(data.tucs)])].sort().map((tc) => <option key={tc} value={tc}>{tc} · {data.tucs[tc]?.nome ?? "Sem definição conferida"}</option>)}
          </select></label>
          <label>Tipo de bem A1<select value={bem} onChange={(e) => setA1(e.target.value)} disabled={!t}>{Object.values(t?.bens ?? {}).map((b) => <option key={b.codigo} value={b.codigo}>{b.codigo} · {b.descricao_documental || "Descrição individual pendente"}</option>)}</select></label>
          <label>Atributo patrimonial<select value={slot} onChange={(e) => setSlot(e.target.value)}>{["A1", "A2", "A3", "A4", "A5", "A6"].map((v) => <option key={v}>{v}</option>)}</select></label>
          <label>Código do atributo<input value={code} onChange={(e) => setCode(e.target.value)} inputMode="text" maxLength={20} style={{ minHeight: 44, minWidth: 0, width: "100%", boxSizing: "border-box" }} /></label>
          <label>DIST do agregado publicado<select value={dist} onChange={(e) => setDist(e.target.value)}><option value="">Todas as DIST disponíveis</option>{[...new Set(data.agregados_tipo_bem.map((r) => r.DIST))].sort((a, b) => Number(a) - Number(b)).map((id) => <option key={id}>{id}</option>)}</select></label>
        </div>
        <p><b>{slot}: {slot === "A1" ? "Tipo de bem" : spec?.nome ?? "Significado não verificado"}</b> · Tabela {slot === "A1" ? "I" : spec?.tabela ?? "N/D"}.</p>
        <div role="status" data-testid="patrimonio-traducao"><p>{result?.status}</p>{result?.valores.map((v, i) => <p key={`${v.codigo}-${i}`}><b>{v.codigo}</b> · {v.descricao} · página {v.pagina}. Valor pontual: {v.valor_tecnico ?? "N/D"} {v.unidade ?? ""}{v.natureza_valor === "FAIXA" ? " — faixa normativa; não equivale a valor nominal exato" : ""}.</p>)}</div>
        <p><b>Agregado publicado de 2025 por TUC e A1:</b> {quantidade === null ? "N/D — sem grupo publicado para este recorte" : quantidade.toLocaleString("pt-BR") + " registros"}. O código consultado de A2–A6 não filtra essa quantidade: esses atributos não estão no cubo conjunto disponível. Equipamentos e instalações não são somados.</p>
        <p><b>Potência recuperável:</b> N/D. A tabela IIIB possui {data.auditoria.tabela_IIIB.codigos} entradas documentais e nenhuma potência pontual inequívoca. Em TUC 340, potência é A3; em 565/570 é A4; em 575, A4 é relação de corrente/tensão. Não usar limite de faixa como potência exata.</p>
        <p><b>Painel de variáveis:</b> TUC, A1–A6, traduções, códigos originais, unidades, fonte, referência, disponibilidade e rupturas são previstos no contrato de enriquecimento. O envio ao motor permanece bloqueado até vigência, proveniência dos registros e comparabilidade serem verificadas.</p>
        <a className={s.export} download={`patrimonio_${tuc}_${bem}_${slot}.json`} href={`data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify({ schema_version: data.schema_version, TUC: tuc, A1: bem, atributo: slot, codigo_original: code, consulta: result, fonte: data.source, elegivel_modelo: false, potencia_recuperada_homologada_kva: null, limites: data.limites }, null, 2))}`}>Exportar consulta patrimonial (JSON)</a>
        <p className={s.provenance}>Fonte documental SHA-256 <code>{data.source.sha256}</code>. <a href={`${data.source.url}#page=${result?.valores[0]?.pagina ?? spec?.pagina ?? 173}`} target="_blank" rel="noreferrer">Consultar página normativa referenciada</a>.</p>
      </>}
    </details>
  </section>;
}
