"""Produto republicado x commit de referência 4ba0710: que campos mudaram (só leitura)."""
import json, subprocess, sys
from collections import Counter
from pathlib import Path
RAIZ = Path('D:/NUCLEO_BDGD_2025/wt-confiabilidade/nucleo-dados-bdgd')
REF = sys.argv[1] if len(sys.argv) > 1 else '4ba0710'
BASE = 'nucleo-dados-bdgd/web/public/data/confiabilidade/'


def velho(rel):
    r = subprocess.run(['git', '-C', str(RAIZ), 'show', f'{REF}:{BASE}{rel}'], capture_output=True)
    return json.loads(r.stdout.decode('utf-8')) if r.returncode == 0 else None


mud = Counter(); exemplos = {}
def nota(k, ex):
    mud[k] += 1
    exemplos.setdefault(k, ex)

for f in sorted((RAIZ / 'web/public/data/confiabilidade/distribuidoras').glob('*.json')):
    rel = 'distribuidoras/' + f.name
    n, v = json.loads(f.read_text(encoding='utf-8')), velho(rel)
    for k in set(n) | set(v):
        if k in ('conjuntos', 'anual'):
            continue
        if n.get(k) != v.get(k):
            nota(f'dist.{k}', (f.name,))
    for a in set(n['anual']) | set(v['anual']):
        x, y = n['anual'].get(a, {}), v['anual'].get(a, {})
        for k in set(x) | set(y):
            if x.get(k) != y.get(k):
                nota(f'anual.{k}', (f.name, a, y.get(k), x.get(k)))
    vc = {c['c']: c for c in v['conjuntos']}
    for c in n['conjuntos']:
        o = vc.pop(c['c'], None)
        if o is None:
            nota('conjunto novo', (f.name, c['c'])); continue
        for k in set(c) | set(o):
            if k == 'a':
                continue
            if c.get(k) != o.get(k):
                nota(f'conj.{k}', (f.name, c['c']))
        for a in set(c['a']) | set(o['a']):
            x, y = c['a'].get(a), o['a'].get(a)
            if x is None or y is None:
                nota('ano incluído/removido', (f.name, c['c'], a)); continue
            for k in set(x) | set(y):
                if k == 'rec':
                    rx, ry = x.get('rec') or {}, y.get('rec') or {}
                    for kk in set(rx) | set(ry):
                        if rx.get(kk) != ry.get(kk) and kk not in ('meses_dec', 'meses_fec'):
                            nota(f'rec.{kk}', (f.name, c['c'], a, ry.get(kk), rx.get(kk)))
                elif x.get(k) != y.get(k):
                    nota(f'bloco.{k}', (f.name, c['c'], a, y.get(k), x.get(k)))
    for c in vc:
        nota('conjunto removido', (f.name, c))
for a in (2022, 2023, 2024, 2025):
    n = json.loads((RAIZ / f'web/public/data/confiabilidade/nacional/{a}.json').read_text(encoding='utf-8')); v = velho(f'nacional/{a}.json')
    cv = v['campos']; cn = n['campos']
    if [c for c in cn if c not in ('meses_dec', 'meses_fec')] != cv:
        nota('nacional.campos (além de meses_*)', a)
    for rn, rv in zip(n['linhas'], v['linhas']):
        dn = {c: rn[i] for i, c in enumerate(cn) if c not in ('meses_dec', 'meses_fec')}
        dv = dict(zip(cv, rv))
        if dn != dv:
            nota('nacional.linha', (a, rv[:3]))
    if len(n['linhas']) != len(v['linhas']):
        nota('nacional.n_linhas', a)
for rel in ('indice.json',):
    n, v = json.loads((RAIZ / 'web/public/data/confiabilidade' / rel).read_text(encoding='utf-8')), velho(rel)
    for k in set(n) | set(v):
        if k in ('gerado_em', 'distribuidoras'):
            continue
        if n.get(k) != v.get(k):
            nota(f'indice.{k}', (v.get(k) if k == 'totais' else None, n.get(k) if k == 'totais' else None))
    for dn, dv in zip(n['distribuidoras'], v['distribuidoras']):
        for k in set(dn) | set(dv):
            if k == 'anual':
                for a in dn['anual']:
                    for kk in set(dn['anual'][a]) | set(dv['anual'].get(a, {})):
                        if dn['anual'][a].get(kk) != dv['anual'].get(a, {}).get(kk):
                            nota(f'indice.anual.{kk}', (dn['dist'], a))
            elif dn.get(k) != dv.get(k):
                nota(f'indice.dist.{k}', dn['dist'])
for k, c in sorted(mud.items()):
    print(f'{k}: {c}  ex: {exemplos[k]}')
