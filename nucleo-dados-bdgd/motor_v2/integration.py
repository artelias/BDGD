"""Reuse the validated V1 bundle writer without changing V1's registry or production."""
from copy import deepcopy
from pathlib import Path
from motor_universal.registry import registry_from_catalog
from motor_universal.parquet_io import write_bundle,read_bundle
from motor_universal.contracts import validate_panel

def export(results,catalog,directory,version):
 registry=registry_from_catalog(catalog)
 template=deepcopy(next(x for x in registry['objetivos'] if x['objetivo_id']=='consumidores' and x['metrica']=='quantidade'))
 template.update(objetivo_id='ucbt',nome='Clientes UCBT ativos',entidades=['UCBT'],regra_agregacao='UC-v3 COD_ID+PN_CON, UCBT only; geographic conflicts audited')
 registry['objetivos'].append(template)
 rows=[]
 for result in results:
  for h in result['history']:
   value=h['value'];qa=h['qa'];rows.append(dict(ano=h['year'],DIST=str(result['dist']),objetivo_id='ucbt',metrica='quantidade',unidade=template['unidade'],valor_alvo=value,status_qualidade='observado' if value and value>0 else 'ausente',status_homologacao='APTO_COM_RESSALVAS',homologado=False,fonte=qa['source'],competencia=f"{h['year']}-12-31",disponivel_em=h['available'],cobertura=qa['coverage'],territorio={'nivel':'dist','id':str(result['dist'])},perimetro_id='UCBT-publicacao-original',regra_versao='UC-v3-UCBT-v2',ruptura=h['rupture'],nao_somar=False,comparabilidade_validada=False,evidencia_comparabilidade=None,natureza_alvo='estoque_fisico',features={},proveniencia={'parquet_sha256':qa['parquet_sha256'],'publication':h['source']['item'],'source_sha256':h['source']['source_sha']}))
 panel=dict(schema_version='painel-bdgd-1',dataset_version=version,sintetico=False,feature_definitions={},rows=rows)
 validate_panel(panel,registry)
 if not Path(directory).exists():write_bundle(panel,registry,directory)
 read_bundle(directory,registry)
 return registry
