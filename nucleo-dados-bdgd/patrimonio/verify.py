"""Reprodutibilidade de conteúdo, independente do cabeçalho gzip/Python/zlib."""
import gzip,hashlib,json,tempfile
from pathlib import Path
from .web_product import generate
from .published import audit_published

def compare_gzip(expected,actual):
    left=gzip.decompress(Path(expected).read_bytes());right=gzip.decompress(Path(actual).read_bytes())
    if left!=right:raise ValueError('Conteúdo gzip descomprimido diverge')
    return hashlib.sha256(left).hexdigest()

def compare_file(expected,actual):
    if expected.name.endswith('.gz'):return compare_gzip(expected,actual)
    if expected.suffix=='.parquet':
        import pyarrow.parquet as pq
        a,b=pq.read_table(expected),pq.read_table(actual)
        if not a.schema.equals(b.schema) or a.to_pylist()!=b.to_pylist():raise ValueError('Tabela Parquet diverge: '+expected.name)
    elif expected.read_bytes()!=actual.read_bytes():raise ValueError('Artefato diverge: '+expected.name)

def verify(root):
    root=Path(root)
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);target=tmp/'dicionario.json.gz';generate(root,target)
        digest=compare_gzip(root/'web/public/data/patrimonio/dicionario.json.gz',target)
        out=tmp/'publicados';audit_published(root,output=out)
        for p in (root/'patrimonio/data/publicados').iterdir():compare_file(p,out/p.name)
        print(json.dumps({'conteudo_web_sha256':digest,'artefatos_versionados_modificados':False,'gzip_metadata_ignorada':True,'gzip_header_versionado':(root/'web/public/data/patrimonio/dicionario.json.gz').read_bytes()[:10].hex(),'gzip_header_gerado':target.read_bytes()[:10].hex()}))
if __name__=='__main__':verify(Path(__file__).resolve().parents[1])
