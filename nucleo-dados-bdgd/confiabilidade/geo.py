"""Geometria oficial dos conjuntos (camada CONJ da BDGD 2025): simplificação para o mapa e área.

    python -m confiabilidade.geo --dist 6600        # ou --todas

Requer shapely e pyproj (o mesmo ambiente do ETL do portal). A origem é o polígono publicado pela distribuidora na BDGD
(EPSG:4674). Nada é desenhado quando o conjunto não tem polígono: ele fica sem geometria. Os Parquets de 2022–2024 foram
convertidos sem geometria; por isso o mapa usa a delimitação de 31/12/2025.
A simplificação preserva a topologia de cada polígono (tolerância em graus, ~110 m), mas é feita polígono a polígono:
podem surgir frestas ou sobreposições mínimas entre vizinhos. Serve para visualização, não para medição.
A área é calculada no elipsoide (geodésica) sobre a geometria ORIGINAL.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .contrato import VERSAO_CONTRATO
from .infra import STAGING_2025, dists_disponiveis, lit

TRABALHO = Path(os.environ.get('CONF_TRABALHO', 'D:/NUCLEO_BDGD_2025/confiabilidade'))
TOLERANCIA_GRAUS = 0.001
PRECISAO = 1e-4          # ~11 m; reduz o tamanho do GeoJSON


def processar(dist, trabalho=TRABALHO):
    import duckdb
    import shapely
    from pyproj import Geod
    base = STAGING_2025 / f'DIST={dist}' / 'DATA_BASE=2025-12-31' / 'entidade=CONJ'
    arqs = sorted(base.glob('*.parquet')) if (base / '_OK').exists() else []
    destino = Path(trabalho) / 'derivado' / 'geo' / f'{dist}.json'
    if not arqs:
        return dict(dist=dist, status='SEM_CAMADA_CONJ')
    con = duckdb.connect()
    cols = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet([{', '.join(lit(a) for a in arqs)}])").fetchall()}
    if not {'COD_ID', 'Shape'} <= cols:
        return dict(dist=dist, status='SEM_GEOMETRIA', motivo='camada CONJ sem coluna Shape')
    rows = con.execute(f"SELECT try_cast(COD_ID AS BIGINT), {'NOME' if 'NOME' in cols else 'NULL'}, Shape FROM read_parquet([{', '.join(lit(a) for a in arqs)}])").fetchall()
    geod = Geod(ellps='GRS80')
    feats, conj, problemas = [], {}, []
    for cod, nome, wkb in rows:
        if cod is None:
            problemas.append('COD_ID nulo'); continue
        if wkb is None:
            conj[str(cod)] = dict(geometria=False, motivo='sem polígono na origem'); continue
        try:
            g = shapely.from_wkb(bytes(wkb))
        except Exception as e:  # geometria ilegível: o conjunto fica sem polígono, não com um polígono inventado
            conj[str(cod)] = dict(geometria=False, motivo=f'WKB ilegível: {type(e).__name__}'); continue
        if g.is_empty or g.geom_type not in ('Polygon', 'MultiPolygon'):
            conj[str(cod)] = dict(geometria=False, motivo=f'geometria {g.geom_type} vazia ou não poligonal'); continue
        valida = bool(g.is_valid)
        if not valida:
            g = shapely.make_valid(g)
            partes = [p for p in getattr(g, 'geoms', [g]) if p.geom_type in ('Polygon', 'MultiPolygon')]
            if not partes:
                conj[str(cod)] = dict(geometria=False, motivo='geometria inválida sem parte poligonal'); continue
            g = shapely.union_all(partes)
        x0, y0, x1, y1 = g.bounds
        if not (-75 <= x0 <= x1 <= -28 and -35 <= y0 <= y1 <= 7):
            conj[str(cod)] = dict(geometria=False, motivo='coordenadas fora do Brasil'); continue
        area_km2 = abs(geod.geometry_area_perimeter(g)[0]) / 1e6
        s = g.simplify(TOLERANCIA_GRAUS, preserve_topology=True)
        s = shapely.set_precision(s, PRECISAO)
        if s.is_empty:
            s = shapely.set_precision(g, PRECISAO)
        if not s.is_valid:
            s = shapely.make_valid(s)
            s = shapely.union_all([p for p in getattr(s, 'geoms', [s]) if p.geom_type in ('Polygon', 'MultiPolygon')])
        if s.is_empty:
            conj[str(cod)] = dict(geometria=False, motivo='polígono degenerado após simplificação', area_km2=round(area_km2, 3)); continue
        pt = s.representative_point()
        conj[str(cod)] = dict(geometria=True, area_km2=round(area_km2, 3), valida_na_origem=valida, partes=len(getattr(g, 'geoms', [g])),
                              centro=[round(pt.x, 4), round(pt.y, 4)], bbox=[round(v, 4) for v in s.bounds])
        feats.append(dict(type='Feature', properties=dict(c=int(cod), n=(nome or '').strip()), geometry=shapely.geometry.mapping(s)))
    doc = dict(type='FeatureCollection', features=feats,
               meta=dict(contrato=VERSAO_CONTRATO, dist=dist, fonte='BDGD 2025 (ANEEL) — camada CONJ, EPSG:4674', data_base='2025-12-31',
                         tipo='POLIGONO_OFICIAL_SIMPLIFICADO', tolerancia_graus=TOLERANCIA_GRAUS, precisao_graus=PRECISAO,
                         area='geodésica (GRS80) sobre a geometria original', problemas=problemas,
                         gerado_em=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')),
               conjuntos=conj)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix('.parcial')
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    tmp.replace(destino)
    return dict(dist=dist, status='PROCESSADO', conjuntos=len(conj), com_geometria=len(feats), bytes=destino.stat().st_size)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dist', type=int, nargs='*')
    ap.add_argument('--todas', action='store_true')
    a = ap.parse_args()
    for d in (dists_disponiveis() if a.todas else a.dist or []):
        try:
            r = processar(d)
        except Exception as e:
            r = dict(dist=d, status='FALHOU', motivo=f'{type(e).__name__}: {e}'[:300])
        print(json.dumps(r, ensure_ascii=False), flush=True)
