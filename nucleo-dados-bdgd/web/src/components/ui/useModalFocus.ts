"use client";
import { useEffect, useRef, type RefObject } from "react";

/** Ciclo de teclado de um modal e retorno ao acionador ao fechar. */
export function useModalFocus(open: boolean, dialog: RefObject<HTMLElement | null>, onClose: () => void,
  trigger?: RefObject<HTMLElement | null>) {
  const close = useRef(onClose);
  useEffect(() => { close.current = onClose; }, [onClose]);
  useEffect(() => {
    if (!open) return;
    const anteriores = trigger?.current ?? document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const itens = () => [...(dialog.current?.querySelectorAll<HTMLElement>(
      'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]',
    ) ?? [])].filter((el) => el.getClientRects().length > 0 && !el.closest('[inert]'));
    const frame = requestAnimationFrame(() => itens()[0]?.focus());
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close.current(); }
      else if (e.key === "Tab") {
        const lista = itens();
        const primeiro = lista[0], ultimo = lista.at(-1);
        if (!primeiro) { e.preventDefault(); return; }
        if (!dialog.current?.contains(document.activeElement) || e.shiftKey && document.activeElement === primeiro) {
          e.preventDefault(); (e.shiftKey ? ultimo : primeiro)?.focus();
        } else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primeiro.focus(); }
      }
    };
    document.addEventListener("keydown", key, true);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", key, true);
      document.body.style.overflow = overflow;
      requestAnimationFrame(() => { if (anteriores?.isConnected) anteriores.focus(); });
    };
  }, [open, dialog, trigger]);
}
