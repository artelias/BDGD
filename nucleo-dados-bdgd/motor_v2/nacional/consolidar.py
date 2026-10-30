"""Final national deliverables (internal, experimental): inventory, model matrices, decisions, projections, unavailable cases,
provenance with hashes, execution resources and the national summary with proven counts.

    python -m motor_v2.nacional.consolidar [--repo-copy motor_v2/reports/nacional]

National totals only add series that are COMPLETE: projection generated, anchored on 2025, all 5 years x 3 scenarios present and
not flagged `nao_somar`; every excluded series is listed with its reason, so no total silently includes an incomplete result."""
import argparse
import csv
import json
import shutil
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from . import CONTRACT, LEVEL_A, ROOT_OUT, elegibilidade
from .comparativos import ALIAS, OUT as CMP
from .relatorio import write_csv
from ..report_lote import FUNCOES, rows_for
from ..runner import ROOT, atomic, digest, read

FINAL = ROOT_OUT / 'final'
ESCOPOS = {'individual': 'individual (so a propria DIST)', 'grupo_economico': 'grupo economico (controlador em 31/12/2025)',
           'comparaveis': 'DIST + 4 mais semelhantes em escala/perfil fisico (painel nacional, linhas de treino)'}


def rcsv(p):
    p = Path(p)
    return list(csv.DictReader(open(p, encoding='utf-8'))) if p.exists() else []


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def inventory():
    rows = []
    st = read(ROOT_OUT / 'extracao' / 'STATUS.json')
    for bid in sorted(st['lotes']):
        for r in rcsv(ROOT_OUT / 'extracao' / bid / 'INTEGRIDADE.csv'):
            rows.append(dict(nivel='A_territorial', **r))
    for r in csv.DictReader(open(CONTRACT, encoding='utf-8-sig')):
        ok, why, cav = elegibilidade.estoque(r)
        rows.append(dict(nivel='B_distribuidora', lote=None, DIST=r['dist'], ativo=r['conceitoId'], metrica=r['metrica'], ano=r['ano'],
                         status='utilizavel' if ok else 'indisponivel', motivo=why, ressalvas=';'.join(cav), intervalo_base=r['intervalo_base'],
                         item=r['publicacao_id'], valor=r['valor'], ruptura_contrato=r['ruptura_desde_ano_anterior']))
    return rows


FITS = Counter()
PROJ = ('distribuidora', 'territorial', 'distribuidora+territorial')
PROXY = set()     # (concept, DIST) whose 2025 weight in the universe is the last observed stock (no eligible 2025 stock)


def matrix_a():
    """Comparison rows IN FORCE per asset x DIST (a revision batch supersedes the first-run batch of its DIST). FITS counts the fits
    actually performed: first run (all batches) and revision separately."""
    from .revisao_a import vigentes
    st = read(CMP / 'STATUS.json')
    out = []
    force = {a: vigentes(st, a) for a in LEVEL_A}
    for bid, r in sorted(st['lotes'].items()):
        if r.get('estado') != 'completed':
            continue
        cfg = read(Path(r['output']).parents[1] / 'nacional_config.json')
        rows, _ = rows_for(r['output'], cfg.get('grupos', {}))
        tag = 'revisao' if r.get('revisao') else 'primeira_execucao'
        for sm in read(Path(r['output']) / 'summaries.json'):      # fits actually performed: outer folds + inner selection trials
            for c in sm['candidates']:
                if c['candidate'].split(':')[0] in ('persistencia', 'deriva', 'cagr'):
                    continue
                FITS[tag, 'outer'] += len(c.get('folds', [])); FITS[tag, 'inner'] += sum(len(f.get('trials', [])) for f in c.get('folds', []))
                if c.get('n_predictions'):
                    FITS[tag, 'candidatos'] += 1
        rows = [x for x in rows if force[r['ativo']].get(int(x['DIST']), (None,))[0] == bid]
        for x in rows:
            model, scope = x['candidato'].split(':', 1)
            x.update(lote=bid, escopo=ESCOPOS.get(scope, scope), funcao=FUNCOES.get(model, model))
            out.append(x)
    return out


