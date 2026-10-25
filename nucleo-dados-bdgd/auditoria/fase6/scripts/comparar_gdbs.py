"""Fase 6 — compara publicacoes direto dos ZIPs oficiais (somente leitura; sem DuckDB, sem pipeline):
por camada, esquema + contagem + impressao (n, soma, xor) de blake2b-64 sobre atributos (exceto OBJECTID) e geometria.
Usado para: arquivos excluidos por competencia x publicacao valida do ano declarado na BASE; candidatos extras de pares.
Saida: evidencias/comparacao_gdbs.csv"""
import csv, hashlib, json, pathlib, sys, zipfile
import pyogrio
from pyogrio import raw as pr

H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024"); R = pathlib.Path("D:/NUCLEO_BDGD_2025"); OUT = R / "auditoria-fase6/evidencias/comparacao_gdbs.csv"
M64 = 2 ** 64


def zip_de(ano, dist, item):
    if str(ano) == "2025":
        return next((R / "staging_raw" / f"DIST={dist}" / "DATA_BASE=2025-12-31").glob("*.zip"), None)
    return next((H / "raw" / str(ano) / str(dist) / item).glob("*.zip"), None)


def src_de(z):
    with zipfile.ZipFile(z) as zz:
        raizes = sorted({n[:n.lower().index(".gdb") + 4] for n in zz.namelist() if ".gdb/" in n.lower() or n.lower().endswith(".gdb")})
    return f"/vsizip/{pathlib.Path(z).as_posix()}/{raizes[0]}" if raizes else f"/vsizip/{pathlib.Path(z).as_posix()}"


def impressoes(src):
    out = {}
    for nome, _ in pyogrio.list_layers(src):
        n = s = x = 0
        with pr.open_arrow(src, layer=nome, batch_size=20000, use_pyarrow=True) as (meta, rdr):
            campos = [f for f in meta["fields"] if f.upper() != "OBJECTID"]; g = meta.get("geometry_name") or "wkb_geometry"
            for b in rdr:
                cols = [b.column(b.schema.get_field_index(c)).to_pylist() for c in campos if c in b.schema.names]
                gg = b.column(b.schema.get_field_index(g)).to_pylist() if g in b.schema.names else [None] * b.num_rows
                for i in range(b.num_rows):
                    h = hashlib.blake2b(digest_size=8)
                    for c in cols: h.update(repr(c[i]).encode("utf-8", "surrogatepass")); h.update(b"\x1f")
                    h.update(gg[i] or b""); v = int.from_bytes(h.digest(), "little"); n += 1; s = (s + v) % M64; x ^= v
        out[nome.upper().removesuffix("_TAB")] = (n, s, x)
    return out


def comparar(a, b):
    za, zb = zip_de(*a), zip_de(*b)
    if not za or not zb: return dict(resultado="zip_ausente")
    ia, ib = impressoes(src_de(za)), impressoes(src_de(zb))
    comuns = sorted(set(ia) & set(ib)); iguais = [c for c in comuns if ia[c] == ib[c]]
    reg_a = sum(v[0] for v in ia.values()); reg_b = sum(v[0] for v in ib.values())
    res = "identico" if len(iguais) == len(comuns) == len(ia) == len(ib) else ("mesmo_conteudo_parcial" if iguais else "distinto")
    return dict(resultado=res, camadas_a=len(ia), camadas_b=len(ib), camadas_identicas=len(iguais), camadas_comuns=len(comuns),
                registros_a=reg_a, registros_b=reg_b, camadas_diferentes=";".join(c for c in comuns if ia[c] != ib[c])[:300])


inv = {(r["ano"], r["dist"], r["item_id"]): r for r in csv.DictReader(open(H / "inventario/inventario_historico_2022_2024.csv", encoding="utf-8"))}
CONF = list(csv.DictReader(open(R / "auditoria-fase4/MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv", encoding="utf-8")))
usado = {(c["ano_alvo"], c["dist"]): c["item_id"] for c in CONF if c["uso_na_serie"] in ("em_uso_na_serie", "pacote_2025", "par_competencia_unica_valida_em_uso")}
pares = {}
for c in CONF:
    if c["uso_na_serie"] == "par_divergente_pendente": pares.setdefault((c["ano_alvo"], c["dist"]), []).append(c["item_id"])
casos = []
for c in CONF:
    if c["uso_na_serie"] not in ("excluido_competencia", "par_item_excluido_competencia"): continue
    ano_base = c["DAT_FNL"][-4:]
    a = (c["ano_alvo"], c["dist"], c["item_id"])
    alvos = [(ano_base, c["dist"], usado[(ano_base, c["dist"])])] if (ano_base, c["dist"]) in usado else [(ano_base, c["dist"], it) for it in pares.get((ano_base, c["dist"]), [])]
    if not alvos: casos.append((a, None, f"BASE declara {ano_base}: sem publicacao valida nesse ano para comparar"))
    for b in alvos: casos.append((a, b, f"excluido por competencia (titulo {c['ano_alvo']}, BASE {c['DAT_INC']}-{c['DAT_FNL']}) x publicacao de {ano_base}"))
linhas = []
for a, b, motivo in casos:
    r = comparar(a, b) if b else dict(resultado="sem_comparacao")
    linhas.append(dict(ano_a=a[0], dist=a[1], item_a=a[2], ano_b=b[0] if b else "", item_b=b[2] if b else "", contexto=motivo, **{k: r.get(k, "") for k in
                  ("resultado", "camadas_a", "camadas_b", "camadas_identicas", "camadas_comuns", "registros_a", "registros_b", "camadas_diferentes")}))
    print(linhas[-1]["dist"], a[0], "x", linhas[-1]["ano_b"], linhas[-1]["resultado"], linhas[-1]["camadas_identicas"], "/", linhas[-1]["camadas_comuns"], flush=True)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(linhas[0]), lineterminator="\n"); w.writeheader(); w.writerows(linhas)
