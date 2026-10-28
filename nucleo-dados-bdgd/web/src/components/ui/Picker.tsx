"use client";
import { ChevronDown, Search } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import s from "./ui.module.css";

export interface PickerOption { value: string; label: string; group?: string; meta?: string; color?: string; keywords?: string; disabled?: boolean }

function norm(t: string) { return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }

/** Combobox pesquisável: teclado completo, grupos, Escape fecha e devolve o foco. No celular vira folha inferior. */
export function Picker({ label, value, options, onChange, placeholder = "Selecionar", searchPlaceholder = "Buscar", width, icon, testId, compact, inlineMenu = false }: {
  label: string; value: string | null; options: PickerOption[]; onChange: (v: string) => void; placeholder?: string; searchPlaceholder?: string; width?: number | string; icon?: ReactNode; testId?: string; compact?: boolean; inlineMenu?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const btn = useRef<HTMLButtonElement>(null);
  const pop = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();
  const current = options.find((o) => o.value === value);

  const filtered = useMemo(() => {
    const t = norm(q.trim());
    return t ? options.filter((o) => norm(`${o.label} ${o.meta ?? ""} ${o.keywords ?? ""} ${o.group ?? ""}`).includes(t)) : options;
  }, [q, options]);

  const [wasOpen, setWasOpen] = useState(open);
  if (wasOpen !== open) { setWasOpen(open); if (open) { setQ(""); setActive(Math.max(0, options.findIndex((o) => o.value === value))); } }
  useEffect(() => {
    if (!open) return;
    requestAnimationFrame(() => input.current?.focus());
    const close = (e: MouseEvent) => { if (!pop.current?.contains(e.target as Node) && !btn.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  useEffect(() => { pop.current?.querySelector(`[data-idx="${active}"]`)?.scrollIntoView({ block: "nearest" }); }, [active]);

  const choose = (o?: PickerOption) => { if (!o || o.disabled) return; onChange(o.value); setOpen(false); btn.current?.focus(); };
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(filtered.length - 1, a + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    else if (e.key === "Home") { e.preventDefault(); setActive(0); }
    else if (e.key === "End") { e.preventDefault(); setActive(filtered.length - 1); }
    else if (e.key === "Enter") { e.preventDefault(); choose(filtered[active]); }
    else if (e.key === "Escape") { e.preventDefault(); setOpen(false); btn.current?.focus(); }
    else if (e.key === "Tab") setOpen(false);
  };

  return (
    <div style={{ position: "relative", width, minWidth: 0 }}>
      <button ref={btn} type="button" className={`${s.pickerBtn} ${compact ? s.pickerCompact : ""}`} style={{ width: "100%" }} aria-haspopup="listbox" aria-expanded={open}
        aria-label={`${label}: ${current?.label ?? placeholder}`} data-testid={testId}
        onClick={() => setOpen((o) => !o)} onKeyDown={(e) => { if (e.key === "ArrowDown" && !open) { e.preventDefault(); setOpen(true); } }}>
        {icon}
        <span className={s.pickerValue} style={{ flex: 1 }}>
          <span className={s.pickerLabel}>{label}</span>
          <span className={s.pickerText} style={{ display: "flex", alignItems: "center", gap: 7 }}>
            {current?.color && <span className={s.swatch} style={{ background: current.color }} />}
            {current?.label ?? <span className="faint">{placeholder}</span>}
          </span>
        </span>
        <ChevronDown size={16} className={s.chev} aria-hidden />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div ref={pop} className={`${s.popover} ${inlineMenu ? s.popoverInline : ""}`} style={inlineMenu ? { width: "100%", marginTop: 8 } : { top: "calc(100% + 6px)", left: 0, width: "max(100%, 300px)" }} data-testid={testId ? `${testId}-menu` : undefined}
            initial={{ opacity: 0, scale: 0.97, y: -4 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98, y: -2 }}
            transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}>
            <div className={s.popSearch}>
              <Search size={15} aria-hidden />
              <input ref={input} value={q} onChange={(e) => { setQ(e.target.value); setActive(0); }} onKeyDown={onKey} placeholder={searchPlaceholder}
                role="combobox" aria-expanded aria-controls={listId} aria-activedescendant={filtered[active] ? `${listId}-${active}` : undefined} aria-label={`Buscar em ${label}`} />
            </div>
            <ul className={s.list} role="listbox" id={listId} aria-label={label}>
              {filtered.length === 0 && <li className={s.empty}>Nenhum resultado para “{q}”.</li>}
              {filtered.map((o, i) => {
                const header = o.group && o.group !== filtered[i - 1]?.group ? o.group : null;
                return (
                  <li key={o.value} role="presentation">
                    {header && <div className={s.groupLabel} role="presentation">{header}</div>}
                    <div id={`${listId}-${i}`} role="option" aria-selected={o.value === value} aria-disabled={o.disabled} data-active={i === active} data-idx={i}
                      className={s.option} style={o.disabled ? { opacity: 0.45 } : undefined} onMouseEnter={() => setActive(i)} onMouseDown={(e) => e.preventDefault()} onClick={() => choose(o)}>
                      {o.color && <span className={s.swatch} style={{ background: o.color }} />}
                      <span>{o.label}</span>
                      {o.meta && <span className={s.optionMeta}>{o.meta}</span>}
                    </div>
                  </li>
                );
              })}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
