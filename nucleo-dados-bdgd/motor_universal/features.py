"""Transformações apenas do passado e ajuste exclusivo no treino."""
from statistics import fmean, pstdev
from .contracts import iso, usable


def feature_row(history, year, source, definitions, cutoff):
    past = [r for r in history if r["ano"] < year and usable(r)]
    if not past or past[-1]["ano"] != year - 1:
        raise ValueError("Sem defasagem anual contígua")
    values = [r["valor_alvo"] for r in past]
    out = {"ano": year, "lag_1": values[-1], "media_movel_3": fmean(values[-3:]),
           "crescimento_lag": (values[-1] / values[-2] - 1) if len(values) > 1 and values[-2] > 0 else None}
    # Cada referência também precisa ser conhecida no corte, não apenas ter ano antigo.
    for name, spec in definitions.items():
        if not spec.get("comparabilidade_validada") or not spec.get("evidencia_comparabilidade"):
            raise ValueError(f"FEATURE_SEM_COMPARABILIDADE_VALIDADA:{name}")
        f = source.get("features", {}).get(name)
        if f is None or iso(f["disponivel_em"]) > iso(cutoff):
            raise ValueError(f"FEATURE_INDISPONIVEL_NO_CORTE:{name}")
        if iso(f["referencia"]).year >= year and not f.get("cenario_id"):
            raise ValueError(f"FEATURE_CONTEMPORANEA_SEM_CENARIO:{name}")
        if f["valor"] is None and not spec.get("permite_imputacao", False):
            raise ValueError(f"FEATURE_AUSENTE:{name}")
        out[name] = f["valor"]
    # Razões/densidades/interações são declaradas pelo fornecedor, nunca inferidas de nomes.
    for name, spec in definitions.items():
        for denominator in spec.get("dividir_por", []):
            if denominator not in out:
                raise ValueError("Denominador não declarado")
            a, b = out[name], out[denominator]
            out[f"razao:{name}/{denominator}"] = a / b if a is not None and b is not None and b > 0 else None
        for other in spec.get("interagir_com", []):
            if other not in out:
                raise ValueError("Interação não declarada")
            a, b = out[name], out[other]
            out[f"interacao:{name}*{other}"] = a * b if a is not None and b is not None else None
    return out


class FeaturePipeline:
    """Encoder pequeno, auditável; médias/escalas/categorias aprendidas só no fit."""
    def fit(self, rows):
        if not rows:
            raise ValueError("Treino de features vazio")
        self.columns = sorted({k for row in rows for k in row})
        self.numeric, self.categories = {}, {}
        for name in self.columns:
            values = [r[name] for r in rows if r.get(name) is not None]
            if not values:
                raise ValueError(f"Feature sem dados de treinamento: {name}")
            if isinstance(values[0], str):
                self.categories[name] = sorted(set(values))
            else:
                self.numeric[name] = (fmean(values), pstdev(values) or 1)
        return self

    def transform(self, rows):
        out = []
        for row in rows:
            encoded = []
            for name in self.columns:
                if name in self.numeric:
                    mean, scale = self.numeric[name]
                    v = row.get(name)
                    encoded.append(((mean if v is None else v) - mean) / scale)
                else:
                    encoded.extend(float(row.get(name) == c) for c in self.categories[name])
            out.append(encoded)
        return out
