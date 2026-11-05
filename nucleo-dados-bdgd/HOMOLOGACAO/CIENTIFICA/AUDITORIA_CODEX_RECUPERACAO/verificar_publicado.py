"""Verificação independente dos extremos publicados (só valores publicados, sem reexecutar modelos).

Uso: python verificar_publicado.py <commit> <saida_dir> [rotulo]

Lê `web/public/data/previsoes/cenarios-motor.json` do próprio commit (git show), sem
depender da worktree. Aplica, sobre os valores PUBLICADOS (Ĉ, M̂, Â), as regras do
protocolo recuperacao-1 que não exigem trajetória contínua:
  ORDEM (Q6)     s·(Ê_t − M̂_t) ≥ 0 nos 5 anos
  PLAUS (Q1–Q4)  finito ≥ 0; Ê_2030/y25 ∈ [0,5; 3]; g e salto 2026 no P01–P99 das transições
  DIF   (Q7)     s·(ĝ_E − ĝ_M) ≥ 0,05 p.p./ano, com ĝ = ln(X̂_2030/y25)/5
  UNID  (Q8)     contagens: s·(Ê_2030 − M̂_2030) ≥ 1
  FIS   (Q9)     contagens inteiras; km/kVA com até 3 decimais
Os percentis P01–P99 vêm das transições comparáveis do contrato (dados de entrada, não modelos).
Implementação nova: não importa `recuperar.py` nem `qualidade.py`.
"""
import csv
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / 'motor_cenarios'))
import cenarios as C  # noqa: E402  (só os carregadores do contrato)

JSON_PUB = 'nucleo-dados-bdgd/web/public/data/previsoes/cenarios-motor.json'
SINAL = {'conservador': -1, 'agressivo': 1}
DIF_MIN = C.DIFERENCA_MINIMA_PP / 100
ANOS = C.HORIZONTE


def transicoes_percentis(series, k):
    gs = []
    for anos in series.get(k, {}).values():
        for t in range(2023, C.BASE + 1):
            a, b = anos.get(t - 1), anos.get(t)
            if a and b and a[0] == b[0] == 'observado' and (a[1] or 0) > 0 and (b[1] or 0) > 0 and not b[2]:
                gs.append(math.log(b[1] / a[1]))
    return (float(np.percentile(gs, 1)), float(np.percentile(gs, 99))) if len(gs) >= 20 else (None, None)


def avaliar(E, M, y25, lado, disc, p01, p99):
    s = SINAL[lado]
    gaps = [s * (e - m) for e, m in zip(E, M)]
    falhas = []
    por_ano = ['OK' if g > 0 else 'IGUAL' if g == 0 else 'INVERTIDO' for g in gaps]
    if not all(isinstance(x, (int, float)) and math.isfinite(x) and x >= 0 for x in E):
        falhas.append('Q1_NAO_FINITO_OU_NEGATIVO')
    ok_y = y25 is not None and y25 > 0 and E[-1] > 0 and E[0] > 0
    gE = math.log(E[-1] / y25) / 5 if ok_y else float('nan')
    gM = math.log(M[-1] / y25) / 5 if ok_y and M[-1] > 0 else float('nan')
    g26 = math.log(E[0] / y25) if ok_y else float('nan')
    razao = E[-1] / y25 if ok_y else float('nan')
    if not (C.RAZAO_PLAUSIVEL[0] <= razao <= C.RAZAO_PLAUSIVEL[1]):
        falhas.append('Q2_RAZAO_2030_2025')
    if p01 is not None and not (p01 <= gE <= p99):
        falhas.append('Q3_CRESCIMENTO_FORA_P01_P99')
    if p01 is not None and not (p01 <= g26 <= p99):
        falhas.append('Q4_SALTO_2026_FORA_P01_P99')
    if any(g < 0 for g in gaps):
        falhas.append('Q6_ORDEM_' + ('C_ACIMA_DE_M' if s < 0 else 'A_ABAIXO_DE_M'))
    if not (math.isfinite(gE) and s * (gE - gM) >= DIF_MIN - 1e-12):
        falhas.append('Q7_DIFERENCA_MENOR_0_05PP')
    if disc and not s * (E[-1] - M[-1]) >= 1:
        falhas.append('Q8_DIFERENCA_MENOR_1_UNIDADE')
    if disc and any(type(x) is not int for x in E):
        falhas.append('Q9_CONTAGEM_NAO_INTEIRA')
    if not disc and any(abs(x - round(x, 3)) > 1e-9 for x in E):
        falhas.append('Q9_CONTINUO_MAIS_DE_3_DECIMAIS')
    if all(g <= 0 for g in gaps):
        estado = 'LADO_OPOSTO' if any(g < 0 for g in gaps) else 'IDENTICO'
    elif any(f.startswith(('Q1', 'Q2', 'Q3', 'Q4')) for f in falhas):
        estado = 'IMPLAUSIVEL'
    elif any(f.startswith('Q6') for f in falhas):
        estado = 'CRUZA'
    elif any(f.startswith(('Q7', 'Q8')) for f in falhas):
        estado = 'DIFERENCA_IMATERIAL'
    elif falhas:
        estado = 'IMPLAUSIVEL'
    else:
        estado = 'APROVADO'
    return estado, falhas, por_ano, dict(g_extremo=gE, g_moderado=gM, razao=razao, g_2026=g26)


