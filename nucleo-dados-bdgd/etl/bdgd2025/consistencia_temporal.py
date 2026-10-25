"""Consistencia temporal da serie 2022-2025 (somente leitura): para cada DIST/ativo/medida com anos consecutivos validados,
sinaliza variacao anual > 50% (ou valor que vai a zero / sai de zero) que NAO esteja marcada como quebra de classificacao
ou de perimetro. Saida: output-historico/2022-2025/qa_consistencia_temporal.csv (sinal para revisao, nao correcao)."""
import csv, collections, pathlib
OUT = pathlib.Path("D:/NUCLEO_BDGD_2025/output-historico/2022-2025")
S = collections.defaultdict(dict)
for r in csv.DictReader(open(OUT / "serie_ativos_original.csv", encoding="utf-8-sig")):
    if r["status"] == "validado" and r["valor"] != "":
        S[(r["dist"], r["empresa"], r["ativo"], r["medida"])][int(r["ano"])] = (float(r["valor"]), r["comparabilidade"])
L = []; tot = 0
for (d, emp, at, med), v in S.items():
    for a in (2023, 2024, 2025):
        if a - 1 in v and a in v:
            tot += 1; x0, x1, comp = v[a - 1][0], v[a][0], v[a][1]
            var = None if x0 == 0 else x1 / x0 - 1
            if (x0 == 0) != (x1 == 0) or (var is not None and abs(var) > 0.5):
                L.append(dict(dist=d, empresa=emp, ativo=at, medida=med, de=a - 1, para=a, valor_de=x0, valor_para=x1,
                              variacao_pct="" if var is None else round(100 * var, 1), comparabilidade=comp,
                              situacao="explicada (quebra marcada)" if comp.startswith("quebra") else "revisar"))
with open(OUT / "qa_consistencia_temporal.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, ["dist", "empresa", "ativo", "medida", "de", "para", "valor_de", "valor_para", "variacao_pct", "comparabilidade", "situacao"], lineterminator="\n")
    w.writeheader(); w.writerows(sorted(L, key=lambda r: (r["situacao"], r["ativo"], int(r["dist"]), r["de"])))
c = collections.Counter(r["situacao"] for r in L)
print(f"pares ano-ano comparados: {tot}; sinalizados: {len(L)} {dict(c)}")
print("por ativo (revisar):", collections.Counter(r["ativo"] for r in L if r["situacao"] == "revisar").most_common(10))
