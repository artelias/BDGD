"""Aplica ao produto publicado a regra de série "extremo só com Moderado" e os motivos por série, preservando os números publicados.

    python motor_cenarios/aplicar_regra_moderado.py <contrato> <internas> <raw> <saida_dir> <web_json>

Etapa de 2026-11-03 (correções finais da RC 1.0). O gerador passou a:
  * não publicar Conservador nem Agressivo numa série cujo Moderado não é publicável (6 séries publicavam um extremo sem o Moderado:
    os extremos são definidos em relação ao Moderado, então o estado era inconsistente);
  * registrar, em `motivos`, por que uma série fica sem o cenário quando a métrica tem modelo para ele.
Como em preservar_publicado.py, uma regeneração no Windows concorda com o produto publicado (gerado no Linux) só dentro da tolerância
de plataforma. Para não trocar números publicados por ruído de plataforma, o produto final é o publicado com a mesma regra aplicada:

  * a regra é aplicada ao JSON e ao CSV publicados (só remove valores; nenhum número é recalculado);
  * os `motivos` e o SHA-256 do código vêm da regeneração, nos mesmos caminhos;
  * o JSON final precisa concordar com a regeneração (comparar_produtos sem erro); o CSV final só pode diferir dela por contagens de
    até 1 unidade; senão o script falha sem gravar nada;
  * MANIFESTO.json registra o SHA-256 dos bytes finais do CSV de cenários e do código.
Depois disso, `cenarios.py ... --check` precisa aprovar o produto final (é a verificação oficial)."""
import csv
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cenarios as C  # noqa: E402

EXTREMOS = ("conservador", "agressivo")
CSV_NOME = "CENARIOS_CONSERVADOR_MODERADO_AGRESSIVO.csv"
ANOS = [str(a) for a in C.HORIZONTE]


def aplicar(pub, reg):
    """Remove de `pub` os extremos sem Moderado e copia os motivos de `reg`. Devolve as séries alteradas (conceito, métrica, dist, cenário)."""
    regm = {(m["conceito"], m["metrica"]): m for m in reg["metricas"]}
    removidos = []
    for m in pub["metricas"]:
        r = regm[(m["conceito"], m["metrica"])]
        for d, s in m["series"].items():
            if s.get("moderado") is None:
                for c in EXTREMOS:
                    if s.get(c) is not None:
                        s[c] = None
                        removidos.append((m["conceito"], m["metrica"], d, c))
            mot = r["series"].get(d, {}).get("motivos")
            if mot:
                s["motivos"] = mot
    pub["fontes_sha256"]["codigo/cenarios.py"] = reg["fontes_sha256"]["codigo/cenarios.py"]
    return removidos


def main(contrato, internas, raw, saida, web):
    saida, web = Path(saida), Path(web)
    with tempfile.TemporaryDirectory() as tmp:
        C.main(contrato, internas, raw, Path(tmp) / "saida", Path(tmp) / "web.json")
        reg = json.loads((Path(tmp) / "web.json").read_text(encoding="utf-8"))
        csv_reg = (Path(tmp) / "saida" / CSV_NOME).read_text(encoding="utf-8").replace("\r\n", "\n")
    pub = json.loads(web.read_text(encoding="utf-8"))
    removidos = aplicar(pub, reg)
    erros, contagens, folga = C.comparar_produtos(reg, pub)
    if erros:
        sys.exit(f"BLOQUEADO: produto com a regra diverge da regeneração ({len(erros)}): {erros[:3]}")
    # CSV publicado com a mesma regra: valores dos extremos removidos em branco e status próprio
    alvo = saida / CSV_NOME
    linhas = list(csv.DictReader(io.StringIO(alvo.read_text(encoding="utf-8").replace("\r\n", "\n"))))
    tirar = set(removidos)
    for r in linhas:
        if (r["conceito"], r["metrica"], r["dist"], r["cenario"]) in tirar:
            r.update({a: "" for a in ANOS}); r["status"] = "indisponivel_sem_moderado"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(linhas[0]), lineterminator="\n"); w.writeheader(); w.writerows(linhas)
    csv_final = buf.getvalue()
    dif = [(a, b) for a, b in zip(csv_final.split("\n"), csv_reg.split("\n")) if a != b]
    for a, b in dif:
        xa, xb = a.split(","), b.split(",")
        ruins = [(u, v) for u, v in zip(xa, xb) if u != v and not (u.lstrip("-").isdigit() and v.lstrip("-").isdigit() and abs(int(u) - int(v)) <= 1)]
        if len(xa) != len(xb) or ruins:
            sys.exit(f"BLOQUEADO: CSV com a regra difere da regeneração além de 1 unidade: {a[:120]} | {b[:120]}")
    if len(csv_final.split("\n")) != len(csv_reg.split("\n")):
        sys.exit("BLOQUEADO: CSV com a regra e regeneração têm números de linhas diferentes")
    web.write_text(json.dumps(pub, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8", newline="\n")
    alvo.write_text(csv_final, encoding="utf-8", newline="\n")
    man = json.loads((saida / "MANIFESTO.json").read_text(encoding="utf-8"))
    man["fontes_sha256"]["codigo/cenarios.py"] = reg["fontes_sha256"]["codigo/cenarios.py"]
    man["saidas_sha256"][CSV_NOME] = hashlib.sha256(alvo.read_bytes()).hexdigest()
    (saida / "MANIFESTO.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    n_mot = sum(1 for m in pub["metricas"] for s in m["series"].values() if s.get("motivos"))
    print(f"REGRA APLICADA: {len(removidos)} extremos sem Moderado removidos {removidos}; {n_mot} séries com motivos; "
          f"{len(dif)} linhas do CSV com o valor publicado (regeneração difere em até 1 unidade); contagens comparadas {contagens}, folga {folga}")


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    main(*sys.argv[1:])
