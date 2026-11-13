"""Auditoria independente: produto publicado x arquivos brutos da ANEEL (só leitura)."""
import json, math, sys, glob, random
from pathlib import Path
import duckdb
RAW = Path('D:/NUCLEO_BDGD_2025/confiabilidade/aneel_raw')
PROD = Path(sys.argv[1])
con = duckdb.connect(); con.execute("SET memory_limit='2GB'; SET threads=4")
P = (RAW/'indicadores-continuidade-coletivos-2020-2029.parquet').as_posix()
print('meses distintos:', con.execute(f"SELECT list(DISTINCT NumPeriodoIndice ORDER BY NumPeriodoIndice) FROM read_parquet('{P}') WHERE AnoIndice BETWEEN 2022 AND 2025").fetchone())
con.execute(f"""CREATE TABLE t AS SELECT DISTINCT IdeConjUndConsumidoras::BIGINT conj, SigIndicador ind, AnoIndice::INT ano, NumPeriodoIndice::INT mes, VlrIndiceEnviado v
 FROM read_parquet('{P}') WHERE AnoIndice BETWEEN 2022 AND 2025""")
con.execute("CREATE TABLE w AS PIVOT t ON ind USING max(v) GROUP BY conj, ano, mes")
cols = [r[0] for r in con.execute("DESCRIBE w").fetchall()]
def has(*c): return all(x in cols for x in c)
for I in ('DEC','FEC'):
    q = lambda e: con.execute(f"SELECT COUNT(*), SUM((abs({I} - ({e})) <= 0.011)::INT) FROM w WHERE {I} IS NOT NULL").fetchone()
    print(I, 'IP+IND', q(f'coalesce({I}IP,0)+coalesce({I}IND,0)'))
    print(I, 'IP+IND+XP+XN', q(f'coalesce({I}IP,0)+coalesce({I}IND,0)+coalesce({I}XP,0)+coalesce({I}XN,0)'))
    print(I, 'IP+IND+expurgos', q(f'coalesce({I}IP,0)+coalesce({I}IND,0)+coalesce({I}INE,0)+coalesce({I}INC,0)+coalesce({I}INO,0)+coalesce({I}IPC,0)'))
    # componentes ausentes quando o indicador existe
    print(I, 'IP ou IND nulos com indicador presente', con.execute(f"SELECT COUNT(*) FROM w WHERE {I} IS NOT NULL AND ({I}IP IS NULL OR {I}IND IS NULL)").fetchone())
# limites
L = (RAW/'indicadores-continuidade-coletivos-limite.csv').as_posix()
con.execute(f"""CREATE TABLE l AS SELECT DISTINCT IdeConjUndConsumidoras::BIGINT conj, SigIndicador ind, AnoLimiteQualidade::INT ano, replace(VlrLimite, ',', '.')::DOUBLE lim
 FROM read_csv('{L}', delim=';', header=true, all_varchar=true, quote='"') WHERE AnoLimiteQualidade::INT BETWEEN 2022 AND 2025 AND SigIndicador IN ('DEC','FEC')""")
anual = {(c,a): (d,f,nm,nd,nf) for c,a,d,f,nm,nd,nf in con.execute("SELECT conj, ano, round(sum(DEC),2), round(sum(FEC),2), count(*), count(DEC), count(FEC) FROM w GROUP BY 1,2").fetchall()}
mens = {(c,a,m): (d,f,n) for c,a,m,d,f,n in con.execute("SELECT conj, ano, mes, DEC, FEC, NumCon FROM w").fetchall()}
lim = {(c,i,a): v for c,i,a,v in con.execute("SELECT conj, ind, ano, lim FROM l").fetchall()}
comp = {(c,a): r for c,a,*r in con.execute("""SELECT conj, ano, round(sum(DECIP),2), round(sum(DECIND),2), round(sum(DECXP),2), round(sum(DECXN),2),
  round(sum(coalesce(DECINC,0)+coalesce(DECINE,0)+coalesce(DECINO,0)+coalesce(DECIPC,0)+coalesce(DECXNC,0)+coalesce(DECXPC,0)),2) FROM w GROUP BY 1,2""").fetchall()}
n = falhas = 0; ex = []
dif = {'dec':0,'fec':0,'ld':0,'lf':0,'meses':0,'mensal':0,'nuc':0,'comp':0}
for f in sorted(glob.glob(str(PROD/'distribuidoras/*.json'))):
    d = json.loads(Path(f).read_text(encoding='utf-8'))
    for c in d['conjuntos']:
        for a, b in c['a'].items():
            a = int(a); n += 1; k = (c['c'], a)
            if k not in anual:
                if b['dec'] is not None: dif['dec'] += 1; ex.append(('sem bruto', k))
                continue
            D, F, nm, nd, nf = anual[k]
            # soma dos meses publicada x bruto (12 meses)
            if b['meses_dec'] != nd: dif['meses'] += 1
            if b['dec'] is not None and abs(b['dec'] - D) > 0.011: dif['dec'] += 1; ex.append(('dec', k, b['dec'], D))
            if b['fec'] is not None and abs(b['fec'] - F) > 0.011: dif['fec'] += 1; ex.append(('fec', k, b['fec'], F))
            for kk, ind in (('ld','DEC'),('lf','FEC')):
                L0 = lim.get((c['c'], ind, a))
                if (b[kk] is None) != (L0 is None) or (L0 is not None and abs(b[kk]-L0) > 1e-6): dif[kk] += 1; ex.append((kk, k, b[kk], L0))
            for i in range(12):
                M = mens.get((c['c'], a, i+1))
                if M is None: continue
                pv = b['m']['dec'][i]
                if (pv is None) != (M[0] is None) or (pv is not None and abs(pv - M[0]) > 0.006): dif['mensal'] += 1
                pn = b['m']['nuc'][i]
                if M[2] is not None and pn is not None and abs(pn - M[2]) > 0.5: dif['nuc'] += 1
            C = comp.get(k)
            if C and b.get('comp') and b['comp'].get('dec'):
                pc = b['comp']['dec']
                for j, key in enumerate(('ip','ind','xp','xn','exp')):
                    if pc.get(key) is not None and C[j] is not None and abs(pc[key] - C[j]) > 0.02: dif['comp'] += 1; ex.append(('comp', k, key, pc[key], C[j])); break
print('conjunto-anos no produto:', n, 'divergencias:', dif)
for e in ex[:15]: print(' ', e)
# exemplo Mataraca
print('Mataraca 2025 bruto:', anual[(16849, 2025)], lim.get((16849,'DEC',2025)), lim.get((16849,'FEC',2025)), comp[(16849,2025)])
