"""Before / after record of the final audit: first national run (d4982e8, saved in nacional/_v1_d4982e8) against the revised run.

    python -m motor_v2.nacional.comparacao_v1_v2

Per series (both levels): anchor, choice (best baseline, best ML, experimental, fallback, projection model), robust scores, the
error of the model used for projection and the 2030 values of the three scenarios. Every change is attributed to its cause:
`elegibilidade_v2` (Level B series whose inputs changed, REVISAO_ELEGIBILIDADE_B.json), `ponte_celesc` (Level A Celesc and its
dependants, DEPENDENCIAS_CELESC.json), `politica_estoque` (stocks the common policy rejects) or `envelope_v2` (only the
conservative / aggressive values) or `sucessao_societaria` (Level B series whose inputs changed with the succession rule,
REVISAO_SUCESSAO_B.json). A moderate path that changed without one of the first three causes is reported as UNEXPLAINED."""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from . import ROOT_OUT
from .relatorio import write_csv
from ..runner import atomic, read

V1 = ROOT_OUT / '_v1_d4982e8'
OUT = ROOT_OUT / 'comparacao_v1_v2'
FIELDS = ('ano_ancora', 'melhor_baseline', 'score_melhor_baseline', 'melhor_ml', 'score_melhor_ml', 'melhor_modelo_experimental', 'modelo_fallback',
          'modelo_projecao', 'modelo_usado_na_projecao', 'status_projecao')


