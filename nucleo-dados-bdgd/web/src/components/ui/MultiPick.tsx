"use client";
import { Check, ChevronDown, Search, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import s from "./multipick.module.css";

export interface MultiOption { value: string; label: string; meta?: string; group?: string; keywords?: string; color?: string; disabled?: boolean; hint?: string }
export interface MultiPreset { id: string; label: string; values: string[] }

const norm = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** Seleção múltipla com busca, grupos e conjuntos prontos. Vazio = todos (sem filtro). */
export function MultiPick({ label, options, value, onChange, presets, icon, testId, allLabel = "Todos", width = 340, footer }: {
  label: string; options: MultiOption[]; value: string[]; onChange: (v: string[]) => void; presets?: MultiPreset[]; icon?: ReactNode; testId?: string; allLabel?: string; width?: number; footer?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const box = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (!open) return;
    input.current?.focus();
    const away = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", away); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", esc); };
  }, [open]);
  const sel = new Set(value);
  const shown = useMemo(() => {
    const t = norm(q.trim());
    return t ? options.filter((o) => norm(`${o.label} ${o.value} ${o.meta ?? ""} ${o.keywords ?? ""} ${o.group ?? ""}`).includes(t)) : options;
  }, [q, options]);
  const groups = useMemo(() => {
    const m = new Map<string, MultiOption[]>();
    for (const o of shown) { const g = o.group ?? ""; if (!m.has(g)) m.set(g, []); m.get(g)!.push(o); }
    return [...m.entries()];
  }, [shown]);
  const toggle = (v: string) => onChange(sel.has(v) ? value.filter((x) => x !== v) : [...value, v]);
  const summary = value.length === 0 ? allLabel : value.length === 1 ? (options.find((o) => o.value === value[0])?.label ?? value[0]) : `${value.length} selecionados`;
  return (
    <div className={s.wrap} ref={box}>
      <button type="button" className={s.trigger} aria-expanded={open} aria-haspopup="dialog" onClick={() => setOpen((o) => !o)} data-testid={testId} style={{ maxWidth: width }}>
        {icon}<span className={s.lab}>{label}</span><span className={s.sum}>{summary}</span><ChevronDown size={14} aria-hidden />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div className={s.pop} role="dialog" aria-label={label} style={{ width }} initial={{ opacity: 0, y: -4, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -2 }} transition={{ duration: 0.16 }}>
            <label className={s.search}><Search size={14} aria-hidden /><input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar" aria-label={`Buscar em ${label}`} />{q && <button onClick={() => setQ("")} aria-label="Limpar busca"><X size={13} /></button>}</label>
            {presets && presets.length > 0 && !q && (
              <div className={s.presets}>
                {presets.map((p) => <button key={p.id} type="button" className={s.preset} aria-pressed={p.values.length === value.length && p.values.every((v) => sel.has(v))} onClick={() => onChange(p.values)}>{p.label}</button>)}
              </div>
            )}
            <div className={s.list} role="group" aria-label={`Opções de ${label}`}>
              {groups.map(([g, os]) => (
                <div key={g}>
                  {g && <div className={s.group}>{g}</div>}
                  {os.map((o) => (
                    <button key={o.value} type="button" className={s.item} aria-pressed={sel.has(o.value)} disabled={o.disabled} onClick={() => toggle(o.value)} title={o.hint}>
                      <span className={s.box} aria-hidden>{sel.has(o.value) && <Check size={11} />}</span>
                      {o.color && <span className={s.sw} style={{ background: o.color }} aria-hidden />}
                      <span className={s.txt}>{o.label}{o.hint && <span className={s.hint}>{o.hint}</span>}</span>
                      {o.meta && <span className={s.meta}>{o.meta}</span>}
                    </button>
                  ))}
                </div>
              ))}
              {shown.length === 0 && <div className={s.empty}>Nada encontrado.</div>}
            </div>
            <div className={s.foot}>
              <button type="button" className={s.link} onClick={() => onChange([])}>Limpar ({allLabel.toLowerCase()})</button>
              {footer}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
