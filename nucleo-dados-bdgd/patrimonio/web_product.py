"""Visão pública documental, sem registros individuais e sem promover targets."""
from collections import defaultdict
import gzip,json
from pathlib import Path
from .engine import load_dictionary,technical


def generate(root,output):
 root=Path(root);d=load_dictionary(root/'patrimonio/data/dicionario.json');summary=json.loads((root/'patrimonio/data/auditoria/resumo.json').read_text())
 groups=[];observed=set()
 for path in sorted((root/'web/public/data/2025-12-31/conceitos').glob('*.json')):
  cd=json.loads(path.read_text());cube=cd.get('cubos',{}).get('principal',{});dims=cube.get('dims',[])
  if 'tipo' not in dims or 'a1' not in dims:continue
  totals=defaultdict(int)
  for row in cube['rows']:
   tc=cd['valores']['tipo'][row[dims.index('tipo')+1]];a1=cd['valores']['a1'][row[dims.index('a1')+1]]
   totals[(row[0],tc,a1)]+=row[len(dims)+1]
   observed.add(tc)
  for (dist,tc,a1),n in sorted(totals.items()):groups.append({'DIST':str(dist),'ANO':2025,'conceito':cd['id'],'TUC':tc,'A1':a1,'quantidade':n,
       'fonte':path.name,'entidades':cube.get('entidades',[]),'status':'AGREGADO_PUBLICADO_2025_SEM_A2_A6'})
 product={'schema_version':'patrimonio-web-1','source':d['source'],'referencia_r3':d['referencia_r3'],'vigencias':d['vigencias'],
  'tucs':{tc:{k:v for k,v in t.items() if k!='atributos_documentais'} for tc,t in d['tucs'].items()},'tabelas':{k:[{**v,**technical(v['descricao'])} for v in values] for k,values in d['tabelas'].items()},
  'auditoria':summary,'observados_cubos_2025':sorted(observed),'agregados_tipo_bem':groups,'limites':d['limites'],
  'potencia_recuperada_homologada_kva':None,'previsao_validada':False}
 out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_bytes(gzip.compress((json.dumps(product,ensure_ascii=False,separators=(',',':'))+'\n').encode(),mtime=0))
 print(json.dumps({'tucs_documentais':len(d['tucs']),'tucs_observadas_cubos_2025':len(observed),'agregados':len(groups),'bytes_web':out.stat().st_size}))
 return product
if __name__=='__main__':generate(Path(__file__).resolve().parents[1],Path(__file__).resolve().parents[1]/'web/public/data/patrimonio/dicionario.json.gz')
