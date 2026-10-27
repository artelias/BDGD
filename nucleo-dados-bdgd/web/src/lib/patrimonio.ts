export interface SlotPatrimonial { nome: string; tabela: string; pagina: number }
export interface TucPatrimonial { tuc: string; nome: string; paginas: number[]; bens: Record<string, { codigo: string; descricao_documental: string; pagina: number; status: string }>; slots: Record<string, SlotPatrimonial>; status_slots: string; excecoes_a1?: Record<string, Record<string, SlotPatrimonial>>; tabelas_a4_por_a1?: Record<string, string> }
export interface ValorPatrimonial { codigo: string; descricao: string; pagina: number; valor_tecnico: string | null; unidade: string | null; natureza_valor: string; restricao_asterisco?: boolean }
export interface PatrimonioData { schema_version: string; source: { revisao_lida: string; sha256: string; url: string }; tucs: Record<string, TucPatrimonial>; tabelas: Record<string, ValorPatrimonial[]>; observados_cubos_2025: string[]; limites: string[]; auditoria: { arquivos_parquet_listados: number; arquivos_parquet_com_registros_acessiveis: number; tabela_IIIB: { codigos: number; valores_pontuais_inequivocos: number } }; agregados_tipo_bem: { DIST: string; ANO: number; conceito: string; TUC: string; A1: string; quantidade: number; entidades: string[]; fonte: string }[]; potencia_recuperada_homologada_kva: null; previsao_validada: false }
const obj = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null;
export function parsePatrimonio(x: unknown): PatrimonioData {
  if (!obj(x) || x.schema_version !== "patrimonio-web-1" || !obj(x.source) || !["2", "3"].includes(String(x.source.revisao_lida)) ||
    !obj(x.tucs) || !obj(x.tabelas) || !Array.isArray(x.observados_cubos_2025) || !Array.isArray(x.agregados_tipo_bem) ||
    !obj(x.auditoria) || x.potencia_recuperada_homologada_kva !== null || x.previsao_validada !== false) throw Error("Contrato patrimonial inválido.");
  for (const row of x.agregados_tipo_bem) if (!obj(row) || typeof row.DIST !== "string" || row.ANO !== 2025 || typeof row.quantidade !== "number" || !Number.isFinite(row.quantidade) || row.quantidade < 0 || !Array.isArray(row.entidades) || row.entidades.some((e) => typeof e !== "string" || e.startsWith("UN"))) throw Error("Agregado patrimonial sem população de equipamentos separada.");
  return x as unknown as PatrimonioData;
}
export function slotPatrimonial(t: TucPatrimonial | undefined, a1: string, slot: string) {
  const s = (t?.excecoes_a1?.[a1] ?? t?.slots)?.[slot];
  return s && s.tabela === "CONDICIONAL:575:A4" ? { ...s, tabela: t?.tabelas_a4_por_a1?.[a1] ?? "PENDENTE" } : s;
}
export function consultarCodigo(data: PatrimonioData, tuc: string, a1: string, slot: string, raw: string) {
  const code = /^[0-9]{1,2}$/.test(raw.trim()) ? raw.trim().padStart(2, "0") : raw.trim();
  const t = data.tucs[tuc], spec = slotPatrimonial(t, a1, slot);
  if (!code) return { status: "Vazio", valores: [] as ValorPatrimonial[] };
  if (/^(NA|N\/A)$/i.test(code)) return { status: "Não aplicável declarado", valores: [] as ValorPatrimonial[] };
  if (slot === "A1") { const b = t?.bens[code]; return { status: b ? b.status : "Código não traduzido", valores: b ? [{ codigo: code, descricao: b.descricao_documental, pagina: b.pagina, valor_tecnico: null, unidade: null, natureza_valor: "CATEGORICO" }] : [] }; }
  if (!t) return { status: "TUC não traduzida", valores: [] as ValorPatrimonial[] };
  if (!t.bens[a1]) return { status: "A1 não traduzido", valores: [] as ValorPatrimonial[] };
  if (!spec) return { status: t.status_slots === "CONFERIDO_DOCUMENTAL" ? "Não aplicável no documento lido" : "Slot não verificado", valores: [] as ValorPatrimonial[] };
  const valores = (data.tabelas[spec.tabela] ?? []).filter((v) => v.codigo === code);
  return { status: !valores.length ? "Código não traduzido" : new Set(valores.map((v) => v.descricao)).size > 1 ? "Código ambíguo — não escolher valor" : valores.some((v) => v.restricao_asterisco) ? "Restrição contextual pendente" : "Tradução documental — vigência pendente", valores };
}
