"""Confronta códigos nos cubos existentes; não audita registros brutos indisponíveis."""
from collections import Counter
import gzip,json
from pathlib import Path
from .audit import export_rows


def audit_published(root):
 root=Path(root)
 p=json.loads(gzip.decompress((root/'web/public/data/patrimonio/dicionario.json.gz').read_bytes()))
 rows=[]
 for r in p['agregados_tipo_bem']:
  t=p['tucs'].get(r['TUC']);b=t['bens'].get(r['A1']) if t else None
  status='TUC_SEM_CORRESPONDENCIA_R2' if not t else 'A1_SEM_CORRESPONDENCIA_R2' if not b else 'CODIGOS_CATALOGADOS_R2'
  rows.append({**r,'CONFRONTO':status,'NOME_NORMATIVO_R2':t['nome'] if t else None,
               'DESCRICAO_A1_R2':b['descricao_documental'] if b else None,'REVISAO_CONFERIDA':'2',
               'VIGENCIA_NORMATIVA':'PENDENTE_R3','CORRECAO_AUTOMATICA_AUTORIZADA':False})
 out=root/'patrimonio/data/publicados';out.mkdir(parents=True,exist_ok=True)
 export_rows(out,'confronto-publicado-2025',rows)
 summary={'grupos':len(rows),'por_status':dict(Counter(r['CONFRONTO'] for r in rows)),
  'codigos_tuc_sem_correspondencia_r2':sorted({r['TUC'] for r in rows if r['CONFRONTO']=='TUC_SEM_CORRESPONDENCIA_R2'}),
  'nota':'Grupos DIST×conceito×TUC×A1, não registros individuais; SEM_CODIGO é marcador do cubo. Não correspondência na Revisão 2 não autoriza corrigir código sem verificar Revisão 3/vigência. Não somar esses grupos como amostras independentes.',
  'source_sha256':p['source']['sha256'],'targets_modificados':False}
 (out/'resumo.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(summary,ensure_ascii=False));return summary
if __name__=='__main__':audit_published(Path(__file__).resolve().parents[1])
