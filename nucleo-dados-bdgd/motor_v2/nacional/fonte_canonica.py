"""Canonical INTERNAL source of consumers for future integrations: the hierarchically reconciled projection.

    python -m motor_v2.nacional.fonte_canonica          # declares the contract (hash, columns, rules) after verifying the series

Rule for any internal consumer of consumers projections (DIST x ano x cenario):
  * `consumidores_reconciliado` is the value to use; it satisfies Consumidores >= UCBT, integers >= 0, ordered scenarios and holds exactly
    15 unique (ano, cenario) pairs per reconciled DIST;
  * `consumidores_B_original` (independent Level B model) is kept ONLY as an independent result and audit material: it is never a fallback;
    a DIST absent from the reconciled series has no canonical value and the caller must handle that explicitly;
  * the source is internal and experimental: no publication, no dashboard, no scientific homologation.
`carregar` refuses a source whose hash differs from the declared contract or whose series fails the contract checks."""
import json
from collections import defaultdict

import pyarrow.parquet as pq

from . import hierarquia
from ..runner import atomic, digest, read

FONTE = hierarquia.OUT / 'PROJECOES_CONSUMIDORES_RECONCILIADAS.parquet'
CONTRATO = hierarquia.OUT / 'FONTE_CANONICA_CONSUMIDORES_INTERNA.json'
COLUNA = 'consumidores_reconciliado'
COLUNA_AUDITORIA = 'consumidores_B_original'


class FonteCanonicaInvalida(RuntimeError):
    pass


def verificar(rows):
    """Contract checks on reconciled rows -> list of problems (empty when the source is usable)."""
    rec = [r for r in rows if r['status'] == 'reconciliada']
    return hierarquia.violations(rec) + hierarquia.incompletude(rec)


def declarar(fonte=FONTE, contrato=CONTRATO):
    rows = pq.read_table(fonte).to_pylist()
    bad = verificar(rows)
    if bad:
        raise FonteCanonicaInvalida(f'{len(bad)} problemas nas series reconciliadas; contrato nao declarado')
    rec = [r for r in rows if r['status'] == 'reconciliada']
    dist = sorted({r['DIST'] for r in rec})
    ancora = defaultdict(list)
    for d in dist:
        ancora[next(r['ancora'] for r in rec if r['DIST'] == d)].append(d)
    c = dict(
        contrato='fonte-canonica-consumidores-1', escopo='interno e experimental; nao publicavel; sem homologacao cientifica',
        fonte=fonte.name, sha256=digest(fonte), coluna_canonica=COLUNA, coluna_somente_auditoria=COLUNA_AUDITORIA,
        chave=['DIST', 'ano', 'cenario'], anos=list(hierarquia.YEARS), cenarios=list(hierarquia.SCEN),
        pares_por_dist=len(hierarquia.YEARS) * len(hierarquia.SCEN), linhas_reconciliadas=len(rec), dist_reconciliadas=dist,
        dist_sem_valor_canonico=sorted({r['DIST'] for r in rows if r['status'] != 'reconciliada'}),
        dist_por_ancora={str(k): v for k, v in sorted(ancora.items())},
        regras=['consumidores_reconciliado >= ucbt_A', 'inteiros >= 0', 'Conservador <= Moderado <= Agressivo', '15 pares (ano, cenario) unicos por DIST'],
        proibido=['usar consumidores_B_original como substituto quando falta valor canonico', 'publicar ou exibir no dashboard', 'declarar homologacao'])
    atomic(contrato, c)
    return c


def carregar(fonte=FONTE, contrato=CONTRATO):
    """{(DIST, ano, cenario): int} canonical consumers; raises FonteCanonicaInvalida when the hash or the contract checks fail."""
    c = read(contrato)
    if digest(fonte) != c['sha256']:
        raise FonteCanonicaInvalida('hash da fonte difere do contrato declarado')
    rows = pq.read_table(fonte).to_pylist()
    bad = verificar(rows)
    if bad:
        raise FonteCanonicaInvalida(f'{len(bad)} problemas nas series reconciliadas')
    return {(r['DIST'], r['ano'], r['cenario']): int(r[COLUNA]) for r in rows if r['status'] == 'reconciliada'}


if __name__ == '__main__':
    c = declarar()
    print(json.dumps({k: c[k] for k in ('fonte', 'sha256', 'linhas_reconciliadas', 'pares_por_dist', 'dist_sem_valor_canonico')} | dict(dist=len(c['dist_reconciliadas'])), ensure_ascii=False, indent=1))
