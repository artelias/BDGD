import argparse,json
from .engine import load_dictionary
from .parquet import enrich_parquets
from .audit import audit

def main():
 p=argparse.ArgumentParser(description='Auditoria patrimonial separada dos targets; sem reconstrução de GDB')
 p.add_argument('--dictionary');p.add_argument('--handoff');p.add_argument('--manifest');p.add_argument('--output',required=True)
 a=p.parse_args();d=load_dictionary(a.dictionary)
 if bool(a.handoff)==bool(a.manifest):p.error('Escolha --handoff ou --manifest')
 result=audit(a.handoff,d,a.output) if a.handoff else enrich_parquets(json.load(open(a.manifest)),d,a.output)
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
