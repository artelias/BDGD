"""Municipality codes: official IBGE reference, national invalid-code scan and the audited (NOT homologated) Celesc 2023 bridge.

Reference: the IBGE SIDRA extracts already on disk (motor_v2/externals/raw, downloaded earlier for the external features); each
row carries the 7-digit code (D1C) and the official name "Name - UF" (D1N). Nothing is downloaded here.

Bridge proposal for a code written as '0' + the first six digits of the IBGE code (e.g. 0420910 for 4209102): the candidate is
the unique IBGE code whose first six digits match. Evidence recorded per code: uniqueness of the six-digit prefix, the UF implied
by the candidate, whether the candidate appears in the same company's adjacent competences, agreement of the CONJ -> municipality
relation with the adjacent competences (record aggregates of the same company), and continuity of the UC counts. The proposal is
written as PENDENTE_HOMOLOGACAO; until a person homologates it the affected (DIST, year) stays out of the model panels."""
import json
from collections import defaultdict
from pathlib import Path

import duckdb

from ..runner import atomic, digest

RAW = Path('D:/NUCLEO_BDGD_2025/motor_v2/externals/raw')


def reference():
    """{code: dict(nome, uf)} from every SIDRA extract on disk + the source hashes."""
    out, sources = {}, {}
    for p in sorted(RAW.glob('*.json')):
        data = json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(data, list) or not data or data[0].get('D1C') != 'Município (Código)':
            continue
        sources[p.name] = digest(p)
        for r in data[1:]:
            code, name = str(r.get('D1C') or ''), str(r.get('D1N') or '')
            if len(code) == 7 and code.isdigit():
                nome, _, uf = name.rpartition(' - ')
                out[code] = dict(nome=nome or name, uf=uf or None)
    return out, sources


def units_by_year(panel, dist):
    """{year: {MUN: customers}} and {year: {CONJ: {MUN: customers}}} from the checkpointed UCBT aggregates."""
    db = duckdb.connect(); db.execute("SET memory_limit='256MB'; SET threads=1")
    mun, conj = defaultdict(dict), defaultdict(lambda: defaultdict(dict))
    try:
        for f in sorted(Path(panel).glob(f'{dist}/ucbt_quantidade/*/territorial.parquet')):
            y = int(f.parent.name)
            for m, c, n in db.execute('SELECT MUN, CONJ, sum(clientes_ativos) FROM read_parquet(?) GROUP BY ALL', [str(f)]).fetchall():
                m = m or 'NULO'
                mun[y][m] = mun[y].get(m, 0) + int(n)
                conj[y][c or 'NULO'][m] = conj[y][c or 'NULO'].get(m, 0) + int(n)
    finally:
        db.close()
    return mun, conj


def scan(panel, dists, ref):
    """Share of active UCBT customers whose municipality code is not an IBGE code, per (DIST, year)."""
    out = []
    for d in dists:
        mun, _ = units_by_year(panel, d)
        for y, m in sorted(mun.items()):
            tot = sum(m.values()); bad = {k: v for k, v in m.items() if k not in ref}
            zero6 = sum(v for k, v in bad.items() if len(k) == 7 and k.startswith('0') and k.isdigit())
            out.append(dict(DIST=d, ano=y, clientes=tot, municipios=len(m), codigos_fora_ibge=len(bad), clientes_fora_ibge=sum(bad.values()),
                            share_fora_ibge=sum(bad.values()) / tot if tot else None, clientes_padrao_zero_mais_6=zero6,
                            exemplos=sorted(bad)[:5]))
    return out


