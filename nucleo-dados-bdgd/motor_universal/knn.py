"""Análogos entre DIST, ancorados em estoque confiável. Sem imputar alvos ou dependências novas."""
from collections import Counter,defaultdict
from math import log1p,sqrt,isfinite
from statistics import fmean,pstdev
from .contracts import validate_panel,usable,iso,contiguous_tail
from .engine import metrics
from .models import CANDIDATES,predict
from .registry import validate_registry

def _feature(row,name,spec,cutoff):
    f=row['features'].get(name)
    if (not spec.get('comparabilidade_validada') or not spec.get('evidencia_comparabilidade') or
        not f or not f.get('fonte') or not f.get('versao') or f.get('unidade')!=spec['unidade'] or
        f.get('status_comparabilidade','VALIDADA')!='VALIDADA' or f.get('ruptura',False)):
        raise ValueError('FEATURE_SEM_PROVENIENCIA_OU_COMPARABILIDADE:'+name)
    if f['disponivel_em']>cutoff or f['referencia']>row['competencia']:
        raise ValueError('FEATURE_POSTERIOR_AO_CORTE_OU_ANCORA:'+name)
    value=f.get('valor')
    if not isinstance(value,(int,float)) or isinstance(value,bool) or not isfinite(value):raise ValueError('FEATURE_AUSENTE:'+name)
    return value

def _available(row,cutoff,positive=True):
    return usable(row) and row['valor_alvo'] is not None and (row['valor_alvo']>0 if positive else row['valor_alvo']>=0) and row['disponivel_em'] is not None and row['disponivel_em']<=cutoff

