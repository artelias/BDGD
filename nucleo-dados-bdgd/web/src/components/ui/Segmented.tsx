"use client";
import { motion } from "motion/react";
import { useId, useRef, type KeyboardEvent } from "react";
import s from "./ui.module.css";

export interface SegOption<T extends string> { value: T; label: string; disabled?: boolean; title?: string }

/** Controle segmentado com indicador que desliza fisicamente até a opção escolhida (setas do teclado navegam). */
export function Segmented<T extends string>({ options, value, onChange, label, size }: { options: SegOption<T>[]; value: T; onChange: (v: T) => void; label: string; size?: "sm" }) {
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);
  const onKey = (e: KeyboardEvent) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const enabled = options.filter((o) => !o.disabled);
    const i = enabled.findIndex((o) => o.value === value);
    const n = enabled[(i + (e.key === "ArrowRight" ? 1 : -1) + enabled.length) % enabled.length];
    onChange(n.value);
    requestAnimationFrame(() => ref.current?.querySelector<HTMLButtonElement>(`[data-v="${n.value}"]`)?.focus());
  };
  return (
    <div ref={ref} className={s.seg} role="radiogroup" aria-label={label} onKeyDown={onKey} style={size === "sm" ? { padding: 2 } : undefined}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button key={o.value} data-v={o.value} type="button" role="radio" aria-checked={on} tabIndex={on ? 0 : -1} disabled={o.disabled}
            title={o.title} className={s.segItem} onClick={() => onChange(o.value)} style={size === "sm" ? { height: 24, padding: "0 10px", fontSize: 12 } : undefined}>
            {on && <motion.span layoutId={`seg-${id}`} className={s.segThumb} transition={{ type: "spring", stiffness: 520, damping: 40, mass: 0.7 }} />}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
