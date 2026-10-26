"""Backtest expansivo e seleção com última origem reservada como auditoria."""
from collections import Counter, defaultdict
from statistics import fmean, pstdev
import math
from . import VERSION
from .contracts import validate_panel, series_key, contiguous_tail, iso, usable
from .registry import fingerprint, validate_registry
from .models import CANDIDATES, EXTENSIONS, predict


def metrics(points):
    if not points:
        return {"n": 0, "mae": None, "rmse": None, "wape": None, "vies": None, "desvio_erros": None}
    errors = [p["previsto"] - p["observado"] for p in points]
    denom = sum(abs(p["observado"]) for p in points)
    return {"n": len(points), "mae": fmean(abs(e) for e in errors),
            "rmse": math.sqrt(fmean(e * e for e in errors)),
            "wape": sum(abs(e) for e in errors) / denom if denom > 0 else None,
            "vies": fmean(errors), "desvio_erros": pstdev(errors)}


def run(panel, registry, *, base_year=2025, final_year=2030, as_of="2026-10-26", code_version="desconhecida",
        candidates=None):
    validate_panel(panel, registry)
    if not base_year < final_year <= 2100 or iso(as_of).year < base_year:
        raise ValueError("Corte/horizonte inválido")
    chosen_ids = candidates or list(CANDIDATES)
    if "persistencia" not in chosen_ids or any(c not in CANDIDATES for c in chosen_ids):
        raise ValueError("Candidatos inválidos; persistência é baseline obrigatório")
    targets = validate_registry(registry)
    grouped = defaultdict(list)
    for row in panel["rows"]:
        if row["ano"] > base_year and row["valor_alvo"] is not None:
            raise ValueError("Alvo posterior ao corte não pode entrar no experimento")
        grouped[series_key(row)].append(row)
    results, aggregate_errors, family_errors = [], defaultdict(list), defaultdict(list)
    for key, all_rows in sorted(grouped.items()):
        target = targets[key[1], key[2]]
        raw = [r for r in all_rows if r["ano"] <= base_year]
        history = contiguous_tail(raw)
        reasons = []
        if any(r["disponivel_em"] is not None and iso(r["disponivel_em"]) > iso(as_of) for r in raw):
            reasons.append("ALVO_AINDA_NAO_DISPONIVEL_NO_CORTE")
        if not history or history[-1]["ano"] != base_year:
            reasons.append("SEM_BASE_FINAL_ELEGIVEL")
        if len(history) < 3:
            reasons.append("MENOS_DE_TRES_OBSERVACOES_CONTIGUAS")
        if target.get("natureza_alvo", "estoque_fisico") != "estoque_fisico":
            reasons.append("NATUREZA_ALVO_FORA_DO_ESCOPO_ESTOQUE_FISICO")
        if target.get("requer_comparabilidade", True) and any(not r.get("comparabilidade_validada") or not r.get("evidencia_comparabilidade") for r in history):
            reasons.append("METRICA_SEM_COMPARABILIDADE_VALIDADA")
        if len({r["unidade"] for r in raw}) > 1:
            raise ValueError("Unidade mudou dentro da série")
        result = {"DIST": key[0], "empresa": all_rows[0].get("empresa", key[0]),
                  "objetivo_id": key[1], "metrica": key[2], "unidade": target["unidade"], "familia": target["familia"],
                  "territorio": all_rows[0]["territorio"], "perimetro_id": key[5], "regra_versao": key[6],
                  "status": "dados_insuficientes" if reasons else "simulacao_condicional",
                  "motivos": reasons, "observacoes_treino": len(history), "treino_anos": [r["ano"] for r in history],
                  "estados_origem": dict(Counter(r["status_qualidade"] for r in raw)),
                  "historico": [{"ano": r["ano"], "valor": r["valor_alvo"], "estado": r["status_qualidade"],
                                 "proveniencia": r.get("proveniencia", {}), "ruptura": r["ruptura"]} for r in sorted(raw, key=lambda r: r["ano"])],
                  "previsao_validada": False, "intervalo_previsao": None, "candidatos": [], "projecoes": []}
        ordered = sorted(raw, key=lambda r: r["ano"])
        for i, point in enumerate(result["historico"]):
            previous = ordered[i-1] if i else None
            current = next(r for r in ordered if r["ano"] == point["ano"])
            comparable = not target.get("requer_comparabilidade", True) or all(r.get("comparabilidade_validada") and r.get("evidencia_comparabilidade") for r in [current, previous or current])
            point["variacao_liquida"] = (current["valor_alvo"] - previous["valor_alvo"]
                if comparable and previous and usable(current) and usable(previous) and not current["ruptura"] and current["ano"] == previous["ano"]+1 else None)
        result["natureza_alvo"] = target.get("natureza_alvo", "estoque_fisico")
        result["necessidade_expansao"] = {"valor": None, "motivo": "NAO_IDENTIFICAVEL_APENAS_POR_ESTOQUE"}
        if reasons:
            results.append(result)
            continue
        # Cada data de origem é compartilhada por todos os candidatos. Última origem nunca seleciona.
        origins = [r["ano"] for r in history[1:-1]]
        selection_origins, holdout = origins[:-1], origins[-1]
        candidate_records = []
        definitions = {name: definition for name, definition in panel.get("feature_definitions", {}).items()
                       if not definition.get("objetivos_aplicaveis") or key[1] in definition["objetivos_aplicaveis"]}
        for model_id in chosen_ids:
            c = CANDIDATES[model_id]
            folds, failures = [], []
            for i in range(2, len(history)):
                train, observation = history[:i], history[i]
                origin = train[-1]["ano"]
                cutoff = f"{origin}-12-31"
                # Revisões históricas são permitidas só como avaliação retrospectiva declarada.
                real_time = all(r["disponivel_em"] is not None and iso(r["disponivel_em"]) <= iso(cutoff) for r in train)
                for horizon in range(1, min(final_year - base_year, len(history) - i) + 1):
                    test = history[i + horizon - 1]
                    # Features do ano alvo só são lidas pelo filtro de disponibilidade do modelo.
                    future = {r["ano"]: r for r in history[i:i+horizon]}
                    try:
                        if model_id == "poisson" and target.get("tipo_alvo") != "contagem":
                            raise ValueError("POISSON_REQUER_CONTAGEM")
                        preds, _ = predict(c, train, list(range(origin+1, test["ano"]+1)),
                                           definitions, future, cutoff)
                        folds.append({"origem": origin, "ano": test["ano"], "horizonte": horizon,
                                      "observado": test["valor_alvo"], "previsto": preds[-1],
                                      "point_in_time": real_time})
                    except (ValueError, OverflowError) as error:
                        failures.append({"origem": origin, "horizonte": horizon, "motivo": str(error)})
            one = [p for p in folds if p["horizonte"] == 1]
            selection = [p for p in one if p["origem"] in selection_origins]
            audit = [p for p in one if p["origem"] == holdout]
            future_rows = {r["ano"]: r for r in all_rows if r["ano"] > base_year}
            try:
                if model_id == "poisson" and target.get("tipo_alvo") != "contagem":
                    raise ValueError("POISSON_REQUER_CONTAGEM")
                future, diagnostics = predict(c, history, list(range(base_year+1, final_year+1)),
                                              definitions, future_rows, as_of)
                future_failure = None
            except (ValueError, OverflowError) as error:
                future, diagnostics, future_failure = [], {}, str(error)
            eligible = (len(selection) == len(selection_origins) and len(selection) >= (3 if c.sklearn_class else 2)
                        and len(audit) == 1 and bool(future))
            record = {"modelo": model_id, "hiperparametros": dict(c.params), "complexidade": c.complexity,
                      "folds": folds, "falhas": failures, "metricas_diagnosticas": metrics(one),
                      "metricas_selecao": metrics(selection), "metricas_auditoria": metrics(audit),
                      "por_horizonte": {str(h): metrics([p for p in folds if p["horizonte"] == h]) for h in sorted({p["horizonte"] for p in folds})},
                      "elegivel_selecao": eligible, "falha_projecao": future_failure,
                      "diagnosticos": diagnostics, "futuro": future}
            candidate_records.append(record)
        baseline = next(r for r in candidate_records if r["modelo"] == "persistencia")
        alternatives = [r for r in candidate_records if r["elegivel_selecao"]]
        # Complexidade só desempata; exige melhoria de 2% no conjunto de seleção, não no holdout.
        selected = baseline
        if alternatives:
            best = min(alternatives, key=lambda r: (r["metricas_selecao"]["mae"], r["complexidade"]))
            base_mae = baseline["metricas_selecao"]["mae"]
            if base_mae and best["metricas_selecao"]["mae"] < 0.98 * base_mae:
                selected = best
        result.update({"modelo_selecionado": selected["modelo"], "candidatos": candidate_records,
                       "origens_selecao": selection_origins, "origem_auditoria": holdout,
                       "justificativa": "Baseline conservador: amostra/ganho insuficiente" if selected is baseline else "Ganho fora da amostra na seleção; última origem reservada para auditoria",
                       "validacao": "retrospectiva_limitada" if len(origins) < 5 or not all(p["point_in_time"] for p in selected["folds"]) else "avaliacao_temporal_sem_homologacao",
                       "variaveis": selected["diagnosticos"].get("variaveis", []),
                       "projecoes": [{"ano": y, "valor": v, "natureza": "simulacao_condicional",
                                      "variacao_liquida": v - (selected["futuro"][i-1] if i else history[-1]["valor_alvo"]),
                                      "necessidade_expansao": None,
                                      "intervalo": None, "horizonte_com_backtest": str(y-base_year) in selected["por_horizonte"]}
                                     for i, (y, v) in enumerate(zip(range(base_year+1, final_year+1), selected["futuro"]))],
                       "proveniencia_treino": [r.get("proveniencia", {}) for r in history]})
        if not selected["futuro"]:
            result["status"] = "dados_insuficientes"
            result["motivos"].append("BASELINE_NAO_EXECUTAVEL")
        for model in candidate_records:
            for p in model["folds"]:
                if p["horizonte"] == 1:
                    aggregate_errors[(key[1], key[2], target["unidade"], model["modelo"])].append(p)
                    family_errors[(target["familia"], key[2], target["unidade"], model["modelo"])].append(p)
        results.append(result)
    target_summaries = []
    for (asset, metric), t in targets.items():
        items = [r for r in results if r["objetivo_id"] == asset and r["metrica"] == metric]
        target_summaries.append({**t, "series": len(items), "series_elegiveis": sum(bool(r["projecoes"]) for r in items),
                                 "motivo": None if items else "SEM_HISTORICO_NESTA_METRICA",
                                 "estados": dict(Counter(r["status"] for r in items))})
    return {"schema_version": "experimento-bdgd-1", "engine_version": VERSION,
            "experiment_id": fingerprint({"panel": panel, "registry": registry, "candidates": chosen_ids,
                                          "base_year": base_year, "final_year": final_year, "as_of": as_of,
                                          "code_version": code_version, "engine_version": VERSION}),
            "dataset_version": panel["dataset_version"], "dataset_sha256": fingerprint(panel),
            "source_sha256": panel.get("source_sha256"),
            "code_version": code_version, "as_of": as_of, "base_year": base_year,
            "horizontes": list(range(base_year+1, final_year+1)), "sintetico": panel["sintetico"],
            "previsao_validada": False, "objetivos": target_summaries, "series": results,
            "comparacao_objetivos": [{"objetivo_id": k[0], "metrica": k[1], "unidade": k[2], "modelo": k[3],
                                      "metricas": metrics(v)} for k, v in sorted(aggregate_errors.items())],
            "comparacao_familias": [{"familia": k[0], "metrica": k[1], "unidade": k[2], "modelo": k[3],
                                     "metricas": metrics(v), "nota": "Diagnóstico de erros, não soma de estoques ou amostra independente"}
                                    for k, v in sorted(family_errors.items())],
            "extensoes_nao_implementadas": EXTENSIONS,
            "agregacao_nacional": {"valor": None, "motivo": "Sem contrato de universo completo, disjunção territorial e reconciliação; somas automáticas bloqueadas"},
            "limites": panel.get("limites", []) + ["Sem intervalos probabilísticos: calibração não demonstrada",
                        "Linhas agregadas compartilham empresas, ativos e anos; não são observações independentes. Validação por série e blocos temporais",
                        "Estoque e variação líquida não identificam necessidade de expansão",
                        "Erros de seleção não substituem auditoria na última origem",
                        "Homologação humana e validação preditiva não são produzidas pelo software"]}
