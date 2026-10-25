"""Fase 6 — integridade de todos os ZIPs locais (somente leitura): SHA-256 recalculado x registrado (download.json /
inventario / checkpoint) e abertura do diretorio central do ZIP. Saida: evidencias/integridade_downloads.csv"""
import csv, glob, hashlib, json, pathlib, zipfile, time
H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024"); R = pathlib.Path("D:/NUCLEO_BDGD_2025"); OUT = R / "auditoria-fase6/evidencias/integridade_downloads.csv"
inv = {r["item_id"]: r for r in csv.DictReader(open(H / "inventario/inventario_historico_2022_2024.csv", encoding="utf-8"))}
inv25 = {r["item_id"]: r for r in csv.DictReader(open(R / "inventario/inventario_2025.csv", encoding="utf-8")) if r["item_id"]}
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(8 << 20), b""): h.update(b)
    return h.hexdigest()
linhas = []
alvos = [(p, "2022-2024") for p in glob.glob(str(H / "raw/*/*/*/*.zip"))] + [(p, "2025") for p in glob.glob(str(R / "staging_raw/**/*.zip"), recursive=True)]
for i, (p, origem) in enumerate(sorted(alvos)):
    p = pathlib.Path(p); t0 = time.time()
    if origem == "2022-2024": item = p.parent.name
    else:
        dist = next((x.split("=")[1] for x in p.parts if x.startswith("DIST=")), "")
        item = next((k for k, r in inv25.items() if r["dist"] == dist), p.stem)
    reg = ""
    dj = p.parent / "download.json"
    if dj.exists():
        try: reg = json.loads(dj.read_text(encoding="utf-8")).get("sha256", "")
        except Exception: reg = ""
    if not reg: reg = (inv.get(item) or {}).get("sha256", "") or (inv25.get(item) or {}).get("checksum_sha256", "")
    real = sha(p)
    try:
        with zipfile.ZipFile(p) as z: n = len(z.namelist()); zok = "sim"
    except Exception as e: n, zok = 0, f"nao: {str(e)[:60]}"
    linhas.append(dict(origem=origem, item_id=item, arquivo=str(p), bytes=p.stat().st_size, sha256=real, sha256_registrado=reg or "nao_registrado",
                       sha_confere="sim" if reg and reg == real else ("sem_registro" if not reg else "NAO"), zip_abre=zok, membros=n))
    print(i, origem, item[:10], linhas[-1]["sha_confere"], zok, f"{time.time() - t0:.0f}s", flush=True)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(linhas[0]), lineterminator="\n"); w.writeheader(); w.writerows(linhas)
import collections
print(collections.Counter((l["origem"], l["sha_confere"], l["zip_abre"][:3]) for l in linhas))
