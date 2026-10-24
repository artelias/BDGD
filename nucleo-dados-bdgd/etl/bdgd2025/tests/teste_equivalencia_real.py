"""Teste real de equivalencia_duplicatas.comparar() com publicacoes de SHA-256 diferente (DIST 11825, dados reais).
Raiz de teste isolada (nao toca o staging): T/proc, T/parquet, T/raw. Casos:
  A  publicacoes reais distintas (2023 x 2024)                -> deve divergir em atributos e geometria
  B1 mesmo GDB reempacotado (ZIP diferente, SHA diferente)     -> deve ser equivalente
  B2 GDB reescrito via GDAL sem alteracao (bytes internos novos) -> esperado equivalente; registra o que divergir
  C  um TUC alterado num registro de EQTRMT (parquet)          -> deve divergir so em EQTRMT tuc_mcpse/registro
  D  uma coordenada de PONNOT deslocada 1e-6 grau (GDB)          -> deve divergir so em PONNOT.geometria
  E  colunas do parquet reordenadas, conteudo igual             -> deve ser equivalente"""
import hashlib, json, os, pathlib, shutil, struct, sys, zipfile
T = pathlib.Path(sys.argv[1])  # raiz descartavel; o teste copia dados reais do staging privado e nada dele vai ao repositorio; SRC = pathlib.Path("D:/NUCLEO_BDGD_2022_2024")
os.environ["BDGD_HIST_ROOT"] = str(T)
sys.path.insert(0, "D:/NUCLEO_BDGD_2025/scripts")
import duckdb, pyogrio
from pyogrio import raw as pr
import equivalencia_duplicatas as eq

DIST = "11825"; I23 = ("2023", "7a0916b7025a4b32bb96fb890312e0d7"); I24 = ("2024", "e5ca1625686f48919e8cdb84b5b4b358")
shutil.rmtree(T, ignore_errors=True)
con = duckdb.connect(); con.execute("SET threads=2; SET memory_limit='256MB'")


def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def montar(caso, item, origem, zip_path, parquet_dir):
    for sub in ("proc", "parquet", "raw"): (T / sub / caso / DIST / item).mkdir(parents=True, exist_ok=True)
    for f in pathlib.Path(parquet_dir).glob("*.parquet"): shutil.copy(f, T / "parquet" / caso / DIST / item / f.name)
    shutil.copy(zip_path, T / "raw" / caso / DIST / item / f"{item}.zip")
    (T / "proc" / caso / DIST / item / "checkpoint.json").write_text(json.dumps({"source_sha256": sha(zip_path), "origem": origem}))


def zip_de(ano, it): return next((SRC / "raw" / ano / DIST / it).glob("*.zip"))
def pq_de(ano, it): return SRC / "parquet" / ano / DIST / it


TMP = T / "_tmp"; TMP.mkdir(parents=True)
z24 = zip_de(*I24)
with zipfile.ZipFile(z24) as z: z.extractall(TMP / "orig"); nomes = z.namelist()
gdb = next((TMP / "orig").glob("**/*.gdb"))


def rezip(pasta_gdb, destino, nivel):
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=nivel) as z:
        for f in sorted(pasta_gdb.rglob("*")):
            if f.is_file(): z.write(f, f"{pasta_gdb.name}/{f.relative_to(pasta_gdb).as_posix()}")


def reescrever(destino_gdb, alterar=None):
    """Copia todas as camadas com GDAL para um GDB novo; alterar(layer, tabela) pode modificar a tabela arrow."""
    destino_gdb.parent.mkdir(parents=True, exist_ok=True)
    for nome, tipo in pyogrio.list_layers(gdb):
        meta, tab = pr.read_arrow(gdb, layer=nome)
        if alterar: tab = alterar(nome, tab, meta)
        gname = meta.get("geometry_name") or "SHAPE"
        kw = dict(geometry_name=gname, geometry_type=meta.get("geometry_type"), crs=meta.get("crs")) if tipo else dict(geometry_type=None)
        if not tipo: tab = tab.drop([c for c in tab.column_names if c in ("wkb_geometry", "geometry")])
        pr.write_arrow(tab, destino_gdb, layer=nome, driver="OpenFileGDB", append=destino_gdb.exists(), **kw)


