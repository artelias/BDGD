"""Definitive coverage matrix DIST x objective x metric (x year x scenario) of the national contract universe, read only.

    python -m motor_v2.nacional.cobertura                 # matrix, summary, audit of the blocked combinations
    python -m motor_v2.nacional.cobertura --verificar-na  # also re-reads the local Parquets behind every ATIVO_NAO_APLICAVEL cell

Universe: the 114 DIST of the national contract x the 29 objective/metric pairs of the catalogue, plus UCBT (the BT part of
consumers, Level A) as a hierarchical sub-series. Every combination gets exactly one state and a specific reason:

  PROJETADA_EXPERIMENTAL          15 values (5 years x 3 scenarios), 2025 anchor, model chosen by the retrospective comparison
  PROJETADA_BASELINE              15 values, 2025 anchor, fallback baseline (persistence / drift / CAGR) by policy
  SEM_ANCORA_2025                 15 values projected from an earlier anchor; the anchor year and the real horizon are recorded,
                                  and the series never enters a total that requires a 2025 anchor
  SUCESSAO_SOCIETARIA             the code has no independent perimeter (incorporated, renamed or reported by another DIST);
                                  an internal projection of an incorporated company is kept only as an audit record
  NAO_APLICAVEL                   the asset does not exist in the DIST (the local entity has zero records) or the metric has no
                                  physical meaning (TUC 575 has no power field)
  SEM_SEMANTICA_FISICA_HOMOGENEA  the field mixes physical quantities (regulators: own and throughput ratings)
  DADO_NAO_HOMOLOGADO             a record exists but fails the contract or the physical-consistency gate
  SEM_PUBLICACAO                  no publication of the DIST in any competence
  HISTORICO_INSUFICIENTE          usable stocks exist, but fewer than the release rule of the metric requires (power: 2)
  BLOQUEIO_TECNICO                a limitation of the code (must be zero: every one is a defect to fix)

Audit classes of the series without projection (the request of 2026-11-01): A no publication; B succession/perimeter;
C physically not applicable; D stock absent or not homologated; E partial history with a usable anchor (projected, SEM_ANCORA_2025);
F blocked by the code (fixable); G other proven impediment.

Additivity: national totals add only additive stocks (counts, km, kVA of one rating) of series anchored in 2025; any total that
misses a DIST of the universe or a part of the 2025 stock is PARCIAL. Regulator power has no national total."""
import csv
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from . import CONTRACT, GROUPS, ROOT_OUT, elegibilidade
from .relatorio import write_csv
from ..runner import atomic, digest

OUT = ROOT_OUT / 'cobertura'
YEARS = (2026, 2027, 2028, 2029, 2030)
CENARIOS = ('Conservador', 'Moderado', 'Agressivo')
ESTADOS = ('PROJETADA_EXPERIMENTAL', 'PROJETADA_BASELINE', 'SEM_ANCORA_2025', 'HISTORICO_INSUFICIENTE', 'DADO_NAO_HOMOLOGADO',
           'SEM_PUBLICACAO', 'SUCESSAO_SOCIETARIA', 'NAO_APLICAVEL', 'SEM_SEMANTICA_FISICA_HOMOGENEA', 'BLOQUEIO_PLAUSIBILIDADE', 'BLOQUEIO_TECNICO')
PROJETADOS = ('PROJETADA_EXPERIMENTAL', 'PROJETADA_BASELINE', 'SEM_ANCORA_2025')
# state at 6327239 (the delivery reviewed on 2026-10-31), for the "gaps resolved" report
ANTERIOR = dict(series_B_geradas=2412, series_B_bloqueadas=438, combinacoes_com_previsao=26, combinacoes_catalogo=29,
                series_A=512, dist_com_projecao=103)
NA_ENTIDADE = {'rede_at': ('SSDAT', None), 'circuitos_at': ('CTAT', None), 'barramentos': ('BAR', None), 'subestacoes': ('SUB', None),
               'reguladores': ('EQRE', None), 'bancos_capacitores': ('EQCR', '125'), 'reatores': ('EQCR', '330')}
# DIST whose own code stops being an independent perimeter in the window, with the official event (eventos_sucessao.csv)
INCORPORADAS = {6611: ('EPB_EBO_2023', 6600, '2023-04-30'), 6612: ('EMR_ENF_2022', 6585, '2022-11-30')}
POTENCIA = {('trafo_forca', 'potencia_kva'): ('trafo_forca_kva',), ('reguladores', 'potencia_kva'): ('reguladores_kva_propria', 'reguladores_kva_passante')}
NAO_ADITIVAS = {('reguladores', 'potencia_kva')}
A_ROWS = {('trafo_dist', 'potencia_kva'): ('trafo_dist', 'potencia_kva'), ('ucbt', 'quantidade'): ('ucbt', 'quantidade')}