def complete_series(proj, key_fields, decisions, dec_key):
    """Series with 5 years x 3 scenarios, anchor 2025, generated; -> (complete keys, excluded list)."""
    by = defaultdict(set)
    for r in proj:
        by[tuple(r[k] for k in key_fields)].add((int(r['ano']), r['cenario']))
    ok, excluded = set(), []
    for d in decisions:
        k = tuple(str(d[f]) for f in dec_key)
        if d.get('status_projecao') != 'gerada':
            excluded.append(dict(serie=k, motivo=d.get('motivo_projecao') or d.get('status_projecao'))); continue
        if str(d.get('ancora_2025')) not in ('True', 'true', '1'):
            excluded.append(dict(serie=k, motivo=f"ancora {d.get('ano_ancora')} != 2025 (horizonte real {d.get('horizonte_real')})")); continue
        got = by.get(tuple(str(x) for x in k), set())
        if len(got) != 15:
            excluded.append(dict(serie=k, motivo=f'{len(got)} de 15 valores (ano x cenario)')); continue
        ok.add(tuple(str(x) for x in k))
    return ok, excluded


def totals(proj, key_fields, ok, group_fields, universe=None):
    """Sums of complete series. `universe` {object: {DIST: observed eligible 2025 stock}} gives the coverage of each total: a total
    is COMPLETO only when every DIST with an eligible 2025 stock of that object is inside it; otherwise PARCIAL, with the share of the
    observed 2025 stock it covers (a partial sum is never presented as a national total)."""
    t = defaultdict(float); n = defaultdict(set)
    for r in proj:
        k = tuple(str(r[f]) for f in key_fields)
        if k not in ok:
            continue
        g = tuple(r[f] for f in group_fields) + (r['ano'], r['cenario'])
        t[g] += float(r['valor']); n[g].add(str(r['DIST']))
    out = []
    for g, v in sorted(t.items()):
        u = (universe or {}).get((g[0], g[1]), {})
        inc = n[g] & set(u); den = sum(u.values()) if u and None not in u.values() else 0
        missing = sorted(set(u) - n[g], key=lambda x: -(u[x] or 0))
        out.append(dict(zip(group_fields + ('ano', 'cenario'), g), valor=v if not float(v).is_integer() else int(v), dist_incluidas=len(n[g]),
                        dist_com_estoque_2025_elegivel=len(u), cobertura_estoque_2025=(sum(u[d] for d in inc) / den) if den else None,
                        status_total=('COMPLETO' if not missing else 'PARCIAL') if u else 'SEM_UNIVERSO',
                        dist_fora=';'.join(missing[:20]) + (f' (+{len(missing) - 20})' if len(missing) > 20 else ''),
                        dist_fora_sem_estoque_2025=';'.join(d for d in missing if any((c, d) in PROXY for c in (g[0], A_CONTRACT.get((g[0], g[1]), ''))))))
    return out


A_CONTRACT = {('ucbt', 'quantidade'): 'consumidores', ('trafo_dist', 'quantidade'): 'trafo_dist', ('trafo_dist', 'potencia_kva'): 'trafo_dist',
              ('rede_mt', 'extensao_km'): 'rede_mt', ('rede_bt', 'extensao_km'): 'rede_bt'}