def anchored_knn(panel,registry,*,dist,objective,metric,anchor_year,target_year,cutoff,k=3):
    validate_panel(panel,registry);iso(cutoff)
    if not isinstance(k,int) or isinstance(k,bool) or k<1 or target_year<=anchor_year or cutoff<f'{anchor_year}-12-31':raise ValueError('CORTE_HORIZONTE_K_INVALIDO')
    definitions={n:s for n,s in panel.get('feature_definitions',{}).items() if s.get('origem') in {'interna','externa'} and s['tipo']=='numerica' and (not s.get('objetivos_aplicaveis') or objective in s['objetivos_aplicaveis'])}
    if not any(s.get('origem')=='externa' for s in definitions.values()):raise ValueError('PAINEL_EXTERNO_COMPARAVEL_NAO_ENTREGUE')
    names=sorted(definitions)
    source=[r for r in panel['rows'] if r['objetivo_id']==objective and r['metrica']==metric]
    spec=validate_registry(registry)[objective,metric]
    if spec.get('requer_comparabilidade',True):
        source=[r for r in source if r.get('comparabilidade_validada') and r.get('evidencia_comparabilidade')]
        if not any(str(r['DIST'])==str(dist) and r['ano']==anchor_year for r in source):raise ValueError('METRICA_SEM_COMPARABILIDADE_VALIDADA')
    if any(r['territorio']['nivel']!='dist' for r in source):raise ValueError('KNN_REQUER_DIST_ANO_SEM_RATEIO_MUNICIPAL')
    anchors=[r for r in source if str(r['DIST'])==str(dist) and r['ano']==anchor_year]
    if len(anchors)!=1 or not _available(anchors[0],cutoff):raise ValueError('ANCORA_CONFIAVEL_DISPONIVEL_AUSENTE')
    anchor=anchors[0]
    latest=max(r['ano'] for r in source if str(r['DIST'])==str(dist) and _available(r,cutoff))
    if anchor_year!=latest:raise ValueError('ANCORA_NAO_E_A_ULTIMA_CONFIAVEL_NO_CORTE')
    source=[r for r in source if all(r[x]==anchor[x] for x in ['unidade','perimetro_id','regra_versao'])]
    vector=lambda r:[log1p(r['valor_alvo'])]+[_feature(r,n,definitions[n],cutoff) for n in names]
    query=vector(anchor);latest_break={}
    for row in source:
        if row['ruptura'] and row['ano']<=iso(cutoff).year and row['disponivel_em'] and row['disponivel_em']<=cutoff:
            latest_break[str(row['DIST'])]=max(row['ano'],latest_break.get(str(row['DIST']),0))
    index={(str(r['DIST']),r['ano']):r for r in source};donors={};excluded=Counter()
    for a in sorted(source,key=lambda r:r['ano']):
        d=str(a['DIST']);b=index.get((d,a['ano']+1))
        if d==str(dist):continue  # todas as respostas da DIST avaliada ficam fora do treino
        if a['ano']<latest_break.get(d,0) or not b or not _available(a,cutoff) or not _available(b,cutoff,positive=False) or b['ruptura'] or b['ano']>iso(cutoff).year:
            excluded['TRANSICAO_NAO_DISPONIVEL_OU_NAO_COMPARAVEL']+=1;continue
        if any(a[x]!=anchor[x] or b[x]!=anchor[x] for x in ['unidade','perimetro_id','regra_versao']):
            excluded['UNIDADE_PERIMETRO_REGRA_INCOMPATIVEL']+=1;continue
        try:x=vector(a)
        except ValueError as e:excluded[str(e)]+=1;continue
        donors[d]={'DIST':d,'ano_ancora':a['ano'],'ano_resposta':b['ano'],'x':x,'fator_anual':b['valor_alvo']/a['valor_alvo'],
                   'proveniencia':{'ancora':{'fonte':a['fonte'],'competencia':a['competencia'],'disponivel_em':a['disponivel_em'],'evidencia':a.get('proveniencia',{})},'resposta':{'fonte':b['fonte'],'competencia':b['competencia'],'disponivel_em':b['disponivel_em'],'evidencia':b.get('proveniencia',{})}},'features_ancora':{n:a['features'][n] for n in names}}
    # Uma transição (a última elegível) por DIST: anos empilhados não multiplicam vizinhos.
    train=list(donors.values())
    if len(train)<k:raise ValueError('DISTRIBUIDORAS_COMPARAVEIS_INSUFICIENTES')
    means=[fmean(t['x'][j] for t in train) for j in range(len(query))]
    scales=[pstdev(t['x'][j] for t in train) or 1.0 for j in range(len(query))]
    for t in train:t['distancia']=sqrt(sum(((t['x'][j]-query[j])/scales[j])**2 for j in range(len(query))))
    nearest=sorted(train,key=lambda t:(t['distancia'],t['DIST']))[:k]
    factors=[t['fator_anual'] for t in nearest];h=target_year-anchor_year;stock=anchor['valor_alvo']
    value=stock*fmean(factors)**h;interval=[stock*min(factors)**h,stock*max(factors)**h]
    if not all(isfinite(x) and x>=0 for x in [value,*interval]):raise ValueError('ESTIMATIVA_FISICAMENTE_INVALIDA')
    return {'modelo':'knn_analogos_ancorado','DIST':str(dist),'objetivo_id':objective,'metrica':metric,'ano_ancora':anchor_year,'ano_alvo':target_year,
            'ancora':stock,'estimativa':value,'intervalo_indicativo':interval,'tipo_intervalo':'DISPERSAO_MIN_MAX_DOS_ANALOGOS_NAO_CALIBRADA',
            'vizinhos':[{q:v for q,v in t.items() if q!='x'} for t in nearest],'k':k,'variaveis':['log1p_estoque_ancora',*names],
            'media_treino':means,'escala_treino':scales,'exclusoes':dict(excluded),'previsao_validada':False,
            'natureza_alvo':'estoque_fisico','necessidade_expansao':None,'sintetico':panel['sintetico']}

