"""Adaptador para a execução científica congelada; nenhuma busca de parâmetros."""
import hashlib
import importlib.util
import json
import platform
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PESQUISA = RAIZ / 'HOMOLOGACAO/CIENTIFICA/RECUPERACAO_CENARIOS'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()).hexdigest()

spec = importlib.util.spec_from_file_location('referencia_recuperacao_1', PESQUISA / 'recuperar.py')
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
C, OT = R.C, R.OT

def verificar_fontes():
    manifesto = json.loads((PESQUISA / 'MANIFESTO.json').read_text())
    paths = dict(R.ENTRADAS)
    paths.update({'recuperar.py': PESQUISA / 'recuperar.py', 'cenarios.py': RAIZ / 'motor_cenarios/cenarios.py',
                  'otimizar.py': RAIZ / 'motor_cenarios/otimizacao/otimizar.py'})
    expected = {**manifesto['entradas_sha256'], **manifesto['codigo_sha256']}
    for name, wanted in expected.items():
        if sha(paths[name]) != wanted:
            raise ValueError(f'Fonte congelada divergente: {name}')
    for name, wanted in manifesto['saidas_sha256'].items():
        paths[name] = PESQUISA / name
        if sha(paths[name]) != wanted:
            raise ValueError(f'Evidência congelada divergente: {name}')
    # Inclui TODAS as entradas efetivamente lidas e a implementação no cache.
    for path in sorted((RAIZ / 'motor_cenarios/entrada').rglob('*')):
        if path.is_file():
            paths[str(path.relative_to(RAIZ))] = path
    for path in [RAIZ / 'motor_v2/metric_contract.py', PESQUISA / '04_PROTOCOLO_CANDIDATOS.md',
                 PESQUISA / 'selecao_congelada.json', *sorted(Path(__file__).parent.glob('*.py'))]:
        paths[str(path.relative_to(RAIZ))] = path
    return {name: sha(path) for name, path in sorted(paths.items())}

def ambiente():
    import numpy, scipy, sklearn
    return dict(python=platform.python_version(), numpy=numpy.__version__, scipy=scipy.__version__,
                sklearn=sklearn.__version__, plataforma=platform.platform())

def carregar():
    entrada = RAIZ / 'motor_cenarios/entrada'
    series, empresas, unidades = C.carregar_contrato(R.ENTRADAS['contrato'].parent)
    pot, _ = C.carregar_potencia(entrada, series)
    for key, values in pot.items():
        series[key], unidades[key] = values, 'kVA'
    fi = C.internas_por_dist(series, entrada)
    fe, _ = C.externas_por_dist(entrada, entrada)
    return series, empresas, unidades, C.Motor(series, fi, fe), OT.MotorX(series, fi, fe)