def deslocar(nome, tab, meta):
    if nome != "PONNOT": return tab
    import pyarrow as pa
    g = meta.get("geometry_name") or "wkb_geometry"; i = tab.schema.get_field_index(g if g in tab.column_names else tab.column_names[-1])
    wkbs = tab.column(i).to_pylist(); w = bytearray(wkbs[0]); bo = "<" if w[0] == 1 else ">"
    x = struct.unpack(bo + "d", w[5:13])[0]; w[5:13] = struct.pack(bo + "d", x + 1e-6); wkbs[0] = bytes(w)
    return tab.set_column(i, tab.schema.field(i), pa.array(wkbs, type=tab.schema.field(i).type))


casos = {}
# A: duas publicacoes reais diferentes
montar("A", "pub2023", "real 2023", zip_de(*I23), pq_de(*I23)); montar("A", "pub2024", "real 2024", z24, pq_de(*I24)); casos["A"] = ["pub2023", "pub2024"]
# B1: mesmo GDB reempacotado
rezip(gdb, TMP / "b1.zip", 1)
montar("B1", "orig", "original", z24, pq_de(*I24)); montar("B1", "rezip", "reempacotado", TMP / "b1.zip", pq_de(*I24)); casos["B1"] = ["orig", "rezip"]
# B2: GDB reescrito pelo GDAL
reescrever(TMP / "b2" / gdb.name); rezip(TMP / "b2" / gdb.name, TMP / "b2.zip", 6)
montar("B2", "orig", "original", z24, pq_de(*I24)); montar("B2", "gdal", "reescrito GDAL", TMP / "b2.zip", pq_de(*I24)); casos["B2"] = ["gdal", "orig"]
# C: um TUC alterado em EQTRMT
(TMP / "c").mkdir(); [shutil.copy(f, TMP / "c" / f.name) for f in pq_de(*I24).glob("*.parquet")]
src = (pq_de(*I24) / "EQTRMT.parquet").as_posix()
alvo = con.execute(f"SELECT COD_ID, TUC FROM read_parquet('{src}') ORDER BY COD_ID LIMIT 1").fetchone()
con.execute(f"COPY (SELECT * REPLACE (CASE WHEN COD_ID = '{alvo[0]}' THEN '999' ELSE TUC END AS TUC) FROM read_parquet('{src}')) TO '{(TMP / 'c' / 'EQTRMT.parquet').as_posix()}' (FORMAT parquet)")
rezip(gdb, TMP / "c.zip", 9)
montar("C", "orig", "original", z24, pq_de(*I24)); montar("C", "tuc", f"TUC de {alvo[0]}: {alvo[1]} -> 999", TMP / "c.zip", TMP / "c"); casos["C"] = ["orig", "tuc"]
# D: uma coordenada de PONNOT deslocada (mesmo parquet)
reescrever(TMP / "d" / gdb.name, deslocar); rezip(TMP / "d" / gdb.name, TMP / "d.zip", 6)
montar("D", "gdal", "reescrito GDAL", TMP / "b2.zip", pq_de(*I24)); montar("D", "geo", "PONNOT[0] x + 1e-6", TMP / "d.zip", pq_de(*I24)); casos["D"] = ["gdal", "geo"]
# E: colunas reordenadas
(TMP / "e").mkdir(); [shutil.copy(f, TMP / "e" / f.name) for f in pq_de(*I24).glob("*.parquet")]
src = (pq_de(*I24) / "SSDMT.parquet").as_posix()
cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{src}')").fetchall()][::-1]
con.execute(f"COPY (SELECT {', '.join(eq.ident(c) for c in cols)} FROM read_parquet('{src}')) TO '{(TMP / 'e' / 'SSDMT.parquet').as_posix()}' (FORMAT parquet)")
rezip(gdb, TMP / "e.zip", 3)
montar("E", "orig", "original", z24, pq_de(*I24)); montar("E", "reord", "colunas SSDMT invertidas", TMP / "e.zip", TMP / "e"); casos["E"] = ["orig", "reord"]

res = {}
for c, itens in casos.items():
    shas = {it: json.loads((T / "proc" / c / DIST / it / "checkpoint.json").read_text())["source_sha256"][:12] for it in itens}
    r = eq.comparar(c, DIST, sorted(itens), con)
    res[c] = {"sha256": shas, "equivalente": r["equivalente"], "criterio": r["criterio"], "n_diferencas": len(r["diferencas"]),
              "diferencas": r["diferencas"][:40], "entidades": len(r["entidades"])}
    print(c, "SHA distintos" if len(set(shas.values())) > 1 else "SHA igual", "->", "EQUIVALENTE" if r["equivalente"] else "DIVERGENTE",
          f"({len(r['diferencas'])} dif.)", r["diferencas"][:8], flush=True)
(T / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
shutil.rmtree(TMP, ignore_errors=True)