def universes(inv):
    """Eligible 2025 stocks per (object, metric). Level B: contract cells eligible under the common policy. Level A: every DIST with an
    eligible 2025 contract cell of the corresponding concept, weighted by its extracted 2025 physical total; a DIST the extraction
    lacks enters with the contract value of the concept (for UCBT an approximation: the contract counts UCBT+UCMT+UCAT); for kVA the
    contract has no value, so a missing DIST makes the coverage share unknown (None) and the status PARCIAL."""
    ua, ub = defaultdict(dict), defaultdict(dict)
    for r in inv:
        if r['nivel'] == 'B_distribuidora' and str(r['ano']) == '2025' and r['status'] == 'utilizavel':
            ub[r['ativo'], r['metrica']][str(r['DIST'])] = num(r['valor']) or 0.
    # a DIST still operating in 2025 (not succeeded: its 2025 consumer cell is not SUCESSAO_SOCIETARIA) without an eligible 2025 stock
    # of the object, but with an eligible stock in an earlier competence, belongs to the 2025 universe with its last observed value
    # as weight (proxy, flagged): e.g. a cooperative whose 2025 publication is missing makes the national total PARCIAL.
    cc = elegibilidade.cells()
    gone = {d for (d, c, y), r in cc.items() if c == 'consumidores' and y == 2025 and r.get('tipo_lacuna') == 'SUCESSAO_SOCIETARIA'}
    for (d, c, y), r in cc.items():
        if y != 2025 or d in gone or elegibilidade.estoque(r)[0]:
            continue
        last = [float(cc[d, c, yy]['valor']) for yy in (2024, 2023, 2022) if (d, c, yy) in cc and elegibilidade.estoque(cc[d, c, yy])[0]]
        if last and last[0] > 0:
            ub[c, r['metrica']][str(d)] = last[0]; PROXY.add((c, str(d)))
    for (a, m), c in A_CONTRACT.items():
        for d, v in ub.get((c, 'quantidade' if m == 'potencia_kva' else m), {}).items():
            ua[a, m][d] = None if m == 'potencia_kva' else v
    for r in rcsv(ROOT_OUT / 'projecao' / 'DECISOES_A.csv'):
        if r.get('ano_ancora') == '2025' and num(r.get('total_ancora')) is not None:
            ua[r['ativo'], r['metrica']][str(r['DIST'])] = num(r['total_ancora'])
    return ua, ub


def resources():
    st = read(ROOT_OUT / 'extracao' / 'STATUS.json')
    ext = {}
    for bid, rec in st['lotes'].items():
        u = (rec.get('etapas') or {}).get('ucbt') or {}
        tim = {}
        if u.get('root') and (Path(u['root']) / 'timings.json').exists():
            tim = read(Path(u['root']) / 'timings.json')
        a = (rec.get('etapas') or {}).get('ativos') or {}
        am = read(Path(a['root']) / 'manifest.json') if a.get('root') else {}
        ext[bid] = dict(dists=rec['dists'], segundos_lote=rec.get('segundos'), segundos_ucbt=u.get('segundos'), segundos_ativos=a.get('segundos'),
                        ucbt_por_dist=tim, pico_rss_gib=max([v['peak_rss_gib'] for v in tim.values()] or [None]) if tim else None,
                        ativos_pico_rss_gib=(am.get('resources') or {}).get('peak_rss_gib'), ativos_reuso=am.get('stats'),
                        falhas_ucbt=u.get('falhas'), retry=(rec.get('etapas') or {}).get('ucbt_retry'), falhas_ativos=a.get('falhas'), estado=rec.get('estado'))
    cmp = read(CMP / 'STATUS.json')
    cmpres = {}
    for bid, r in cmp['lotes'].items():
        prog = read(Path(r['output']) / 'progress.json') if r.get('output') and (Path(r['output']) / 'progress.json').exists() else {}
        cmpres[bid] = dict(ativo=r['ativo'], dists=len(r['dists']), tentativas=r.get('tentativas'), inicio=r.get('inicio'), fim=r.get('fim'), estado=r.get('estado'),
                           experimentos_executados=prog.get('executed'), experimentos_reaproveitados=prog.get('reused'))
    return dict(extracao=ext, comparativos=dict(segundos=cmp.get('segundos'), lotes=cmpres),
                nivel_b=read(ROOT_OUT / 'distribuidora' / 'MANIFESTO_B.json').get('segundos'),
                projecao_a=read(ROOT_OUT / 'projecao' / 'MANIFESTO_A.json').get('segundos'))


