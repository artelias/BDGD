"""Aplica ao produto publicado só o que uma regeneração ACRESCENTA, preservando os números já publicados.

    python motor_cenarios/preservar_publicado.py <json_publicado> <csv_publicado> <saida_dir> <web_json>

Uso desta etapa (2026-11-01): o patch B acrescenta os campos de erro físico (mae_fisico, wape_fisico, vies_fisico, fisico_motivo)
e o status `simulacao_validada_retrospectivamente` passa a `simulacao_comparada_retrospectivamente`. O produto publicado foi gerado
no runner Linux; uma regeneração no Windows (scikit-learn 1.8.0, a versão fixada) concorda com ele dentro da tolerância de plataforma
de comparar_produtos, mas 3 contagens em ~16 mil diferem em 1 unidade (arredondamento meio-para-cima de um valor bruto com ruído).
Para não alterar números publicados por ruído de plataforma, o produto final é o publicado mais os campos novos da regeneração:

  * o JSON regenerado, sem os campos novos, deve concordar com o publicado (comparar_produtos sem erro); senão o script falha;
  * os campos novos são copiados da regeneração para os mesmos caminhos do publicado;
  * o CSV final é o publicado com o status renomeado; a regeneração só pode diferir dele por contagens de até 1 unidade;
  * MANIFESTO.json registra o SHA-256 dos bytes finais.
Depois disso, `cenarios.py ... --check` precisa aprovar o produto final (é a verificação oficial)."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cenarios import comparar_produtos  # noqa: E402

NOVOS = ("mae_fisico", "wape_fisico", "vies_fisico", "fisico_motivo")
ANTIGO, NOVO = "simulacao_validada_retrospectivamente", "simulacao_comparada_retrospectivamente"


def sem_novos(o):
    if isinstance(o, dict):
        return {k: sem_novos(v) for k, v in o.items() if k not in NOVOS}
    if isinstance(o, list):
        return [sem_novos(v) for v in o]
    return o


def enxertar(pub, reg):
    """Copia para `pub` os campos novos que `reg` tem nos mesmos caminhos; devolve quantos objetos receberam campos."""
    n = 0
    if isinstance(pub, dict) and isinstance(reg, dict):
        novos = {k: reg[k] for k in NOVOS if k in reg and k not in pub}
        if novos:
            pub.update(novos); n += 1
        for k in pub:
            if k in reg:
                n += enxertar(pub[k], reg[k])
    elif isinstance(pub, list) and isinstance(reg, list):
        for a, b in zip(pub, reg):
            n += enxertar(a, b)
    return n


def main(json_pub, csv_pub, saida, web):
    saida, web = Path(saida), Path(web)
    pub = json.loads(Path(json_pub).read_text(encoding="utf-8"))
    reg = json.loads(web.read_text(encoding="utf-8"))
    erros, contagens, folga = comparar_produtos(sem_novos(reg), pub)
    if erros:
        sys.exit(f"BLOQUEADO: a regeneração diverge do publicado fora da tolerância ({len(erros)}): {erros[:3]}")
    n = enxertar(pub, reg)
    web.write_text(json.dumps(pub, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8", newline="\n")
    csv_final = Path(csv_pub).read_text(encoding="utf-8").replace("\r\n", "\n").replace(ANTIGO, NOVO)
    alvo = saida / "CENARIOS_CONSERVADOR_MODERADO_AGRESSIVO.csv"
    regen = alvo.read_text(encoding="utf-8").replace("\r\n", "\n")
    dif = [(a, b) for a, b in zip(csv_final.split("\n"), regen.split("\n")) if a != b]
    for a, b in dif:
        xa, xb = a.split(","), b.split(",")
        ruins = [(u, v) for u, v in zip(xa, xb) if u != v and not (u.lstrip("-").isdigit() and v.lstrip("-").isdigit() and abs(int(u) - int(v)) <= 1)]
        if len(xa) != len(xb) or ruins:
            sys.exit(f"BLOQUEADO: CSV regenerado difere além de 1 unidade: {a[:120]} | {b[:120]}")
    alvo.write_text(csv_final, encoding="utf-8", newline="\n")
    m = json.loads((saida / "MANIFESTO.json").read_text(encoding="utf-8"))
    m["saidas_sha256"][alvo.name] = hashlib.sha256(alvo.read_bytes()).hexdigest()
    (saida / "MANIFESTO.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"PRESERVADO: {n} objetos receberam campos físicos; {len(dif)} linhas do CSV mantidas com o valor publicado "
          f"(regeneração difere em até 1 unidade); contagens comparadas {contagens[0] if isinstance(contagens, list) else contagens}")


if __name__ == "__main__":
    main(*sys.argv[1:])
