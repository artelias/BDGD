"""Auditoria dos produtos públicos contra o contrato de natureza física (somente biblioteca padrão, somente leitura).

    python -m motor_v2.audit_public_products [--output motor_v2/reports/auditoria_produtos_publicos.json]

Para cada produto lê os valores publicados, classifica cada um pela natureza da unidade e conta: valores de contagem inteiros,
valores de contagem fracionários (violação), valores negativos de contagem, valores de extensão/potência com decimais (esperado) e
incoerências natureza × unidade × métrica. Sai com código 1 se houver violação. Tooltip, tabela e CSV de exportação da tela são
cobertos por `web/e2e/natureza-fisica.spec.ts`, que usa os mesmos produtos como referência."""
import argparse
import csv
import gzip
import json
import sys
from pathlib import Path

from .metric_contract import nature_of

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "web/public/data/previsoes"
METRIC_NATURE = {"quantidade": "discrete_count", "extensao_km": "continuous_length", "potencia_kva": "continuous_capacity"}
CENARIOS = ("conservador", "moderado", "agressivo")


class Tally:
    def __init__(self, name):
        self.name = name
        self.counts = self.frac_counts = self.neg_counts = self.continuous = self.continuous_decimal = 0
        self.incoherent = []
        self.examples = []

    def add(self, nature, value, where):
        if value is None:
            return
        if nature == "discrete_count":
            self.counts += 1
            if value < 0:
                self.neg_counts += 1; self.examples.append((where, value))
            if float(value) != int(value):
                self.frac_counts += 1
                if len(self.examples) < 5: self.examples.append((where, value))
        else:
            self.continuous += 1
            self.continuous_decimal += float(value) != int(value)

    def check(self, declared, unit, metric, where):
        try:
            by_unit = nature_of(unit) if unit else None
        except ValueError:
            self.incoherent.append(f"{where}: unidade sem natureza ({unit})"); return None
        by_metric = METRIC_NATURE.get(metric)
        nat = declared or by_unit or by_metric
        for label, other in (("unidade", by_unit), ("métrica", by_metric)):
            if nat and other and nat != other:
                self.incoherent.append(f"{where}: natureza {nat} incompatível com {label} ({unit}/{metric})")
        return nat

    def report(self):
        return {"produto": self.name, "contagens": self.counts, "contagens_fracionarias": self.frac_counts, "contagens_negativas": self.neg_counts,
                "continuas": self.continuous, "continuas_com_decimais": self.continuous_decimal,
                "incoerencias": self.incoherent[:10], "n_incoerencias": len(self.incoherent), "exemplos_violacao": self.examples[:5],
                "ok": not (self.frac_counts or self.neg_counts or self.incoherent)}


def audit_cenarios_motor():
    t = Tally("cenarios-motor.json")
    data = json.loads((PUBLIC / "cenarios-motor.json").read_text(encoding="utf-8"))
    for m in data["metricas"]:
        nat = t.check(m.get("natureza"), m["unidade"], m["metrica"], f"{m['conceito']}/{m['metrica']}")
        for dist, s in m["series"].items():
            for _, v in s["hist"]:
                t.add(nat, v, f"{m['conceito']}/{dist}/hist")
            for c in CENARIOS:
                for v in s.get(c) or []:
                    t.add(nat, v, f"{m['conceito']}/{m['metrica']}/{dist}/{c}")
    return t.report()


def audit_resumo_motor_universal():
    t = Tally("motor-universal-resumo.json.gz")
    data = json.loads(gzip.decompress((PUBLIC / "motor-universal-resumo.json.gz").read_bytes()))
    for s in data["series"]:
        nat = t.check(s.get("natureza_fisica"), s["unidade"], s["metrica"], f"{s['objetivo_id']}/{s['metrica']}/{s['DIST']}")
        for h in s["historico"]:
            t.add(nat, h["valor"], f"{s['objetivo_id']}/{s['DIST']}/hist")
        for m in s["modelos"]:
            for v in m["futuro"]:
                t.add(nat, v, f"{s['objetivo_id']}/{s['metrica']}/{s['DIST']}/{m['modelo']}")
    return t.report()


def audit_exploratorios():
    t = Tally("cenarios-exploratorios-2026-2030.json")
    data = json.loads((PUBLIC / "cenarios-exploratorios-2026-2030.json").read_text(encoding="utf-8"))
    for s in data["series"]:
        dist, conceito, metrica, unidade, hist, tendencia = s[0], s[2], s[3], s[4], s[5], s[6]
        nat = t.check(None, unidade, metrica, f"{conceito}/{metrica}/{dist}")
        for v in list(hist) + list(tendencia):
            t.add(nat, v, f"{conceito}/{dist}")
    return t.report()


def audit_csv(path, nature_col, value_cols, label):
    """CSV publicado: coluna de natureza por linha e colunas numéricas por ano."""
    t = Tally(label)
    textual_decimal = 0
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            nat = row[nature_col]
            for col in value_cols:
                raw = (row.get(col) or "").strip()
                if raw == "":
                    continue
                t.add(nat, float(raw), f"{label}/{row.get('conceito')}/{row.get('dist')}/{col}")
                if nat == "discrete_count" and "." in raw:
                    textual_decimal += 1       # "123.0": inteiro, mas grafado com casa decimal
    out = t.report(); out["contagens_grafadas_com_casa_decimal"] = textual_decimal
    return out


def run():
    saida = ROOT / "motor_cenarios/saida"
    reports = [audit_cenarios_motor(), audit_resumo_motor_universal(), audit_exploratorios()]
    reports.append(audit_csv(saida / "CENARIOS_CONSERVADOR_MODERADO_AGRESSIVO.csv", "natureza", ("2026", "2027", "2028", "2029", "2030", "base_2025"),
                             "CENARIOS_CONSERVADOR_MODERADO_AGRESSIVO.csv"))
    return {"schema": "auditoria-produtos-publicos-1", "produtos": reports, "ok": all(r["ok"] for r in reports)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
