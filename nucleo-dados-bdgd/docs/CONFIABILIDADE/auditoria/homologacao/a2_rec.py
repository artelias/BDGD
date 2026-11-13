"""combinações < 80%: diagnóstico da causa (só leitura)."""
import json, sys, glob, csv, statistics as st
from collections import defaultdict, Counter
from pathlib import Path
PROD = Path(sys.argv[1]); CSV = Path(sys.argv[2])
rows = list(csv.DictReader(open(CSV, encoding='utf-8')))
baixo = [r for r in rows if float(r['pct_reconciliados']) < 0.8]
print('linhas CSV', len(rows), 'abaixo de 80%:', len(baixo), 'distribuidoras', len({r['dist'] for r in baixo}))
print('por ano', Counter(r['ano'] for r in baixo)); print('por indicador', Counter(r['indicador'] for r in baixo))
print('conjuntos nas combinações baixas: soma', sum(int(r['conjuntos']) for r in baixo), '| com 1 conjunto:', sum(r['conjuntos']=='1' for r in baixo), '| <=3:', sum(int(r['conjuntos'])<=3 for r in baixo))
alvo = {(int(r['dist']), int(r['ano']), r['indicador'].lower()) for r in baixo}
tol = lambda rec, of: abs(rec - of) <= 0.05 or abs(rec - of) <= 0.05 * abs(of)
cat = Counter(); cob = []; nuc_rel = []; por_comb = defaultdict(Counter); exemplos = []
for f in sorted(glob.glob(str(PROD/'distribuidoras/*.json'))):
    d = json.loads(Path(f).read_text(encoding='utf-8'))
    for c in d['conjuntos']:
        for a, b in c['a'].items():
            for ind in ('dec','fec'):
                k = (d['dist'], int(a), ind)
                if k not in alvo: continue
                r = b.get('rec') or {}
                of, rec = b[ind], r.get(ind)
                if of is None or rec is None:
                    cat['sem_reconstrucao'] += 1; por_comb[k]['sem_reconstrucao'] += 1; continue
                if tol(rec, of): cat['ok'] += 1; por_comb[k]['ok'] += 1; continue
                comp = (b.get('comp') or {}).get(ind) or {}
                ext = (comp.get('xp') or 0) + (comp.get('xn') or 0); exp_ = comp.get('exp') or 0
                cob.append(r.get('cobertura'))
                nuc = b.get('nuc'); uc = (b.get('infra') or {}).get('uc')
                if nuc and uc: nuc_rel.append(uc / nuc)
                if tol(rec, of + exp_) and exp_ > 0.05: lab = 'rec≈oficial+expurgos'
                elif tol(rec, of + ext) and ext > 0.05: lab = 'rec≈oficial+externas'
                elif tol(rec, of + ext + exp_) and ext + exp_ > 0.05: lab = 'rec≈oficial+ext+exp'
                elif rec == 0 and of > 0: lab = 'DIC/FIC zerado na BDGD'
                elif (r.get('cobertura') or 1) < 0.9: lab = 'cobertura DIC < 90%'
                elif rec < of: lab = 'reconstruído menor (outro)'
                else: lab = 'reconstruído maior (outro)'
                cat[lab] += 1; por_comb[k][lab] += 1
                if len(exemplos) < 8 and lab.endswith('(outro)'): exemplos.append((k, c['c'], of, rec, r.get('dif_'+ind), r.get('cobertura'), ext, exp_, nuc, uc))
print('\nconjunto-indicadores nas combinações abaixo de 80%, por diagnóstico:'); [print(f'  {k}: {v}') for k, v in cat.most_common()]
cobv = [x for x in cob if x is not None]
print('cobertura DIC dos divergentes: mediana', st.median(cobv) if cobv else None, '| <0.9:', sum(x < 0.9 for x in cobv))
print('UC BDGD / NumCon dos divergentes: mediana', round(st.median(nuc_rel),3) if nuc_rel else None, '| fora de 0.95–1.05:', sum(not 0.95 <= x <= 1.05 for x in nuc_rel), 'de', len(nuc_rel))
dom = Counter(max(cnt, key=lambda x: cnt[x] if x != 'ok' else -1) for cnt in por_comb.values())
print('\ncausa dominante por combinação:', dom.most_common())
for e in exemplos: print('  ex', e)

# padrão por combinação: razão reconstruído/oficial
print('\npor combinação: n, ok, mediana rec/of, IQR, rótulo')
tipos = Counter(); linhas = []
for f in sorted(glob.glob(str(PROD/'distribuidoras/*.json'))):
    d = json.loads(Path(f).read_text(encoding='utf-8'))
    for c in d['conjuntos']:
        for a, b in c['a'].items():
            for ind in ('dec','fec'):
                k = (d['dist'], int(a), ind)
                if k in alvo and b[ind] and (b.get('rec') or {}).get(ind) is not None:
                    linhas.append((k, d['nome'], b['rec'][ind] / b[ind], tol(b['rec'][ind], b[ind])))
g = defaultdict(list); nomes = {}
for k, nm, rz, ok in linhas: g[k].append((rz, ok)); nomes[k] = nm
for k in sorted(g):
    rz = sorted(x for x, _ in g[k]); med = st.median(rz)
    q1, q3 = (rz[len(rz)//4], rz[(3*len(rz))//4]) if len(rz) >= 4 else (rz[0], rz[-1])
    lab = 'sistemático (todos do mesmo lado)' if all(x < 0.95 for x in rz) or all(x > 1.05 for x in rz) else ('disperso' if len(rz) > 1 else 'conjunto único')
    if len(rz) == 1: lab = 'conjunto único'
    tipos[lab] += 1
    print(f'  {k} {nomes[k][:22]:22s} n={len(rz):3d} ok={sum(o for _, o in g[k]):3d} med={med:.3f} iqr=[{q1:.3f};{q3:.3f}] {lab}')
print('tipos:', tipos.most_common())
