import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { consultarCodigo, parsePatrimonio, slotPatrimonial } from "../src/lib/patrimonio";
const raw = () => JSON.parse(gunzipSync(readFileSync("public/data/patrimonio/dicionario.json.gz")).toString("utf8"));
describe("Patrimônio documental sem homologação automática", () => {
  it("mantém Revisão 2 explícita e a vigência como pendência", () => { const d = parsePatrimonio(raw()); expect(d.source.revisao_lida).toBe("2"); expect(d.auditoria.arquivos_parquet_com_registros_acessiveis).toBe(0); });
  it("não confunde potência de 565, regulador e medida", () => { const d = parsePatrimonio(raw()); expect(slotPatrimonial(d.tucs["565"], "01", "A4")?.tabela).toBe("IIIB"); expect(slotPatrimonial(d.tucs["340"], "01", "A3")?.tabela).toBe("IIIB"); expect(slotPatrimonial(d.tucs["575"], "01", "A4")?.tabela).toBe("XII"); expect(slotPatrimonial(d.tucs["575"], "02", "A4")?.tabela).toBe("XIV"); });
  it("faixa de potência não vira valor nominal pontual", () => { const d = parsePatrimonio(raw()); const r = consultarCodigo(d, "565", "01", "A4", "29"); expect(r.valores[0].descricao).toContain("75"); expect(r.valores[0].natureza_valor).toBe("FAIXA"); expect(r.valores[0].valor_tecnico).toBeNull(); });
  it("distingue vazio, não aplicável e não traduzido", () => { const d = parsePatrimonio(raw()); expect(consultarCodigo(d, "565", "01", "A4", "").status).toBe("Vazio"); expect(consultarCodigo(d, "565", "01", "A4", "NA").status).toBe("Não aplicável declarado"); expect(consultarCodigo(d, "565", "01", "A4", "ZZ").status).toBe("Código não traduzido"); });
  it("recusa homologação de potência e mistura EQ/UN em agregados", () => { const a = raw(); a.potencia_recuperada_homologada_kva = 0; expect(() => parsePatrimonio(a)).toThrow(); const b = raw(); b.agregados_tipo_bem[0].entidades.push("UNTRMT"); expect(() => parsePatrimonio(b)).toThrow(); });
  it("código ambíguo não escolhe a primeira tradução", () => { const d = parsePatrimonio(raw()); expect(consultarCodigo(d, "565", "01", "A2", "91").status).toContain("ambíguo"); });
});