def rcsv(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if Path(p).exists() else []


def proj(path, keyf):
    out = defaultdict(dict)
    for r in rcsv(path):
        if r['ano'] == '2030':
            out[tuple(r[k] for k in keyf)][r['cenario']] = float(r['valor'])
    return out


def errors(path):
    return {(r['nivel'], r['DIST'], r['objeto']): r for r in rcsv(path)}


def same(a, b):
    if a == b:
        return True
    try:
        return abs(float(a) - float(b)) <= 1e-9 * max(1., abs(float(a)))
    except (TypeError, ValueError):
        return False


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    rb = read(ROOT_OUT / 'distribuidora' / 'REVISAO_ELEGIBILIDADE_B.json')
    aff_b = set(rb['afetadas'])
    rs = ROOT_OUT / 'distribuidora' / 'REVISAO_SUCESSAO_B.json'
    aff_s = set(read(rs)['afetadas']) if rs.exists() else set()
    dep = read(ROOT_OUT / 'comparativos' / 'DEPENDENCIAS_CELESC.json')
    alias = {'ucbt_quantidade': ('ucbt', 'quantidade'), 'trafo_dist_quantidade': ('trafo_dist', 'quantidade'), 'trafo_dist_potencia_kva': ('trafo_dist', 'potencia_kva'),
             'rede_mt_extensao_km': ('rede_mt', 'extensao_km'), 'rede_bt_extensao_km': ('rede_bt', 'extensao_km')}
    aff_a = {(str(d),) + alias[a] for a, x in dep.items() for d in x['alvos']}
    e1, e2 = errors(V1 / 'final' / 'ERROS_DO_MODELO_DE_PROJECAO.csv'), errors(ROOT_OUT / 'final' / 'ERROS_DO_MODELO_DE_PROJECAO.csv')
    rows = []
    for lvl, d1, d2, p1, p2, key in (
            ('A', V1 / 'projecao' / 'DECISOES_A.csv', ROOT_OUT / 'projecao' / 'DECISOES_A.csv', V1 / 'projecao' / 'PROJECOES_A_DISTRIBUIDORA.csv',
             ROOT_OUT / 'projecao' / 'PROJECOES_A_DISTRIBUIDORA.csv', ('DIST', 'ativo', 'metrica')),
            ('B', V1 / 'distribuidora' / 'DECISOES_B.csv', ROOT_OUT / 'distribuidora' / 'DECISOES_B.csv', V1 / 'distribuidora' / 'PROJECOES_B.csv',
             ROOT_OUT / 'distribuidora' / 'PROJECOES_B.csv', ('DIST', 'conceito', 'metrica'))):
        old = {tuple(r[k] for k in key): r for r in rcsv(d1)}; new = {tuple(r[k] for k in key): r for r in rcsv(d2)}
        po, pn = proj(p1, key), proj(p2, key)
        for k in sorted(set(old) | set(new), key=lambda x: (x[1], x[2], int(x[0]))):
            o, n = old.get(k, {}), new.get(k, {})
            ch = [f for f in FIELDS if not same(o.get(f), n.get(f))]
            vo, vn = po.get(k, {}), pn.get(k, {})
            mod_ch = not same(vo.get('Moderado'), vn.get('Moderado'))
            env_ch = any(not same(vo.get(s), vn.get(s)) for s in ('Conservador', 'Agressivo'))
            if not ch and not mod_ch and not env_ch:
                continue
            obj = k[1] + '/' + k[2]
            cause = ('elegibilidade_v2' if lvl == 'B' and f'{k[0]}/{k[1]}' in aff_b else
                     'sucessao_societaria' if lvl == 'B' and f'{k[0]}/{k[1]}' in aff_s else
                     'ponte_celesc' if lvl == 'A' and k in aff_a else
                     'politica_estoque' if (n.get('motivo_projecao') or '').find('politica de elegibilidade') >= 0 else
                     'envelope_v2' if not ch and not mod_ch else 'NAO_EXPLICADA')
            eo, en = e1.get((lvl, k[0], obj), {}), e2.get((lvl, k[0], obj), {})
            rows.append(dict(nivel=lvl, DIST=k[0], objeto=obj, causa=cause, campos_alterados=';'.join(ch), moderado_alterado=mod_ch, envelope_alterado=env_ch,
                             **{f'{f}_antes': o.get(f) for f in ('ano_ancora', 'melhor_ml', 'melhor_modelo_experimental', 'modelo_usado_na_projecao')},
                             **{f'{f}_depois': n.get(f) for f in ('ano_ancora', 'melhor_ml', 'melhor_modelo_experimental', 'modelo_usado_na_projecao')},
                             wape_modelo_projecao_antes=eo.get('wape'), wape_modelo_projecao_depois=en.get('wape'),
                             mae_modelo_projecao_antes=eo.get('mae'), mae_modelo_projecao_depois=en.get('mae'),
                             **{f'{s.lower()}_2030_antes': vo.get(s) for s in ('Conservador', 'Moderado', 'Agressivo')},
                             **{f'{s.lower()}_2030_depois': vn.get(s) for s in ('Conservador', 'Moderado', 'Agressivo')}))
    write_csv(OUT / 'ANTES_DEPOIS_SERIES.csv', rows)
    t1 = {(r['nivel'], r.get('ativo') or r.get('conceito'), r['metrica'], r['cenario']): r for r in rcsv(V1 / 'final' / 'TOTAIS_NACIONAIS_SERIES_COMPLETAS.csv') if r['ano'] == '2030'}
    t2 = {(r['nivel'], r.get('ativo') or r.get('conceito'), r['metrica'], r['cenario']): r for r in rcsv(ROOT_OUT / 'final' / 'TOTAIS_NACIONAIS_SERIES_COMPLETAS.csv') if r['ano'] == '2030'}
    tot = [dict(nivel=k[0], objeto=k[1] + '/' + k[2], cenario=k[3], total_2030_antes=float(t1[k]['valor']) if k in t1 else None,
                total_2030_depois=float(t2[k]['valor']) if k in t2 else None, dist_antes=t1.get(k, {}).get('dist_incluidas'), dist_depois=t2.get(k, {}).get('dist_incluidas'),
                status_total_depois=t2.get(k, {}).get('status_total'), cobertura_depois=t2.get(k, {}).get('cobertura_estoque_2025'))
           for k in sorted(set(t1) | set(t2))]
    write_csv(OUT / 'ANTES_DEPOIS_TOTAIS_2030.csv', tot)
    cel = [r for r in rows if r['DIST'] == '5697' and r['nivel'] == 'A']
    summary = dict(series_com_alteracao=len(rows), por_causa=Counter(r['causa'] for r in rows),
                   moderado_alterado_por_causa=Counter(r['causa'] for r in rows if r['moderado_alterado']),
                   nao_explicadas=[r for r in rows if r['causa'] == 'NAO_EXPLICADA'],
                   escolha_alterada=dict(Counter((r['nivel'], r['causa']) for r in rows if 'melhor_modelo_experimental' in r['campos_alterados'] or 'modelo_projecao' in r['campos_alterados'])),
                   celesc_nivel_A=cel)
    summary['escolha_alterada'] = {f'{a}/{b}': n for (a, b), n in summary['escolha_alterada'].items()}
    atomic(OUT / 'ANTES_DEPOIS_RESUMO.json', summary)
    return summary


if __name__ == '__main__':
    s = run()
    print(json.dumps({k: v for k, v in s.items() if k != 'celesc_nivel_A'}, ensure_ascii=False, indent=1, default=str)[:4000])
