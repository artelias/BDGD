"""Gabarito científico é somente oráculo de teste, nunca fonte de seleção."""
import csv
from .fontes import PESQUISA
from .qualidade import LADOS


def comparar(produto, audit, modo):
    expected = {(r['conceito'],r['metrica'],r['DIST']):r for r in csv.DictReader((PESQUISA/'02_MATRIZ_SERIES_CENARIOS.csv').open(encoding='utf-8'))}
    op={'originais':'so_originais','otimizados':'originais_otimizados','condicionais':'gateB'}[modo]
    cl={'originais':'classe_gateB_so_originais','otimizados':'classe_gateB_originais_e_otimizados','condicionais':'classe_gateB'}[modo]
    errors=[]; compared=0
    for m in produto['metricas']:
        for d,s in m['series'].items():
            key=(m['conceito'],m['metrica'],d); e=expected[key]; compared+=1
            if s['completude'] != e[cl]:
                errors.append(dict(chave=key,campo='completude',esperado=e[cl],obtido=s['completude']))
            for side in LADOS:
                model=(s['extremos'][side] or {}).get('modelo','')
                wanted=e.get(f'{side}_{op}_modelo','')
                if model != wanted:
                    errors.append(dict(chave=key,campo=side+'_modelo',esperado=wanted,obtido=model))
                value=s[side][-1] if s[side] else None
                want_value=e.get(f'{side}_{op}_2030','')
                tol=1 if m['natureza']=='discrete_count' else .001+1e-9
                if (value is None) != (not want_value) or (value is not None and want_value and abs(value-float(want_value))>tol):
                    errors.append(dict(chave=key,campo=side+'_2030',esperado=want_value,obtido=value))
    # A auditoria 06 só persiste P1 e o vencedor final da pesquisa (que inclui N).
    # Compara os registros sobrepostos e contabiliza explicitamente os demais.
    lookup={(r['CONCEITO_ID'],r['METRICA'],r['DIST'],r['lado'],r['modelo'],r['etapa']):r for r in audit}
    n06=0; unshared=0
    for e in csv.DictReader((PESQUISA/'06_AUDITORIA_PLAUSIBILIDADE.csv').open(encoding='utf-8')):
        stage='P1' if e['origem_extremo']=='PUBLICADO' else e['origem_extremo'].replace('FINAL_','')
        key=(e['conceito'],e['metrica'],e['DIST'],e['lado'],e['candidato'],stage)
        a=lookup.get(key)
        if a is None:
            unshared+=1
            continue
        n06+=1
        if a['estado']!=e['estado']:
            errors.append(dict(chave=key,campo='estado_06',esperado=e['estado'],obtido=a['estado']))
        for q in ['Q'+str(i) for i in range(1,10)]:
            if e[q] and a['regras'].get(q)!=(e[q]=='True'):
                errors.append(dict(chave=key,campo=q,esperado=e[q],obtido=a['regras'].get(q)))
    return dict(series_comparadas=compared,auditorias_comparadas=n06,auditorias_fora_do_escopo=unshared,divergencias=errors)
