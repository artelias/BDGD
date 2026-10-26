"""Auditoria derivada: universo catalogado × DIST, sem fabricar linhas históricas."""
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from .contracts import usable, iso
from .parquet_io import arrow, sha
from .registry import validate_registry

CATEGORIES = {
    'HISTORICO_INSUFICIENTE': 'Histórico insuficiente',
    'AUSENCIA_OBSERVACOES': 'Ausência de observações',
    'FALTA_HOMOLOGACAO': 'Falta de homologação/decisão',
    'RUPTURA_CADASTRAL': 'Ruptura cadastral',
    'INCOMPATIBILIDADE_TEMPORAL': 'Incompatibilidade temporal',
    'SOBREPOSICAO_ATIVOS': 'Sobreposição/não somável',
    'PROBLEMA_UNIDADE': 'Problemas de unidade',
    'FALTA_COMPARABILIDADE': 'Falta de comparabilidade',
    'ZERO_TECNICO_SEM_EVIDENCIA': 'Zero técnico sem evidência independente',
    'NAO_APLICAVEL': 'Não aplicável no contrato',
    'COBERTURA_INCOMPLETA': 'Cobertura incompleta ou desconhecida',
    'METRICA_SEM_HISTORICO': 'Métrica catalogada sem linhas no contrato',
    'OUTROS': 'Outros motivos',
}


def row_causes(row, target, as_of):
    causes = []
    state = row['status_qualidade']
    if state == 'nao_aplicavel': causes.append('NAO_APLICAVEL')
    if state == 'ausente': causes.append('AUSENCIA_OBSERVACOES')
    if state == 'zero_tecnico': causes.append('ZERO_TECNICO_SEM_EVIDENCIA')
    if state == 'nao_homologado' or row['status_homologacao'] in {'BLOQUEADO', 'PENDENTE_DECISAO'}:
        causes.append('FALTA_HOMOLOGACAO')
    if row['ruptura'] or row.get('ponte_pendente'): causes.append('RUPTURA_CADASTRAL')
    if row['disponivel_em'] and iso(row['disponivel_em']) > iso(as_of): causes.append('INCOMPATIBILIDADE_TEMPORAL')
    if row['nao_somar']: causes.append('SOBREPOSICAO_ATIVOS')
    if row['unidade'] != target['unidade']: causes.append('PROBLEMA_UNIDADE')
    if target.get('requer_comparabilidade', True) and (not row.get('comparabilidade_validada') or not row.get('evidencia_comparabilidade')):
        causes.append('FALTA_COMPARABILIDADE')
    if row['cobertura'] != 1: causes.append('COBERTURA_INCOMPLETA')
    return causes


def overlap_audit(registry):
    """Interseção potencial pelo catálogo; nunca certifica disjunção por falta de registros."""
    targets = list(validate_registry(registry).values())
    pairs = []
    for i, a in enumerate(targets):
        for b in targets[i+1:]:
            if a['objetivo_id'] == b['objetivo_id'] or a['metrica'] != b['metrica']:
                continue
            entities = sorted(set(a['entidades']) & set(b['entidades']))
            if not entities: continue
            af, bf = a.get('filtros', {}), b.get('filtros', {})
            if any(set(af[k]).isdisjoint(bf[k]) for k in set(af) & set(bf)):
                continue
            pairs.append({'objetivo_a': a['objetivo_id'], 'objetivo_b': b['objetivo_id'], 'metrica': a['metrica'],
                          'entidades': entities, 'filtros_a': af, 'filtros_b': bf,
                          'status': 'SOBREPOSICAO_POTENCIAL_NAO_SOMAR',
                          'evidencia': 'Entidades comuns e predicados não disjuntos no catálogo; não somar objetivos'})
    return pairs


