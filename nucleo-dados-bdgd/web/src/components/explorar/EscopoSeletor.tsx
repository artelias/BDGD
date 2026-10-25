"use client";
import { Building2 } from "lucide-react";
import { MultiPick, type MultiOption } from "@/components/ui/MultiPick";
import { Picker } from "@/components/ui/Picker";
import { Segmented } from "@/components/ui/Segmented";
import { groupColor } from "@/lib/colors";
import { displayName, type Dataset } from "@/lib/dataset";
import type { Escopo } from "@/lib/escopo";
import { useTheme } from "@/lib/theme";
import s from "./explorar.module.css";

/** Brasil | Grupo (todas ou algumas distribuidoras do grupo) | Distribuidoras (uma ou várias, de qualquer grupo). */
export function EscopoSeletor({ ds, value, onChange, testId = "escopo" }: { ds: Dataset; value: Escopo; onChange: (e: Escopo) => void; testId?: string }) {
  const { resolved } = useTheme();
  const opDist = (lista: Dataset["dists"], agrupar: boolean): MultiOption[] => lista.map((d) => ({
    value: String(d.dist), label: displayName(d), meta: `DIST ${d.dist}`, keywords: `${d.nome} ${d.ufs.join(" ")}`,
    group: agrupar ? (d.grupo_status === "verificado" ? ds.grupo(d.grupo)?.nome : "Grupo não confirmado") : undefined,
    color: d.grupo_status === "verificado" ? groupColor(d.grupo, resolved) : undefined,
  })).sort((a, b) => (a.group ?? "").localeCompare(b.group ?? "") || a.label.localeCompare(b.label));
  const setModo = (m: string) => {
    if (m === "brasil") onChange({ modo: "brasil" });
    else if (m === "grupo") onChange({ modo: "grupo", grupo: value.modo === "grupo" ? value.grupo : ds.grupos[0].id, dists: [] });
    else onChange({ modo: "dists", dists: value.modo === "brasil" ? [ds.dists[0].dist] : value.modo === "grupo" ? (value.dists.length ? value.dists : ds.groupDists(value.grupo).slice(0, 1).map((d) => d.dist)) : value.dists });
  };
  return (
    <div className={s.scopeBar} role="group" aria-label="Escopo da análise" data-testid={testId}>
      <Segmented label="Escopo" value={value.modo} onChange={setModo} options={[{ value: "brasil", label: "Brasil" }, { value: "grupo", label: "Grupo" }, { value: "dists", label: "Distribuidoras" }]} />
      {value.modo === "grupo" && (
        <>
          <Picker label="Grupo" value={value.grupo} compact width={220} testId={`${testId}-grupo`}
            options={ds.grupos.map((g) => ({ value: g.id, label: g.nome, color: groupColor(g.id, resolved), meta: `${ds.groupDists(g.id).length} DIST` }))}
            onChange={(v) => onChange({ modo: "grupo", grupo: v, dists: [] })} />
          <MultiPick label="Distribuidoras do grupo" options={opDist(ds.groupDists(value.grupo), false)} value={value.dists.map(String)} allLabel="Todas"
            onChange={(v) => onChange({ modo: "grupo", grupo: value.grupo, dists: v.map(Number) })} icon={<Building2 size={14} aria-hidden />} testId={`${testId}-grupo-dists`} width={300} />
        </>
      )}
      {value.modo === "dists" && (
        <MultiPick label="Distribuidoras" options={opDist(ds.dists, true)} value={value.dists.map(String)} allLabel="Nenhuma"
          onChange={(v) => onChange(v.length ? { modo: "dists", dists: v.map(Number) } : { modo: "brasil" })} icon={<Building2 size={14} aria-hidden />} testId={`${testId}-dists`} width={340} />
      )}
    </div>
  );
}
