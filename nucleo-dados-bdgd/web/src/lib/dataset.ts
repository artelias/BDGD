import type { Distribuidora, Entidade, FatoRow, Grupo, IndexData, Metric, Scope, Status } from "./types";

const METRIC_COL: Record<Metric, number> = {
  quantidade: 2,
  quantidade_registros: 3,
  quantidade_cod_id_distinto: 4,
  extensao_km: 5,
  potencia_kva: 6,
};

export interface Cell {
  v: number | null;
  status: Status;
  motivo: string;
}

export interface Aggregate {
  v: number | null;
  /** DISTs que contribuíram com valor */
  n: number;
  /** DISTs do recorte com o indicador N/D */
  nd: number;
  /** DISTs do recorte que não têm a entidade no GDB */
  ausentes: number;
  total: number;
  alerta: number;
  partial: boolean;
}

/** Índice em memória do pacote público. Somente agregados; nenhuma linha individual. */
export class Dataset {
  readonly raw: IndexData;
  readonly dists: Distribuidora[];
  readonly grupos: Grupo[];
  readonly entidades: Entidade[];
  readonly familias: string[];
  private fatos = new Map<string, FatoRow>();
  private distById = new Map<number, Distribuidora>();
  private grupoById = new Map<string, Grupo>();
  private entById = new Map<string, Entidade>();

  constructor(raw: IndexData) {
    this.raw = raw;
    this.dists = [...raw.distribuidoras].sort((a, b) => a.sigla.localeCompare(b.sigla, "pt-BR"));
    this.grupos = [...raw.grupos].sort((a, b) => this.distsOfGroup(b.id, raw).length - this.distsOfGroup(a.id, raw).length || a.nome.localeCompare(b.nome));
    this.entidades = raw.entidades;
    const famOrder = ["Consumidores", "Geração conectada", "Rede", "Transformação", "Seccionamento", "Regulação", "Compensação reativa", "Medição", "Estruturas", "Iluminação pública", "Subestações e circuitos", "Perdas e balanço", "Cadastro auxiliar", "Área de atuação"];
    const fams = new Set(raw.entidades.map((e) => e.familia));
    this.familias = [...famOrder.filter((f) => fams.has(f)), ...[...fams].filter((f) => !famOrder.includes(f))];
    for (const r of raw.fatos.rows) this.fatos.set(`${r[0]}|${r[1]}`, r);
    for (const d of raw.distribuidoras) this.distById.set(d.dist, d);
    for (const g of raw.grupos) this.grupoById.set(g.id, g);
    for (const e of raw.entidades) this.entById.set(e.id, e);
  }

  private distsOfGroup(id: string, raw: IndexData) {
    return raw.distribuidoras.filter((d) => d.grupo === id && d.grupo_status === "verificado");
  }

  dist(id: number) { return this.distById.get(id); }
  grupo(id: string) { return this.grupoById.get(id); }
  entidade(id: string) { return this.entById.get(id); }
  entidadesDaFamilia(f: string) { return this.entidades.filter((e) => e.familia === f); }
  groupDists(id: string) { return this.dists.filter((d) => d.grupo === id && d.grupo_status === "verificado"); }

  hasEntity(dist: number, ent: string) { return this.fatos.has(`${dist}|${ent}`); }

  cell(dist: number, ent: string, metric: Metric): Cell | null {
    const r = this.fatos.get(`${dist}|${ent}`);
    if (!r) return null; // entidade inexistente no GDB do DIST: N/D, nunca zero
    return { v: r[METRIC_COL[metric]] as number | null, status: r[7], motivo: r[8] };
  }

  scopeDists(scope: Scope): number[] {
    if (scope.tipo === "brasil") return this.dists.map((d) => d.dist);
    if (scope.tipo === "grupo") return this.groupDists(scope.id).map((d) => d.dist);
    return this.distById.has(scope.id) ? [scope.id] : [];
  }

  scopeLabel(scope: Scope): string {
    if (scope.tipo === "brasil") return "Brasil";
    if (scope.tipo === "grupo") return this.grupo(scope.id)?.nome ?? scope.id;
    const d = this.dist(scope.id);
    return d ? d.sigla.replaceAll("_", " ") : `DIST ${scope.id}`;
  }

  /** Soma entre DISTs. DISTs são partições do território, então métricas por DIST são aditivas entre si. */
  aggregate(dists: number[], ent: string, metric: Metric): Aggregate {
    let v = 0, n = 0, nd = 0, ausentes = 0, alerta = 0;
    for (const d of dists) {
      const c = this.cell(d, ent, metric);
      if (!c) { ausentes++; continue; }
      if (c.v === null || c.status === "b") { nd++; continue; }
      v += c.v; n++;
      if (c.status === "l") alerta++;
    }
    return { v: n ? v : null, n, nd, ausentes, total: dists.length, alerta, partial: nd > 0 };
  }

  /** Consumidores: união de COD_ID por DIST (UCBT, UCMT e UCAT podem compartilhar códigos). Soma só DISTs com UC validadas. */
  consumidores(dists: number[]): Aggregate {
    const uni = this.raw.complementares["uc_uniao_distinta"] ?? {};
    let v = 0, n = 0, nd = 0, alerta = 0;
    for (const d of dists) {
      const valid = ["UCBT", "UCMT", "UCAT"].every((e) => { const c = this.cell(d, e, "quantidade"); return !c || c.v !== null; });
      const u = uni[String(d)]?.["UC*"];
      if (!valid || !u || u[0] === null) { nd++; continue; }
      v += u[0]; n++;
      if (u[1] === "l") alerta++;
    }
    return { v: n ? v : null, n, nd, ausentes: 0, total: dists.length, alerta, partial: nd > 0 };
  }

  complementar(indicador: string, dist: number, ent: string) {
    return this.raw.complementares[indicador]?.[String(dist)]?.[ent] ?? null;
  }
}

export function displayName(d: Distribuidora) {
  return d.sigla.replaceAll("_", " ");
}
