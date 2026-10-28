"""Reconciliação dirigida de derivados existentes. Sem extração, imputação ou homologação."""
import csv,hashlib,json
from pathlib import Path
from .contratos import observacoes,ROOT

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jsonwrite(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
def csvupdate(path,fn):
    path=Path(path)
    with path.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    for row in rows:fn(row)
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)

def apply(root=ROOT):
    root=Path(root);notes=observacoes(root);by={(n['dist'],n['ativo']):n for n in notes if n['ano']==2025}
    pkg=root/'output-publicavel/2025-12-31';web=root/'web/public/data/2025-12-31'
    # As contagens brutas de linhas ficam intactas. Quantidade física desconhecida vira NULL.
    empty={(5370,'UCBT'):by[5370,'consumidores'],(7371,'EQTRM'):by[7371,'trafo_medida']}
    reason=lambda n:n['problema']+' '+n['tratamento']
    original_manifest=json.loads((pkg/'manifest.json').read_text())
    sources={int(x['dist']):x for x in original_manifest['sources']}
    for (d,entity),n in empty.items():
        if sources[d]['sha256']!=n['origem']['sha256_zip']:raise ValueError('Nova fonte exige reauditoria: '+str(d))
    with (pkg/'ativos_agregados.csv').open(encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if (int(row['dist']),row['entidade']) in empty and row['quantidade_registros']!='0':
                raise ValueError('Entidade não está vazia; ressalva antiga não pode sobrescrever registros')

    paths=[pkg/x for x in ['ativos_totais.csv','ativos_agregados.csv','matriz_empresas_2025.csv','indicadores_complementares.csv','manifest.json']]+[web/'index.json',web/'assets.json',web/'conceitos/consumidores.json',web/'conceitos/transformadores.json']
    audit=root/'auditoria/reconciliacao/evidencias';audit.mkdir(parents=True,exist_ok=True)
    basefile=audit/'derivados-antes.json'
    if not basefile.exists():basefile.write_text(json.dumps({str(p.relative_to(root)):sha(p) for p in paths},indent=2)+'\n')
    def totals(r):
        n=by.get((int(r['dist']),r['ativo']))
        if not n or r['medida']!='quantidade':return
        if n['bloqueia_total']:r.update(valor='',status='bloqueado',motivo=reason(n))
        else:r.update(status='alerta',motivo=reason(n))
    csvupdate(pkg/'ativos_totais.csv',totals)
    def facts(r):
        n=empty.get((int(r['dist']),r['entidade']))
        if n:r.update(quantidade='',status_qualidade='bloqueado',motivo_qualidade=reason(n))
    csvupdate(pkg/'ativos_agregados.csv',facts)
    def matrix(r):
        for (d,e),n in empty.items():
            if int(r['dist'])==d:r[e+'__quantidade']=''
    csvupdate(pkg/'matriz_empresas_2025.csv',matrix)
    def comps(r):
        if r['dist']=='5370' and (r['indicador']=='uc_uniao_distinta' or (r['indicador']=='uc_ativadas' and r['entidade']=='UCBT')):
            r.update(valor='',status='bloqueado',motivo=reason(by[5370,'consumidores']))
    csvupdate(pkg/'indicadores_complementares.csv',comps)
    index=json.loads((web/'index.json').read_text());ST={'aprovado':'a','alerta':'l','bloqueado':'b','em_validacao':'e','nao_aplicavel':'n'}
    for row in index['fatos']['rows']:
        n=empty.get((row[0],row[1]))
        if n:row[2]=None;row[7]='b';row[8]=reason(n)
    for (d,asset),n in by.items():
        for row in index['ativosTotais'][asset]['quantidade']:
            if row[0]==d:
                if n['bloqueia_total']:row[1]=None;row[2]='b'
                else:row[2]='l'
                row[3]=reason(n)
    for name,ent in [('uc_uniao_distinta','UC*'),('uc_ativadas','UCBT')]:
        index['complementares'][name]['5370'][ent]=[None,'b',reason(by[5370,'consumidores'])]
    # Metadados de cobertura reutilizados pelo agregador universal; cubos observados intactos.
    for concept,dimension,code,dist in [('consumidores','nivel','BT',5370),('transformadores','tipo','575',7371)]:
        p=web/'conceitos'/f'{concept}.json';obj=json.loads(p.read_text())
        obj['cobertura_incompleta']=[{'dist':dist,'dimensao':dimension,'codigo':code,'metrica':'quantidade'}];jsonwrite(p,obj)
    manifest=json.loads((pkg/'manifest.json').read_text())
    if not manifest['release_id'].endswith('-rec1'):manifest['release_id']+='-rec1'
    manifest['status']='com_ressalvas';manifest['quality']['status']='com_ressalvas'
    manifest['reconciliacao']={'versao':'observacoes-bdgd-1','fonte':'auditoria/reconciliacao/observacoes.json','sha256':sha(root/'auditoria/reconciliacao/observacoes.json'),'homologacao_adicional':False}
    for p in paths[:4]:manifest['checksums'][p.name]=sha(p)
    jsonwrite(pkg/'manifest.json',manifest)
    index['release']['release_id']=manifest['release_id'];index['release']['status']=manifest['status'];index['release']['quality']=manifest['quality'];index['reconciliacao']=manifest['reconciliacao'];jsonwrite(web/'index.json',index)
    assets=json.loads((web/'assets.json').read_text());assets['release_id']=manifest['release_id'];jsonwrite(web/'assets.json',assets)
    # Fonte única também para TypeScript. Identificadores/anotações não são dados individuais.
    jsonwrite(root/'web/src/lib/observacoes-dados.json',{'schema_version':'observacoes-bdgd-1','observacoes':notes})
    (audit/'derivados-depois.json').write_text(json.dumps({str(p.relative_to(root)):sha(p) for p in paths},indent=2)+'\n')
    return {'derivados':len(paths),'homologacao_adicional':False}
if __name__=='__main__':print(apply())