def main(commit, saida, rotulo=None):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    rotulo = rotulo or commit
    sha = subprocess.run(['git', 'rev-parse', commit], capture_output=True, text=True, check=True, cwd=RAIZ).stdout.strip()
    blob = subprocess.run(['git', 'rev-parse', f'{commit}:{JSON_PUB}'], capture_output=True, text=True, check=True, cwd=RAIZ).stdout.strip()
    raw = subprocess.run(['git', 'show', f'{commit}:{JSON_PUB}'], capture_output=True, check=True, cwd=RAIZ).stdout
    pub = json.loads(raw.decode('utf-8'))
    series, _, unidades = C.carregar_contrato(RAIZ / 'output-historico/contrato-integracao')
    pot, _ = C.carregar_potencia(RAIZ / 'motor_cenarios/entrada', series)
    series.update(pot)
    empresas = pub.get('empresas', {})
    longas, extremos = [], []
    cont = Counter()
    por_metrica = defaultdict(Counter)
    for pm in pub['metricas']:
        k = (pm['conceito'], pm['metrica'])
        pm.setdefault('natureza', C.mc.nature_of(pm['unidade']))
        disc = pm['natureza'] == 'discrete_count'
        p01, p99 = transicoes_percentis(series, k)
        for d, s in sorted(pm['series'].items(), key=lambda x: int(x[0])):
            M = s.get('moderado')
            hist = s.get('hist') or []
            y25 = hist[-1][1] if hist and hist[-1][0] == C.BASE else None
            pres = [l for l in ('conservador', 'agressivo') if s.get(l)]
            cont['series'] += 1
            cont['com_moderado'] += bool(M)
            completa = bool(M) and len(pres) == 2
            cont['completas_publicadas'] += completa
            res = {}
            for lado in pres:
                if not M:
                    continue
                estado, falhas, por_ano, g = avaliar(s[lado], M, y25, lado, disc, p01, p99)
                res[lado] = (estado, falhas, por_ano)
                cont['extremos_publicados'] += 1
                cont['ext_' + estado] += 1
                cont['ext_' + estado + '_' + lado] += 1
                por_metrica[k]['extremos'] += 1
                por_metrica[k][estado] += 1
                extremos.append(dict(commit=sha[:7], DIST=d, empresa=(empresas.get(d) or {}).get('nome', '') if isinstance(empresas.get(d), dict) else empresas.get(d, ''),
                                     conceito=k[0], ativo=pm.get('ativo', ''), metrica=k[1], unidade=pm['unidade'], natureza=pm['natureza'],
                                     lado=lado, modelo_publicado=pm['cenarios'].get(lado), modelo_moderado=pm['cenarios'].get('moderado'),
                                     y_2025=y25, moderado_2030=M[-1], extremo_2030=s[lado][-1], estado=estado, regras_violadas='|'.join(falhas),
                                     anos_invertidos=sum(a == 'INVERTIDO' for a in por_ano), anos_iguais=sum(a == 'IGUAL' for a in por_ano),
                                     g_extremo=round(g['g_extremo'], 6) if math.isfinite(g['g_extremo']) else '',
                                     g_moderado=round(g['g_moderado'], 6) if math.isfinite(g['g_moderado']) else '',
                                     razao_2030_2025=round(g['razao'], 6) if math.isfinite(g['razao']) else ''))
            aprov = [l for l in pres if l in res and res[l][0] == 'APROVADO']
            cont['completas_defensaveis'] += completa and len(aprov) == 2
            if completa and len(aprov) == 2:
                por_metrica[k]['completas_defensaveis'] += 1
            if completa:
                por_metrica[k]['completas_publicadas'] += 1
            if any(res[l][0] != 'APROVADO' for l in res):
                for i, ano in enumerate(ANOS):
                    longas.append(dict(commit=sha[:7], DIST=d, conceito=k[0], ativo=pm.get('ativo', ''), metrica=k[1], unidade=pm['unidade'], ano=ano,
                                       conservador=s['conservador'][i] if s.get('conservador') else '', moderado=M[i],
                                       agressivo=s['agressivo'][i] if s.get('agressivo') else '',
                                       ordem_conservador=res['conservador'][2][i] if 'conservador' in res else '',
                                       ordem_agressivo=res['agressivo'][2][i] if 'agressivo' in res else '',
                                       estado_conservador=res['conservador'][0] if 'conservador' in res else '',
                                       estado_agressivo=res['agressivo'][0] if 'agressivo' in res else '',
                                       regras_conservador='|'.join(res['conservador'][1]) if 'conservador' in res else '',
                                       regras_agressivo='|'.join(res['agressivo'][1]) if 'agressivo' in res else ''))
    def wcsv(nome, linhas):
        with open(saida / nome, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0]))
            w.writeheader()
            w.writerows(linhas)
    wcsv(f'EXTREMOS_PUBLICADOS_{rotulo}.csv', extremos)
    wcsv(f'EVIDENCIA_ANUAL_{rotulo}.csv', longas)
    resumo_m = [dict(conceito=k[0], metrica=k[1], **{c: v[c] for c in ('extremos', 'APROVADO', 'LADO_OPOSTO', 'IDENTICO', 'CRUZA', 'DIFERENCA_IMATERIAL', 'IMPLAUSIVEL',
                                                                         'completas_publicadas', 'completas_defensaveis')}) for k, v in sorted(por_metrica.items())]
    wcsv(f'RESUMO_POR_METRICA_{rotulo}.csv', resumo_m)
    out = dict(commit=sha, blob_json=blob, arquivo=JSON_PUB, schema=pub.get('schema_version'), contagens=dict(sorted(cont.items())))
    (saida / f'RESUMO_{rotulo}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:])
