"""Registro extensível de candidatos. Dependências ML são opcionais e lazy."""
from dataclasses import dataclass
from statistics import fmean
import math
from .features import FeaturePipeline, feature_row


@dataclass(frozen=True)
class Candidate:
    id: str
    min_train: int
    complexity: int
    sklearn_class: str = ""
    params: tuple = ()


CANDIDATES = {
    c.id: c for c in [Candidate("persistencia", 2, 0), Candidate("tendencia_ols", 2, 1),
                      Candidate("crescimento_historico", 2, 2),
                      Candidate("ridge", 8, 3, "Ridge", (("alpha", 10.0),)),
                      Candidate("lasso", 8, 4, "Lasso", (("alpha", 1.0), ("max_iter", 10000))),
                      Candidate("elastic_net", 8, 5, "ElasticNet", (("alpha", 1.0), ("l1_ratio", 0.5), ("max_iter", 10000))),
                      Candidate("poisson", 12, 6, "PoissonRegressor", (("alpha", 1.0), ("max_iter", 1000))),
                      Candidate("random_forest", 20, 7, "RandomForestRegressor", (("n_estimators", 80), ("max_depth", 4), ("min_samples_leaf", 3), ("random_state", 42), ("n_jobs", 1))),
                      Candidate("hist_gradient_boosting", 30, 8, "HistGradientBoostingRegressor", (("max_iter", 80), ("max_leaf_nodes", 7), ("min_samples_leaf", 5), ("random_state", 42))) ]
}
EXTENSIONS = {"sazonal": "Frequência anual; não há sazonalidade identificável",
              "painel_hierarquico": "Exige contrato territorial/populações e avaliação entre grupos; plugin futuro",
              "gam": "Plugin opcional não implementado", "binomial_negativa": "Plugin opcional não implementado",
              "xgboost": "Dependência não adicionada sem benefício demonstrado",
              "lightgbm": "Dependência não adicionada sem benefício demonstrado",
              "catboost": "Dependência não adicionada sem benefício demonstrado"}


def predict(candidate, history, years, definitions=None, future=None, cutoff=None):
    if len(history) < candidate.min_train:
        raise ValueError("AMOSTRA_TREINO_INSUFICIENTE")
    values = [r["valor_alvo"] for r in history]
    end = history[-1]["ano"]
    if not years or years != sorted(set(years)) or any(not isinstance(y, int) or isinstance(y, bool) or y <= end for y in years):
        raise ValueError("HORIZONTES_FUTUROS_ORDENADOS_OBRIGATORIOS")
    if cutoff is not None and any(r.get("disponivel_em") is not None and r["disponivel_em"] > cutoff for r in history):
        raise ValueError("ALVO_TREINO_INDISPONIVEL_NA_ORIGEM")
    diagnostics = {"variaveis": [], "hiperparametros": dict(candidate.params)}
    if not candidate.sklearn_class:
        mx, my = fmean(r["ano"] for r in history), fmean(values)
        slope = sum((r["ano"] - mx) * (r["valor_alvo"] - my) for r in history) / sum((r["ano"] - mx) ** 2 for r in history)
        if candidate.id == "crescimento_historico" and (values[0] <= 0 or values[-1] <= 0):
            raise ValueError("CRESCIMENTO_INDEFINIDO_COM_ZERO")
        rate = (values[-1] / values[0]) ** (1 / (end - history[0]["ano"])) - 1 if values[0] > 0 and values[-1] > 0 else None
        out = [values[-1] if candidate.id == "persistencia" else my + slope * (y - mx)
               if candidate.id == "tendencia_ols" else values[-1] * (1 + rate) ** (y - end) for y in years]
        diagnostics.update({"variaveis": ["estoque_passado", "ano"], "inclinacao_ols": slope if candidate.id == "tendencia_ols" else None})
    else:
        if cutoff is None:
            raise ValueError("DATA_CORTE_OBRIGATORIA_PARA_FEATURES")
        try:
            from sklearn import linear_model, ensemble
        except ImportError as exc:
            raise ValueError("DEPENDENCIA_ML_NAO_INSTALADA") from exc
        definitions, future = definitions or {}, future or {}
        xs = [feature_row(history[:i], r["ano"], r, definitions, min(cutoff, f"{r['ano']-1}-12-31"))
              for i, r in enumerate(history) if i >= 2]
        encoder = FeaturePipeline().fit(xs)
        factory = getattr(linear_model if hasattr(linear_model, candidate.sklearn_class) else ensemble, candidate.sklearn_class)
        model = factory(**dict(candidate.params))
        if candidate.id == "poisson" and sum(values[2:]) == 0:
            raise ValueError("POISSON_SEM_MASSA_POSITIVA")
        model.fit(encoder.transform(xs), values[2:])
        working, out = list(history), []
        # Recursão usa previsões anteriores identificadas, jamais alvos futuros observados.
        for year in range(end + 1, max(years) + 1):
            source = future.get(year, {"features": {}})
            x = feature_row(working, year, source, definitions, cutoff, allow_imputation=False)
            value = float(model.predict(encoder.transform([x]))[0])
            if not math.isfinite(value) or value < 0:
                raise ValueError("PROJECAO_NEGATIVA_OU_NAO_FINITA_REJEITADA")
            working.append({**history[-1], "ano": year, "valor_alvo": value})
            if year in years:
                out.append(value)
        diagnostics.update({"variaveis": encoder.columns, "transformacoes_ajustadas_no_treino": True,
                            "explicacao": "Associações preditivas; não identificam causalidade ou necessidade de investimento"})
    if any(not math.isfinite(v) or v < 0 for v in out):
        raise ValueError("PROJECAO_NEGATIVA_OU_NAO_FINITA_REJEITADA")
    return out, diagnostics
