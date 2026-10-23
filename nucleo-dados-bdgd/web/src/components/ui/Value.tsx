"use client";
import { animate, useInView, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { fmt, fmtUnit, fmtUnitCompact, ND } from "@/lib/format";
import type { Metric, Status } from "@/lib/types";
import s from "./ui.module.css";

/** Valor com unidade. Nulo é exibido como N/D (estado próprio), nunca como zero. */
export function Value({ v, metric, unitOverride, className }: { v: number | null | undefined; metric: Metric; unitOverride?: string; className?: string }) {
  if (v === null || v === undefined) return <span className={[s.value, s.nd, className].filter(Boolean).join(" ")} title="Não disponível">{ND}</span>;
  const { value, unit } = fmtUnit(v, metric);
  return (
    <span className={[s.value, className].filter(Boolean).join(" ")}>
      {value}
      {(unitOverride ?? unit) && <span className={s.unit}>{unitOverride ?? unit}</span>}
    </span>
  );
}

/** Contagem curta (≈650 ms) só depois do dado real carregar e entrar na tela. Leitores de tela recebem o valor final. */
export function Ticker({ v, metric, unit, compact }: { v: number | null; metric: Metric; unit?: string; compact?: boolean }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const reduce = useReducedMotion();
  const [anim, setAnim] = useState<{ target: number | null; x: number }>({ target: null, x: 0 });
  useEffect(() => {
    if (v === null || reduce || !inView) return;
    const c = animate(0, v, { duration: 0.65, ease: [0.22, 1, 0.36, 1], onUpdate: (x) => setAnim({ target: v, x }) });
    return () => c.stop();
  }, [v, inView, reduce]);
  // valor final quando não há animação (redução de movimento, fora da tela ainda não animado) ou quando ela terminou
  const shown = v === null ? null : reduce ? v : anim.target === v ? anim.x : inView ? 0 : v;
  const f = compact ? fmtUnitCompact : fmtUnit;
  const final = v === null ? ND : `${fmtUnit(v, metric).value} ${unit ?? fmtUnit(v, metric).unit}`.trim();
  if (v === null) return <span ref={ref} className={`${s.value} ${s.nd}`}>{ND}</span>;
  const disp = f(shown === null ? v : (Number.isInteger(v) ? Math.round(shown) : shown), metric);
  return (
    <span ref={ref} className={s.value} aria-label={final} title={final}>
      <span aria-hidden>{disp.value}</span>
      {(unit ?? disp.unit) && <span className={s.unit} aria-hidden>{unit ?? disp.unit}</span>}
    </span>
  );
}

const ST_LABEL: Record<Status, string> = { a: "Aprovado", l: "Alerta", b: "Bloqueado", e: "Em validação", n: "Não aplicável" };
export function StatusDot({ status, label }: { status: Status; label?: boolean }) {
  return (
    <span className={s.status} title={ST_LABEL[status]}>
      <span className={`${s.dot} ${s[`dot_${status}`]}`} aria-hidden />
      {label ? ST_LABEL[status] : <span className="sr-only">{ST_LABEL[status]}</span>}
    </span>
  );
}

export function Pill({ tone = "default", children, title }: { tone?: "default" | "ok" | "warn" | "nd" | "accent"; children: ReactNode; title?: string }) {
  return <span className={`${s.pill} ${tone !== "default" ? s[`pill_${tone}`] : ""}`} title={title}>{children}</span>;
}

export function Num({ v }: { v: number | null | undefined }) {
  return v === null || v === undefined ? <span className={s.nd}>{ND}</span> : <span className="num">{fmt(v)}</span>;
}
