"use client";
import { Filter, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { LoadingBlock } from "@/components/ui/Feedback";
import { MultiPick } from "@/components/ui/MultiPick";
import { Segmented } from "@/components/ui/Segmented";
import { ESSENCIAIS, recorteDe, ROTULO_MEDIDA } from "@/lib/ativos";
import { dimsCompativeis, juntar, rotulo } from "@/lib/cubo";
import type { Dataset } from "@/lib/dataset";
import { useConceito } from "@/lib/data-context";
import type { AtivoCfg, Filtro, MedidaConceito } from "@/lib/types";
import s from "./matriz.module.css";

/** Filtro de um ativo (coluna da Matriz ou recorte do Comparador): medida alternativa + características do próprio conceito.
 *  Só oferece características com cubo exato compatível; o mesmo motor de cubos do Explorar calcula os valores. */
export function FiltroAtivo({ ds, ativo, filtro, medida, onChange, testId }: {
  ds: Dataset; ativo: AtivoCfg; filtro: Filtro; medida: MedidaConceito; onChange: (f: Filtro, m: MedidaConceito) => void; testId?: string;
}) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<CSSProperties>({});
  const btn = useRef<HTMLButtonElement>(null);
  const pop = useRef<HTMLDivElement>(null);
  const ativoFiltrado = Object.values(filtro).some((v) => v.length) || medida !== ativo.medida;
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => { const t = e.target as Node; if (!pop.current?.contains(t) && !btn.current?.contains(t) && !(t as Element).closest?.("[data-multipick-pop]")) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", away); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", esc); };
  }, [open]);
  const abrir = (e: React.MouseEvent) => {
    e.stopPropagation();
    const r = btn.current!.getBoundingClientRect(), w = Math.min(380, window.innerWidth - 24);
    setPos({ top: Math.min(r.bottom + 6, window.innerHeight - 120), left: Math.max(12, Math.min(r.right - w, window.innerWidth - w - 12)), width: w });
    setOpen((o) => !o);
  };
  return (
    <>
      <button ref={btn} type="button" className={s.filterBtn} data-on={ativoFiltrado} onClick={abrir} aria-expanded={open} aria-label={`Filtrar ${ativo.nome}`} title={`Filtrar ${ativo.nome}`} data-testid={testId}>
        <Filter size={12} aria-hidden />
      </button>
      {typeof document !== "undefined" && createPortal(
        <AnimatePresence>
          {open && (
            <motion.div ref={pop} className={s.pop} style={pos} role="dialog" aria-label={`Filtro de ${ativo.nome}`} onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -2 }} transition={{ duration: 0.15 }}>
              <div className={s.popHead}><b>{ativo.nome}</b><button type="button" className={s.close} onClick={() => setOpen(false)} aria-label="Fechar"><X size={14} /></button></div>
              <Conteudo ds={ds} ativo={ativo} filtro={filtro} medida={medida} onChange={onChange} />
            </motion.div>
          )}
        </AnimatePresence>, document.body)}
    </>
  );
}

function Conteudo({ ds, ativo, filtro, medida, onChange }: { ds: Dataset; ativo: AtivoCfg; filtro: Filtro; medida: MedidaConceito; onChange: (f: Filtro, m: MedidaConceito) => void }) {
  const c = useConceito(ativo.conceito);
  const medidas = [ativo.medida, ...(ativo.medidas_extra ?? [])];
  if (c.loading || !c.data) return <LoadingBlock lines={3} label="Carregando características" />;
  const cd = c.data;
  const base = recorteDe(ativo);
  const fixadas = new Set(Object.keys(base.filtro));
  const todas = [...new Set(Object.values(cd.cubos).flatMap((x) => x.dims))].filter((d) => !fixadas.has(d));
  const ess = (ESSENCIAIS[ativo.conceito] ?? []).filter((d) => todas.includes(d));
  const ordem = [...ess, ...todas.filter((d) => !ess.includes(d))];
  const rec = juntar(base, { filtro });
  const compat = dimsCompativeis(cd, rec);
  const rot = (d: string) => ds.raw.conceitos!.dimensoes[d]?.rotulo ?? d;
  return (
    <div className={s.popBody}>
      {medidas.length > 1 && <Segmented label="Medida" size="sm" value={medida} onChange={(v) => onChange(filtro, v as MedidaConceito)} options={medidas.map((m) => ({ value: m, label: ROTULO_MEDIDA[m] }))} />}
      <div className={s.popDims}>
        {ordem.map((d) => {
          const ok = compat.has(d) || (filtro[d]?.length ?? 0) > 0;
          return (
            <div key={d} style={ok ? undefined : { opacity: 0.45, pointerEvents: "none" }} title={ok ? undefined : "Sem cubo exato para combinar com o filtro atual"}>
              <MultiPick label={rot(d)} value={filtro[d] ?? []} allLabel="Todos" width={340} testId={`col-filtro-${d}`}
                options={(cd.valores[d] ?? []).map((code) => ({ value: code, label: rotulo(cd, d, code, rec), keywords: code }))}
                onChange={(v) => onChange({ ...filtro, [d]: v }, medida)} />
            </div>
          );
        })}
      </div>
      {(Object.values(filtro).some((v) => v.length) || medida !== ativo.medida) && (
        <button type="button" className={s.linkBtn} onClick={() => onChange({}, ativo.medida)}>Limpar filtro desta coluna</button>
      )}
    </div>
  );
}
