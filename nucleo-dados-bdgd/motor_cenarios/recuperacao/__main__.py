"""CLI isolada: python -m motor_cenarios.recuperacao --ajuda via --help."""
import argparse
import os
# Limita tanto BLAS/OpenMP quanto os estimadores n_jobs=1 do gerador original.
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
import json
import time
from pathlib import Path

from .fontes import RAIZ, R, ambiente, carregar, digest, verificar_fontes
from .inventario import construir
from .selecao import selecionar
from .relatorio import COLUNAS, cobertura, csv_write, linhas
from .validacao import comparar

BASE_SAIDA=RAIZ/'motor_cenarios/experimental/recuperacao'


def destino(nome):
    if not nome or Path(nome).name != nome or nome in ('.','..','_cache','cache'):
        raise ValueError('Informe somente um nome de execução, sem caminho')
    path=BASE_SAIDA/nome
    # Não permite redirecionar resultados por symlink a fontes/produto público.
    if path.resolve()!=path.absolute():
        raise ValueError('Saída não pode conter links simbólicos')
    return path


def write_json(path, value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
    tmp.replace(path)


def memoria():
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 if os.name=='posix' else 1)
    except ImportError:
        return None


def limitar_memoria():
    if os.name=='posix':
        import resource
        _, hard=resource.getrlimit(resource.RLIMIT_AS)
        limit=8*1024**3
        resource.setrlimit(resource.RLIMIT_AS,(min(limit,hard) if hard != resource.RLIM_INFINITY else limit,hard))


def executar(modo, nome, metricas=()):
    limitar_memoria()
    start=time.perf_counter(); resources=[]
    output=destino(nome)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Execução já existe: use outro --nome para preservar os resultados')
    output.mkdir(parents=True,exist_ok=True)
    cache=BASE_SAIDA/'cache'
    if cache.resolve()!=cache.absolute():
        raise ValueError('Cache não pode conter links simbólicos')
    cache.mkdir(parents=True,exist_ok=True)
    hashes=verificar_fontes()
    env=ambiente()
    fingerprint=digest(dict(fontes=hashes,ambiente=env,protocolo=R.PROTOCOLO))
    series,empresas,_,motor,motor_x=carregar()
    pub=json.loads(R.ENTRADAS['publicado'].read_text(encoding='utf-8'))
    keys={m['conceito']+'/'+m['metrica'] for m in pub['metricas'] if m['series']}
    if set(metricas)-keys:
        raise ValueError('Métrica desconhecida: '+str(set(metricas)-keys))
    product=dict(schema_version='cenarios-motor-recuperacao-1',modo=modo,protocolo=R.PROTOCOLO,
                 estado='EXPERIMENTAL_NAO_HOMOLOGADO',base=2025,horizonte=list(range(2026,2031)),
                 hash_proveniencia=fingerprint,metricas=[])
    audit=[]; inventory=[]
    for pm in pub['metricas']:
        key=pm['conceito'],pm['metrica']
        if not pm['series'] or (metricas and '/'.join(key) not in metricas):
            continue
        t=time.perf_counter()
        cache_key=digest({'execucao':fingerprint,'metrica':key})
        path=cache/(cache_key+'.json')
        hit=path.exists()
        if hit:
            entry=json.loads(path.read_text(encoding='utf-8'))
            if entry['chave']!=cache_key or entry['sha256']!=digest(entry['conteudo']):
                raise ValueError('Cache corrompido: '+str(path))
            bundle=entry['conteudo']
        else:
            try:
                bundle=construir(key,pm,motor,motor_x)
            except ValueError as error:
                write_json(output/'bloqueio.json',dict(etapa='/'.join(key),erro=str(error),
                    hash_proveniencia=fingerprint,ambiente=env,estado='BLOQUEADO_NAO_PRONTO_PARA_REVISAO',
                    segundos=round(time.perf_counter()-start,6),pico_rss_mib=memoria()))
                raise
            write_json(path,dict(chave=cache_key,sha256=digest(bundle),conteudo=bundle))
        result, checks=selecionar(pm,bundle,series,modo,fingerprint)
        product['metricas'].append(result); audit.extend(checks)
        inventory.append(dict(conceito=key[0],metrica=key[1],**bundle))
        resources.append(dict(etapa='/'.join(key),cache=hit,segundos=round(time.perf_counter()-t,6),pico_rss_mib=memoria()))
        print(json.dumps(resources[-1]),flush=True)
    rows, trajectories=linhas(product,empresas)
    summary=cobertura(rows,product)
    oracle=comparar(product,audit,modo)
    # Confirma novamente a integridade após o processamento.
    if verificar_fontes()!=hashes:
        raise ValueError('Fontes alteradas durante a execução')
    product['aceite_gabarito']=not oracle['divergencias']
    write_json(output/'produto.json',product)
    write_json(output/'inventario.json',inventory)
    write_json(output/'cobertura.json',summary)
    write_json(output/'gabarito.json',oracle)
    csv_write(output/'comparacao.csv',rows,COLUNAS)
    csv_write(output/'cenarios.csv',trajectories)
    csv_write(output/'elegibilidade.csv',audit)
    csv_write(output/'cobertura.csv',summary['por_grupo'])
    resources.append(dict(etapa='TOTAL',segundos=round(time.perf_counter()-start,6),pico_rss_mib=memoria()))
    write_json(output/'execucao.json',dict(ambiente=env,recursos=resources,novos_modelos=[],busca_1504_reexecutada=False))
    from .fontes import sha
    write_json(output/'proveniencia.json',dict(entradas=hashes,ambiente=env,protocolo=R.PROTOCOLO,
        saidas={p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file() and p.name not in ('execucao.json','proveniencia.json')},
        hash=fingerprint,validacao_2025='retrospectiva_exploratoria_alvo_ja_consultado',homologacao_2026_2030=False))
    print(json.dumps(summary['nacional'],ensure_ascii=False),flush=True)
    if oracle['divergencias']:
        raise ValueError(f"Gabarito divergiu em {len(oracle['divergencias'])} campos; ver {output/'gabarito.json'}")
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modo',choices=['originais','otimizados','condicionais'],default='originais')
    parser.add_argument('--nome',required=True,help='Subdiretório experimental, nunca caminho público')
    parser.add_argument('--metrica',action='append',default=[],help='conceito/metrica; omita para nacional')
    args=parser.parse_args()
    executar(args.modo,args.nome,args.metrica)

if __name__=='__main__':
    main()
