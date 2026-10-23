"use client";
import { CircleCheck, CircleDashed, TriangleAlert } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import s from "./ui.module.css";

export function Skeleton({ w = "100%", h = 14, r }: { w?: number | string; h?: number | string; r?: number }) {
  return <span className="skeleton" style={{ display: "block", width: w, height: h, borderRadius: r }} aria-hidden />;
}

export function LoadingBlock({ lines = 3, label = "Carregando dados oficiais 2025" }: { lines?: number; label?: string }) {
  return (
    <div role="status" aria-live="polite" style={{ display: "grid", gap: 10, padding: "8px 0" }}>
      <span className="sr-only">{label}</span>
      {Array.from({ length: lines }, (_, i) => <Skeleton key={i} w={`${92 - i * 17}%`} h={i === 0 ? 22 : 13} />)}
    </div>
  );
}

export function EmptyState({ title, children, tone = "nd" }: { title: string; children?: ReactNode; tone?: "nd" | "warn" }) {
  return (
    <div className={s.state} role="status">
      {tone === "warn" ? <TriangleAlert size={22} /> : <CircleDashed size={22} />}
      <div className={s.stateTitle}>{title}</div>
      {children && <div className={s.stateText}>{children}</div>}
    </div>
  );
}

/** Falha fechada: sem dados oficiais, nada de números de demonstração. */
export function DataError({ error }: { error: string }) {
  return (
    <EmptyState title="Dados oficiais indisponíveis" tone="warn">
      Os agregados BDGD 31/12/2025 não puderam ser carregados ({error}). Nenhum número substituto é exibido.
    </EmptyState>
  );
}

type Toast = { id: number; text: string };
const ToastCtx = createContext<(text: string) => void>(() => {});
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, set] = useState<Toast[]>([]);
  const n = useRef(0);
  const push = useCallback((text: string) => {
    const id = ++n.current;
    set((x) => [...x.slice(-2), { id, text }]);
    setTimeout(() => set((x) => x.filter((t) => t.id !== id)), 3200);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className={s.toasts} aria-live="polite" role="status">
        <AnimatePresence>
          {items.map((t) => (
            <motion.div key={t.id} className={s.toast} initial={{ opacity: 0, y: 12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 6 }}
              transition={{ type: "spring", stiffness: 420, damping: 34 }}>
              <CircleCheck size={16} aria-hidden /> {t.text}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  );
}
export const useToast = () => useContext(ToastCtx);

export function Tip({ text, children }: { text: string; children: ReactNode }) {
  const [on, set] = useState(false);
  return (
    <span className={s.tipWrap} onMouseEnter={() => set(true)} onMouseLeave={() => set(false)} onFocus={() => set(true)} onBlur={() => set(false)}>
      {children}
      <AnimatePresence>
        {on && (
          <motion.span role="tooltip" className={s.tip} initial={{ opacity: 0, y: 3 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.12 }}>
            {text}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}

export function downloadText(name: string, text: string, type = "text/csv;charset=utf-8") {
  const blob = new Blob(["﻿" + text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
