"""Inventory of every local BDGD holding, from metadata only (ok.json, conversao.json, ArcGIS inventories, national contract).

    python -m motor_v2.inventory --output D:/NUCLEO_BDGD_2025/motor_v2/inventario_v2

No Parquet data page is read and nothing is downloaded. Each local publication (DIST x competence x ArcGIS item) is classified:

* ordinaria            - the item the national contract selected for that DIST/competence (the only kind any public product uses);
* extraordinaria       - any other local item: another version of the same competence (revision or duplicate), an item outside
                         the contract, or a file whose DIST/competence could not be identified. Extraordinary items are research
                         inputs only (see motor_v2/extraordinary.py) and never a new temporal observation unless their competence
                         is not covered by an ordinary item.

Per entity the row counts come from the conversion receipts. An alternate version whose per-entity row counts and source checksum
equal the ordinary ones is a duplicate; otherwise it is a revision. Competence and data-base come from the BASE table (2025) or the
inventory title (2022-2024, where BASE was not converted); the publication/revision dates are the ArcGIS ones."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HIST = Path('D:/NUCLEO_BDGD_2022_2024')
CUR = Path('D:/NUCLEO_BDGD_2025')
ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'output-historico/contrato-integracao/serie_fisica_nacional.csv'
# Entities the executor reads (granular targets) and the ones that identify the release
KEY_ENTITIES = ('UCBT', 'UCMT', 'UCAT', 'EQTRMT', 'UNTRMT', 'EQTRAT', 'UNTRAT', 'SSDMT', 'SSDBT', 'CONJ', 'CTMT')


def _csv(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def contract_selection(path=CONTRACT):
    """{(dist, year): {item_id, homologation statuses, ruptures}} from the national contract (the ordinary selection)."""
    sel = defaultdict(lambda: dict(items=set(), status=Counter(), ruptura=0))
    for r in _csv(path):
        k = (r['dist'], int(r['ano']))
        if r['publicacao_id']:
            sel[k]['items'].add(r['publicacao_id'])
        sel[k]['status'][r['status_homologacao']] += 1
        sel[k]['ruptura'] += r['ruptura_desde_ano_anterior'] == 'true'
    return sel


def publications():
    pubs = {}
    for r in _csv(HIST / 'inventario/inventario_historico_2022_2024.csv'):
        pubs[r['item_id']] = dict(dist=r['dist'], empresa=r['empresa'], ano=int(r['ano']), data_base=r['data_base'], versao=r['layout_versao'],
                                  publicado_em=r['publicado_em'], atualizado_em=r['atualizado_em'], status_inventario=r['status'], motivo=r['motivo'])
    for r in _csv(CUR / 'inventario/inventario_2025.csv'):
        pubs[r['item_id']] = dict(dist=r['dist'], empresa=r['empresa'], ano=2025, data_base=r['data_base_validada'] or r['data_base_declarada'],
                                  versao=r['versao'], publicado_em=r['publicado_em'], atualizado_em=r['atualizado_em'],
                                  status_inventario=r['status'], motivo=r['motivo'])
    return pubs


def holdings():
    """Every converted local item with its per-entity row counts and source checksum."""
    out = []
    for year_dir in sorted((HIST / 'parquet').iterdir()):
        for dist_dir in sorted(year_dir.iterdir()):
            for item_dir in sorted(dist_dir.iterdir()):
                ents, src = {}, set()
                for ok in item_dir.glob('*.ok.json'):
                    meta = _json(ok)
                    ents[ok.name[:-8]] = meta.get('rows')
                    src.add(meta.get('source_sha'))
                out.append(dict(ano=int(year_dir.name), dist=dist_dir.name, item_id=item_dir.name, entidades=ents,
                                source_sha=sorted(s for s in src if s)[0] if src - {None} else None, base=None, origem='parquet_2022_2024'))
    for dist_dir in sorted((CUR / 'staging_parquet').iterdir()):
        for base_dir in sorted(dist_dir.iterdir()):
            conv = base_dir / 'conversao.json'
            meta = _json(conv) if conv.exists() else {}
            ents = {e: v.get('linhas') for e, v in meta.get('entidades', {}).items()}
            out.append(dict(ano=int(base_dir.name.split('=')[1][:4]), dist=dist_dir.name.split('=')[1], item_id=meta.get('item_id'),
                            entidades=ents, source_sha=meta.get('sha256_zip'), base=meta.get('BASE'), origem='staging_2025'))
    return out


def unconverted(converted_ids):
    """Raw downloads without a converted Parquet (e.g. the ArcGIS item titled 'DUP', whose DIST/competence is unknown)."""
    out = []
    for year_dir in sorted((HIST / 'raw').iterdir()) if (HIST / 'raw').exists() else []:
        if not year_dir.name.isdigit():
            continue
        for dist_dir in sorted(year_dir.iterdir()):
            for item_dir in sorted(p for p in dist_dir.iterdir() if p.is_dir()):
                if item_dir.name not in converted_ids:
                    out.append(dict(ano=int(year_dir.name), dist=dist_dir.name, item_id=item_dir.name, motivo='download sem Parquet convertido'))
    for d in sorted((HIST / 'raw_fase6').glob('DUP_*')) if (HIST / 'raw_fase6').exists() else []:
        out.append(dict(ano=None, dist=None, item_id=d.name[4:], motivo="item ArcGIS com título 'DUP' não reconhecido: DIST e competência desconhecidos"))
    return out


def classify(items, sel, pubs):
    by_key = defaultdict(list)
    for it in items:
        by_key[(it['dist'], it['ano'])].append(it)
    rows = []
    for (dist, ano), its in sorted(by_key.items(), key=lambda x: (int(x[0][0]), x[0][1])):
        chosen = sel.get((dist, ano), {}).get('items', set())
        ordinary = [i for i in its if i['item_id'] in chosen]
        if ano == 2025 and not chosen and len(its) == 1:
            ordinary = its                          # 2025 contract rows may omit publicacao_id; the single staged item is the release
        ref = ordinary[0] if ordinary else None
        for it in its:
            p = pubs.get(it['item_id'] or '', {})
            ents = it['entidades']
            if it in ordinary:
                natureza, tipo = 'ordinaria', 'selecionada_no_contrato'
            elif ref is None:
                natureza, tipo = 'extraordinaria', 'fora_do_contrato'
            elif ents == ref['entidades'] and it['source_sha'] == ref['source_sha']:
                natureza, tipo = 'extraordinaria', 'duplicata_da_ordinaria'
            else:
                natureza, tipo = 'extraordinaria', 'versao_alternativa_mesma_competencia'
            delta = {}
            if ref is not None and it is not ref:
                delta = {e: (ents.get(e) or 0) - (ref['entidades'].get(e) or 0) for e in KEY_ENTITIES if ents.get(e) != ref['entidades'].get(e)}
            base = it['base'] or {}
            rows.append(dict(
                dist=dist, empresa=p.get('empresa', ''), competencia=ano,
                data_base=p.get('data_base') or (f'{ano}-12-31' if base.get('DAT_FNL', '').endswith(str(ano)) else ''),
                data_base_fonte='BASE.DAT_FNL' if base else 'titulo/inventario',
                base_dat_inc=base.get('DAT_INC', ''), base_dat_fnl=base.get('DAT_FNL', ''), base_dat_ext=base.get('DAT_EXT', ''),
                item_id=it['item_id'], versao=p.get('versao', ''), publicado_em=p.get('publicado_em', ''), atualizado_em=p.get('atualizado_em', ''),
                disponivel_em=max([d[:10] for d in (p.get('publicado_em'), p.get('atualizado_em')) if d] or ['']),
                natureza=natureza, tipo=tipo, nova_observacao_temporal=natureza == 'ordinaria' or ref is None,
                status_inventario=p.get('status_inventario', ''), homologacao_contrato=dict(sel.get((dist, ano), {}).get('status', {})),
                rupturas_contrato=sel.get((dist, ano), {}).get('ruptura', 0), entidades_convertidas=len(ents),
                registros_total=sum(v or 0 for v in ents.values()), **{f'linhas_{e}': ents.get(e) for e in KEY_ENTITIES},
                delta_vs_ordinaria=delta, source_sha=it['source_sha'] or '', origem=it['origem']))
    return rows


def contract_without_parquet(rows, sel, pubs, raw_only):
    """Contract-selected (ordinary) publications with no converted Parquet locally: part of the public series, unreadable by the
    executor until converted. Listed so that the isolation check knows them and the executor reports them as unavailable."""
    have = {r['item_id'] for r in rows}
    raw = {r['item_id'] for r in raw_only}
    out = []
    for (dist, ano), v in sorted(sel.items(), key=lambda x: (int(x[0][0]), x[0][1])):
        for item_id in sorted(v['items'] - have):
            p = pubs.get(item_id, {})
            out.append(dict(
                dist=dist, empresa=p.get('empresa', ''), competencia=ano, data_base=p.get('data_base', ''), data_base_fonte='titulo/inventario',
                base_dat_inc='', base_dat_fnl='', base_dat_ext='', item_id=item_id, versao=p.get('versao', ''), publicado_em=p.get('publicado_em', ''),
                atualizado_em=p.get('atualizado_em', ''), disponivel_em=max([d[:10] for d in (p.get('publicado_em'), p.get('atualizado_em')) if d] or ['']),
                natureza='ordinaria', tipo='selecionada_no_contrato_sem_parquet_local', nova_observacao_temporal=True,
                status_inventario=p.get('status_inventario', ''), homologacao_contrato=dict(v['status']), rupturas_contrato=v['ruptura'],
                entidades_convertidas=0, registros_total=0, **{f'linhas_{e}': None for e in KEY_ENTITIES}, delta_vs_ordinaria={},
                source_sha='', origem='zip_bruto_sem_conversao' if item_id in raw else 'ausente_localmente'))
    return out


def summarise(rows, raw_only):
    ordin = [r for r in rows if r['natureza'] == 'ordinaria']
    extra = [r for r in rows if r['natureza'] == 'extraordinaria']
    per_dist = defaultdict(set)
    for r in ordin:
        if r['entidades_convertidas']:          # temporal depth the executor can actually read
            per_dist[r['dist']].add(r['competencia'])
    years_hist = Counter(len(v) for v in per_dist.values())
    return dict(
        publicacoes_locais=len(rows), ordinarias=len(ordin), extraordinarias=len(extra),
        extraordinarias_por_tipo=dict(Counter(r['tipo'] for r in extra)),
        extraordinarias_novas_observacoes_temporais=sum(r['nova_observacao_temporal'] for r in extra),
        ordinarias_sem_parquet_local=[dict(dist=r['dist'], competencia=r['competencia'], item_id=r['item_id'], origem=r['origem'])
                                      for r in ordin if r['tipo'] == 'selecionada_no_contrato_sem_parquet_local'],
        nao_convertidas=raw_only, dist_com_ordinaria=len(per_dist),
        dist_por_numero_de_competencias=dict(sorted(years_hist.items())),
        dist_com_2022_2025_completo=sorted(int(d) for d, v in per_dist.items() if v == {2022, 2023, 2024, 2025}),
        competencias=sorted({r['competencia'] for r in rows}),
        datas_base=dict(Counter(r['data_base'] for r in rows)),
        registros_ordinarios=sum(r['registros_total'] for r in ordin),
        registros_extraordinarios=sum(r['registros_total'] for r in extra),
        linhas_ordinarias_por_entidade={e: sum(r[f'linhas_{e}'] or 0 for r in ordin) for e in KEY_ENTITIES},
        intervalo_disponibilidade={str(c): [min((r['disponivel_em'] for r in ordin if r['competencia'] == c and r['disponivel_em']), default=None),
                                            max((r['disponivel_em'] for r in ordin if r['competencia'] == c and r['disponivel_em']), default=None)]
                                   for c in sorted({r['competencia'] for r in ordin})})


def main(output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    items = holdings()
    sel, pubs = contract_selection(), publications()
    rows = classify(items, sel, pubs)
    raw_only = unconverted({i['item_id'] for i in items})
    rows += contract_without_parquet(rows, sel, pubs, raw_only)
    summary = summarise(rows, raw_only)
    fields = list(rows[0])
    with open(out / 'INVENTARIO_PUBLICACOES_LOCAIS.csv', 'w', encoding='utf-8', newline='\n') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else v for k, v in r.items()})
    (out / 'INVENTARIO_RESUMO.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return rows, summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='D:/NUCLEO_BDGD_2025/motor_v2/inventario_v2')
    _, s = main(ap.parse_args().output)
    print(json.dumps({k: v for k, v in s.items() if k not in ('nao_convertidas',)}, ensure_ascii=False, indent=1))
