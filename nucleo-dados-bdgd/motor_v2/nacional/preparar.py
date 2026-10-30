"""Between extraction and comparison: national panel, IBGE municipality list, invalid-code scan, bridge proposals and quarantine.

    python -m motor_v2.nacional.preparar

Quarantine rules (a (DIST, year) leaves the model panels as target AND as t-1 feature year; it stays in the audit):
  * municipality codes outside the IBGE list for more than 2% of the active UCBT customers of that (DIST, year);
  * a recoding bridge proposal exists for it and is not homologated (Celesc 2023 at the time of writing).
Units whose code is outside the IBGE list are never territorial units (they stay in the company total)."""
import json

from . import ROOT_OUT
from .municipios import propose, reference, scan
from .painel import PANEL, build, dists_with
from .relatorio import write_csv
from ..runner import atomic

MAX_INVALID_SHARE = 0.02


def run():
    build()
    ref, sources = reference()
    vm = ROOT_OUT / 'referencias' / 'municipios_ibge.json'
    atomic(vm, sorted(ref))
    atomic(ROOT_OUT / 'referencias' / 'municipios_ibge_nomes.json', dict(fontes_sidra_sha256=sources, municipios=ref))
    dists = dists_with('ucbt_quantidade', 1)
    sc = scan(PANEL, dists, ref)
    write_csv(ROOT_OUT / 'auditoria' / 'CODIGOS_MUNICIPAIS_POR_DIST_ANO.csv', sc)
    quarantine, proposals = [], []
    for r in sc:
        if r['share_fora_ibge'] and r['share_fora_ibge'] > MAX_INVALID_SHARE:
            p = propose(PANEL, r['DIST'], r['ano'], ref) if r['clientes_padrao_zero_mais_6'] else None
            if p:
                proposals.append(p)
                atomic(ROOT_OUT / 'auditoria' / f"PONTE_{p['id']}_PROPOSTA.json", p)
                write_csv(ROOT_OUT / 'auditoria' / f"PONTE_{p['id']}_MAPEAMENTO.csv", p['mapeamento'])
            why = (f"ponte de recodificacao municipal {p['id']} pendente de homologacao" if p else
                   f"{r['share_fora_ibge']:.1%} dos clientes com codigo municipal fora da tabela IBGE")
            quarantine.append([r['DIST'], r['ano'], why])
    atomic(ROOT_OUT / 'quarentena.json', dict(quarentena=quarantine, municipios_validos=str(vm), limite_share_fora_ibge=MAX_INVALID_SHARE,
                                              propostas=[dict(id=p['id'], suficiente=p['evidencia_suficiente_para_proposta'], status=p['status'],
                                                              verificacoes=p['verificacoes']) for p in proposals]))
    return quarantine, proposals


if __name__ == '__main__':
    q, p = run()
    print(json.dumps(dict(quarentena=q, propostas=[x['id'] for x in p]), ensure_ascii=False))
