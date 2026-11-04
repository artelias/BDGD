"""Gera RELATORIO_MODELOS_EXECUTADOS.md e TABELA_FINAL_METRICA_DISTRIBUIDORA.csv a partir do produto publicado.
Uso: python relatorio.py <web_json> <saida_dir>"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROT = {"conservador": "Conservador", "moderado": "Moderado", "agressivo": "Agressivo"}
EST = {"tres_cenarios": "três cenários", "dois_cenarios": "dois cenários", "somente_moderado": "somente moderado",
       "somente_baseline": "somente baseline (persistência)", "bloqueado": "bloqueado"}


def pct(x, d=2):
    return "N/D" if x is None else f"{x * 100:.{d}f}%".replace(".", ",")


def main(web, saida):
    p = json.loads(Path(web).read_text(encoding="utf-8"))
    saida = Path(saida)
    M, V = p["metricas"], p["variaveis"]
    ext_usadas = {v["variavel"]: v["modelos_que_usaram"] for v in V if v["tipo"] == "externa" and v["modelos_que_usaram"]}
    linhas = []
    for m in M:
        cen = m["cenarios"]
        usa_ext = [v for v, mods in ext_usadas.items() if any(cen[c] and cen[c] in mods.split("|") for c in cen)]
        for d, s in sorted(m["series"].items(), key=lambda x: p["empresas"].get(x[0], x[0])):
            contagem = m.get("natureza") == "discrete_count"

            def val(c):
                if not cen[c]:
                    return "indisponível (métrica)"
                if not s[c]:
                    return "indisponível (série)"
                v = s[c][-1]
                if contagem and (type(v) is not int or v < 0):       # contagem: inteiro não negativo, nunca 650.0 nem 649.5
                    raise ValueError(f"contagem fracionária ou negativa em {m['ativo']}/{d}/{c}: {v!r}")
                return f"{v if contagem else format(v, '.1f')} [{cen[c]}]"
            status = ("bloqueado" if not s["moderado"] else "experimental" if m["experimental"] else "publicável — simulação condicional")
            linhas.append({"metrica": f"{m['ativo']} — {m['metrica']} ({m['unidade']})", "distribuidora": f"{p['empresas'].get(d, d)} (DIST {d})",
                           "base_2025": s["hist"][-1][1], "conservador_2030": val("conservador"), "moderado_2030": val("moderado"),
                           "agressivo_2030": val("agressivo"), "melhor_erro_observado_mdape": pct(s["erro_moderado"]) if s["erro_moderado"] is not None else "N/D",
                           "variaveis_externas_utilizadas": "|".join(usa_ext) or "nenhuma", "status_publicacao": status})
    with open(saida / "TABELA_FINAL_METRICA_DISTRIBUIDORA.csv", "w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), lineterminator="\n"); w.writeheader(); w.writerows(linhas)

    est = Counter(m["estado"] for m in M)
    n_ext = sum(1 for m in M if any(m["cenarios"][c] and m["cenarios"][c] in "|".join(ext_usadas.values()).split("|") for c in ROT))
    melhor = sum(1 for m in M if m["cenarios"]["moderado"] and m["modelos"].get("persistencia", {}).get("wape") is not None
                 and m["modelos"][m["cenarios"]["moderado"]]["wape"] < m["modelos"]["persistencia"]["wape"])
    ativos_2030 = sorted({m["ativo"] for m in M if any(s["moderado"] for s in m["series"].values())})
    series_mod = sum(1 for m in M for s in m["series"].values() if s["moderado"])
    series_hist = sum(len(m["series"]) for m in M)
    uso_modelo = Counter((c, m["cenarios"][c]) for m in M for c in ROT if m["cenarios"][c])
    L = []
    L.append("# Relatório dos modelos executados — Motor de Expansão Elétrica\n")
    L.append(f"Produto: `web/public/data/previsoes/cenarios-motor.json` (esquema `{p['schema_version']}`). Ano-base {p['base']}; horizonte "
             f"{p['horizonte'][0]}–{p['horizonte'][-1]}; origens de backtest {', '.join(map(str, p['origens_backtest']))}. "
             "Todos os números abaixo vêm da execução real (`motor_cenarios/cenarios.py`), regenerável e verificada no CI com `--check`.\n")
    L.append("## Resumo\n")
    L.append(f"- Métricas (ativo × métrica) avaliadas: **{len(M)}** (25 ativos; quantidade/extensão do contrato nacional e potência kVA experimental de transformadores TUC 565/570 via EQ→UN).")
    for k in ("tres_cenarios", "dois_cenarios", "somente_moderado", "somente_baseline", "bloqueado"):
        L.append(f"- {EST[k].capitalize()}: **{est.get(k, 0)}**")
    L.append(f"- Métricas cujo modelo moderado supera a persistência no backtest: **{melhor}**")
    L.append(f"- Métricas com algum cenário usando variáveis externas: **{n_ext}**")
    L.append(f"- Métricas experimentais: **{sum(1 for m in M if m['experimental'])}**")
    L.append(f"- Ativos com trajetória 2026–2030 no cenário moderado: **{len(ativos_2030)}** — {', '.join(ativos_2030)}")
    L.append(f"- Séries DIST × métrica com histórico ≥ 1 ano terminando em 2025: {series_hist}; com trajetória moderada: **{series_mod}**\n")
    L.append("## Modelos selecionados por cenário (contagem de métricas)\n")
    L.append("| Cenário | Modelo | Métricas |\n|---|---|---|")
    for (c, mid), n in sorted(uso_modelo.items(), key=lambda x: (list(ROT).index(x[0][0]), -x[1])):
        L.append(f"| {ROT[c]} | {p['modelos'][mid]['nome']} | {n} |")
    L.append("\n## Matriz por métrica\n")
    L.append("| Ativo | Métrica | Estado | Conservador | Moderado | Agressivo | WAPE moderado | WAPE persistência | Pontos | Séries projetadas |\n|---|---|---|---|---|---|---|---|---|---|")
    for m in sorted(M, key=lambda m: (m["familia"], m["ativo"], m["metrica"])):
        c = m["cenarios"]; mo = m["modelos"]
        ws = mo[c["moderado"]]["wape"] if c["moderado"] else None
        L.append(f"| {m['ativo']} | {m['metrica']}{' (exp.)' if m['experimental'] else ''} | {EST[m['estado']]} | {c['conservador'] or '—'} | {c['moderado'] or '—'} | "
                 f"{c['agressivo'] or '—'} | {pct(ws)} | {pct(mo.get('persistencia', {}).get('wape'))} | {mo[c['moderado']]['n'] if c['moderado'] else 0} | "
                 f"{sum(1 for s in m['series'].values() if s['moderado'])} |")
    L.append("\n## Modelos executados — formulação\n")
    for mid, d in p["modelos"].items():
        L.append(f"- **{d['nome']}** (`{mid}`; {d['familia']}): `{d['formula']}`")
    L.append("\n## Variáveis\n")
    L.append("| Variável | Tipo | Fonte | Disponível em | Utilizada | Modelos |\n|---|---|---|---|---|---|")
    for v in V:
        L.append(f"| `{v['variavel']}` | {v['tipo']} | {v['fonte']} | {v['disponivel_em']} | {v['utilizada']} | {v['modelos_que_usaram'].replace('|', ', ') or '—'} |")
    L.append("\n## Limitações\n")
    L.append("- Quatro competências anuais: backtest com 2 origens e horizontes 1–2; 2028–2030 são extrapolações sem verificação retrospectiva.")
    L.append("- Avaliação retrospectiva revisada (os anos 2022–2024 são `COMPLETO_TECNICO`/ressalvas, não homologação humana); não é point-in-time.")
    L.append("- Sem intervalos probabilísticos; a distância entre cenários não é intervalo de confiança.")
    L.append("- Estoque físico não identifica entradas, baixas, obras, necessidade técnica ou CAPEX. Nenhum total nacional projetado é publicado.")
    L.append("- Potência kVA (TUC 565/570) é experimental: derivada fora do contrato homologado, com portões de vínculo EQ→UN ≥ 98%, escala kVA e igualdade da contagem com o contrato.")
    L.append("- Potência de reguladores: indisponível (EQRE.POT_NOM é código de domínio e UNREMT não tem POT_NOM). Potência de transformadores de medida: não derivada nesta execução.")
    L.append("- Coopera 2025 (DIST 5370): consumidores sem projeção — UCBT vazia na fonte, mantida a ressalva; nunca convertida em zero.")
    (saida / "RELATORIO_MODELOS_EXECUTADOS.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main(*sys.argv[1:])