def propose(panel, dist, year, ref):
    mun, conj = units_by_year(panel, dist)
    prefix = defaultdict(list)
    for c in ref:
        prefix[c[:6]].append(c)
    adj = {y: set(mun.get(y, {})) for y in (year - 1, year + 1)}
    # CONJ -> set of municipalities it holds in the adjacent competences (a conjunto may span several municipalities)
    dom = {}
    for y in (year - 1, year + 1):
        for c, ms in conj.get(y, {}).items():
            dom.setdefault(c, set()).update(ms)
    mapping, agree_w, total_w = [], 0, 0
    for code, n in sorted(mun.get(year, {}).items()):
        if code in ref:
            continue
        cand = prefix.get(code[1:7], []) if len(code) == 7 and code.startswith('0') and code.isdigit() else []
        target = cand[0] if len(cand) == 1 else None
        # record-level evidence through CONJ: customers of this code whose CONJ is dominated by `target` in the adjacent years
        a = w = 0
        for c, ms in conj.get(year, {}).items():
            if code in ms and c in dom:
                w += ms[code]
                if target and target in dom[c]:
                    a += ms[code]
        agree_w += a; total_w += w
        prev, nxt = mun.get(year - 1, {}).get(target), mun.get(year + 1, {}).get(target)
        mapping.append(dict(codigo_publicado=code, clientes=n, candidato_ibge=target, candidatos=cand, nome=ref.get(target, {}).get('nome'),
                            uf=ref.get(target, {}).get('uf'), prefixo_unico=len(cand) == 1, colisao_no_mesmo_ano=bool(target and target in mun.get(year, {})),
                            presente_ano_anterior=bool(target and target in adj[year - 1]), presente_ano_seguinte=bool(target and target in adj[year + 1]),
                            clientes_ano_anterior=prev, clientes_ano_seguinte=nxt,
                            razao_vs_anterior=(n / prev) if prev else None, razao_vs_seguinte=(nxt / n) if nxt and n else None,
                            concordancia_conj=(a / w) if w else None))
    targets = [m['candidato_ibge'] for m in mapping if m['candidato_ibge']]
    ufs = sorted({m['uf'] for m in mapping if m['uf']})
    adj_ufs = sorted({ref[c]['uf'] for y in (year - 1, year + 1) for c in mun.get(y, {}) if c in ref})
    ratios = [m['razao_vs_anterior'] for m in mapping if m['razao_vs_anterior']]
    checks = dict(codigos_fora_ibge=len(mapping), com_candidato_unico=sum(m['prefixo_unico'] for m in mapping),
                  candidatos_distintos=len(set(targets)), colisoes=sum(m['colisao_no_mesmo_ano'] for m in mapping),
                  ufs_dos_candidatos=ufs, ufs_da_empresa_nos_anos_adjacentes=adj_ufs, conj_estaveis=sum(1 for c in conj.get(year, {}) if c in dom),
                  conj_no_ano=len(conj.get(year, {})), presentes_nos_dois_anos_adjacentes=sum(m['presente_ano_anterior'] and m['presente_ano_seguinte'] for m in mapping),
                  concordancia_conj_ponderada=(agree_w / total_w) if total_w else None,
                  razao_clientes_vs_ano_anterior_min=min(ratios) if ratios else None, razao_clientes_vs_ano_anterior_max=max(ratios) if ratios else None,
                  clientes_cobertos=sum(m['clientes'] for m in mapping if m['candidato_ibge']), clientes_fora_ibge=sum(m['clientes'] for m in mapping))
    sufficient = (checks['codigos_fora_ibge'] and checks['com_candidato_unico'] == checks['codigos_fora_ibge'] and checks['colisoes'] == 0
                  and checks['candidatos_distintos'] == checks['codigos_fora_ibge'] and set(ufs) <= set(adj_ufs)
                  and checks['presentes_nos_dois_anos_adjacentes'] == checks['codigos_fora_ibge']
                  and (checks['concordancia_conj_ponderada'] or 0) >= .95)
    return dict(id=f'MUN_RECODE_{dist}_{year}', tipo='recodificacao_municipal', dist=dist, ano=year, status='PENDENTE_HOMOLOGACAO',
                regra="codigo publicado = '0' + 6 primeiros digitos do codigo IBGE; candidato = unico codigo IBGE com esse prefixo",
                evidencia_suficiente_para_proposta=bool(sufficient), verificacoes=checks, mapeamento=mapping,
                efeito_no_motor='quarentena: (DIST, ano) fora dos paineis de treino/teste ate decisao humana registrada',
                decisao=None)