def coverage(panel, registry, report):
    targets = validate_registry(registry)
    grouped = defaultdict(list)
    for r in panel['rows']:
        if r['ano'] <= report['base_year']:
            grouped[(str(r['DIST']), r['objetivo_id'], r['metrica'])].append(r)
    # O universo é explicitamente o de DIST presentes, não uma certificação nacional.
    dists = sorted({str(r['DIST']) for r in panel['rows']}, key=int)
    results = defaultdict(list)
    for s in report['series']:
        results[(s['DIST'], s['objetivo_id'], s['metrica'])].append(s)
    if any(len(v) != 1 for v in results.values()):
        raise ValueError('Cobertura DIST × ano exige perímetro/regra canônico único por série')
    rows = []
    for dist in dists:
        for (objective, metric), target in sorted(targets.items()):
            key = (dist, objective, metric)
            raw = sorted(grouped[key], key=lambda r: r['ano'])
            s = results[key][0] if results[key] else None
            annual = [{'ano': r['ano'], 'estado': r['status_qualidade'], 'homologacao': r['status_homologacao'],
                       'causas': row_causes(r, target, report['as_of']), 'motivo_origem': r.get('motivo', ''),
                       'publicacao_id': r.get('proveniencia', {}).get('publicacao_id')} for r in raw]
            valid = [r['ano'] for r in raw if usable(r) and not any(c in row_causes(r, target, report['as_of']) for c in
                     ('INCOMPATIBILIDADE_TEMPORAL', 'PROBLEMA_UNIDADE', 'FALTA_COMPARABILIDADE'))]
            executable = bool(s and s['projecoes'])
            boundary = None
            if not raw:
                primary, status = 'METRICA_SEM_HISTORICO', 'AUSENTE_NO_CONTRATO'
            elif executable:
                primary, status = '', 'BASELINE_EXECUTAVEL'
            else:
                status = 'BLOQUEADA'
                # A causa principal explica a fronteira do segmento final, não a primeira falha de 2022.
                tail_years = set(s['treino_anos']) if s else set()
                boundary = next((a for a in reversed(annual) if a['ano'] not in tail_years or 'RUPTURA_CADASTRAL' in a['causas']), None)
                causes = boundary['causas'] if boundary else []
                priority = ('INCOMPATIBILIDADE_TEMPORAL', 'PROBLEMA_UNIDADE', 'SOBREPOSICAO_ATIVOS', 'FALTA_HOMOLOGACAO',
                            'NAO_APLICAVEL', 'ZERO_TECNICO_SEM_EVIDENCIA', 'AUSENCIA_OBSERVACOES', 'FALTA_COMPARABILIDADE',
                            'RUPTURA_CADASTRAL', 'COBERTURA_INCOMPLETA')
                if s and 'ALVO_AINDA_NAO_DISPONIVEL_NO_CORTE' in s['motivos']:
                    primary = 'INCOMPATIBILIDADE_TEMPORAL'
                elif s and 'METRICA_SEM_COMPARABILIDADE_VALIDADA' in s['motivos']:
                    primary = 'FALTA_COMPARABILIDADE'
                elif raw[-1]['ano'] != report['base_year']:
                    primary = 'INCOMPATIBILIDADE_TEMPORAL'
                else:
                    primary = next((c for c in priority if c in causes), 'HISTORICO_INSUFICIENTE')
            all_causes = sorted({c for a in annual for c in a['causas']} | ({primary} if primary else set()) |
                                ({'HISTORICO_INSUFICIENTE'} if s and 'MENOS_DE_TRES_OBSERVACOES_CONTIGUAS' in s['motivos'] else set()))
            resolution = {'FALTA_HOMOLOGACAO': 'DEPENDE_DECISAO_FORMAL_FONTE', 'RUPTURA_CADASTRAL': 'DEPENDE_PONTE_DE_POPULACAO',
                          'ZERO_TECNICO_SEM_EVIDENCIA': 'DEPENDE_EVIDENCIA_INDEPENDENTE_ZERO', 'NAO_APLICAVEL': 'MANTER_ND_NAO_REATIVAR',
                          'COBERTURA_INCOMPLETA': 'DEPENDE_COMPROVACAO_COBERTURA', 'AUSENCIA_OBSERVACOES': 'DEPENDE_FONTE_OU_NOVOS_DADOS',
                          'METRICA_SEM_HISTORICO': 'DEPENDE_PAINEL_ENRIQUECIDO_COMPARAVEL'}.get(primary, 'DEPENDE_EVIDENCIA_OU_NOVOS_DADOS')
            rows.append({'DIST': dist, 'OBJETIVO_ID': objective, 'METRICA': metric, 'UNIDADE': target['unidade'],
                         'ANOS_DISPONIVEIS': [r['ano'] for r in raw if r['valor_alvo'] is not None],
                         'ANOS_VALIDOS': valid, 'ANOS_REGISTRADOS': [r['ano'] for r in raw],
                         'ANOS_SEGMENTO_FINAL': s['treino_anos'] if s else [], 'STATUS': status,
                         'MOTIVO_BLOQUEIO': primary, 'ANO_FRONTEIRA': boundary['ano'] if boundary else None, 'CAUSAS_CONTRIBUINTES': all_causes,
                         'MOTIVOS_MOTOR': s['motivos'] if s else ['SEM_HISTORICO_NESTA_METRICA'],
                         'RESOLUCAO': 'NAO_NECESSARIA' if executable else resolution, 'CORRIGIVEL_AUTOMATICAMENTE_COM_DADOS_ATUAIS': False,
                         'EVIDENCIAS_ANUAIS': annual})
    by_target = []
    for (objective, metric), t in sorted(targets.items()):
        items = [r for r in rows if r['OBJETIVO_ID'] == objective and r['METRICA'] == metric]
        by_target.append({'OBJETIVO_ID': objective, 'METRICA': metric, 'UNIDADE': t['unidade'],
                          'ESPERADO': len(dists), 'OBSERVADO': sum(bool(r['ANOS_REGISTRADOS']) for r in items),
                          'ELEGIVEL': sum(r['STATUS'] == 'BASELINE_EXECUTAVEL' for r in items),
                          'BLOQUEADO': sum(r['STATUS'] == 'BLOQUEADA' for r in items),
                          'AUSENTE': sum(r['STATUS'] == 'AUSENTE_NO_CONTRATO' for r in items)})
    by_metric = []
    for metric in sorted({t['metrica'] for t in targets.values()}):
        items = [r for r in by_target if r['METRICA'] == metric]
        by_metric.append({'METRICA': metric, **{name: sum(r[name] for r in items) for name in ('ESPERADO', 'OBSERVADO', 'ELEGIVEL', 'BLOQUEADO', 'AUSENTE')}})
    blocked = [r for r in rows if r['STATUS'] == 'BLOQUEADA']
    summary = {'schema_version': 'cobertura-bdgd-1', 'experiment_id': report['experiment_id'], 'dataset_sha256': report['dataset_sha256'],
               'universo': 'DIST presentes no painel; não certifica universo nacional completo', 'dist': len(dists),
               'esperado': len(rows), 'observado': sum(bool(r['ANOS_REGISTRADOS']) for r in rows),
               'elegivel': sum(r['STATUS'] == 'BASELINE_EXECUTAVEL' for r in rows), 'bloqueado': len(blocked),
               'ausente_no_contrato': sum(r['STATUS'] == 'AUSENTE_NO_CONTRATO' for r in rows),
               'causa_principal_exclusiva': {c: sum(r['MOTIVO_BLOQUEIO'] == c for r in blocked) for c in CATEGORIES},
               'causas_contribuintes_nao_exclusivas': {c: sum(c in r['CAUSAS_CONTRIBUINTES'] for r in blocked) for c in CATEGORIES},
               'resolucao_bloqueados': dict(Counter(r['RESOLUCAO'] for r in blocked)),
               'por_objetivo_metrica': by_target, 'por_metrica': by_metric, 'sobreposicoes_catalogo': overlap_audit(registry),
               'nota': 'ANOS_DISPONIVEIS conta valores não nulos, inclusive zero técnico; não comprova disponibilidade histórica point-in-time. ANOS_VALIDOS é qualidade local; a elegibilidade usa segmento final contíguo. Causas anuais podem coexistir.'}
    return rows, summary


def write_coverage(panel, registry, report, directory):
    root = Path(directory); root.mkdir(parents=True, exist_ok=True)
    rows, summary = coverage(panel, registry, report)
    pa, pq = arrow()
    pq.write_table(pa.Table.from_pylist(rows), root / 'cobertura.parquet', compression='zstd')
    for filename, values in [('cobertura.csv', rows), ('cobertura-por-metrica.csv', summary['por_metrica']), ('cobertura-por-objetivo.csv', summary['por_objetivo_metrica'])]:
        with (root / filename).open('w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(values[0]) if values else [])
            writer.writeheader()
            for r in values:
                writer.writerow({k: json.dumps(v, ensure_ascii=False, separators=(',', ':')) if isinstance(v, (list, dict)) else v for k, v in r.items()})
    summary['arquivos_sha256'] = {name: sha(root/name) for name in ('cobertura.parquet', 'cobertura.csv', 'cobertura-por-metrica.csv', 'cobertura-por-objetivo.csv')}
    (root/'cobertura-resumo.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return summary