def _csv(p):
    if not Path(p).exists():
        return []
    op = gzip.open if str(p).endswith('.gz') else open
    with op(p, 'rt', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def _num(v):
    try:
        return float(v) if v not in ('', None) else None
    except ValueError:
        return None


def catalogo():
    rows = _csv(ROOT_OUT / 'MATRIZ_ELEGIBILIDADE_CATALOGO.csv')
    cat = [dict(objetivo=r['objetivo_id'], nome=r['nome'], familia=r['familia'], metrica=r['metrica'], unidade=r['unidade'],
                natureza=r['natureza'], no_catalogo=True, motivo_catalogo=r['motivo_bloqueio']) for r in rows]
    cat.append(dict(objetivo='ucbt', nome='Unidades consumidoras BT (UCBT)', familia='Clientes', metrica='quantidade', unidade='itens',
                    natureza='discrete_count', no_catalogo=False, motivo_catalogo='sub-serie hierarquica de Consumidores (nivel A)'))
    return cat


def sucessoes(contract):
    """{DIST: reason} of the codes without an independent perimeter in 2022-2025 (contract SUCESSAO_SOCIETARIA or incorporation)."""
    out = {}
    for (d, c, y), r in contract.items():
        if r['tipo_lacuna'] == 'SUCESSAO_SOCIETARIA' and d not in out:
            out[d] = r['motivo_nd'] or 'SUCESSAO_SOCIETARIA no contrato'
    for d, (ev, dest, dt) in INCORPORADAS.items():
        out[d] = f'incorporada a DIST {dest} em {dt} (evento {ev}); ultima publicacao propria 2022; perimetro reportado pela sucessora'
    return out


def assinatura(contract, d, c):
    """Contract states of one (DIST, concept) in 2022-2025 -> (state counter, lacunas, any observed value)."""
    est, lac, obs = Counter(), Counter(), False
    for y in range(2022, 2026):
        r = contract.get((d, c, y))
        if r is None:
            est['sem_celula'] += 1; continue
        est[r['estado']] += 1
        if r['tipo_lacuna']:
            lac[r['tipo_lacuna']] += 1
        obs |= r['estado'] in ('observado', 'zero_verificado') and r['valor'] != ''
    return est, lac, obs


def classe_bloqueio(contract, d, c, suc, na_verif):
    """State and audit class (A..G) of a combination without any usable stock, from the contract cells and the local check."""
    est, lac, obs = assinatura(contract, d, c)
    anos = {y: (contract.get((d, c, y)) or {}) for y in range(2022, 2026)}
    detalhe = '; '.join(f"{y}: {r.get('estado', 'sem_celula')}{':' + r['tipo_lacuna'] if r.get('tipo_lacuna') else ''}" for y, r in anos.items())
    if d in suc:
        return 'SUCESSAO_SOCIETARIA', 'B', suc[d]
    if lac.get('ATIVO_NAO_APLICAVEL'):
        v = na_verif.get((d, c))
        prova = f' (verificado: {v} registro(s) na entidade local)' if v is not None else ''
        if v:      # the entity has records although the contract says not applicable: a defect of the chain, never hidden
            return 'BLOQUEIO_TECNICO', 'F', 'contrato diz ATIVO_NAO_APLICAVEL mas a entidade local tem registros' + prova + ' | ' + detalhe
        return 'NAO_APLICAVEL', 'C', 'entidade sem registros na publicacao da DIST' + prova + ' | ' + detalhe
    if lac and set(lac) <= {'PUBLICACAO_NAO_LOCALIZADA'}:
        return 'SEM_PUBLICACAO', 'A', detalhe
    if est.get('nao_homologado') or lac.get('ENTIDADE_VAZIA_NA_ORIGEM') or lac.get('INDICADOR_AUSENTE_OUTRA_RAZAO'):
        return 'DADO_NAO_HOMOLOGADO', 'D', detalhe
    if obs:
        return 'DADO_NAO_HOMOLOGADO', 'D', 'valor observado sem estoque elegivel (data-base ou soma) | ' + detalhe
    return 'BLOQUEIO_TECNICO', 'G', detalhe


def estado_potencia(contract, d, o, m, suc, na_verif, serP, conv):
    """State of a power metric without a released series: the contract concept first (not applicable, absent, not homologated),
    then the reasons recorded by potencia_b for every year (release rule, convention, physical gate)."""
    est, lac, obs = assinatura(contract, d, o)
    if not obs:
        return classe_bloqueio(contract, d, o, suc, na_verif)
    motivos = {c: json.loads(serP[d, c]['motivos']) for c in POTENCIA[o, m] if (d, c) in serP}
    texto = '; '.join(f'{c}: ' + ', '.join(f'{y} {w}' for y, w in mm.items()) for c, mm in motivos.items() if mm)
    if o == 'reguladores':
        if not motivos and not conv[d]:
            return 'DADO_NAO_HOMOLOGADO', 'D', 'sem auditoria de convencao dos reguladores para a DIST'
        if 'SEM_SEMANTICA' in texto or (conv[d] and (conv[d].get('MISTA') or (conv[d].get('PROPRIA') and conv[d].get('PASSANTE')))):
            return 'SEM_SEMANTICA_FISICA_HOMOGENEA', 'G', f'convencao de POT_NOM por ano: {dict(conv[d])}; ' + texto
    if 'HISTORICO_INSUFICIENTE' in texto:
        return 'HISTORICO_INSUFICIENTE', 'D', texto
    return 'DADO_NAO_HOMOLOGADO', 'D', texto or 'sem auditoria de potencia para a DIST'


def verificar_na(contract):
    """{(DIST, concept): records in the local entity over the NA years} for every ATIVO_NAO_APLICAVEL cell (reads the Parquets)."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    inv = {}
    for r in _csv(Path('D:/NUCLEO_BDGD_2025/motor_v2/inventario_v2/INVENTARIO_PUBLICACOES_LOCAIS.csv')):
        if r['tipo'] == 'selecionada_no_contrato':
            inv[int(r['dist']), int(r['competencia'])] = r['item_id']
    out, linhas = defaultdict(int), []
    for (d, c, y), r in sorted(contract.items()):
        if r['tipo_lacuna'] != 'ATIVO_NAO_APLICAVEL' or c not in NA_ENTIDADE:
            continue
        ent, tip = NA_ENTIDADE[c]
        p = (Path(f'D:/NUCLEO_BDGD_2025/staging_parquet/DIST={d}/DATA_BASE=2025-12-31/entidade={ent}/part-0.parquet') if y == 2025 else
             Path(f'D:/NUCLEO_BDGD_2022_2024/parquet/{y}/{d}/{inv.get((d, y), "-")}/{ent}.parquet'))
        n = None
        if p.exists():
            if tip is None:
                n = pq.ParquetFile(p).metadata.num_rows
            else:
                t = pq.read_table(p)
                col = next((k for k in ('TIP_UNID', 'TIP_EQ', 'TUC') if k in t.column_names), None)
                n = int(pc.sum(pc.equal(pc.cast(t[col], 'string'), tip)).as_py() or 0) if col else t.num_rows
        out[d, c] += n or 0
        linhas.append(dict(DIST=d, conceito=c, ano=y, entidade=ent, tipo=tip or '', arquivo_local=p.exists(), registros=n))
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / 'VERIFICACAO_NAO_APLICAVEL.csv', linhas)
    return dict(out)


def ler_na():
    out = defaultdict(int)
    for r in _csv(OUT / 'VERIFICACAO_NAO_APLICAVEL.csv'):
        out[int(r['DIST']), r['conceito']] += int(r['registros'] or 0)
    return dict(out)


def _status_gerada(dec, base_key='base_da_projecao'):
    anchor = int(float(dec['ano_ancora']))
    if anchor != 2025:
        return 'SEM_ANCORA_2025', 'E', f"ancora {anchor}; horizonte real {dec.get('horizonte_real') or f'{2026 - anchor}..{2030 - anchor} anos'}; fora dos totais com ancora 2025"
    if dec.get(base_key) == 'melhor_modelo_experimental':
        return 'PROJETADA_EXPERIMENTAL', '', dec.get('motivo_experimental') or ''
    return 'PROJETADA_BASELINE', '', dec.get('motivo_fallback') or dec.get('motivo_experimental') or ''


def erros():
    out = {}
    for r in _csv(ROOT_OUT / 'final' / 'ERROS_DO_MODELO_DE_PROJECAO.csv'):
        out[r['nivel'], int(r['DIST']), r['objeto']] = r
    return out


def montar(verificar=False):
    contract = elegibilidade.cells(CONTRACT)
    empresas = {d: r['empresa'] for (d, c, y), r in contract.items()}
    dists = sorted(empresas)
    grupos = {int(x): g['grupo_id'] for g in json.loads(Path(GROUPS).read_text(encoding='utf-8'))['grupos'] for x in g['dists']}
    suc = sucessoes(contract)
    na_verif = verificar_na(contract) if verificar else ler_na()
    err = erros()
    decB = {(int(r['DIST']), r['conceito']): r for r in _csv(ROOT_OUT / 'distribuidora' / 'DECISOES_B.csv')}
    projB = defaultdict(dict)
    for r in _csv(ROOT_OUT / 'distribuidora' / 'PROJECOES_B.csv'):
        projB[int(r['DIST']), r['conceito']][int(r['ano']), r['cenario']] = _num(r['valor'])
    decA = {(int(r['DIST']), r['ativo'], r['metrica']): r for r in _csv(ROOT_OUT / 'projecao' / 'DECISOES_A.csv')}
    projA = defaultdict(dict)
    for r in _csv(ROOT_OUT / 'projecao' / 'PROJECOES_A_DISTRIBUIDORA.csv'):
        projA[int(r['DIST']), r['ativo'], r['metrica']][int(r['ano']), r['cenario']] = _num(r['valor'])
    indA = defaultdict(list)
    for r in _csv(ROOT_OUT / 'final' / 'CASOS_INDISPONIVEIS.csv'):
        if r['nivel'] == 'A':
            indA[int(r['DIST']), r['objeto']].append(f"{r['ano']}: {r['status']} ({r['motivo']})")
    rec = defaultdict(dict); recmeta = {}
    for r in _csv(ROOT_OUT / 'hierarquia_consumidores' / 'PROJECOES_CONSUMIDORES_RECONCILIADAS.csv'):
        rec[int(r['DIST'])][int(r['ano']), r['cenario']] = _num(r['consumidores_reconciliado'])
        recmeta[int(r['DIST'])] = r
    decP = {(int(r['DIST']), r['conceito']): r for r in _csv(ROOT_OUT / 'distribuidora_potencia' / 'DECISOES_B.csv')}
    projP = defaultdict(dict)
    for r in _csv(ROOT_OUT / 'distribuidora_potencia' / 'PROJECOES_B.csv'):
        projP[int(r['DIST']), r['conceito']][int(r['ano']), r['cenario']] = _num(r['valor'])
    serP = {(int(r['DIST']), r['conceito']): r for r in _csv(ROOT_OUT / 'distribuidora_potencia' / 'SERIES_POTENCIA_B.csv')}
    conv = defaultdict(Counter)
    for r in _csv(ROOT_OUT / 'potencia' / 'REGULADORES_CONVENCAO_POR_DIST_ANO.csv'):
        conv[int(r['DIST'])][r['convencao']] += 1

    linhas, valores = [], []
    for d in dists:
        for cat in catalogo():
            o, m = cat['objetivo'], cat['metrica']
            row = dict(DIST=d, empresa=empresas[d], grupo=grupos.get(d, ''), familia=cat['familia'], objetivo=o, nome=cat['nome'], metrica=m,
                       unidade=cat['unidade'], natureza=cat['natureza'], no_catalogo=cat['no_catalogo'], fonte='', estado='', classe_auditoria='',
                       motivo='', ano_ancora='', horizonte_real='', valor_ancora='', modelo_projecao='', base_da_projecao='', melhor_baseline='',
                       melhor_ml='', origens='', mae='', rmse='', wape='', vies='', cenarios_degenerados='', variante='', entra_em_totais=False)
            vals = {}
            if d in suc:
                row.update(estado='SUCESSAO_SOCIETARIA', classe_auditoria='B', motivo=suc[d], fonte='contrato')
                if d in INCORPORADAS and (d, o) in decB and decB[d, o]['status_projecao'] == 'gerada':
                    row['motivo'] += '; projecao interna ancorada em 2022 mantida so como registro de auditoria (nao e empresa ativa)'
            elif (o, m) in A_ROWS:
                a = decA.get((d,) + A_ROWS[o, m])
                if a and a['status_projecao'] == 'gerada':
                    st, cl, why = _status_gerada(a)
                    e = err.get(('A', d, f'{A_ROWS[o, m][0]}/{m}'), {})
                    row.update(fonte='nivel_A', estado=st, classe_auditoria=cl, motivo=why, ano_ancora=a['ano_ancora'], horizonte_real=a['horizonte_real'],
                               valor_ancora=a['total_ancora'], modelo_projecao=a['modelo_usado_na_projecao'] or a['modelo_projecao'],
                               base_da_projecao=a['base_da_projecao'], melhor_baseline=a['melhor_baseline'], melhor_ml=a['melhor_ml'], origens=a['origens'],
                               mae=e.get('mae', ''), rmse=e.get('rmse', ''), wape=e.get('wape', ''), vies=e.get('vies', ''), cenarios_degenerados=a['cenario_cenarios_degenerados'])
                    vals = projA[(d,) + A_ROWS[o, m]]
                else:
                    key = 'ucbt_quantidade' if o == 'ucbt' else 'trafo_dist_potencia_kva'
                    why = '; '.join(indA.get((d, key), [])) or (a or {}).get('motivo_projecao') or 'sem serie no nivel A'
                    bad = 'extraido_sem_valor_valido' in why
                    row.update(fonte='nivel_A', estado='DADO_NAO_HOMOLOGADO' if bad or a else 'SEM_PUBLICACAO' if 'indisponivel' in why else 'DADO_NAO_HOMOLOGADO',
                               classe_auditoria='D' if bad or a else 'A', motivo=why)
            elif (o, m) == ('trafo_medida', 'potencia_kva'):
                row.update(fonte='semantica', estado='NAO_APLICAVEL', classe_auditoria='C',
                           motivo='TUC 575 (transformador de medida, EQTRM) nao tem campo de potencia: relacao e classe de exatidao, nao potencia de transformacao')
            elif (o, m) in POTENCIA:
                cands = [(c, decP.get((d, c))) for c in POTENCIA[o, m]]
                ger = [(c, x) for c, x in cands if x and x['status_projecao'] == 'gerada']
                if ger:
                    c, x = ger[0]
                    st, cl, why = _status_gerada(x)
                    row.update(fonte='nivel_B_potencia', estado=st, classe_auditoria=cl, motivo=why, ano_ancora=x['ano_ancora'], horizonte_real=x['horizonte_real'],
                               valor_ancora=x['valor_ancora'], modelo_projecao=x['modelo_usado_na_projecao'], base_da_projecao=x['base_da_projecao'],
                               melhor_baseline=x['melhor_baseline'], melhor_ml=x['melhor_ml'], origens=x['origens'], cenarios_degenerados=x['cenario_cenarios_degenerados'],
                               variante=c, unidade=x['unidade'])
                    vals = projP[d, c]
                else:
                    st, cl, why = estado_potencia(contract, d, o, m, suc, na_verif, serP, conv)
                    row.update(fonte='nivel_B_potencia', estado=st, classe_auditoria=cl, motivo=why)
            else:
                x = decB.get((d, o))
                if x and x['status_projecao'] == 'gerada':
                    st, cl, why = _status_gerada(x)
                    e = err.get(('B', d, f'{o}/{m}'), {})
                    row.update(fonte='nivel_B', estado=st, classe_auditoria=cl, motivo=why, ano_ancora=x['ano_ancora'], horizonte_real=x['horizonte_real'],
                               valor_ancora=x['valor_ancora'], modelo_projecao=x['modelo_usado_na_projecao'], base_da_projecao=x['base_da_projecao'],
                               melhor_baseline=x['melhor_baseline'], melhor_ml=x['melhor_ml'], origens=x['origens'], mae=e.get('mae', ''), rmse=e.get('rmse', ''),
                               wape=e.get('wape', ''), vies=e.get('vies', ''), cenarios_degenerados=x['cenario_cenarios_degenerados'])
                    vals = projB[d, o]
                    if o == 'consumidores' and d in rec:
                        rm = recmeta[d]
                        ua = decA.get((d, 'ucbt', 'quantidade'))
                        if ua and ua['status_projecao'] == 'gerada':      # the reconciled path is driven by the UCBT model (Level A)
                            st, cl, why = _status_gerada(ua)
                            row.update(estado=st, classe_auditoria=cl, motivo=why, base_da_projecao=ua['base_da_projecao'], melhor_baseline=ua['melhor_baseline'],
                                       melhor_ml=ua['melhor_ml'], origens=ua['origens'], cenarios_degenerados=ua['cenario_cenarios_degenerados'])
                        row.update(fonte='consumidores_reconciliado', ano_ancora=rm['ancora'],
                                   modelo_projecao=f"UCBT nivel A ({rm['modelo_A']}) + complemento ({rm['metodo_complemento']})",
                                   motivo=(row['motivo'] + '; ' if row['motivo'] else '') + f"fonte canonica interna; B independente ({x['modelo_usado_na_projecao']}) so como auditoria")
                        vals = rec[d]
                        if int(rm['ancora']) != 2025:
                            row.update(estado='SEM_ANCORA_2025', classe_auditoria='E')
                elif x:
                    st, cl, why = classe_bloqueio(contract, d, o, suc, na_verif)
                    row.update(fonte='nivel_B', estado=st, classe_auditoria=cl, motivo=why)
                else:
                    row.update(fonte='nivel_B', estado='BLOQUEIO_TECNICO', classe_auditoria='G', motivo='combinacao sem decisao no nivel B')
            if row['estado'] in PROJETADOS and len(vals) != 15:
                row.update(estado='BLOQUEIO_TECNICO', classe_auditoria='F', motivo=f'{len(vals)} valores em vez de 15 | ' + row['motivo'])
            row['entra_em_totais'] = row['estado'] in ('PROJETADA_EXPERIMENTAL', 'PROJETADA_BASELINE') and (o, m) not in NAO_ADITIVAS
            linhas.append(row)
            for y in YEARS:
                for s in CENARIOS:
                    valores.append(dict(DIST=d, objetivo=o, metrica=m, ano=y, cenario=s, estado=row['estado'],
                                        valor=vals.get((y, s), '') if row['estado'] in PROJETADOS else ''))
    return linhas, valores, contract, suc


def estoque_2025(contract):
    """{(objective, metric): (sum of eligible 2025 stocks, DIST with one)} from the contract (the 25 concepts)."""
    out = defaultdict(lambda: [0.0, 0])
    for (d, c, y), r in contract.items():
        if y == 2025 and elegibilidade.estoque(r)[0]:
            out[c, r['metrica']][0] += float(r['valor']); out[c, r['metrica']][1] += 1
    return out


def completa(r):
    """A series counts as having the 15 values only when its state projects and no scenario was blocked by the plausibility gate."""
    return r['estado'] in PROJETADOS and not r.get('cenarios_bloqueados')


def resumo(linhas, valores, contract):
    est = Counter(r['estado'] for r in linhas)
    cat = Counter(r['estado'] for r in linhas if r['no_catalogo'])
    st25 = estoque_2025(contract)
    por = []
    for (o, m), rr in sorted(groupby(linhas).items()):
        e = Counter(r['estado'] for r in rr)
        proj = [r for r in rr if r['entra_em_totais']]
        anc = sum(_num(r['valor_ancora']) or 0 for r in proj)
        tot, nd = st25.get((o, m), (None, None))
        # the three scenario totals sum the SAME set of series: those with the three scenarios publishable (a total per scenario over
        # different sets would break Conservador <= Moderado <= Agressivo). Moderate over every projected series is reported apart.
        comum = {r['DIST'] for r in proj if completa(r)}
        todas = {r['DIST'] for r in proj}
        v30 = [v for v in valores if v['objetivo'] == o and v['metrica'] == m and v['ano'] == 2030 and v['estado'] in ('PROJETADA_EXPERIMENTAL', 'PROJETADA_BASELINE') and v['valor'] != '']
        tot2030 = {s: sum(_num(v['valor']) or 0 for v in v30 if v['cenario'] == s and v['DIST'] in comum) for s in CENARIOS} if proj else {}
        n_tot = {s: len(comum) for s in CENARIOS} if proj else {}
        tot_mod_todas = sum(_num(v['valor']) or 0 for v in v30 if v['cenario'] == 'Moderado' and v['DIST'] in todas) if proj else None
        cobert = anc / tot if tot else None
        por.append(dict(objetivo=o, metrica=m, unidade=rr[0]['unidade'], dist_universo=len(rr), **{k: e.get(k, 0) for k in ESTADOS},
                        series_com_15_valores=sum(1 for r in rr if completa(r)), series_com_cenario_bloqueado=sum(1 for r in rr if r['estado'] in PROJETADOS and r.get('cenarios_bloqueados')),
                        series_com_cenario_corrigido=sum(1 for r in rr if r.get('cenarios_corrigidos')), dist_ancora_2025_nos_totais=len(proj),
                        n_series_total_conservador=n_tot.get('Conservador'), n_series_total_moderado=n_tot.get('Moderado'), n_series_total_agressivo=n_tot.get('Agressivo'),
                        estoque_2025_contrato=tot, dist_estoque_2025_contrato=nd, ancora_2025_projetada=anc if proj else None,
                        cobertura_estoque_2025=cobert,
                        total_2030_conservador=tot2030.get('Conservador'), total_2030_moderado=tot2030.get('Moderado'), total_2030_agressivo=tot2030.get('Agressivo'), n_series_total_comum=len(comum) if proj else None,
                        total_2030_moderado_todas_as_series=tot_mod_todas, n_series_moderado_todas=len(todas) if proj else None,
                        rotulo_total='' if not proj or (o, m) in NAO_ADITIVAS else ('COMPLETO' if cobert is not None and cobert >= 0.9999 and e.get('SEM_ANCORA_2025', 0) == 0 and all(r.get('cenarios_bloqueados', '') == '' for r in proj) and e.get('BLOQUEIO_PLAUSIBILIDADE', 0) == 0 else 'PARCIAL'),
                        observacao='potencia propria e passante nao somaveis: sem total nacional' if (o, m) in NAO_ADITIVAS else
                        (f"{e.get('SEM_ANCORA_2025', 0)} DIST com ancora anterior a 2025 e {len(rr) - len(proj) - sum(e.get(k, 0) for k in ('SEM_ANCORA_2025', 'NAO_APLICAVEL', 'SUCESSAO_SOCIETARIA'))} "
                         f"DIST aplicaveis sem projecao ficam fora do total; {e.get('NAO_APLICAVEL', 0)} nao aplicaveis e {e.get('SUCESSAO_SOCIETARIA', 0)} codigos de sucessao nao tem perimetro proprio" if proj else '')))
    univ = len(linhas)
    com15 = sum(1 for r in linhas if completa(r))
    parciais = sum(1 for r in linhas if r['estado'] in PROJETADOS and r.get('cenarios_bloqueados'))
    ncen = Counter()
    for r in linhas:
        for k in ('cenarios_bloqueados', 'cenarios_corrigidos'):
            ncen[k] += len(r[k].split('|')) if r.get(k) else 0
    return dict(
        universo=dict(dist=len({r['DIST'] for r in linhas}), objetivos_metricas_catalogo=len({(r['objetivo'], r['metrica']) for r in linhas if r['no_catalogo']}),
                      subseries_hierarquicas=len({(r['objetivo'], r['metrica']) for r in linhas if not r['no_catalogo']}), combinacoes=univ,
                      celulas_ano_cenario=len(valores)),
        cobertura_processamento=dict(combinacoes_com_estado=sum(est.values()), sem_estado=univ - sum(est.values()), fracao=sum(est.values()) / univ),
        cobertura_previsao=dict(com_15_valores=com15, com_moderado_e_extremo_bloqueado=parciais, series_bloqueadas_inteiras=est.get('BLOQUEIO_PLAUSIBILIDADE', 0),
                                cenarios_extremos_bloqueados=ncen['cenarios_bloqueados'], cenarios_extremos_corrigidos=ncen['cenarios_corrigidos'],
                                ancora_2025=est.get('PROJETADA_EXPERIMENTAL', 0) + est.get('PROJETADA_BASELINE', 0),
                                ancora_anterior=est.get('SEM_ANCORA_2025', 0), fracao=com15 / univ,
                                fracao_aplicavel=com15 / max(1, univ - est.get('NAO_APLICAVEL', 0) - est.get('SUCESSAO_SOCIETARIA', 0))),
        estados=dict(est), estados_catalogo=dict(cat),
        combinacoes_objetivo_metrica_com_previsao=sum(1 for p in por if p['series_com_15_valores'] > 0 and p['objetivo'] != 'ucbt'),
        dist_com_alguma_projecao=len({r['DIST'] for r in linhas if r['estado'] in PROJETADOS}),
        plausibilidade=PLAUS_RESUMO,
        bloqueio_tecnico=est.get('BLOQUEIO_TECNICO', 0),
        classes_auditoria=dict(Counter(r['classe_auditoria'] for r in linhas if r['classe_auditoria'])),
        por_objetivo=por, anterior_6327239=ANTERIOR)


def groupby(linhas):
    g = defaultdict(list)
    for r in linhas:
        g[r['objetivo'], r['metrica']].append(r)
    return g


def lacunas(linhas):
    """Combinations whose state changed against 6327239 (B blocked 438, A/B projections, no power series at DIST level)."""
    antes_b = {(int(r['DIST']), r['conceito']): r['status_projecao'] for r in _csv(Path(__file__).resolve().parents[1] / 'reports/nacional/DECISOES_B.csv')}
    out = []
    for r in linhas:
        d, o, m = r['DIST'], r['objetivo'], r['metrica']
        if (o, m) in POTENCIA or (o, m) == ('trafo_dist', 'potencia_kva'):
            antes = 'sem serie por DIST (nivel B)' if (o, m) != ('trafo_dist', 'potencia_kva') else 'so territorial (nivel A)'
        elif (o, m) == ('trafo_medida', 'potencia_kva'):
            antes = 'nao_aplicavel'
        elif o == 'ucbt':
            antes = 'nivel A'
        else:
            antes = antes_b.get((d, o), '')
        if antes in ('', 'gerada') and r['estado'] in PROJETADOS and not (d in INCORPORADAS):
            continue
        out.append(dict(DIST=d, empresa=r['empresa'], objetivo=o, metrica=m, antes_6327239=antes, depois=r['estado'], classe=r['classe_auditoria'],
                        resolvido=r['estado'] in PROJETADOS and antes not in ('gerada',), motivo=r['motivo']))
    return out


PLAUS_RESUMO = {}


def run(verificar=False):
    global PLAUS_RESUMO
    from . import plausibilidade as PL
    linhas, valores, contract, suc = montar(verificar)
    from . import exportar_web as EW
    hist, hpot, _ = EW.historicos(contract)
    for v in valores:
        v.setdefault('estado_cenario', '')
    for r in linhas:
        for k in ('cenarios_bloqueados', 'cenarios_corrigidos', 'plaus_classe', 'plaus_severidade', 'plaus_motivo', 'plaus_json', 'plaus_alerta_intensidade'):
            r.setdefault(k, '')
    linhas, valores, audit, brutos, PLAUS_RESUMO = PL.avaliar(linhas, valores, lambda r: sorted(hpot.get((r['DIST'], r['variante']), [])) if r['variante'] else sorted(hist.get((r['DIST'], r['objetivo'], r['metrica']), [])))
    PL.gravar(audit, brutos, PLAUS_RESUMO)
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / 'MATRIZ_COBERTURA_SERIES.csv', [{k: v for k, v in r.items() if k != 'plaus_json'} for r in linhas])
    with gzip.GzipFile(OUT / 'MATRIZ_COBERTURA_COMPLETA.csv.gz', 'wb', mtime=0) as gz:
        import io
        buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=list(valores[0]), lineterminator='\n'); w.writeheader(); w.writerows(valores)
        gz.write(buf.getvalue().encode('utf-8'))
    blq = [r for r in linhas if r['estado'] not in PROJETADOS]
    write_csv(OUT / 'AUDITORIA_COMBINACOES_SEM_PREVISAO.csv', [{k: r[k] for k in ('DIST', 'empresa', 'objetivo', 'metrica', 'estado', 'classe_auditoria', 'motivo')} for r in blq])
    write_csv(OUT / 'LACUNAS_VERSUS_6327239.csv', lacunas(linhas))
    res = resumo(linhas, valores, contract)
    res['fontes'] = {p: digest(ROOT_OUT / p) for p in ('distribuidora/DECISOES_B.csv', 'distribuidora/PROJECOES_B.csv', 'projecao/DECISOES_A.csv',
                                                       'projecao/PROJECOES_A_DISTRIBUIDORA.csv', 'hierarquia_consumidores/PROJECOES_CONSUMIDORES_RECONCILIADAS.csv',
                                                       'distribuidora_potencia/DECISOES_B.csv', 'distribuidora_potencia/PROJECOES_B.csv',
                                                       'potencia/REGULADORES_CONVENCAO_POR_DIST_ANO.csv') if (ROOT_OUT / p).exists()}
    res['contrato_sha256'] = digest(CONTRACT)
    write_csv(OUT / 'COBERTURA_POR_OBJETIVO.csv', res['por_objetivo'])
    atomic(OUT / 'RESUMO_COBERTURA.json', res)
    return res


if __name__ == '__main__':
    r = run('--verificar-na' in sys.argv)
    print(json.dumps({k: v for k, v in r.items() if k not in ('por_objetivo', 'fontes')}, ensure_ascii=False, indent=1))