def backtest_knn(panel,registry,*,objective,metric,ks=(1,3,5)):
    validate_panel(panel,registry)
    if not panel.get('feature_definitions'):return {'status':'bloqueado','motivo':'PAINEL_EXTERNO_COMPARAVEL_NAO_ENTREGUE','estimativa':None,'metricas_knn':metrics([]),'previsao_validada':False,'sintetico':panel['sintetico']}
    source=[r for r in panel['rows'] if r['objetivo_id']==objective and r['metrica']==metric]
    years=sorted({r['ano'] for r in source if usable(r) and r['valor_alvo'] is not None});origins=years[1:-1]
    if len(origins)<2:raise ValueError('ORIGENS_PARA_SELECAO_E_AUDITORIA_INSUFICIENTES')
    points={k:[] for k in ks};outer=[];failures=Counter();allpoints={k:[] for k in ks}
    for origin in origins:
        for target in source:
            if target['ano']!=origin+1 or not usable(target) or target['ruptura']:continue
            cutoff=f'{origin}-12-31'
            # Resposta tardia pode ser pontuada retrospectivamente, mas nunca treina o fold.
            for k in ks:
                try:p=anchored_knn(panel,registry,dist=target['DIST'],objective=objective,metric=metric,anchor_year=origin,target_year=origin+1,cutoff=cutoff,k=k)
                except ValueError as e:failures[str(e)]+=1;continue
                entry={'DIST':str(target['DIST']),'origem':origin,'ano':origin+1,'previsto':p['estimativa'],'observado':target['valor_alvo'],'vizinhos':p['vizinhos']}
                allpoints[k].append(entry)
                if origin!=origins[-1]:points[k].append(entry)
    # Mesmos pares (DIST, origem) na seleção de todo k; última origem nunca escolhe hiperparâmetro.
    common=set.intersection(*[{(x['DIST'],x['origem']) for x in points[k]} for k in ks])
    if not common:return {'status':'bloqueado','motivo':'SEM_FOLDS_COMUNS_COM_FEATURES_E_ANCORAS_VALIDAS','falhas':dict(failures),'estimativa':None,'previsao_validada':False,'sintetico':panel['sintetico']}
    selection={k:metrics([x for x in points[k] if (x['DIST'],x['origem']) in common]) for k in ks}
    selected=min(ks,key=lambda k:(selection[k]['mae'],k))
    outer=[x for x in allpoints[selected] if x['origem']==origins[-1]]
    baselines={name:[] for name in ['persistencia','tendencia_ols','crescimento_historico']}
    # Baselines usam exatamente os mesmos pares da auditoria externa do KNN.
    for x in outer:
        hist=contiguous_tail([r for r in source if str(r['DIST'])==x['DIST'] and r['ano']<=x['origem'] and _available(r,f"{x['origem']}-12-31",positive=False)])
        for name in baselines:
            try:prediction,_=predict(CANDIDATES[name],hist,[x['ano']],cutoff=f"{x['origem']}-12-31")
            except ValueError:continue
            baselines[name].append({**x,'previsto':prediction[0]})
    comparable={(x['DIST'],x['ano']) for x in outer}
    for rows in baselines.values():comparable&={(x['DIST'],x['ano']) for x in rows}
    if not comparable:return {'status':'bloqueado','motivo':'SEM_PARES_COMUNS_NA_AUDITORIA','k':selected,'estimativa':None,'metricas_knn':metrics([]),'previsao_validada':False,'sintetico':panel['sintetico']}
    pick=lambda rows:[x for x in rows if (x['DIST'],x['ano']) in comparable]
    return {'status':'avaliacao_retrospectiva_sem_homologacao','k':selected,'selecao':selection,'origens_selecao':origins[:-1],
            'origem_auditoria':origins[-1],'metricas_knn':metrics(pick(outer)),'baselines':{k:metrics(pick(v)) for k,v in baselines.items()},
            'auditoria':pick(outer),'falhas':dict(failures),'previsao_validada':False,'sintetico':panel['sintetico'],
            'limites':['Vizinhos são DIST distintas, não linhas independentes de um painel empilhado','Intervalo indica dispersão entre análogos; não é cobertura probabilística calibrada','Quatro anos não homologam previsões 2026–2030']}

if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    from .registry import registry_from_catalog,read_json
    from .adapters import national_panel
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--panel',type=Path)
    args=p.parse_args();root=Path(__file__).resolve().parents[1];reg=registry_from_catalog(read_json(root/'etl/bdgd2025/config/conceitos_2025.json'))
    if args.panel:
        from .parquet_io import read_bundle
        panel=read_bundle(args.panel,reg)
    else:panel=national_panel(root/'output-historico/contrato-integracao',reg)
    result=backtest_knn(panel,reg,objective='consumidores',metric='quantidade')
    result.update(dataset_version=panel['dataset_version'],source_sha256=panel.get('source_sha256'),ancora_coopera_2024=next((r['valor_alvo'] for r in panel['rows'] if str(r['DIST'])=='5370' and r['ano']==2024 and r['objetivo_id']=='consumidores'),None),
        disponibilidade_ancora_original='DESCONHECIDA_NO_CONTRATO_NACIONAL',fontes_externas_entregues=len(panel['feature_definitions']))
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
