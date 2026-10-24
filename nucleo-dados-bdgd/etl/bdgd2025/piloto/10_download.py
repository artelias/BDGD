"""Download retomavel (HTTP Range) com retries, SHA-256 e teste de integridade do ZIP.
Uso: 10_download.py <inventario_2025.csv> <dir_raw> <dist> [<dist>...]"""
import csv, hashlib, json, sys, time, urllib.request, zipfile, pathlib, datetime
inv, raw = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
alvo = set(sys.argv[3:])
for r in csv.DictReader(open(inv, encoding="utf-8")):
    if r["dist"] not in alvo or r["data_base_declarada"] != "2025-12-31": continue
    d = raw / f"DIST={r['dist']}" / "DATA_BASE=2025-12-31"; d.mkdir(parents=True, exist_ok=True)
    dest = d / f"{r['item_id']}.gdb.zip"; total = int(r["tamanho_bytes"])
    for tent in range(6):
        have = dest.stat().st_size if dest.exists() else 0
        if have >= total: break
        try:
            req = urllib.request.Request(r["url_download"], headers={"Range": f"bytes={have}-"})
            with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "ab" if resp.status == 206 else "wb") as f:
                while chunk := resp.read(1 << 20): f.write(chunk)
        except Exception as e:
            print(r["dist"], "tentativa", tent, repr(e), flush=True); time.sleep(min(60, 2 ** tent))
    h = hashlib.sha256()
    with open(dest, "rb") as f:
        while b := f.read(1 << 22): h.update(b)
    ok_zip = zipfile.ZipFile(dest).testzip() is None
    rec = {"dist": r["dist"], "item_id": r["item_id"], "arquivo": str(dest), "bytes": dest.stat().st_size, "esperado": total,
           "sha256": h.hexdigest(), "zip_integro": ok_zip, "baixado_em": datetime.datetime.now().isoformat(timespec="seconds")}
    (d / "download.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec), flush=True)
