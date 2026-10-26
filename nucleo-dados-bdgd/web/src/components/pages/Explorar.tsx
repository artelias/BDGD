"use client";
import { Code2 } from "lucide-react";
import { motion } from "motion/react";
import { useMemo } from "react";
import { ConceitoPainel } from "@/components/explorar/ConceitoPainel";
import { EntidadeTecnica } from "@/components/explorar/EntidadeTecnica";
import { EscopoSeletor } from "@/components/explorar/EscopoSeletor";
import { DataError, EmptyState, LoadingBlock } from "@/components/ui/Feedback";
import { Picker } from "@/components/ui/Picker";
import { fmtCompact } from "@/lib/format";
import { ativo, itensMenu, totalAtivo } from "@/lib/ativos";
import type { Dataset } from "@/lib/dataset";
import { useData } from "@/lib/data-context";
import { distsDoEscopo, escreverEscopo, lerEscopo, type Escopo } from "@/lib/escopo";
import { useStoredValue } from "@/lib/hooks";
import type { MenuItem } from "@/lib/types";
import { useQueryPatch, useQueryState } from "@/lib/url-state";
import p from "./pages.module.css";
import s from "@/components/explorar/explorar.module.css";

export function Explorar() {
  const data = useData();
  if (data.status === "loading") return <LoadingBlock lines={6} />;
  if (data.status === "error") return <DataError error={data.error} />;
  if (!data.ds.raw.conceitos) return <EmptyState title="Catálogo de ativos indisponível" tone="warn">O pacote publicado não contém o catálogo de conceitos.</EmptyState>;
  return <ExplorarReady ds={data.ds} />;
}

/** item padrão a partir de um link antigo por entidade (?ent=UCBT): o conceito que contém a entidade */
function itemDaEntidade(ds: Dataset, ent: string): MenuItem | undefined {
  const cat = ds.raw.conceitos!;
  const itens = itensMenu(ds);
  const porConceito = itens.find((i) => i.conceito && !i.filtro && !i.excluir && (cat.conceitos[i.conceito].entidades.includes(ent) || cat.conceitos[i.conceito].vinculos?.includes(ent)));
  return porConceito ?? itens.find((i) => i.tecnico?.includes(ent));
}

function ExplorarReady({ ds }: { ds: Dataset }) {
  const patch = useQueryPatch();
  const [ativoQ] = useQueryState("ativo");
  const [entQ] = useQueryState("ent");
  const [escopoQ] = useQueryState("escopo", "brasil");
  const [distsQ] = useQueryState("dists");
  const [avRaw, setAv] = useStoredValue("bdgd.explorar.avancado", "0");
  const avancado = avRaw === "1" || !!entQ;
  const menu = ds.raw.conceitos!.menu;
  const itens = itensMenu(ds);
  const item = itens.find((i) => i.id === ativoQ) ?? (entQ ? itemDaEntidade(ds, entQ) : undefined) ?? itens.find((i) => i.id === "transformadores") ?? itens[0];
  const escopo = useMemo(() => lerEscopo(ds, escopoQ, distsQ), [ds, escopoQ, distsQ]);
  const dists = useMemo(() => distsDoEscopo(ds, escopo), [ds, escopo]);
  const S = useMemo(() => new Set(dists), [dists]);

  const ir = (id: string) => patch({ ativo: id, ent: null, f: null, c: null, m: null, por: null, inv: null, inv_dist: null, tec: null, a1: null, c1: null, a2: null }, true);
  const setEscopo = (e: Escopo) => { const w = escreverEscopo(e); patch({ escopo: w.escopo, dists: w.dists, inv: null, inv_dist: null }); };
  // total do ativo principal do item no escopo, para orientar a navegação
  const resumo = (i: MenuItem) => {
    const a = ativo(ds, i.id);
    if (!a) return "";
    const t = totalAtivo(ds, a.id, dists);
    return t.v === null ? "" : `${fmtCompact(t.v, a.medida)}`;
  };

  return (
    <>
      <header className={`${p.head} rise`}>
        <div className="eyebrow">Ativo → tipo → medida → características</div>
        <h1 className="display" style={{ marginTop: 8 }}>Explorar ativos</h1>
        <p className="lede">Escolha um ativo e veja sua composição por tipo patrimonial e por características oficiais, no Brasil, num grupo econômico ou em distribuidoras específicas.</p>
      </header>

      <EscopoSeletor ds={ds} value={escopo} onChange={setEscopo} />

      <div className={s.layout}>
        <nav className={s.rail} aria-label="Ativos">
          {menu.map((g) => (
            <div key={g.grupo}>
              <div className={s.railGroup}>{g.grupo}</div>
              {g.itens.map((i) => (
                <button key={i.id} type="button" className={s.railItem} aria-current={i.id === item.id} onClick={() => ir(i.id)} data-testid={`menu-${i.id}`}>
                  {i.id === item.id && <motion.span layoutId="ativo-sel" className={s.railActive} transition={{ type: "spring", stiffness: 480, damping: 38 }} />}
                  <span>{i.nome}</span><span className={s.railMeta}>{resumo(i)}</span>
                </button>
              ))}
            </div>
          ))}
          <button type="button" className={s.railItem} aria-pressed={avancado} onClick={() => setAv(avancado ? "0" : "1")} data-testid="modo-avancado" style={{ marginTop: 14 }}>
            <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}><Code2 size={14} aria-hidden /> Modo avançado</span><span className={s.railMeta}>{avancado ? "ligado" : "desligado"}</span>
          </button>
        </nav>

        <div style={{ minWidth: 0 }}>
          <div className={s.mobileMenu} style={{ marginBottom: 12 }}>
            <Picker label="Ativo" value={item.id} onChange={ir} testId="menu-mobile"
              options={menu.flatMap((g) => g.itens.map((i) => ({ value: i.id, label: i.nome, group: g.grupo, meta: resumo(i) })))} />
            <button type="button" className={s.advancedMobile} aria-pressed={avancado} onClick={() => setAv(avancado ? "0" : "1")} data-testid="modo-avancado-mobile">
              <Code2 size={14} aria-hidden /> Modo avançado · {avancado ? "ligado" : "desligado"}
            </button>
          </div>
          {item.tecnico ? (
            <section aria-labelledby="tec-titulo">
              <div className="eyebrow">Registros declarados</div>
              <h2 className={s.title} id="tec-titulo" data-testid="conceito-titulo">{item.nome}</h2>
              <p className={s.desc}>{item.descricao}</p>
              <EntidadeTecnica ds={ds} entidades={entQ && item.tecnico.includes(entQ) ? [entQ, ...item.tecnico.filter((e) => e !== entQ)] : item.tecnico}
                dists={S} scope={dists.length === 1 ? { tipo: "dist", id: dists[0] } : { tipo: "brasil" }} />
            </section>
          ) : (
            <ConceitoPainel ds={ds} item={item} escopo={escopo} avancado={avancado} />
          )}
        </div>
      </div>
    </>
  );
}
