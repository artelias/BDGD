"use client";
import { ChevronRight, Info, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useEffect, useId, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { createPortal } from "react-dom";
import s from "./explain.module.css";

/** "Como é calculado?": explicação humana primeiro; fórmula técnica só quando pedida. */
export function Explain({ title, children, tecnico, ressalva, cobertura, align = "start", label, testId }: {
  title: string; children: ReactNode; tecnico?: string; ressalva?: string; cobertura?: string; align?: "start" | "end"; label?: string; testId?: string;
}) {
  const [open, setOpen] = useState(false);
  const [tech, setTech] = useState(false);
  const btn = useRef<HTMLButtonElement>(null);
  const pop = useRef<HTMLDivElement>(null);
  const id = useId();
  const [pos, setPos] = useState<CSSProperties>({});
  /** O balão vai para o <body> com posição fixa: nenhum contexto de empilhamento ou overflow o corta. */
  const place = () => {
    const r = btn.current?.getBoundingClientRect(); if (!r) return;
    const w = Math.min(340, window.innerWidth - 32);
    const left = align === "end" ? Math.max(16, r.right - w) : Math.min(Math.max(16, r.left - 8), window.innerWidth - w - 16);
    const below = window.innerHeight - r.bottom > 260 || r.top < 260;
    setPos(below ? { left, top: r.bottom + 6, width: w } : { left, bottom: window.innerHeight - r.top + 6, width: w });
  };
  useEffect(() => {
    if (!open) return;
    const close = (e: Event) => { if (e.target instanceof Node && pop.current?.contains(e.target)) return; setOpen(false); };
    window.addEventListener("scroll", close, { passive: true, capture: true }); window.addEventListener("resize", close);
    const away = (e: MouseEvent) => { if (!pop.current?.contains(e.target as Node) && !btn.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); btn.current?.focus(); } };
    document.addEventListener("mousedown", away); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", esc); window.removeEventListener("scroll", close, { capture: true }); window.removeEventListener("resize", close); };
  }, [open]);
  return (
    <span className={s.wrap}>
      <button ref={btn} type="button" className={s.trigger} aria-expanded={open} aria-controls={id} onClick={(e) => { e.stopPropagation(); if (!open) place(); setOpen((o) => !o); }}
        aria-label={label ?? `Como é calculado: ${title}`} data-testid={testId}>
        <Info size={13} aria-hidden />{label && <span>{label}</span>}
      </button>
      {typeof document !== "undefined" && createPortal(<AnimatePresence>
        {open && (
          <motion.div ref={pop} id={id} role="dialog" aria-label={title} className={s.pop} style={pos} onClick={(e) => e.stopPropagation()}
            initial={{ opacity: 0, y: -4, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -2 }} transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}>
            <div className={s.head}>
              <span className={s.kicker}>Como é calculado?</span>
              <button type="button" className={s.close} aria-label="Fechar" onClick={() => { setOpen(false); btn.current?.focus(); }}><X size={14} /></button>
            </div>
            <div className={s.title}>{title}</div>
            <div className={s.body}>{children}</div>
            {ressalva && <div className={s.note}>{ressalva}</div>}
            {cobertura && <div className={s.meta}>{cobertura}</div>}
            {tecnico && (
              <div className={s.tech}>
                <button type="button" className={s.techBtn} aria-expanded={tech} onClick={() => setTech((t) => !t)}>
                  <ChevronRight size={13} style={{ transform: tech ? "rotate(90deg)" : undefined, transition: "transform var(--dur-2) var(--ease-out)" }} aria-hidden /> Ver cálculo técnico
                </button>
                {tech && <code className={s.code}>{tecnico}</code>}
              </div>
            )}
            <Link href="/metodologia/#dicionario" className={s.link}>Dicionário de indicadores</Link>
          </motion.div>
        )}
      </AnimatePresence>, document.body)}
    </span>
  );
}
