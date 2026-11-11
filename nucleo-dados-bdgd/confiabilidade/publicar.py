"""Monta o produto público do módulo (agregados compactos para o frontend) a partir dos derivados.

    python -m confiabilidade.publicar [--saida web/public/data/confiabilidade] [--dists 6600 26 ...]

Entradas (em <trabalho>/derivado): continuidade.parquet e limites.parquet (ANEEL), infra/DIST=<d>/ANO=<a>.json e geo/<d>.json (BDGD).
Saída: indice.json, distribuidoras/<DIST>.json, geo/<DIST>.json, nacional/<ANO>.json, manifesto.json.
O produto novo é montado numa pasta temporária, validado e só então troca de lugar com o anterior: uma carga que falha
não substitui o produto válido. Nenhum registro individual de consumidor sai daqui.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import contrato as K
from .metricas import IDS, TIPO, derivar, dicionario

RAIZ = Path(__file__).resolve().parents[1]
TRABALHO = Path(os.environ.get('CONF_TRABALHO', 'D:/NUCLEO_BDGD_2025/confiabilidade'))
SAIDA = RAIZ / 'web/public/data/confiabilidade'
INDEX_PORTAL = RAIZ / 'web/public/data/2025-12-31/index.json'
COMP = (('ip', 'IP'), ('ind', 'IND'), ('xp', 'XP'), ('xn', 'XN'))
EXPURGOS = ('INC', 'INE', 'INO', 'IPC', 'XNC', 'XPC')


def r2(v, n=2):
    return None if v is None or not K.finito(v) else round(v, n)


def carregar_aneel(trabalho):
    import duckdb
    d = Path(trabalho) / 'derivado'
    con = duckdb.connect()
    cont, lim = {}, {}
    cols = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{(d / 'continuidade.parquet').as_posix()}')").fetchall()]
    for row in con.execute(f"SELECT * FROM read_parquet('{(d / 'continuidade.parquet').as_posix()}') ORDER BY conj, ano, mes").fetchall():
        x = dict(zip(cols, row))
        e = cont.setdefault((x['conj'], x['ano']), dict(agente=x['agente'], cnpj=x['cnpj'], nome=x['nome'], meses={}))
        e['meses'][x['mes']] = x
    for c, a, ld, lf in con.execute(f"SELECT conj, ano, lim_dec, lim_fec FROM read_parquet('{(d / 'limites.parquet').as_posix()}')").fetchall():
        lim[(c, a)] = (ld, lf)
    return cont, lim


def serie_mensal(e, campo):
    return [e['meses'].get(m, {}).get(campo) for m in range(1, 13)]


def continuidade_ano(e, limite):
    """Bloco anual oficial de um conjunto: valores, limites, meses, componentes."""
    dec_m, fec_m, nuc_m = serie_mensal(e, 'DEC'), serie_mensal(e, 'FEC'), serie_mensal(e, 'NumCon')
    dec, n_dec, comp_dec = K.anual(dec_m)
    fec, n_fec, comp_fec = K.anual(fec_m)
    nucs = [v for v in nuc_m if K.finito(v) and v > 0]
    ld, lf = limite if limite else (None, None)
    bloco = dict(dec=r2(dec), fec=r2(fec), ld=r2(ld), lf=r2(lf), nuc=round(sum(nucs) / len(nucs)) if nucs else None,
                 nuc_dez=int(nuc_m[11]) if K.finito(nuc_m[11]) else None, meses_dec=n_dec, meses_fec=n_fec,
                 m=dict(dec=[r2(v) for v in dec_m], fec=[r2(v) for v in fec_m], nuc=[int(v) if K.finito(v) else None for v in nuc_m]))
    comp = {}
    for ind in ('DEC', 'FEC'):
        c = {k: r2(K.anual(serie_mensal(e, ind + s))[0]) for k, s in COMP}
        exp = [K.anual(serie_mensal(e, ind + s))[0] for s in EXPURGOS]
        c['exp'] = r2(math.fsum(v for v in exp if v is not None)) if any(v is not None for v in exp) else None
        comp[ind.lower()] = c
    bloco['comp'] = comp
    return bloco, dec_m, fec_m, nuc_m


def reconstrucao(dic_fic, dec_m, fec_m, nuc_m, dec, fec, uc_bdgd):
    """DEC/FEC reconstruídos dos DIC/FIC da BDGD. Denominador oficial (NumCon do mês) e, à parte, o da fotografia de 31/12."""
    if not dic_fic:
        return None
    def rec(somas, den):
        v = [K.razao(s, d) for s, d in zip(somas, den)]
        return K.anual(v)[0] if all(x is not None for x in v) else None
    rd, rf = rec(dic_fic['soma_dic'], nuc_m), rec(dic_fic['soma_fic'], nuc_m)
    bd = rec(dic_fic['soma_dic'], [uc_bdgd] * 12) if uc_bdgd else None
    bf = rec(dic_fic['soma_fic'], [uc_bdgd] * 12) if uc_bdgd else None
    ok_d, ok_f = K.reconciliado(rd, dec), K.reconciliado(rf, fec)
    estado = K.RECONSTRUIDO_VALIDADO if ok_d and ok_f else K.DERIVADO_EXPLORATORIO
    cob = K.razao(dic_fic['linhas_com_dic'], dic_fic['linhas'])
    return dict(dec=r2(rd), fec=r2(rf), dec_bdgd=r2(bd), fec_bdgd=r2(bf), dif_dec=r2(None if rd is None or dec is None else rd - dec),
                dif_fec=r2(None if rf is None or fec is None else rf - fec), cobertura=r2(cob, 4), estado=estado,
                denominador='NumCon mensal oficial (ANEEL); *_bdgd usa as unidades ativas em 31/12 da BDGD')


def publicar(trabalho=TRABALHO, saida=SAIDA, dists=None):
    trabalho, saida = Path(trabalho), Path(saida)
    portal = json.loads(INDEX_PORTAL.read_text(encoding='utf-8'))
    cad = {d['dist']: d for d in portal['distribuidoras']}
    grupos = {g['id']: g['nome'] for g in portal['grupos']}
    cont, lim = carregar_aneel(trabalho)
    prov_aneel = json.loads((trabalho / 'derivado/PROVENIENCIA_ANEEL.json').read_text(encoding='utf-8'))
    dists = sorted(dists or [int(p.name.split('=')[1]) for p in (trabalho / 'derivado/infra').glob('DIST=*')])
    infra, geo = {}, {}
    for d in dists:
        for a in K.ANOS:
            p = trabalho / f'derivado/infra/DIST={d}/ANO={a}.json'
            if p.exists():
                infra[(d, a)] = json.loads(p.read_text(encoding='utf-8'))
        g = trabalho / f'derivado/geo/{d}.json'
        if g.exists():
            geo[d] = json.loads(g.read_text(encoding='utf-8'))

    # ---------- a quem pertence cada (conjunto, ano): primeiro pela BDGD do próprio ano, depois pelo CNPJ do agente
    aud = dict(conflitos_de_conjunto=[], aneel_sem_distribuidora=Counter(), bdgd_fora_da_aneel=defaultdict(list), codigo_de_outro_agente=[])
    dono, peso = {}, {}
    por_cnpj_ano = Counter((e['cnpj'], a) for (c, a), e in cont.items())
    for (d, a), doc in infra.items():
        codigos = [int(c) for c in doc['conjuntos'] if int(c) > 0]
        casados = Counter(cont[(c, a)]['cnpj'] for c in codigos if (c, a) in cont)
        # um código isolado que coincide com o conjunto de outro agente não transfere o conjunto: o agente só é aceito para a
        # distribuidora quando casa pelo menos metade dos códigos (da BDGD do ano ou do agente na ANEEL, o que for menor)
        aceitos = {cnpj for cnpj, n in casados.items() if n >= 0.5 * min(len(codigos), por_cnpj_ano[(cnpj, a)])}
        for c, v in doc['conjuntos'].items():
            c = int(c)
            if (c, a) not in cont:
                if c > 0:
                    aud['bdgd_fora_da_aneel'][f'{d}/{a}'].append(c)
                continue
            if cont[(c, a)]['cnpj'] not in aceitos:
                aud['codigo_de_outro_agente'].append(dict(dist=d, ano=a, conj=c, agente=cont[(c, a)]['agente']))
                continue
            w = v['metricas'].get('uc_bt') or 0
            if (c, a) in dono and dono[(c, a)] != d:
                aud['conflitos_de_conjunto'].append(dict(conj=c, ano=a, dists=[dono[(c, a)], d]))
                if w <= peso[(c, a)]:
                    continue
            dono[(c, a)], peso[(c, a)] = d, w
    votos = defaultdict(Counter)
    for (c, a), d in dono.items():
        votos[cont[(c, a)]['cnpj']][d] += 1
    cnpj_dist = {cnpj: v.most_common(1)[0][0] for cnpj, v in votos.items()}
    for (c, a), e in cont.items():
        if (c, a) not in dono:
            d = cnpj_dist.get(e['cnpj'])
            if d is None:
                aud['aneel_sem_distribuidora'][e['agente']] += 1
            else:
                dono[(c, a)] = d
    por_dist = defaultdict(lambda: defaultdict(list))
    for (c, a), d in dono.items():
        por_dist[d][c].append(a)

    novo = saida.with_name(saida.name + '.novo')
    if novo.exists():
        shutil.rmtree(novo)
    for sub in ('distribuidoras', 'geo', 'nacional'):
        (novo / sub).mkdir(parents=True)
    nacional = {a: [] for a in K.ANOS}
    indice_dists, tot = [], Counter()

    for d in dists:
        if d not in por_dist:
            continue
        gd = geo.get(d, {}).get('conjuntos', {})
        conjuntos, resumo = [], {a: dict(meses=[[] for _ in range(12)], meses_fec=[[] for _ in range(12)], n=0, acima_dec=0, acima_fec=0, com_infra=0, nuc=0) for a in K.ANOS}
        ant = {}
        for c in sorted(por_dist[d]):
            g = gd.get(str(c), {})
            area = g.get('area_km2') if g.get('geometria') else None
            ent = dict(c=c, n=None, geo=bool(g.get('geometria')), area_km2=area, centro=g.get('centro'), a={}, al=None)
            for a in sorted(por_dist[d][c]):
                e = cont[(c, a)]
                ent['n'] = e['nome']
                bloco, dec_m, fec_m, nuc_m = continuidade_ano(e, lim.get((c, a)))
                bloco['estado'] = K.OBSERVADO_OFICIAL
                alertas = []
                if bloco['meses_dec'] < 12:
                    alertas.append('apuracao_parcial')
                if bloco['ld'] is None or bloco['lf'] is None:
                    alertas.append('sem_limite')
                doc = infra.get((d, a))
                bruto = doc['conjuntos'].get(str(c)) if doc else None
                if bruto is None:
                    bloco['infra'] = None
                    bloco['infra_motivo'] = ('distribuidora sem BDGD utilizável neste ano' if doc is None else 'conjunto sem registros na BDGD deste ano')
                    bloco['rec'] = None
                else:
                    met = derivar(bruto['metricas'], area)
                    bloco['infra'] = met
                    bloco['infra_estado'] = K.DERIVADO_EXPLORATORIO
                    bloco['rec'] = reconstrucao(bruto['dic_fic'], dec_m, fec_m, nuc_m, bloco['dec'], bloco['fec'], met['uc'])
                    if met['uc'] and bloco['nuc_dez'] and not (0.85 <= met['uc'] / bloco['nuc_dez'] <= 1.15):
                        alertas.append('consumidores_divergentes')
                    p = ant.get(c)
                    if p and p[0] == a - 1:
                        for k in ('uc', 'km_mt'):
                            if p[1].get(k) and met.get(k) and abs(met[k] / p[1][k] - 1) > 0.30:
                                alertas.append('variacao_cadastral_' + k)
                    ant[c] = (a, met)
                    resumo[a]['com_infra'] += 1
                    ent['al'] = dict(ano=a, lista=[{k: (round(v, 3) if isinstance(v, float) else v) for k, v in al.items()} for al in bruto['alimentadores'] if al.get('km_mt') or al.get('uc_bt')])
                bloco['alertas'] = alertas
                ent['a'][str(a)] = bloco
                rs = resumo[a]
                rs['n'] += 1
                rs['acima_dec'] += K.situacao_limite(bloco['dec'], bloco['ld']) == 'ACIMA'
                rs['acima_fec'] += K.situacao_limite(bloco['fec'], bloco['lf']) == 'ACIMA'
                rs['nuc'] += bloco['nuc'] or 0
                for i in range(12):
                    rs['meses'][i].append((dec_m[i], nuc_m[i])); rs['meses_fec'][i].append((fec_m[i], nuc_m[i]))
                inf = bloco['infra'] or {}
                nacional[a].append([d, c, e['nome'], bloco['dec'], bloco['fec'], bloco['ld'], bloco['lf'], bloco['nuc']] + [inf.get(i) for i in IDS])
                tot['conjunto_ano'] += 1; tot['conjunto_ano_com_infra'] += bool(bloco['infra'])
                tot['rec_validado'] += bool(bloco['rec'] and bloco['rec']['estado'] == K.RECONSTRUIDO_VALIDADO); tot['rec_calculado'] += bool(bloco['rec'] and bloco['rec']['dec'] is not None)
            conjuntos.append(ent)
        info = cad.get(d, {})
        anual = {}
        for a in K.ANOS:
            rs = resumo[a]
            if not rs['n']:
                continue
            dec, _, cd = K.agregado_anual(rs['meses']); fec, _, cf = K.agregado_anual(rs['meses_fec'])
            anual[str(a)] = dict(dec=r2(dec), fec=r2(fec), completo=cd and cf, nuc=rs['nuc'], conjuntos=rs['n'], acima_dec=rs['acima_dec'], acima_fec=rs['acima_fec'], com_infra=rs['com_infra'],
                                 estado=K.DERIVADO_EXPLORATORIO, regra='média dos conjuntos ponderada pelo NumCon de cada mês; soma dos 12 meses')
        agentes = Counter(cont[(c, a)]['agente'] for c in por_dist[d] for a in por_dist[d][c])
        fontes = {str(a): dict(item=infra[(d, a)]['meta']['fonte']['item'], sha256_gdb=infra[(d, a)]['meta']['fonte']['sha256_gdb'],
                               data_extracao=(infra[(d, a)]['meta']['fonte'].get('base_bdgd') or {}).get('DAT_EXT'), ausencias=infra[(d, a)]['auditoria']['ausencias'],
                               reconciliacao=infra[(d, a)]['auditoria']['totais_dist']) for a in K.ANOS if (d, a) in infra}
        doc = dict(contrato=K.VERSAO_CONTRATO, dist=d, nome=info.get('nome') or agentes.most_common(1)[0][0], agente_aneel=agentes.most_common(1)[0][0],
                   anual=anual, fontes_bdgd=fontes, geo=bool(geo.get(d, {}).get('features')), conjuntos=conjuntos)
        (novo / 'distribuidoras' / f'{d}.json').write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        if geo.get(d, {}).get('features'):
            gj = dict(type='FeatureCollection', meta=geo[d]['meta'], features=[f for f in geo[d]['features'] if f['properties']['c'] in por_dist[d]])
            (novo / 'geo' / f'{d}.json').write_text(json.dumps(gj, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        bb = [c['centro'] for c in conjuntos if c['centro']]
        indice_dists.append(dict(dist=d, nome=doc['nome'], sigla=(info.get('sigla') or '').replace('_', ' ') or doc['nome'], agente_aneel=doc['agente_aneel'],
                                 grupo=info.get('grupo') if info.get('grupo_status') == 'verificado' else None, grupo_nome=grupos.get(info.get('grupo')) if info.get('grupo_status') == 'verificado' else None,
                                 ufs=info.get('ufs') or [], bbox=(info.get('arat') or {}).get('bbox'), anual=anual, anos_infra=[a for a in K.ANOS if (d, a) in infra], geo=doc['geo'],
                                 conjuntos=len(conjuntos), conjuntos_com_geo=sum(c['geo'] for c in conjuntos)))
        tot['distribuidoras'] += 1; tot['conjuntos'] += len(conjuntos); tot['conjuntos_com_geo'] += sum(c['geo'] for c in conjuntos)

    campos = ['dist', 'c', 'n', 'dec', 'fec', 'ld', 'lf', 'nuc'] + IDS
    for a, rows in nacional.items():
        (novo / 'nacional' / f'{a}.json').write_text(json.dumps(dict(ano=a, campos=campos, linhas=rows), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    agora = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    indice = dict(
        contrato=K.VERSAO_CONTRATO, gerado_em=agora, anos=list(K.ANOS), demonstrativo=False,
        estados=dict(continuidade=K.OBSERVADO_OFICIAL, infraestrutura=K.DERIVADO_EXPLORATORIO, distribuidora=K.DERIVADO_EXPLORATORIO),
        fontes=dict(
            continuidade=dict(nome='ANEEL — Indicadores Coletivos de Continuidade (DEC e FEC)', url=prov_aneel['url'], licenca=prov_aneel['licenca'],
                              gerado_pela_aneel_em=prov_aneel['gerado_pela_aneel_em'], recursos={k: dict(sha256=v.get('sha256'), last_modified=v.get('last_modified')) for k, v in prov_aneel['recursos'].items()}),
            infraestrutura=dict(nome='ANEEL — BDGD (Base de Dados Geográfica da Distribuidora), competências 2022–2025', nota='agregados por conjunto calculados neste módulo; não homologados'),
            geometria=dict(nome='BDGD 2025 — camada CONJ (polígonos dos conjuntos)', tipo='POLIGONO_OFICIAL_SIMPLIFICADO', data_base='2025-12-31')),
        metricas=dicionario(), supressao_k=K.SUPRESSAO_K, tolerancia_reconstrucao=dict(relativa=K.TOL_RECONSTRUCAO, absoluta=K.TOL_RECONSTRUCAO_ABS),
        totais=dict(tot), distribuidoras=indice_dists,
        auditoria=dict(conflitos_de_conjunto=aud['conflitos_de_conjunto'][:50], aneel_sem_distribuidora=dict(aud['aneel_sem_distribuidora']),
                       bdgd_fora_da_aneel={k: v[:20] for k, v in aud['bdgd_fora_da_aneel'].items()}, codigo_de_outro_agente=aud['codigo_de_outro_agente'][:100]))
    (novo / 'indice.json').write_text(json.dumps(indice, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    validar(novo)
    arquivos = sorted(p for p in novo.rglob('*.json'))
    man = dict(contrato=K.VERSAO_CONTRATO, gerado_em=agora, arquivos=[dict(caminho=str(p.relative_to(novo)).replace('\\', '/'), bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in arquivos])
    (novo / 'manifesto.json').write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding='utf-8')
    velho = saida.with_name(saida.name + '.anterior')
    if velho.exists():
        shutil.rmtree(velho)
    if saida.exists():
        saida.rename(velho)
    novo.rename(saida)
    if velho.exists():
        shutil.rmtree(velho)
    print(json.dumps(dict(totais=dict(tot), bytes=sum(a['bytes'] for a in man['arquivos']), arquivos=len(man['arquivos']),
                          aneel_sem_distribuidora=dict(aud['aneel_sem_distribuidora']), conflitos=len(aud['conflitos_de_conjunto'])), ensure_ascii=False))
    return indice


def validar(pasta):
    """Falha (sem publicar) se o produto violar o contrato: NaN, contagem não inteira, valor negativo, chave duplicada, dado individual."""
    pasta = Path(pasta)
    ind = json.loads((pasta / 'indice.json').read_text(encoding='utf-8'))
    if ind.get('demonstrativo') is not False:
        raise SystemExit('produto público não pode ser demonstrativo')
    for p in (pasta / 'distribuidoras').glob('*.json'):
        txt = p.read_text(encoding='utf-8')
        if 'NaN' in txt or 'Infinity' in txt:
            raise SystemExit(f'{p.name}: NaN ou Infinity')
        d = json.loads(txt)
        vistos = set()
        for c in d['conjuntos']:
            if c['c'] in vistos:
                raise SystemExit(f"{p.name}: conjunto {c['c']} duplicado")
            vistos.add(c['c'])
            for a, b in c['a'].items():
                if int(a) not in K.ANOS:
                    raise SystemExit(f'{p.name}: ano {a} fora de 2022–2025')
                for k in ('dec', 'fec', 'ld', 'lf'):
                    if b[k] is not None and b[k] < 0:
                        raise SystemExit(f"{p.name}: {k} negativo em {c['c']}/{a}")
                for i, v in (b['infra'] or {}).items():
                    if v is None:
                        continue
                    if v < 0:
                        raise SystemExit(f"{p.name}: {i} negativo em {c['c']}/{a}")
                    if TIPO[i] == 'contagem' and not isinstance(v, int):
                        raise SystemExit(f"{p.name}: contagem não inteira {i}={v!r} em {c['c']}/{a}")
            for al in (c['al'] or {}).get('lista', []):
                for k in ('uc_bt', 'uc_mt'):
                    if al.get(k) is not None and 0 < al[k] < K.SUPRESSAO_K:
                        raise SystemExit(f"{p.name}: contagem pequena não suprimida em {c['c']}/{al['ctmt']}")
    return True


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--saida', default=str(SAIDA))
    ap.add_argument('--dists', type=int, nargs='*')
    a = ap.parse_args()
    publicar(saida=a.saida, dists=a.dists)
