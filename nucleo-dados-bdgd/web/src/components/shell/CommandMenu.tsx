"use client";
import { Building2, CornerDownLeft, FileText, Layers3, Network, Search } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { displayName } from "@/lib/dataset";
import { useData } from "@/lib/data-context";
import s from "./shell.module.css";

type Item = { key: string; group: string; label: string; meta?: string; href: string; icon: typeof Search; kw: string };
const norm = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Busca global por sigla, nome, DIST, UF, grupo ou entidade — sem exigir que o usuário conheça códigos. */
export function CommandMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  const data = useData();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLDivElement>(null);

  const items = useMemo<Item[]>(() => {
    const pages: Item[] = [
      { key: "p-pan", group: "Páginas", label: "Panorama Brasil", href: "/", icon: FileText, kw: "mapa arat kpi" },
      { key: "p-mat", group: "Páginas", label: "Matriz nacional", href: "/matriz/", icon: FileText, kw: "tabela" },
      { key: "p-evo", group: "Páginas", label: "Evolução histórica", href: "/evolucao/", icon: FileText, kw: "historico 2022 2023 2024 serie" },
      { key: "p-cmp", group: "Páginas", label: "Comparador", href: "/comparar/", icon: FileText, kw: "comparar a b" },
      { key: "p-exp", group: "Páginas", label: "Explorar ativos", href: "/explorar/", icon: FileText, kw: "filtros facetas entidades dda tuc" },
      { key: "p-met", group: "Páginas", label: "Metodologia e qualidade", href: "/metodologia/", icon: FileText, kw: "fontes qa" },
    ];
    if (data.status !== "ready") return pages;
    const ds = data.ds;
    const dists: Item[] = ds.dists.map((d) => ({
      key: `d${d.dist}`, group: "Distribuidoras", label: displayName(d), meta: `DIST ${d.dist}${d.ufs.length ? " · " + d.ufs.join(", ") : ""}`,
      href: `/?dist=${d.dist}`, icon: Building2, kw: `${d.nome} ${d.dist} ${d.ufs.join(" ")} ${ds.grupo(d.grupo)?.nome ?? ""}`,
    }));
    const grupos: Item[] = ds.grupos.map((g) => ({ key: `g${g.id}`, group: "Grupos econômicos", label: g.nome, meta: `${ds.groupDists(g.id).length} distribuidoras`, href: `/?grupo=${g.id}`, icon: Network, kw: g.controlador }));
    const ents: Item[] = ds.entidades.map((e) => ({ key: `e${e.id}`, group: "Entidades BDGD", label: e.nome, meta: e.id, href: `/explorar/?ent=${e.id}`, icon: Layers3, kw: `${e.id} ${e.familia}` }));
    return [...pages, ...grupos, ...dists, ...ents];
  }, [data]);

  const filtered = useMemo(() => {
    const t = norm(q.trim());
    if (!t) return items.filter((i) => i.group !== "Distribuidoras" && i.group !== "Entidades BDGD").concat(items.filter((i) => i.group === "Distribuidoras").slice(0, 6));
    return items.filter((i) => norm(`${i.label} ${i.meta ?? ""} ${i.kw}`).includes(t)).slice(0, 60);
  }, [q, items]);

  const [wasOpen, setWasOpen] = useState(open);
  if (wasOpen !== open) { setWasOpen(open); if (open) { setQ(""); setActive(0); } }
  useEffect(() => { if (open) requestAnimationFrame(() => input.current?.focus()); }, [open]);
  useEffect(() => { list.current?.querySelector(`[data-i="${active}"]`)?.scrollIntoView({ block: "nearest" }); }, [active]);

  const go = (i?: Item) => { if (!i) return; onClose(); router.push(i.href); };
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(filtered.length - 1, a + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    else if (e.key === "Enter") { e.preventDefault(); go(filtered[active]); }
    else if (e.key === "Escape") { e.preventDefault(); onClose(); }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div className={s.cmdOverlay} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.16 }} onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
          <motion.div className={s.cmd} role="dialog" aria-modal="true" aria-label="Busca global" initial={{ opacity: 0, scale: 0.97, y: -8 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98, y: -4 }}
            transition={{ type: "spring", stiffness: 460, damping: 36 }}>
            <div className={s.cmdInput}>
              <Search size={18} aria-hidden />
              <input ref={input} value={q} onChange={(e) => { setQ(e.target.value); setActive(0); }} onKeyDown={onKey} placeholder="Distribuidora, DIST, UF, grupo ou entidade"
                aria-label="Buscar" role="combobox" aria-expanded aria-controls="cmd-list" data-testid="search-input" />
            </div>
            <div className={s.cmdList} ref={list} role="listbox" id="cmd-list">
              {filtered.length === 0 && <div style={{ padding: 24, textAlign: "center" }} className="faint">Nada encontrado para “{q}”.</div>}
              {filtered.map((i, n) => {
                const head = i.group !== filtered[n - 1]?.group ? i.group : null; const Icon = i.icon;
                return (
                  <div key={i.key}>
                    {head && <div className={s.cmdGroup}>{head}</div>}
                    <div role="option" aria-selected={n === active} data-active={n === active} data-i={n} className={s.cmdItem} onMouseEnter={() => setActive(n)} onClick={() => go(i)}>
                      <Icon size={17} aria-hidden /><span>{i.label}</span>{i.meta && <span className={s.cmdItemMeta}>{i.meta}</span>}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className={s.cmdFoot}><span>↑↓ navegar</span><span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}><CornerDownLeft size={12} /> abrir</span><span>esc fechar</span></div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
