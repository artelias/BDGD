"use client";
import { ArrowDown, Download, Info, Search, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { downloadText, EmptyState, LoadingBlock, useToast } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { displayName, type Dataset } from "@/lib/dataset";
import { useInventario } from "@/lib/data-context";
import { fmt } from "@/lib/format";
import { useQueryState } from "@/lib/url-state";
import s from "./explorar.module.css";

type Tipo = "sub" | "ctmt" | "ctat" | "conj";
const TITULO: Record<Tipo, string> = { sub: "Subestações", ctmt: "Alimentadores", ctat: "Circuitos de alta tensão", conj: "Conjuntos" };
const SINGULAR: Record<Tipo, string> = { sub: "subestação", ctmt: "alimentador", ctat: "circuito", conj: "conjunto" };
/** rótulo, unidade e casas: contagens por vínculo oficial deduplicado (equipamento -> instalação -> objeto) */
const METRICAS: Array<[string, string, "itens" | "km" | "kVA"]> = [
  ["consumidores", "Unidades consumidoras ativas", "itens"], ["alimentadores", "Alimentadores", "itens"], ["subestacoes", "Subestações que atendem", "itens"],
  ["trafo_dist", "Transformadores de distribuição", "itens"], ["trafo_dist_kva", "Potência dos transformadores de distribuição", "kVA"], ["trafo_forca", "Transformadores de força", "itens"],
  ["rede_mt_km", "Rede de média tensão", "km"], ["rede_bt_km", "Rede de baixa tensão", "km"], ["rede_at_km", "Rede de alta tensão", "km"], ["ramais_km", "Ramais de ligação", "km"],
  ["chaves", "Chaves", "itens"], ["religadores", "Religadores", "itens"], ["disjuntores", "Disjuntores", "itens"], ["reguladores", "Reguladores", "itens"],
  ["bancos_capacitores", "Bancos de capacitores", "itens"], ["iluminacao", "Pontos de iluminação pública", "itens"], ["geradores", "Geradores ativos", "itens"],
  ["barramentos", "Barramentos", "itens"], ["bays", "Bays", "itens"],
];
const ESPECIAL: Record<string, string> = { SEM_VINCULO: "Código sem cadastro correspondente", SEM_CODIGO: "Sem código informado", NA: "Sem o campo de vínculo" };
const COLUNAS: Record<Tipo, string[]> = {
  sub: ["alimentadores", "consumidores", "trafo_dist", "trafo_forca", "religadores", "chaves", "rede_mt_km"],
  ctmt: ["consumidores", "trafo_dist", "rede_mt_km", "rede_bt_km", "religadores", "chaves", "reguladores"],
  ctat: ["rede_at_km", "consumidores", "geradores"],
  conj: ["consumidores", "subestacoes", "alimentadores", "trafo_dist", "rede_mt_km", "rede_bt_km", "religadores"],
};
const norm = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function InventarioObjetos({ ds, tipo, dists }: { ds: Dataset; tipo: Tipo; dists: number[] }) {
  const [distQ, setDistQ] = useQueryState("inv_dist");
  const dist = dists.includes(Number(distQ)) ? Number(distQ) : dists.length === 1 ? dists[0] : null;
  return (
    <section className={s.inv} aria-labelledby="inv-titulo" data-testid="inventario">
      <div className={s.analysisHead}>
        <div>
          <h3 className="headline" id="inv-titulo" style={{ fontSize: "1rem" }}>{TITULO[tipo]} e ativos associados</h3>
          <p className="caption" style={{ marginTop: 2, maxWidth: "70ch", lineHeight: 1.5 }}>Cada {SINGULAR[tipo]} com os ativos ligados a ele pelos vínculos oficiais da BDGD. Equipamentos chegam pela instalação em que estão montados, contados uma única vez.</p>
        </div>
        {dists.length > 1 && (
          <Picker label="Distribuidora" value={dist !== null ? String(dist) : null} compact width={260} testId="inv-dist"
            options={dists.map((d) => ds.dist(d)!).map((d) => ({ value: String(d.dist), label: displayName(d), meta: `DIST ${d.dist}` }))} onChange={(v) => setDistQ(v)} />
        )}
      </div>
      {dist === null ? <EmptyState title={`Escolha uma distribuidora`}>A lista de {TITULO[tipo].toLowerCase()} é aberta por distribuidora.</EmptyState> : <Tabela ds={ds} tipo={tipo} dist={dist} />}
    </section>
  );
}

function Tabela({ ds, tipo, dist }: { ds: Dataset; tipo: Tipo; dist: number }) {
  const toast = useToast();
  const inv = useInventario(dist);
  const [q, setQ] = useState("");
  const [ord, setOrd] = useState<string>(COLUNAS[tipo][0]);
  const [selQ, setSel] = useQueryState("inv");
  const t = inv.data?.[tipo];
  const subNome = useMemo(() => new Map((inv.data?.sub?.rows ?? []).map((r) => [String(r[0]), String(r[1] ?? "")])), [inv.data]);
  const linhas = useMemo(() => {
    if (!t) return [];
    const ci = (c: string) => t.cols.indexOf(c);
    const tt = norm(q.trim());
    const out = t.rows.map((r) => ({ chave: String(r[ci("chave")]), nome: String(r[ci("nome")] ?? ""), r, get: (c: string) => (ci(c) >= 0 ? (r[ci(c)] as number | null) : null) }))
      .filter((x) => !tt || norm(`${x.nome} ${x.chave}`).includes(tt));
    const esp = (x: { chave: string }) => (x.chave in ESPECIAL ? 1 : 0);
    out.sort((a, b) => esp(a) - esp(b) || ((b.get(ord) ?? -1) - (a.get(ord) ?? -1)) || a.nome.localeCompare(b.nome));
    return out;
  }, [t, q, ord]);
  if (inv.loading) return <LoadingBlock lines={4} label="Carregando inventário" />;
  if (inv.error || !t) return <EmptyState title="Inventário indisponível" tone="warn">{inv.error ?? `Esta distribuidora não tem ${TITULO[tipo].toLowerCase()} cadastrados.`}</EmptyState>;
  const sel = linhas.find((x) => x.chave === selQ) ?? null;
  const cols = COLUNAS[tipo].filter((c) => t.cols.includes(c));
  const meta = (c: string) => METRICAS.find((x) => x[0] === c)!;
  const nomeDe = (x: { chave: string; nome: string }) => ESPECIAL[x.chave] ?? (x.nome || x.chave);
  const exportCSV = () => {
    const nome = `bdgd_2025-12-31_inventario_${tipo}_${dist}.csv`;
    const header = ["data_base", "dist", "codigo", "nome", ...t.cols.filter((c) => !["chave", "nome"].includes(c))];
    const esc = (v: unknown) => { const s2 = v === null || v === undefined ? "" : String(v); return /[",\n]/.test(s2) ? `"${s2.replace(/"/g, '""')}"` : s2; };
    downloadText(nome, [header.join(","), ...t.rows.map((r) => ["2025-12-31", dist, r[t.cols.indexOf("chave")], r[t.cols.indexOf("nome")], ...t.cols.filter((c) => !["chave", "nome"].includes(c)).map((c) => r[t.cols.indexOf(c)])].map(esc).join(","))].join("\n"));
    toast(`${nome} exportado`);
  };
  return (
    <>
      <div className={s.invTools}>
        <label className={s.searchMini}><Search size={14} aria-hidden /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder={`Buscar ${SINGULAR[tipo]} por nome ou código`} aria-label={`Buscar ${SINGULAR[tipo]}`} data-testid="inv-busca" />{q && <button onClick={() => setQ("")} aria-label="Limpar"><X size={13} /></button>}</label>
        <span className="caption">{linhas.filter((x) => !(x.chave in ESPECIAL)).length} {TITULO[tipo].toLowerCase()}</span>
        <span style={{ flex: 1 }} />
        <Button size="sm" onClick={exportCSV} data-testid="inv-csv"><Download size={13} /> CSV</Button>
      </div>
      <div className={s.invWrap} tabIndex={0} role="region" aria-label={`Tabela de ${TITULO[tipo].toLowerCase()}`}>
        <table className={s.invTable} data-testid="inv-tabela">
          <thead>
            <tr>
              <th scope="col">{SINGULAR[tipo][0].toUpperCase() + SINGULAR[tipo].slice(1)}</th>
              {tipo === "ctmt" && <th scope="col">Subestação</th>}
              {cols.map((c) => (
                <th key={c} scope="col" aria-sort={ord === c ? "descending" : "none"}>
                  <button type="button" onClick={() => setOrd(c)}>{ord === c && <ArrowDown size={11} aria-hidden />}{meta(c)[1]}{meta(c)[2] !== "itens" ? ` (${meta(c)[2]})` : ""}</button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {linhas.slice(0, 400).map((x) => (
              <tr key={x.chave} aria-selected={sel?.chave === x.chave} onClick={() => setSel(sel?.chave === x.chave ? null : x.chave)} tabIndex={0}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSel(sel?.chave === x.chave ? null : x.chave); } }}>
                <td><span className={s.invName} title={nomeDe(x)}>{nomeDe(x)}</span>{!(x.chave in ESPECIAL) && <span className={s.code} style={{ marginLeft: 0 }}>{x.chave}</span>}</td>
                {tipo === "ctmt" && <td style={{ textAlign: "left" }}>{subNome.get(String(x.get("sub") ?? x.r[t.cols.indexOf("sub")])) || <span className="faint">—</span>}</td>}
                {cols.map((c) => <td key={c}>{x.get(c) === null ? <span className="faint">0</span> : fmt(x.get(c), meta(c)[2] === "km" ? "extensao_km" : meta(c)[2] === "kVA" ? "potencia_kva" : "quantidade")}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {linhas.length > 400 && <p className="caption" style={{ marginTop: 6 }}>Mostrando os 400 primeiros pela ordenação; use a busca ou o CSV para a lista completa.</p>}
      {sel && (
        <div className={s.detail} data-testid="inv-detalhe" aria-live="polite">
          <div className="headline" style={{ fontSize: "1rem" }}>{nomeDe(sel)} {!(sel.chave in ESPECIAL) && <span className={s.code}>{sel.chave}</span>}</div>
          {tipo === "ctmt" && <div className="caption">Subestação: {subNome.get(String(sel.get("sub") ?? sel.r[t.cols.indexOf("sub")])) || "—"} · Tensão: {String(sel.r[t.cols.indexOf("ten_nom")] ?? "—")}</div>}
          {tipo === "ctat" && <div className="caption">Tensão: {String(sel.r[t.cols.indexOf("ten_nom")] ?? "—")}</div>}
          {tipo === "sub" && t.cols.includes("pos") && <div className="caption">Propriedade: {String(sel.r[t.cols.indexOf("pos")] ?? "—")}</div>}
          <div className={s.detailGrid}>
            {METRICAS.filter(([c]) => t.cols.includes(c)).map(([c, label, un]) => (
              <div key={c} className={s.detailItem}>
                <div className={s.detailLabel}>{label}</div>
                <div className={s.detailValue}>{fmt(sel.get(c) ?? 0, un === "km" ? "extensao_km" : un === "kVA" ? "potencia_kva" : "quantidade")}{un !== "itens" && <span className="caption"> {un}</span>}</div>
              </div>
            ))}
          </div>
          <p className={s.note}><Info size={13} aria-hidden /><span>Contagens por vínculo oficial (alimentador, subestação ou conjunto informado no registro; equipamentos via a instalação vinculada). Zero significa nenhum registro vinculado.</span></p>
        </div>
      )}
    </>
  );
}