def run(repo_copy=None):
    FINAL.mkdir(parents=True, exist_ok=True)
    inv = inventory(); write_csv(FINAL / 'INVENTARIO_NACIONAL.csv', inv)
    ma = matrix_a(); write_csv(FINAL / 'MATRIZ_MODELOS_A_TERRITORIAL.csv', ma)
    mb = rcsv(ROOT_OUT / 'distribuidora' / 'RESULTADOS_CANDIDATOS_B.csv')
    da = rcsv(ROOT_OUT / 'projecao' / 'DECISOES_A.csv'); db = rcsv(ROOT_OUT / 'distribuidora' / 'DECISOES_B.csv')
    pa = rcsv(ROOT_OUT / 'projecao' / 'PROJECOES_A_DISTRIBUIDORA.csv'); pb = rcsv(ROOT_OUT / 'distribuidora' / 'PROJECOES_B.csv')
    for f in ('DECISOES_A.csv', 'PROJECOES_A_DISTRIBUIDORA.csv', 'INDISPONIVEIS_A.csv'):
        shutil.copyfile(ROOT_OUT / 'projecao' / f, FINAL / f)
    for f in ('DECISOES_B.csv', 'PROJECOES_B.csv', 'INDISPONIVEIS_B.csv', 'RESULTADOS_CANDIDATOS_B.csv'):
        shutil.copyfile(ROOT_OUT / 'distribuidora' / f, FINAL / f)
    from .catalogo import run as catalog
    cat = catalog(); shutil.copyfile(ROOT_OUT / 'MATRIZ_ELEGIBILIDADE_CATALOGO.csv', FINAL / 'MATRIZ_ELEGIBILIDADE_CATALOGO.csv')
    # national totals of complete series only
    okA, exA = complete_series(pa, ('DIST', 'ativo', 'metrica'), da, ('DIST', 'ativo', 'metrica'))
    okB, exB = complete_series(pb, ('DIST', 'conceito', 'metrica'), db, ('DIST', 'conceito', 'metrica'))
    ua, ub = universes(inv)
    tA = totals(pa, ('DIST', 'ativo', 'metrica'), okA, ('ativo', 'metrica', 'unidade'), ua)
    tB = totals(pb, ('DIST', 'conceito', 'metrica'), okB, ('conceito', 'metrica', 'unidade'), ub)
    write_csv(FINAL / 'TOTAIS_NACIONAIS_SERIES_COMPLETAS.csv', [dict(nivel='A', **x) for x in tA] + [dict(nivel='B', **x) for x in tB])
    write_csv(FINAL / 'SERIES_EXCLUIDAS_DOS_TOTAIS.csv', [dict(nivel='A', serie='/'.join(map(str, x['serie'])), motivo=x['motivo']) for x in exA] +
              [dict(nivel='B', serie='/'.join(map(str, x['serie'])), motivo=x['motivo']) for x in exB])
    # unavailable cases
    unav = [dict(fonte='extracao', nivel='A', DIST=r['DIST'], objeto=r['ativo'], ano=r['ano'], status=r['status'], motivo=r['motivo'])
            for r in inv if r['nivel'] == 'A_territorial' and r['status'] != 'extraido']
    unav += [dict(fonte='projecao', nivel='A', DIST=r['DIST'], objeto=r['ativo'], ano=None, status='bloqueada', motivo=r['motivo']) for r in rcsv(FINAL / 'INDISPONIVEIS_A.csv')]
    unav += [dict(fonte='contrato', nivel='B', DIST=r['DIST'], objeto=r['conceito'], ano=None, status='bloqueada', motivo=r['motivo']) for r in rcsv(FINAL / 'INDISPONIVEIS_B.csv')]
    unav += [dict(fonte='catalogo', nivel='catalogo', DIST=None, objeto=f"{r['objetivo_id']}/{r['metrica']}", ano=None, status=r['status'], motivo=r['motivo_bloqueio'])
             for r in cat if r['status'] not in PROJ]
    unav += [dict(fonte='conversao_zip', nivel='A', DIST=x['dist'], objeto='publicacao_' + x['item_id'], ano=x['competencia_atribuida'], status=x.get('uso_no_motor'),
                  motivo=f"{x.get('classificacao')}: {x.get('motivo') or x.get('erro')}") for x in read('D:/NUCLEO_BDGD_2025/motor_v2/conversao_zips_contrato/CONVERSAO_ZIPS_CONTRATO.json')['itens']]
    qz = read(ROOT_OUT / 'quarentena.json')
    unav += [dict(fonte='quarentena', nivel='A', DIST=d, objeto='painel_territorial', ano=y, status='quarentena', motivo=why) for d, y, why in qz['quarentena']]
    write_csv(FINAL / 'CASOS_INDISPONIVEIS.csv', unav)
    # counts
    elig = {r['DIST'] for r in inv if r['nivel'] == 'A_territorial'}
    processed = {r['DIST'] for r in inv if r['nivel'] == 'A_territorial' and r['status'] == 'extraido'}
    ml_a = [r for r in ma if r['modelo'] not in ('persistencia', 'deriva', 'cagr') and int(r['previsoes_teste'] or 0) > 0 and r['rotulo'].startswith('retrospective')]
    ml_b = [r for r in mb if r['modelo'] not in ('persistencia', 'deriva', 'cagr') and int(r['previsoes'] or 0) > 0]
    trained = {str(r['DIST']) for r in ml_a} | {str(r['DIST']) for r in ml_b}
    genA = [r for r in da if r.get('status_projecao') == 'gerada']; genB = [r for r in db if r.get('status_projecao') == 'gerada']
    with_proj = {r['DIST'] for r in genA} | {r['DIST'] for r in genB}
    expA = [r for r in da if r.get('melhor_modelo_experimental')]; expB = [r for r in db if r.get('melhor_modelo_experimental')]
    def beats(rows, lvl, obj):
        return [dict(nivel=lvl, DIST=r['DIST'], objeto=r[obj] + '/' + r['metrica'], modelo=r['melhor_modelo_experimental'], melhor_baseline=r['melhor_baseline'],
                     ganho_vs_melhor_baseline=num(r['ganho_ml_vs_melhor_baseline']) if ':' in r['melhor_modelo_experimental'] else None)
                for r in rows if r.get('melhor_modelo_experimental')]
    winners = beats(da, 'A', 'ativo') + beats(db, 'B', 'conceito')
    write_csv(FINAL / 'MODELOS_EXPERIMENTAIS_ESCOLHIDOS.csv', winners)
    def err_summary(rows, obj, lvl):
        out = []
        for k in sorted({r[obj] + '/' + r['metrica'] for r in rows}):
            rr = [r for r in rows if r[obj] + '/' + r['metrica'] == k and r.get('status_projecao') == 'gerada']
            out.append(dict(nivel=lvl, objeto=k, series=len(rr), experimental_ml=sum(1 for r in rr if ':' in (r.get('melhor_modelo_experimental') or '')),
                            experimental_tendencia=sum(1 for r in rr if (r.get('melhor_modelo_experimental') or '') in ('deriva', 'cagr')),
                            fallback=sum(1 for r in rr if r.get('base_da_projecao') == 'modelo_fallback'),
                            persistencia_superior_empiricamente=sum(1 for r in rr if r.get('persistencia_superior_empiricamente') == 'True'),
                            mediana_ganho_melhor_ml_vs_melhor_baseline=statistics.median([num(r['ganho_ml_vs_melhor_baseline']) for r in rr if num(r['ganho_ml_vs_melhor_baseline']) is not None] or [float('nan')])))
        return out
    write_csv(FINAL / 'RESUMO_ESCOLHAS_POR_OBJETO.csv', err_summary(da, 'ativo', 'A') + err_summary(db, 'conceito', 'B'))
    # errors of the model used for projection (Level A: from the matrix; Level B: candidates file)
    used = []
    for r in genA:
        m = next((x for x in ma if str(x['DIST']) == str(r['DIST']) and x['ativo'] == r['ativo'] and x['metrica'] == r['metrica'] and x['rotulo'].startswith('retrospective')
                  and x['candidato'] == (r['modelo_usado_na_projecao'] + (':individual' if ':' not in r['modelo_usado_na_projecao'] else ''))), None)
        used.append(dict(nivel='A', DIST=r['DIST'], objeto=r['ativo'] + '/' + r['metrica'], modelo=r['modelo_usado_na_projecao'], base=r['base_da_projecao'],
                         mae=m and m['mae'], rmse=m and m['rmse'], wape=m and m['wape'], vies=m and m['vies'], mae_fisico=m and m['mae_fisico'],
                         cobertura_territorial_min=m and m['cobertura_territorial_min'], origens=m and m['origens_independentes']))
    for r in genB:
        m = next((x for x in mb if x['DIST'] == r['DIST'] and x['conceito'] == r['conceito'] and x['candidato'] == r['modelo_usado_na_projecao']), None)
        used.append(dict(nivel='B', DIST=r['DIST'], objeto=r['conceito'] + '/' + r['metrica'], modelo=r['modelo_usado_na_projecao'], base=r['base_da_projecao'],
                         mae=m and m['mae'], rmse=m and m['rmse'], wape=m and m['wape'], vies=m and m['vies'], mae_fisico=m and m.get('erro_fisico_mae'), cobertura_territorial_min=None,
                         origens=m and m['origens']))
    write_csv(FINAL / 'ERROS_DO_MODELO_DE_PROJECAO.csv', used)
    res = resources(); atomic(FINAL / 'RECURSOS_EXECUCAO.json', res)
    # physical / territorial coverage (Level A, anchor 2025)
    cov = []
    for asset in LEVEL_A:
        rr = [r for r in genA if f"{r['ativo']}_{r['metrica']}" == asset and r['ano_ancora'] == '2025']
        tot = sum(num(r['total_ancora']) or 0 for r in rr); coh = sum(num(r['coorte_ancora']) or 0 for r in rr)
        cov.append(dict(ativo=asset, dist_projetadas_ancora_2025=len(rr), total_fisico_2025=tot, coorte_territorial_2025=coh,
                        cobertura_territorial=coh / tot if tot else None,
                        dist_com_2025_extraido=len({r['DIST'] for r in inv if r['nivel'] == 'A_territorial' and r['ativo'] == asset and str(r['ano']) == '2025' and r['status'] == 'extraido'})))
    summary = dict(
        dist_no_contrato_nacional=len({r['dist'] for r in csv.DictReader(open(CONTRACT, encoding='utf-8-sig'))}),
        dist_no_inventario_local=len({r['dist'] for r in csv.DictReader(open('D:/NUCLEO_BDGD_2025/motor_v2/inventario_v2/INVENTARIO_PUBLICACOES_LOCAIS.csv', encoding='utf-8-sig'))}),
        dist_elegiveis_extracao=len(elig), dist_processadas_extracao=len(processed), dist_treinadas_ml=len(trained),
        dist_com_projecao=len(with_proj), dist_com_projecao_nivel_A=len({r['DIST'] for r in genA}), dist_com_projecao_nivel_B=len({r['DIST'] for r in genB}),
        combinacoes_catalogo=dict(objetivos_metricas_no_catalogo=len(cat), com_projecao=sum(1 for c in cat if c['status'] in PROJ),
                                  status=dict(Counter(c['status'] for c in cat)),
                                  bloqueados=sum(1 for c in cat if c['status'] == 'bloqueado'),
                                  series_dist_x_objeto_calculadas_A=len(genA), series_dist_x_objeto_calculadas_B=len(genB),
                                  series_dist_x_objeto_bloqueadas_A=len(da) - len(genA), series_dist_x_objeto_bloqueadas_B=len(db) - len(genB)),
        modelos=dict(candidatos_ml_avaliados_A=len(ml_a), ajustes_ml_externos_A=FITS['primeira_execucao', 'outer'], ajustes_ml_selecao_interna_A=FITS['primeira_execucao', 'inner'],
                     revisao_celesc_A=dict(candidatos_ml_medidos=FITS['revisao', 'candidatos'], ajustes_externos=FITS['revisao', 'outer'], ajustes_selecao_interna=FITS['revisao', 'inner']),
                     candidatos_ml_avaliados_B=len(ml_b), escolhas_experimentais_ml_A=sum(1 for r in expA if ':' in r['melhor_modelo_experimental']),
                     escolhas_experimentais_tendencia_A=sum(1 for r in expA if ':' not in r['melhor_modelo_experimental']),
                     escolhas_experimentais_ml_B=sum(1 for r in expB if ':' in r['melhor_modelo_experimental']),
                     escolhas_experimentais_tendencia_B=sum(1 for r in expB if ':' not in r['melhor_modelo_experimental']),
                     modelos_homologados=0),
        projecoes=dict(series_A=len(genA), series_B=len(genB), linhas_A_distribuidora=len(pa), linhas_B=len(pb),
                       series_completas_nos_totais_A=len(okA), series_completas_nos_totais_B=len(okB), excluidas_dos_totais_A=len(exA), excluidas_dos_totais_B=len(exB)),
        cobertura=cov, quarentena=qz['quarentena'], status='experimental_interno_nao_publicavel', modelo_homologado='nenhum (2 origens < 3)')
    summary['auditoria_final'] = dict(politica_elegibilidade=elegibilidade.VERSAO, pontes_experimentais=[x['id'] + ':' + x['status'] for x in
                                      (read(ROOT_OUT / 'pontes_experimentais.json')['pontes'] if (ROOT_OUT / 'pontes_experimentais.json').exists() else [])],
                                      triagem_cenarios='v2 (evidencia fase4; objeto x ano x porte; padrao temporal)',
                                      totais_parciais=sorted({f"{x['nivel']}/{x.get('ativo') or x.get('conceito')}/{x['metrica']}" for x in [dict(nivel='A', **t) for t in tA] + [dict(nivel='B', **t) for t in tB] if x['status_total'] != 'COMPLETO'}))
    atomic(FINAL / 'RESUMO_NACIONAL.json', summary)
    # audit artefacts of the final revision, hashed with the rest
    for src in [*(ROOT_OUT / 'reconciliacao_ab').glob('*'), *(ROOT_OUT / 'auditoria_cenarios').glob('*'), *(ROOT_OUT / 'potencia').glob('*'),
                *(ROOT_OUT / 'comparacao_v1_v2').glob('*'), ROOT_OUT / 'pontes_experimentais.json', ROOT_OUT / 'distribuidora' / 'REVISAO_ELEGIBILIDADE_B.json', ROOT_OUT / 'distribuidora' / 'REVISAO_SUCESSAO_B.json',
                ROOT_OUT / 'testes' / 'MANIFESTO_TESTES.json',
                ROOT_OUT / 'comparativos' / 'DEPENDENCIAS_CELESC.json', ROOT_OUT / 'testes' / 'MATRIZ_TESTES.csv']:
        if src.is_file():
            shutil.copyfile(src, FINAL / src.name)
    # provenance
    git = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    files = {p.name: digest(p) for p in sorted(FINAL.glob('*')) if p.is_file() and p.name != 'MANIFESTO_PROVENIENCIA.json'}
    internal = {str(p): digest(p) for p in [ROOT_OUT / 'projecao' / 'PROJECOES_A_TERRITORIAL_INTERNO.parquet', ROOT_OUT / 'projecao' / 'PROJECOES_A_DISTRIBUIDORA_INTERNO.parquet',
                                            ROOT_OUT / 'distribuidora' / 'PROJECOES_B_INTERNO.parquet', ROOT_OUT / 'painel' / 'MANIFESTO_PAINEL.json'] if p.exists()}
    atomic(FINAL / 'MANIFESTO_PROVENIENCIA.json', dict(commit_base=git, contrato=str(CONTRACT), contrato_sha256=digest(CONTRACT),
                                                       inventario_sha256=digest('D:/NUCLEO_BDGD_2025/motor_v2/inventario_v2/INVENTARIO_PUBLICACOES_LOCAIS.csv'),
                                                       conversao_zips_sha256=digest('D:/NUCLEO_BDGD_2025/motor_v2/conversao_zips_contrato/CONVERSAO_ZIPS_CONTRATO.json'),
                                                       quarentena=qz, arquivos_finais=files, internos=internal,
                                                       codigo_nacional={p.name: digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
                                                       codigo_motor_v2={p.name: digest(p) for p in sorted(Path(__file__).parents[1].glob('*.py'))},
                                                       regra='apenas publicacoes ordinarias do contrato; nenhuma extraordinaria; nada gravado em web/ ou output-*'))
    if repo_copy:
        dst = ROOT / repo_copy; dst.mkdir(parents=True, exist_ok=True)
        import gzip
        for p in FINAL.glob('*'):
            if not p.is_file() or p.stat().st_size >= 25 * 2**20:
                continue
            if p.stat().st_size > 4 * 2**20:      # large tables go gzipped (mtime 0: byte-reproducible)
                with open(p, 'rb') as fi, gzip.GzipFile(dst / (p.name + '.gz'), 'wb', mtime=0) as fo:
                    shutil.copyfileobj(fi, fo)
                (dst / p.name).unlink(missing_ok=True)
            else:
                shutil.copyfile(p, dst / p.name)
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--repo-copy')
    print(json.dumps(run(ap.parse_args().repo_copy), ensure_ascii=False, indent=1, default=str))
